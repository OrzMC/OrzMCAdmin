# OrzMC 权限系统（rank-promotion 二期）细节

仓库：`~/OrzMC/plugin`（分支 feat/rank-promotion，PR #160 → 1.0.16）
方案/验收文档：`docs/permission-system-v2.md` + `-acceptance.md`（与代码同步维护）

## 四级 track 与中文名

`default→member→builder→admin`（LP track 名 `rank`）。中文名唯一事实源 `RankService.groupDisplayName()`：访客/成员/建造者/管理员，组外回退访客。$l 在线列表、广播、rank 通知、/rank、$p 反馈全走此方法。

## 状态展示矩阵（/rank 与 /apply 按当前组动态）

| 当前组 | /rank | /apply 可申请 |
|:--|:--|:--|
| default | 时长 + 晋升成员阈值进度（还需 X / ✅已达标）+ 「下一步：在线时长达标后自动晋升为成员」 | 无 |
| member | 时长 + 阈值（✅已达标）+ 「下一步可申请：晋升建造者（/apply builder）」 | 晋升建造者 |
| builder | 时长（不展示已完成的 member 阈值）+ 「下一步可申请：晋升管理员（/apply admin）」 | 晋升管理员 |
| admin | 时长 + 「已达最高等级（管理员）」 | 无 |

「下一步可申请」由 ReviewType 注册表反向生成（资格预检通过的项），不硬编码。

## 审核框架（features/review/）

- ReviewType 注册表驱动：`builder-promotion`（member→builder）+ `admin-promotion`（builder→admin）；handler 由 rank 模块注入（LP 授权），review 包零 LP/宿主依赖
- 群指令 `$v l/y/n <玩家>`（待审列表含当前组）；游戏内 `/apply`（列表按资格过滤）+ `/review approve|reject`
- 审核通过 = `rankService.promote(playerId) != null`（null=链顶/LP 异常 → 保持 PENDING，避免「已通过但未生效」）
- 群通知 4 环节模板键：review_submitted/cancelled/approved/rejected + rank_promoted/rank_demoted
- 玩家结果三层兜底：游戏内消息 → 群通知 → /apply status
- $h 帮助与 $cmd ? 用法：BotCommandFeedbackService.helpInfo 硬编码拼接 + usageTip switch——加新指令须同步两处（曾漏 $v/$p）

## 管理员私信（PRIVATE）场景（admin_dm 目标）

Notifier.routeEvent 按模板键路由，PRIVATE 仅 3 键：exception_alert（插件/GeoIP 异常，带 ThrottledNotifier 节流）、maintenance_backup_error、maintenance_optimize_error。其余全 PUBLIC 群消息。server_maintenance_hint（最后一人退出提示维护）已移除（8ad86be，触发过频）。

## 排障案例：joker AMBIGUOUS_CALL（根因闭环）

- 现象：$p d joker 提示「无法再降级」；/rank 显示建造者（已 demote 至 default）
- 排查：`$e lp user joker parent info` 实锤 world=world/gamemode=creative 上下文的 builder+member 组——一期 $p 用玩家实时上下文操作产生（LP 把节点存为完整上下文快照）
- 修复链：① 数据清理无上下文叠加组（治标）→ ② 代码统一 global 上下文（治本，63dc5ef）→ AMBIGUOUS_CALL 消失；$p u 不在 track 的玩家连续 promote 直达 member
- 教训：看到 AMBIGUOUS_CALL 先查 parent info 看是否有带上下文/重叠节点；别再只当「边界提示」处理

## 测试环境

- 本地服 ~/minecraft-server（enable-rcon=true, 25575）；部署链：kill java → cp build/libs/OrzMC-1.0.16-dev.jar → rm world/session.lock → start.sh（~50s Done）
- RCON 驱动 orzdebug 模拟群消息：~/minecraft-bot/p-test.js（`$p` 参数须单引号防 shell 展开）
- bot 玩家登录跑游戏内命令：rank-single.js / cmd-one.js（自动 /login，LoginSecurity 有 30s 重登冷却）
- 测试账号：TestMember=81b4d507…、HermesBot=74ce0d95…、joker=bbb8b47e…（密码在脚本内，勿外泄）
- 门禁：./gradlew spotlessApply + check + shadowJar（CI Java 25）
