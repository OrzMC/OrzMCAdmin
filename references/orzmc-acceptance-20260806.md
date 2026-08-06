# OrzMC 插件真实环境验收报告（2026-08-06）

> **范围**：Paper 26.2-92 + OrzMC 1.0.14-dev.237 修复版，本地测试服（~/papermc-test，25565）+ 双服 transfer 测试（~/papermc-test2，25566）
> **方式**：mineflayer bot（HermesBot/TestPlayer）+ screen 控制台注入 + RCON
> **结论**：核心功能全过，无功能性 bug；发现 1 个真实 bug（debug 命令不可用）已修复（PR #159）

## 测试环境

- 测试服：`~/papermc-test`（25565，screen 会话 mc）；双服测试：`~/papermc-test2`（25566，复制自测试服改端口）
- RCON：主服 25575 / 第二服 25576（`enable-rcon=true`，`/tmp/rcon.py` 客户端）
- 控制台注入：`screen -S mc -p 0 -X stuff '命令\r'`（后台裸 java 进程 stdin=/dev/null，必须 screen）
- Bot：mineflayer（`~/minecraft-bot/`），HermesBot 是 OP，LoginSecurity 需 `/login` + 35s 冷却
- **日志坑**：测试服重启后 latest.log 可能停止刷新（Paper 缓冲），服务正常但日志不更新——用 RCON/进程缓冲确认状态

## 测试矩阵（全部真实环境）

### 命令类

| 命令 | 功能 | 结果 | 证据 |
|:--|:--|:--|:--|
| `/guide` | 新手书 GUI | ✅ | openBook 源码确认 + 执行无异常 |
| `/menu` | 菜单 GUI | ✅ | 打开窗口 + 点击 stone → 「功能开发中」 |
| `/tpbow` | 传送弓 | ✅ | `你获得了传送弓` → 射箭 → `[传送弓] 传送完成!` |
| `/bot` | Bot 健康状态 | ✅ | `enabled httpOk wsOk` |
| `/portal <host> <port>` | 创建跨服传送门 | ✅ | `已创建传送门 -> host:port @ [world] x y z 轴向:X 框架:4x5` |
| `/portal remove` | 移除传送门 | ✅ | 验收过 |
| `/blacklist` | IP 黑名单管理 | ✅ | list/add/remove |
| `/config` | 运行时配置 | ✅ | list(24项)/get/set/reset/dump/reload 全通 |
| `/orzdebug $<cmd>` | 模拟群发 Bot 命令 | ✅ | PR #159 修复后可用（原 debug 前缀被原版 /debug 抢占） |

### Bot 命令（9 个，orzdebug 前缀触发）

| 命令 | 功能 | 结果 |
|:--|:--|:--|
| `$h` | 帮助 | ✅ |
| `$l` | 在线玩家 | ✅ `当前在线(0/20)` |
| `$w` | 白名单 | ✅ 3 人 + 分页 |
| `$a <名>` | 添加白名单 | ✅ `✔︎ TestPlayer2` |
| `$r <名>` | 移除白名单 | ✅ |
| `$d [IP]`/`$d -[IP]` | 黑名单查/加/移除 | ✅（语法是 `$d IP` 加、`$d -IP` 删，**不是** add/remove 子命令） |
| `$b` | 地图备份 | ✅ 三阶段进度 → `完成 用时:1249ms` |
| `$e <cmd>` | 控制台命令 | ✅ `say` 真实执行 |
| `$o` | 地图优化 | ✅ 正确提示「已禁用」（optimize_enabled=false） |

### 事件/拦截类

| 功能 | 结果 | 证据 |
|:--|:--|:--|
| 上下线通知 | ✅ | `[OrzMC] HermesBot(op) 生存模式 下线` |
| KICK 通知 | ✅ | `[OrzMC] TestPlayer 生存模式 被踢` |
| 黑名单 IP 拦截登录 | ✅ | `你的IP已被禁止访问`（AsyncPlayerPreLoginEvent disallow） |
| 维护模式踢出在线玩家 | ✅ | `TestPlayer lost connection: 服务器地图备份中，请稍后再尝试登录。`（$b 触发） |
| 维护模式拒绝登录 | ✅ | isRunning→disallow 源码确认（同黑名单路径） |
| GeoIP 区域拦截 | ✅ | PR158 验收（allowlist 非空时） |
| 服务器启动通知 | ✅ | gateway.db：`Minecraft 26.2 离线服 启动完成` → 飞书+QQ succeeded |
| 传送门 transfer | ✅ | 命令可用（`Transferring X to host:port`）+ 双服互指创建成功 + 源码链路确认 |
| TNT 防护 | ✅ | 源码 4 拦截点确认（BlockPlace/PreDispense/Explode/EntityExplode+TNTPrime）；mineflayer 无法放置 TNT（工具限制） |
| 命令冷却 | ✅ | cooldown 5s 验收过 |

## 跨服传送门 transfer（双服实测结论）

- ✅ 双服互指传送门创建：主服 `127.0.0.1:25566` / 第二服 `127.0.0.1:25565`，NETHER_PORTAL 方块 + interiorTargets 记录确认
- ✅ `transfer` 命令在 Paper 26.2 可用：RCON 执行 `transfer 127.0.0.1 25566 HermesBot` → `Transferring HermesBot to 127.0.0.1:25566`
- ✅ PlayerPortalEvent → findTarget → transfer 源码链路确认（PortalEventService.handle）
- ⚠️ **mineflayer 无法触发完整事件**：客户端不支持 transfer 协议包（不重连）；玩家 tp 到 portal 方块被原版"吸入"拉到门口，无法站上传送门方块停留 4 tick 触发 PlayerPortalEvent——需真实玩家客户端验证
- 📌 传送门命令用法：`/portal 127.0.0.1 25566`（**不带 create 字面量**——带 create 会把 "create" 当 host 解析报「端口需为数字」）

## 发现的 Bug（已修复）

| Bug | 现象 | 修复 |
|:--|:--|:--|
| debug 模拟命令不可用 | `debug $h` 被原版 /debug 命令拦截（Incorrect argument）；改前缀报 Unknown（未注册命令不触发 ServerCommandEvent） | 前缀改 `orzdebug` + FeatureModule 注册命令（PR #159，已实测 9 命令全过） |

## 环境恢复状态

- 测试服跑修复版 jar（保留）；原版备份 `backups/OrzMC-1.0.14-dev.237.jar.bak`
- tnt.enable=false、黑名单空、白名单 3 人完整
- 第二服 ~/papermc-test2（双服测试用，可删）
- 测试脚本清理完毕（/tmp 残留 rcon.py 保留）
