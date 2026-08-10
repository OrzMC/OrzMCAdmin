# 权限状态展示动态化 + LP track 数据卫生（2026-08-07 权限二期收尾实测）

## 1. 四级流转状态矩阵（/rank 与 /apply 按当前组动态）

权限链 default→member→builder→admin 完整闭环：
- default→member：**自动晋升**（stats 时长达标，上线时 checkPromotion）
- member→builder：申请审核（BUILDER_PROMOTION，`/apply builder`）
- builder→admin：申请审核（ADMIN_PROMOTION，`/apply admin`——**2026-08-07 补全**，否则 builder 是死胡同）

| 当前组 | /rank 展示 | /apply 可申请 |
|:--|:--|:--|
| default | 时长 + 晋升成员阈值进度（还需 X / ✅已达标「下次上线将自动晋升为成员」） + 「下一步：在线时长达标后自动晋升为成员」 | 无 |
| member | 时长 + 阈值（✅已达标） + 「下一步可申请：晋升建造者（/apply builder）」 | 晋升建造者 |
| builder | 时长（**不再展示已完成的 member 阈值**） + 「下一步可申请：晋升管理员（/apply admin）」 | 晋升管理员 |
| admin | 时长 + 「已达最高等级（管理员）」 | 无 |

**设计原则**（用户两次纠正定案）：
- 已完成的事不再展示（builder/admin 不显示 member 阈值行）
- 展示与当前状态严格匹配：builder 玩家不得看到「申请 builder」、不得看到 member 时长条件
- 「下一步可申请」由 ReviewType 注册表**反向生成**（`isEligible` 过滤）——与审核类型天然同步，新增类型零展示层改动
- `/apply` 列表同样按 `isEligible` 过滤；空列表给通用文案「当前没有可申请的审核类型。」

实现位置：`RankCommandService.statusOf()` 的 switch 分支 + `ReviewCommandService.listTypes()` 的 filter。
分层注意：ReviewCommandService 在 review 框架包内，**不能依赖 RankService**（框架零宿主依赖）——引导文案放 /rank（有 RankService），/apply 只做资格过滤 + 通用空提示。

## 2. LP API 无 TrackNode——叠加组干扰判定（joker 实证）

**事实**（unzip LP api jar 实锤）：`net.luckperms.api.node.types` 只有 InheritanceNode/WeightNode/MetaNode 等，**没有 TrackNode**。track 组在用户身上就是**普通继承节点**（InheritanceNode），track 关系只存在于全局 `Track` 对象（组列表）。

**推论**：`currentTrackGroup` 按「`user.getInheritedGroups()` ∩ `track.getGroups()`」取最高位是官方标准做法，但**代码无法区分**「track 给的组」与「手动 `parent add` 叠加的同名组」。

**故障链（实测）**：joker 有叠加的 builder 组（`lp user joker parent info` 显示 `> builder` 无 track 标注）→ `$p d joker` 三次降级到 default（日志 demote SUCCESS）→ /rank 和 `$l` 仍显示「建造者」（继承组匹配把叠加组当 track 组）。

**唯一正解 = 数据清理 + 规范**（代码层面无解，别浪费时间找 API 区分）：
```bash
lp user X parent info        # 定位：看 parents 里无 track 标注的同名组
lp user X parent remove <组> # 清理叠加组
```
**规范**：权限组只经 `$p u/d`（track）升降级管理，禁止 `lp user X parent add` 叠加——叠加组是体系外数据，会造成权限实际状态与 /rank 显示脱节 + 双写漂移风险。

## 3. AMBIGUOUS_CALL 两个场景

LP promote/demote 返回 `AMBIGUOUS_CALL`（当前实现返回 null → 提示「已在最高/最低等级」，**误导**）：
1. **叠加组**：手动 parent add 的组与 track 组并存（旧场景）
2. **track 节点重叠**：同一玩家同时持有两个 track 组节点（如 builder+member 并存，测试数据脏）——2026-08-07 实测 TestMember

诊断：`lp user X parent info` 看 parents 列表；修复 = `parent remove` 多余节点（保留最高位组）。
日志特征：`[OrzMC.LP] demote(uuid) -> AMBIGUOUS_CALL`。

## 4. 帮助注册单一事实源（$h / $cmd ?）

- `helpInfo` 若手工 `+ OrzUserCmd.X.display()` 拼接 → 新增枚举项后 $h 不自动包含（本会话 $v/$p 漏注册）
- **正确**：帮助列表由枚举 `values()` 遍历生成，或至少补全拼接
- `usageTip` switch 漏 case → `$cmd ?` 静默降级为**直接执行**（`?` 当参数执行，无提示）——新增指令必须补 usageTip case
- 验收：`/orzdebug $h`、`/orzdebug $v ?`、`/orzdebug $p ?` 输出（群侧反馈在服务器日志 cmd debug 段）

## 5. 全面转向外部权威源后的一期残留清理模式

LP track 接管权限状态后，以下「本地兜底」应清理（用户要求「统一清理干净」）：
- **无 LP 时的本地推断**：`hasApprovedBuilder`（按审核记录推断组）→ 删除，无 LP 一律回退 default（访客）——虚假展示比不可用更糟；顺带解除 RankService 对 ReviewStore 的依赖
- **命令面分裂**：`/rank demote` 与群侧 `$p` 并存 → 统一 `$p`（群升降级）+ `/review`（游戏内审核）+ `/rank`（纯查询）
- **死占位符/死条目**：模板 fallback 里的 `{role_alias}`、占位符白名单里的 role_alias（配置已删但 fallback 没删，新装服务器原样输出）
- **过时注释**：描述一期结构（「三段式」「/rank [approve|reject]」）的注释同步更新

清理原则：权限状态判定 100% LP 单一事实源；「配置最少记录、可推导不落盘」。
