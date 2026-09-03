# OrzMC Bot 命令测试 & 控制台注入（2026-08-06 实测）

## 群指令帮助系统（2026-08-13 改版，PR OrzGeeker/OrzMC#12，源码 1.0.17 起）

**老板定稿样式（改版后，别再用下面的旧输出做断言）**：
- **`$h` 总帮助**：`🤖 OrzMC 群指令帮助` + `发送「$x ?」可查看单个指令的用法示例` + ASCII 虚线分隔（`-----------------------------------------`，与其他消息一致）+ emoji 分组标题 `👨‍💼 管理员指令` / `👨🏻‍💻 通用指令`（**无中文方括号、无冒号尾缀**）+ 命令列表（10 半角空格对齐，如 `$a          添加玩家到白名单`）
- **`$x ?` 单命令帮助**：统一三段式模板（`BotCommandFeedbackService.usageBlock()` 单一生成器）：
  ```
  🎯 $v 审核申请
  -----------------------------------------
  📚 用法：
  $v l [页码]       查看待审列表
  $v y <玩家>       通过申请
  $v n <玩家>       拒绝申请
  -----------------------------------------
  🚀 示例：
  $v l
  $v l 2
  $v y Steve
  ```
- **参数标记语义**：必选 `<玩家>`/`<控制台命令>`，可选 `[页码]`/`[IP]`（`$d` 无参=查看，`[IP]` 属可选操作数）
- **11 命令全有 usageTip**（含 `$l/$w/$h/$b/$o`），`$cmd ?` 永不降级执行

**`$cmd ?` 拦截语义（源码 BotCommandService.parse，防误触核心）**：
- **前缀匹配**：`$b ?x`/`$b ??`/`$b ? 2` 均视为帮助请求（`rawArgs.startsWith("?")`）——因 `handleBackup`/`handleOptimize` 忽略 rawArgs 直接执行，精确匹配会让 `?` 后缀变体误触发重量级操作
- **`$e` 特判精确匹配**：控制台命令本身可能以 `?` 开头（`$e ?list` 合法）→ 仅 `$e ?`/`$e ？` 是帮助
- **U+3000 全角空格归一化**：`extractArgs(...).replace('\u3000', ' ').trim()`——Java `String.trim()` 不去全角空格，`$b　?`（全角空格分隔）会绕过拦截直接触发备份（Claude Code 审查 M1 发现，已修）
- **fallback 收敛原则**：无参数/参数不完整（`$p` 空参/缺玩家/非法子命令、`$v` 空参/非法、`$a` 空名、`$e` 空参）一律 `emitUsage(usageTip(...))` 与 `$x ?` 同源，**绝不降级为执行命令**
- **非管理员 `$b ?`**：拦截先于 `guardAdminCommand`，非管理员也先拿帮助（信息面略扩大，有意为之）

**回归测试**：`BotCommandServiceTest` 有 10 个 parse 层用例（`$b ?`/`$o ?` 零执行 backup/optimize、fallback 文本 == usageTip、`$e ?list` 正常执行）；`BotCommandFeedbackServiceTest.usageTip_forEveryCommand_usesUnifiedTemplate` 双前缀（`$`/`!`）断言。

## 🔧 扩展新群指令的框架（2026-08-07 权限系统方向调研）
用户问「权限指令能否走群指令执行」→ 答案：**完全可以**，OrzUserCmd 枚举 + handler map 是现成扩展点（EasyBot 网关已接 QQ/飞书）。扩展一个群指令三步：
1. **`OrzUserCmd.java` 加枚举**：`NEW_CMD("x", "描述", needAdminPermission)` —— 第三个参数 `true`=仅群管理员（isAdmin，来自 EasyBot 群角色）可执行
2. **`BotCommandService` 注册 handler**：`handlers.put(OrzUserCmd.NEW_CMD, this::handleNewCmd)`，handler 签名 `(OrzUserCmd cmd, boolean isAdmin, Consumer<MessageEnvelope> callback, String rawArgs)`；`rawArgs` = 去掉 `$x` 前缀后的参数
3. **`BotCommandFeedbackService.usageTip` 加提示**（支持 `$x ?` 查询）
关键设计点：**群 isAdmin 与游戏内 LP admin 组是两套身份体系**——群审核类命令（如 `$approve`）用群管理员身份即可，无需绑定游戏 UUID。`$e`（执行控制台命令）已能间接操作 LP（`$e lp user X parent add builder`）但无校验、易出错——专用群指令（如 `$rank <名>` 查询 / `$approve <名>` / `$reject <名>` 审核）是更优交互。注意：`$d` 黑名单用 `-` 前缀表移除（`rawArgs.startsWith("-")`），设计新命令避免撞此约定。

## 背景
OrzMC 插件的 Bot 命令（`$l/$w/$h/$a/$r/$b/$o/$e/$d`）正常由**真实群消息**触发（EasyBot WS 推送 message.inbound → `BotInboundDispatcher.dispatch` → `BotInboundHandler.handleMessage`）。插件另提供 `debug <cmd>` 控制台命令模拟群里用户发命令（`OrzDebugEvent.cmdDebugHandler` → `ServerCommandEvent` → 异步 `handleMessage`）。

## ⚠️ Bug：debug 命令在 Paper 26.2 完全不可用（✅ 已修复，PR #159）
**现象**：控制台输入 `debug $h` → `Incorrect argument for command`；改任意其他前缀（如 `debugx`）→ `Unknown command`。
**根因（两层）**：
1. Paper 1.20+ 有**原版 `/debug` 命令**抢占 `debug` 前缀 → 参数解析在事件前失败
2. **未注册的命令根本不触发 `ServerCommandEvent`**（RCON/玩家通道也一样）——事件只在已注册命令执行时触发
**修复（源码级，两处）**：
1. `OrzDebugEvent.java`：前缀 `"debug"` → `"orzdebug"`（避开原版命令）
2. `FeatureModule.java` setupCommandHandlers：**注册 `orzdebug` 命令**（Brigadier，greedyString 参数）——否则命令解析器不放行，事件不触发
3. `OrzDebugEventTest.java`：断言同步改 `orzdebug`（旧前缀测试会挂——`spotlessApply test` 全绿是提 PR 前的必过门禁）
**教训**：`OrzDebugEventTest` 单元测试用 Mockito mock 直接调 handler，**绕过了真实命令解析**，掩盖了此问题——源码 bug 修完必须真实环境验证（控制台注入实测），单元测试通过≠可用。PR 已提：github.com/OrzMC/OrzMCPlugin/pull/159（分支 fix/orzdebug-command）。

## 🔧 控制台注入技术（测 ServerCommandEvent / 控制台命令）
**关键事实**：`ServerCommandEvent` **只对真实控制台 stdin 输入触发**：
- ❌ RCON 命令：不触发（Essentials 记录的 "Rcon issued server command" 是 Essentials 自己监听，非 Bukkit 事件）
- ❌ 玩家 `/cmd`：走 PlayerCommandPreprocessEvent，不触发
- ❌ Hermes 后台进程 stdin：`/dev/null`（`lsof -p <pid> | grep 0u` 可见），`process write` 报 "stdin not available"
- ✅ **screen 会话**：`screen -S mc` 起服 + `screen -S mc -p 0 -X stuff '命令\n'` 模拟真实控制台输入（实测 `say`/`orzdebug` 均生效）

**命令**：
```bash
# 2026-09-03 迁 MCSM 后：起服 = 面板启动实例（无 screen/start.sh）
# orzdebug 注入 = bot 玩家游戏内执行 /orzdebug（Paper 26 Brigadier 命令不触发 RCON 事件；RCON 直连见 scripts/rcon.py）
```
注意：`screen -X hardcopy` 在 detached 模式下可能输出空文件；判断命令生效看 `logs/latest.log`（如 `[OrzMC] cmd debug:`）。

## RCON 辅助（远程查询用）
测试服默认 `enable-rcon=false`。需要时：server.properties 改 `enable-rcon=true` + 设 password + 重启。macOS 无 mcrcon → 用 Python 原生 RCON 协议（**必须完整读响应包**：先 recv(4) 长度 → 循环读满；RCON 会先发空包再发响应，v1 只 recv 一次会漏输出）。`say`/`list`/`bot` 等已注册命令可经 RCON 执行（但**不触发** ServerCommandEvent——见上）。

## OrzMC Bot 命令测试矩阵（via `orzdebug <cmd>`，9/9 实测通过 2026-08-06）
| 命令 | 用途 | 实测输出 |
|:--|:--|:--|
| `$h` | 帮助 | ✅ `🤖 OrzMC 群指令帮助` + `发送「$x ?」可查看单个指令的用法示例`（2026-08-13 改版后样式，见上「群指令帮助系统」节） |
| `$l` | 在线玩家 | ✅ `------当前在线(0/20)------` |
| `$w` | 白名单 | ✅ `------当前白名单玩家(N)------` + 分页 |
| `$a <名>` | 加白 | ✅ `✔︎ <名>`（写操作，测完必须 `$r` 还原）|
| `$r <名>` | 移白 | ✅ 移除确认 |
| `$d` | IP 黑名单 | ✅ 查/加/移除全通 |
| `$b` | 地图备份 | ✅ 三阶段进度（CopyMiscProgress→Compress→Cleanup）→ `地图备份 完成 用时:1249ms` |
| `$e <cmd>` | 控制台命令 | ✅ `命令已执行: say 群测命令` + 服务器实际广播 `[Server] 群测命令` |
| `$o` | 地图优化 | ✅ `地图优化功能已禁用`（optimize_enabled=false 时正确提示）|

⚠️ **`$d` 语法坑**：**不是 `add/remove` 子命令**——`$d IP` = 添加、`$d -IP` = 移除、`$d`（空参）= 查询。实测 `$d add 9.9.9.9` 会被当作「添加名为 'add 9.9.9.9' 的黑名单项」（输出 `已添加: add 9.9.9.9`，产生脏数据），需用 `$d -add 9.9.9.9` 清理。源码：BotCommandService.handleBlacklist——`rawArgs.startsWith("-")` 走移除，否则走添加。

调试输出在 `logs/latest.log` 的 `[OrzMC] cmd debug:` 行（env.message() 内容，多行）。

## 相关链路（EasyBot WS）
- `ws_server` 连不上时 `/bot` 显示 `wsNotOk`；连上后 `wsOk`。`/bot http` `/bot ws` 看详情
- `httpUnknown` = HTTP 健康检查异步未完成（设计状态，非 bug）
- 群通知发送失败看投递诊断（`scripts/easybot_deliveries.py`，0.0.33 起走 API 查 `messages` 表；勿再用 docker cp 查 `outbound_deliveries`——已停止写入）——`11244 token not exist or expire` = QQ token 2h 过期（0.0.33 CachedTokenStore 发送时自动刷新，通常自愈；仍失败可重启 adapter `POST /api/v1/adapters/qq/start`）

## 其他命令补测（同批 2026-08-06，均通过）
- **`/config`**（控制台可测，screen 注入）：`list`（24 项可运行时配置）/ `get <路径>`（值+类型+默认+说明）/ `set <路径> <值>`（持久化，输出 `已设置: ...`）/ `reset <路径>`（恢复默认，输出 `已恢复默认: ...`）/ `dump`（完整配置树含默认值）/ `reload`（`所有配置文件已重新加载`）/ 无参数（用法帮助）。⚠️ 改 `tnt.enable` 等运行时配置**即时生效无需重启**（`currentPolicy()` 每次实时读 configs）——测完必须 set 回原值
- **`/guide`**：打开书 GUI（`GuideService.openGuide` → `player.openBook`），玩家命令（RCON 会 ClassCastException，因为 `(Player) sender` 强转）——mineflayer 看不到书内容，判定看无异常+源码
- **`/menu`**：打开菜单 GUI（`MenuCommandService.handle` → `openMenu`），同样必须玩家身份执行
- **mineflayer 放置方块受限**：`placeBlock` 对 TNT 和对照 dirt 均失败（blockUpdate 超时，出生点区域无领地 claim 但工具仍失败）——TNT 放置保护实测受限，判定靠源码 4 拦截点（BlockPlace/BlockPreDispense/BlockExplode/EntityExplode）+ TNTPrime；`summon tnt` 也不触发通知链。工具限制非插件问题

## 第二批补充真实测试（同批 2026-08-06，全部通过）

第一批覆盖 Bot 命令/命令类；本批补登录拦截链 + 通知链路 + 菜单交互（全部真实环境实测）：

| 测试项 | 方法 | 结果 |
|:--|:--|:--|
| **黑名单 IP 拦截登录** | `orzdebug $d 127.0.0.1` 加黑 → 新 bot 登录 | ✅ 被踢，reason JSON 逐字 = `你的IP已被禁止访问`（AsyncPlayerPreLoginEvent disallow，与源码 `styles.error` 一致）。测完 `$d -127.0.0.1` 移除 |
| **维护模式踢出在线玩家** | bot 在线时触发 `orzdebug $b` | ✅ 日志 `TestPlayer lost connection: 服务器地图备份中，请稍后再尝试登录。` + `[OrzMC] TestPlayer 生存模式 被踢`（KICK 通知）→ `下线`（QUIT 通知）|
| **server_load 启动通知** | 查 gateway.db | ✅ 每次重启后飞书群+QQ 群均收到 `Minecraft 26.2 离线服\n------\n启动完成\n\n发送 "$h" 查看支持的命令消息`，state=succeeded |
| **菜单点击交互** | mineflayer `/menu` → `windowOpen` → `clickWindow(i,0,0)` 点 stone | ✅ 收到 `功能开发中`（MenuEventService.handleClick → InventoryClickEvent 取消默认 + onClick 链路）|

**维护模式机制**（`WorldMaintenanceService.runExclusive`）：`running` AtomicBoolean 置位 → **踢出所有在线玩家**（`p.kick("服务器地图备份中...")`）→ `save-off` + `save-all flush` → 异步执行备份/优化 → `save-on` + 复位。登录拒绝走 `OrzPlayerEvent.onPlayerPreLogin` 的 `isRunning() → disallow`（与黑名单同路径）。无手动开关、无 config 开关——只能靠 `$b`/`$o` 触发窗口（备份 ~1-2s，抓窗口需 bot 提前在线等踢，登录窗口几乎抓不到，用踢出分支验证即可）。

**通知送达验证（0.0.33+）**：投递记录在 `messages` 表（`outbound_deliveries` 已停止写入）；且 SQLite WAL 下 `docker cp` 单文件漏最近提交 → **用 API**：`POST /admin/login {password}` → `GET /api/v1/messages?limit=30`（`raw_data.result.success` 判定成败；`role=Assistant` 出站）。现成脚本 `scripts/easybot_deliveries.py`。内嵌 python heredoc 会被守卫拦，写脚本文件执行。

**mineflayer 射箭坑（传送弓）**：`activateItem()` 单独调用**不触发完整射箭**（EntityShootBowEvent/ProjectileHitEvent 不触发，位置不变、日志无痕迹）——需要完整拉弓充能时序。传送弓完整链路（`/tpbow` → `你获得了传送弓` → 射箭 → `[传送弓] 传送完成!`）此前验收已过，重测射箭失败是工具时序问题非插件问题。

**测试顺序建议**：写操作（`$a`/`$d add`/`$b`）按「测前记录原值 → 测 → 立即还原」执行；`$d` 还原用 `$d -<ip>`；黑名单测试用 127.0.0.1（本机 bot 的 IP）不会误伤线上。
