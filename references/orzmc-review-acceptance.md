# OrzMC 审核框架本地验收（2026-08-07，已全部闭环）

> 背景：权限系统二期（通用审核框架 + `$v` 群指令 + permission.yml 三段式）本地 E2E 验收。
> 验收环境：本地主服 25565（Paper 26.2，OrzMC jar 已部署最新 HEAD），mineflayer bot 进服测玩家侧，
> orzdebug 模拟群指令测管理员侧。

## 已验证通过（游戏内路径，可靠）

1. **持久化**：重启后 permission.yml 的 reviews/ranks 记录保留（markAlwaysSave）
2. **`/apply builder <理由>` 提交**：资格预检 → 防重复 → PENDING 落盘（permission.yml reviews 节可查）
3. **重复申请被拒**：`你已提交过「晋升建造者」申请，请等待管理员审核。`
4. **资格预检**：非 member（本地无 promoted 标记）→ `你不满足「晋升建造者」的申请条件。`
5. **游戏内 `/review approve <玩家>`**（主线程）：记录变 APPROVED + reviewed-at 落盘 ✅，LP 组确认 builder
   （LP info 输出 `> builder` 需连后续行抓——Adventure 组件把标题与内容分行，见 SKILL.md「LP 状态验证三手段」）

## ⚠️ 资格判定看「本地状态」不是 LP 组（验收踩坑，重要）

`RankService.currentGroup()` 判定：**有 APPROVED 的 builder-promotion 记录 = builder；有 promoted 标记 = member；否则 default**。
- **LP 组 ≠ 本地资格**：TestMember 在 LP 是 builder+member，但本地无 promoted 标记 → currentGroup=default → 被预检拒绝
- TestNewbie 已有 APPROVED 记录 → currentGroup=builder → 不能再申请 builder（合理）
- **要测「申请通过路径」需要「干净 member」**：promoted 标记 + 无 APPROVED 记录。验收时手工给 TestMember
  补了 promoted 标记（permission.yml 停服改文件）才通过预检

## ✅ 已闭环问题：群指令 `$v y <玩家>` 受理后状态不落盘（根因：Paper 26 Brigadier 不触发 ServerCommandEvent）

**现象**（干净状态复现）：`$v y TestMember` 经 orzdebug 受理后，LP 授权执行了但 permission.yml 记录保持 PENDING、文件 mtime 不变；同记录游戏内 `/review approve`（主线程）正常落盘。

**最终根因**（分层日志定位，见 SKILL.md #9 断链调试法）：**Paper 26 中 Brigadier 注册的命令（`literal(...)`）不触发 ServerCommandEvent**。
- `/orzdebug` 的 `.executes()` 正常执行（玩家收到"已受理"），但 OrzDebugEvent 监听器**永远收不到任何 ServerCommandEvent/RemoteServerCommandEvent**（旧方案"双事件注册+剥斜杠"已失效）
- 日志 `TestAdmin issued server command: /orzdebug ...` 是 Bukkit 通用命令日志，**不代表** ServerCommandEvent 触发
- **"LP 授权执行了"是上一轮游戏内 `/review approve` 测试的残留**——测试状态污染伪造"部分生效"假象（见 SKILL.md #11）

**修复**：在 Brigadier `.executes()` 里**直接调用** `botModule.botInboundHandler().handleMessage(cmd, true, callback)`（`runTaskAsynchronously` 包裹，输出打日志），不再依赖事件监听器。

**验证**（修复后实测通过）：`$v y TestMember` → 日志出现 `parse 匹配: cmd=v → handleReview 进入 → emit: command_review_result → cmd debug: 已通过` 完整链路 → permission.yml 变 `status: APPROVED + reviewer: 群管理员 + reviewed-at` → PENDING 归零。`$v l` 列表正常（`[晋升建造者] TestMember（当前组：member）：申请晋升 builder：理由（刚刚 提交）`）、`$v n` 拒绝正常（REJECTED + reviewer）、拒绝后可重新申请均验证通过。

## 第二轮补充验收（2026-08-07 晚，全部通过）

修复闭环后做了**完整验收**，覆盖群指令全链路 + 配置化：

1. `$v l` 待审列表：类型/玩家名/当前组/请求内容摘要/提交时间 全显示 ✅
2. `$v n <玩家>` 拒绝：REJECTED + reviewed-at + reviewer=群管理员 ✅；**拒绝后可重新申请**（REJECTED 不阻塞 hasPending）✅
3. `$v y <玩家>` 通过：LP `parent add builder` 执行 + APPROVED 落盘 + reviewer=群管理员 ✅
4. **阈值配置化验收**（模式详见 e2e-testing skill「配置类功能验收模式」）：permission.yml `member-threshold-hours` 10→1 → 重启 → HermesBot（106min > 60min，无 promoted 标记，LP=default）上线 → 日志 `[LP] LOG > promote rank` → LP 组 default→**member**（只升一级）→ permission.yml 写入 `promoted: true` ✅
5. **幂等**：HermesBot 再次上线**无** promote rank 日志（promoted 标记防重复晋升）✅
6. 验收后阈值恢复 10h（测试环境还原）

**测试账号状态（验收后）**：HermesBot 已 promoted（member）；TestMember 已 APPROVED（builder）+ promoted 标记保留（模拟真实晋升状态，无需还原）。

## 验收测试账号状态（改过，测完恢复注意）

- TestMember：permission.yml 手工加了 promoted 标记（验收用）→ 验收后应删除还原
- TestNewbie：LP=member+builder（多次测试叠加），有 APPROVED 记录
- HermesBot：stats 106 分钟（时长读取正常）
- 测试数据清理：markAlwaysSave 的 permission.yml **必须停服改文件**，运行中改会被关服保存覆盖（见 SKILL.md）
