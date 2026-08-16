# 机器人玩家（Mineflayer）——运维视角

> **用途**：玩家身份操作（/home、/tps）、触发区块加载、模拟玩家活动、实体统计锚点（无需真人客户端）。
> ⚠️ **bot 测不了 FPS**——headless 无渲染，FPS 是客户端指标；服务端实体统计见 `entity-statistics.md`。
> 📌 **bot 开发细节（mineflayer API、坑链、脚本模板）→ 独立技能 `minecraft-bot-mineflayer`**——本文件只保留运维需要的部分。
> 项目位置：`~/minecraft-bot/`（含 start.sh / stop.sh / minecraft-bot.js）

## 启动（运维视角）

```bash
# 线上（默认连 {SERVER_HOST}:25565）
cd ~/minecraft-bot && ./start.sh HermesBot
# 本地测试服
BOT_HOST=127.0.0.1 BOT_PORT=25565 node minecraft-bot.js
```

- 协议：**`version: '1.21.11'`** 连 MC 26.2 服（ViaVersion 自动转换）；直接写 `26.2` 报 unsupported
- 白名单：原版 whitelist（OrzMC force_whitelist 也认）；MCSM 用 command `whitelist add`，本地改 whitelist.json + 重启
- 登录：LoginSecurity 密码 **6-32 字符**；已注册账户须 `/login`（未登录时所有命令静默失败）
- 验证：服务器日志 `HermesBot issued server command: /tps`（玩家身份，非 CONSOLE）

## 运维要点

- ⚠️ **MCSM command API 转发丢玩家上下文**：`execute as HermesBot run tp ...` 会被 MCSM 当 CONSOLE 命令简化执行（日志 `CONSOLE issued server command: /tp`，玩家位置不变）——**需要玩家身份的操作必须由 bot 自己通过 mineflayer 执行**（`bot.chat('/home')`），不走 MCSM command API
- ⚠️ **有 Essentials 时原版命令加 `minecraft:` 域**：`/minecraft:tp`（绕 teleport-safety）、`/minecraft:whitelist add`、`/minecraft:tell`（私信）——详细见独立技能
- ✅ **本地测试服（papermc-test）验证价值**：本地出生点有苦力怕等实体，能暴露线上不常触发的崩溃路径（粒子/实体交互），改 bot 后先本地验证再上生产
- ⚠️ **临时验证脚本必须放 `~/minecraft-bot/` 内运行**（Node 模块解析从脚本所在目录向上找 node_modules；放 /tmp 报 `Cannot find module 'mineflayer'`）——一次性验证脚本（如经中转登录）直接 `cp` 进项目目录再 `node` 跑
- ⚠️ **登录验证脚本要素**（2026-08-14 OrzMCProxy 正式档验收实测）：`auth: 'offline'`（离线服）+ `version: '1.21.11'`（26.2 服）；监听 `spawn`（进入游戏=登录成功铁证）、`kicked`（含拒绝原因，如白名单）、`error`；30s 超时兜底；登录成功后 `bot.end()` + `process.exit(0)` 防挂死——服务器日志对应行 `test[/真实IP:port] logged in with entity id N at (...)` 就是**真实 IP 透传验证的终极铁证**（frpc PROXY v2 头场景下显示玩家真实公网 IP）
- ⚠️ bot 项目持久化在 `~/minecraft-bot/`（勿放 /tmp）

## 挂机脚本（stay-with-joker.js，2026-08-16 新增）

```bash
cd ~/minecraft-bot && BOT_COUNT=5 node stay-with-joker.js [分钟=60] [前缀=Test] [目标玩家=joker]
# 5 bot（Test01-05）登录 → RCON /minecraft:tp 到目标玩家身边 → 原地跳跃挂机
# 内置 IPv4+IPv6 分流：Test01-03 走 127.0.0.1，Test04-05 走 ::1（绕 per-IP 5 限制）
# 每 60s 报告在线数；时长到自动 quit
```

- **用途**：多 bot 挂机在指定玩家位置（如 joker 身边），模拟多人在线
- **前置**：Test01-05 已加白名单（`whitelist add`）；**已注册过的 bot 只 `/login` 不 `/register`**（重复 register 可能触发会话重建 → 被踢）
- **验证**：`rc list` 看到 Test01-05 在线 + 服务器日志 `[Rcon: Teleported Test01 to 悅咪丿 - joker]`
- 2026-08-16 实测：5/5 稳定在线 2 分钟零掉线（IPv4 3 + IPv6 2 分流）

## 压测脚本（stress-stay.js，2026-08-12/13 实测沉淀）```bash
cd ~/minecraft-bot && BOT_COUNT=10 node stress-stay.js 2   # N bot 驻留 2 分钟 + RCON 每 5s 采样 TPS
# 输出 /tmp/stress_stay_result.json（采样数组 + joined/peakOnline/avgTps/minTps）
# 环境变量：BOT_HOST/BOT_PORT/BOT_PASSWORD/RCON_PORT/RCON_PASSWORD（默认本地服）
```

- **mineflayer 选项原样透传 minecraft-protocol**（`bot._client = mc.createClient(options)`）→ 可用自定义 `connect: (client) => { client.setSocket(net.connect({host, port, localAddress: srcIp})); client.emit('connect'); }` 绑定源 IP
- ⚠️ **macOS 禁 bind 127.0.0.2+**（`OSError: [Errno 49] Can't assign requested address`；lo0 虽是 /8 掩码但内核只认 127.0.0.1，与 Linux 不同）→ 多回环 IP 模拟多玩家 **macOS 死路**（无 sudo 也加不了 lo0 alias）
- ⚠️ **vanilla per-IP 5 在线限制**：同 IP 已登录 ≥5 时第 6+ 被踢（`Sorry, there are too many players logged in with your IP address`）→ **单出口 IP 压测天花板 = 5 bot 真实在线**（40 bot 尝试全成功但峰值在线 3-6）；真实玩家各 IP 不同不受影响
- ⚠️⚠️ **同 IP 5 bot 全登录后稳定只能 3 个**（2026-08-16 实测）：5 个全走 127.0.0.1 时**后 2 个在登录成功+tp 后 3-5s 被踢**（`too many players`），Test01-03 稳定——不是登录时检查，是延迟踢出（疑似 register/login 会话重建触发计数）
- ✅✅ **IPv4+IPv6 混合绕开 per-IP 限制（2026-08-16 实测成功）**：服务器 `tcp46` 双栈监听时，**127.0.0.1 与 ::1 是不同 IP 各自 5 上限** → 5 bot 分流（Test01-03 走 `127.0.0.1`、Test04-05 走 `::1`）可**全部稳定在线**（实测 5/5 保持 2 分钟零掉线）。mineflayer `createBot({host: '::1'})` 直接可用；服务器日志显示 `[0:0:0:0:0:0:0:1]` 即 ::1 玩家。⚠️ 前提：服务器监听 `tcp46`（`netstat -an | grep 25565` 查）；若只监听 tcp4 则 ::1 不可连
- ⚠️ **tp 到真人玩家身边用 `/minecraft:tp`**（RCON 执行）：`tp <bot名> <玩家名>` 会被 Essentials 拦截（日志 `[Essentials] Rcon issued server command` 但无实际传送、RCON 无输出）；`minecraft:tp <bot名> <玩家名>` 正常（日志 `[Rcon: Teleported Test01 to 悅咪丿 - joker]`，RCON 返回 `Teleported X to Y`）
- ⚠️ **spawn 事件计数只增不减会虚高**（被踢 bot 也算"进入"）——维护 `Set` 真实在线（spawn 增 / end 减），采样打 `在线=N/总数`
- ⚠️ 压测脚本总时长 = 登录风暴（40 bot ≈ 60-90s）+ 采样 → 前台 200s 上限会超时被杀丢结果 → **用 background=true + notify_on_complete**
- 登录风暴：冷启动首登崩（TPS 4.2）、热世界不崩（40 bot 最低 16.1）→ 详见 testing.md

## 常用操作（bot 侧聊天命令，minecraft-bot.js 内置）

```bash
!tp x y z   # 传送（bot.entity.position.set）
!pos        # 报位置
!stats      # 位置+HP
```

> 机器人作为运维工具：用 bot 位置做实体统计锚点（玩家身份上下文正确）。bot 开发/坑链/模板（build-house.js 搭房子、listen.js 收消息、粒子 patch、自动重连）→ `minecraft-bot-mineflayer` 技能。
