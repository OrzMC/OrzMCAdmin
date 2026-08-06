---
name: minecraft-bot-mineflayer
description: "Use when 需要 Minecraft 机器人玩家（Mineflayer bot）进服执行玩家身份操作或模拟玩家。"
version: 1.0.0
author: Hermes Agent
tags: [minecraft, mineflayer, bot, nodejs, automation]
platforms: [macos, linux]
required_commands: [node, npm]
---

# Mineflayer 机器人玩家

## 使用时机
- 用户要一个 bot 玩家进服执行**玩家身份**操作（/home、/tps、/sethome、触发区块加载）
- 用户要模拟玩家活动（走动触发区块 tick）或做登录/传送链自动化测试
- MCSM command API 无法提供玩家身份（见下）时的替代方案

## 关键事实：为什么需要 bot（2026-08-04 实测）

- **MCSM command API 永远以 CONSOLE 身份执行**：`execute as X run tp ...` 会被剥成 CONSOLE 命令（日志显示 `CONSOLE issued server command: /tp`），玩家上下文丢失，`/home` 等玩家专属命令无法用控制台触发
- 需要真实玩家身份的命令 / 行为，只能用 bot 进服
- bot 是 headless，**测不了 FPS/渲染**（那是客户端显卡指标）——别用 bot 测渲染性能

## 搭建步骤（已实测：Paper 26.2 服务器，2026-08-04）

### 1. 安装
```bash
mkdir -p ~/minecraft-bot && cd ~/minecraft-bot
npm init -y && npm install mineflayer   # 实测 4.37.1
```

### 2. 版本协议（最容易踩的坑）
- 服务器是 MC 26.2（protocol 776），但 **minecraft-protocol 4.37.1 的 supportedVersions 最高只到 1.21.11**
- 用 `version: '26.2'` 直接报 `unsupported protocol version: 26.2`（minecraft-data 有 26.2 数据但 minecraft-protocol 客户端实现没跟上）
- ✅ **正解：`version: '1.21.11'`**——服务器装 ViaVersion（block-protocols 为空时不限制旧版），自动转换到 26.2

### 3. 前置条件（一次性，服务器侧）
```bash
# 白名单（Minecraft 原版命令；若装有 OrzMC 等 force_whitelist 插件，也认原版 whitelist）
whitelist add <bot名>
# 验证
whitelist list
```
- 连接地址必须用**公网游戏地址**（如 `mc.fantuantim.xyz:25565`），不是面板地址、更不是 127.0.0.1（本机可能另有测试服，会连错）
- 服务器 online-mode=false（离线模式）→ bot 用任意用户名 + `auth: 'offline'` 即可
- LoginSecurity 等登录插件：首次进服自动 `/register <密码> <密码>`（registration.enabled=true 时），之后自动 `/login`；被踢说明需手动注册
- ⚠️⚠️ **未登录时所有命令静默失败（2026-08-04 实测，最难查的坑）**：LoginSecurity 密码必须 **6-32 字符**，太短（如 `pwd`）注册被拒 → bot 未登录 → `/seed`、`/tp`、`/gamemode` 全部只显示 `issued server command` 但**无执行结果**（无输出/无报错/位置不变），像"命令被静默吞掉"。**诊断**：监听 `bot.on('message')`，出现「请输入 /login <密码>」= 未登录；已注册过必须 `/login`（发 `/register` 提示「这个账户已被注册过」）。**修复**：≥6 字符密码 + 已注册则 `/login`

### 4. 验证成功
- 服务器日志：`X issued server command: /home` = 玩家身份成功（对比 CONSOLE 的 `[Essentials] CONSOLE issued...`）
- bot 侧输出 `[BOT] 已生成，位置: x, y, z` = 进服成功

## 关键坑链（2026-08-04 实测，按踩坑顺序）

### ⚠️⚠️ 未登录时所有命令静默失败（最难查的坑）
- **症状**：`/seed`、`/tp`、`/gamemode` 全部只显示 `issued server command` 但**无任何执行结果**（无输出/无报错/位置不变）——看起来像"命令被静默吞掉"
- **根因**：LoginSecurity 密码必须 **6-32 字符**，测试脚本用 `pwd`（3 字符）被拒 → bot 处于**未登录态** → 所有命令静默失败
- **诊断法**：监听 `bot.on('message')`，若出现「请输入 /login <密码>」= 未登录
- **修复**：用 ≥6 字符密码；**已注册过的账户必须 `/login`**（发 `/register` 会提示「这个账户已被注册过」）

### ⚠️ Essentials 覆盖原版命令 → 必须用 `minecraft:` 权限域
- 服务器有 Essentials 时，`/tp` 是 Essentials 的（`teleport-safety: true` **拦截传送到空中/不安全位置**，命令执行但位置不变）
- ✅ **用 `/minecraft:tp x y z` 走原版命令绕过**（实测 `Teleported HermesBot to ...` 生效）；同理 `/minecraft:gamemode`、`/minecraft:seed`、`/minecraft:whitelist` 均可
- 实测对比：`/whitelist add X`（Essentials 被吞无反馈）vs `/minecraft:whitelist add X`（立刻生效 `Added X to the whitelist`）

### ⚠️ `bot.creative.flyTo` 在 1.21.11 下挂起
- flyTo 等服务器 ack，ViaVersion 场景下不 resolve → **永远卡住**
- **别用 flyTo 移动，用 `/minecraft:tp` 命令**（玩家身份+OP）
- `bot.entity.position.set` 不可靠（服务器会拉回）

### ⚠️ `bot.creative` 默认不加载
- 4.37.1 需 `bot.loadPlugin(require('mineflayer/lib/plugins/creative'))`
- API 是 `setInventorySlot(slot, item, waitTimeout)`（**无 setSlot/getSlot**）；`waitTimeout=0` 跳过 ack 等待防挂起
- item 需 `new Item(id, count)`（prismarine-item 实例，否则 `components.length` 崩溃）

### ⚠️ 搭房子用 `/setblock` 命令最可靠
- `bot.placeBlock(ref, face)` 依赖手持方块+raycast，1.21.11 下易失败（无参考方块）
- **OP 身份直接 `/setblock x y z block[properties]`**——100% 成功且逐块执行有"人在建"效果
- 门特殊处理：`oak_door[facing=east,half=lower]` + 上层单独 `half=upper`
- 模板：`templates/build-house.js`（实测 7×7×6 小屋 7/7 验证通过，含地基/墙/门/窗/屋顶 + 传送/放置逻辑）

## 接收玩家消息（2026-08-04 实测）

- ✅ **公屏消息** → `bot.on('chat', (username, message) => ...)`——任何玩家公屏说话都触发
- ✅ **私信** → `bot.on('message', ...)`——原版私信到达 bot 时消息为 `TestPlayer whispers to you: <内容>`（chat 事件**不**触发私信，只在 message 事件）
- ⚠️ **私信命令用原版 `/minecraft:tell`**：Essentials 的 `/msg`/`/tell` 需要权限（普通玩家报「你没有使用该命令的权限」）
- ⚠️ **新玩家反垃圾**：Essentials 默认新玩家须**先移动一段时间**才能聊天（`Sorry, but you have to move a little more...`）——发送消息前用 `bot.setControlState('forward', true)` 走几秒
- ⚠️ **同账号重连冷却**：LoginSecurity 踢出后重连报 `You must wait N seconds before logging-in again`（约 20-30s）
- 模板：`templates/listen.js`（监听 + 打印 chat/message 事件）

## 粒子包解析崩溃（26.2→1.21.11 必现，2026-08-04 本地测试服发现并修复）

- **症状**：bot 突然断线，stderr 一堆 `PartialReadError: Read error for undefined`，栈指向 `packet_world_particles → Object.Particle → f32`
- **根因**：26.2 新增粒子 ID 115(block_crumble)/116(firefly) 在 1.21.11 的 `Particle` 协议 mappings 里不存在 → protodef 读错字节 → 解析崩溃。**任何触发新粒子的动作（苦力怕爆炸/新方块粒子）都会杀掉 bot**——线上"稳定"只是没触发新粒子，属运气
- **修复（模板已内置）**：bot 启动时运行时 patch `node_modules/minecraft-data/minecraft-data/data/pc/1.21.11/protocol.json` 的 `types.Particle[1][0].type[1].mappings`，补 `"115": "block_crumble", "116": "firefly"`（映射到无数据粒子，protodef 不读附加字节）
- **验证法**：本地测试服出生点有苦力怕，bot 被炸后不再断线 = 修复成功
- ⚠️ **本地测试服验证价值**：本地出生点有苦力怕等实体，能暴露线上不常触发的崩溃路径（粒子/实体交互）——改 bot 后先本地验证再上生产
- ⚠️⚠️ **patch 115/116 后坠亡仍可能崩（2026-08-04 实测）**：`/minecraft:tp` 高空坠落死亡时仍触发 `f32 PartialReadError`（坠亡粒子可能是其他 ID 或带附加字节）。**兜底方案**：`hideErrors: true` + `process.on('uncaughtException')` 吞掉继续跑 + 死亡检测不依赖客户端解析（用 health 轮询或服务器日志）

## 模拟玩家死亡（死亡测试，2026-08-04 实测）

> 用途：测死亡类插件（DeathChest/墓碑/死亡掉落）或复现「死亡瞬间下线」类 bug。

### 死亡检测的正确姿势
- ⚠️ **`bot.on('death')` 事件不可靠**：`/minecraft:kill` 生效（服务器日志 `[HermesBot: Killed HermesBot]`）但 **death 事件不触发**（可能需 respawn 流程才发）
- ⚠️⚠️ **`bot.health` 轮询也不可靠（2026-08-05 实测）**：坠亡瞬间 health **不降到 0.5 以下**（一直显示 20，死亡消息 `fell from a high place` 都出现了 health 还是 20）——mineflayer 的 health 事件和服务器死亡状态不同步。**死亡判定最稳的是 `bot.on('message')` 捕获死亡消息文本**（`你死了`/`died`/`fell from`/`was slain`），或 kill 后用 spawn 二次触发判定
- ⚠️ **死亡后不自动重生**：mineflayer 不会点重生按钮——需主动 `bot.respawn()`（或等待），复活成功 = spawn 事件二次触发 + health 回升 >15
- ⚠️ **`/minecraft:kill` 的死亡消息可能也被吞**：kill 死亡（`Killed`）时 message 事件未必收到死亡文本（2026-08-05 实测）——用 kill 方案就靠 **spawn 二次触发**判定复活，不依赖死亡消息
- ⚠️ **OP 默认创造模式**：日志 `HermesBot(op) 创造模式`——创造模式死亡**不掉落物/不触发掉落逻辑**。测试前必须 `bot.chat('/minecraft:gamemode survival HermesBot')`
- ⚠️ **spawn 事件会重复触发**：死亡重生后 `spawn` 事件再次触发 → 脚本主逻辑会**跑多轮**（give/tp/kill 反复执行）。必须加 `started` 标志 `if (started) return; started = true;`——但**spawn 二次触发也是判定复活的好信号**（`if (started && deathPos && !respawned)` 分支）
- ⚠️ **`/minecraft:kill` vs 坠落死亡**：kill 是 OP 自杀命令，部分死亡插件（如 DeathChest）**不响应 kill 死亡**——要用真实死亡就 `tp 到高空 y=200` 自由落体（日志 `fell from a high place`）
- ✅ 坠亡=最真实的死亡制造法：`/minecraft:tp <x> 200 <z>` → 等 5-8s → message 捕获死亡消息
- ✅ **验证 `/back` 等死亡传送命令的正确姿势**：原地 kill（无坠落偏差）→ 记当前位置为死亡点 → respawn → `/back` → 对比水平距离 <3 格。⚠️ 坠落死亡会有位置偏差（落点 vs 死亡判定点），别用坠落验证 `/back`

### 检查"死亡点有没有生成 X"（避开客户端解析）
- ⚠️ **`/execute if block <x> <y> <z> <block>` 的回显发给执行者 chat，不进服务器日志**——查结果必须 `bot.on('message')` 捕获 `Successfully`/`成功`，不能 grep 服务器日志
- 3x3x3 扫描：对每个坐标发 if block 查询（chest/trapped_chest/barrel），`setTimeout 100-120ms` 间隔防刷屏
- 客户端 `bot.blockAt()` 在坠亡后易撞粒子崩溃 → 优先用服务器命令查询

### 实测结论（DeathChest 3.0.1，2026-08-05 debug 定案）
- **保持在线死亡 → 箱子正常生成**，但创建是**分步异步**且有 **~6s 延迟**：`Clearing drops...`（清掉落物）→ `Starting break animation` → `Creating death chest block` → `Spawning block crack particle` + `Resetting`（完成）。**死亡后立即查会误判"没生成"——必须等 ≥10s 再查**
- **死亡瞬间下线（kill + 800ms 内 quit）→ bug 确认**：`Clearing drops` 已清空掉落物，但 `Creating death chest block` 后玩家离线 → ③④ 步中断（无 crack/reset）→ **箱子未建 + 掉落物已清 = 物品永久丢失**。重启服务器时会出现滞留创建任务（`[null] Creating death chest block`）证明事件链中断
- 早期"三场景全部不生成"结论是**误判**（查询太早 + spawn 重复触发脚本 bug），debug 日志推翻——**判定回归必须按死亡+下线场景 + 等 15s + 查箱子**
- 开启 debug 定位：`plugins/DeathChest/config.yml` → `debug: true` → 日志见 `[DeathChest] [DEBUG]` 完整创建链；重启后滞留 `[null]` 任务 = 历史死亡事件未完成
- 候选替代 AxGraves（Hangar，Artillex-Studios，同步处理死亡事件理论上无此竞态）——替换后回归测试见 papermc 技能 `references/deathchest-regression.md`

## 自动重连架构（生产可用，模板已内置）

- `createBot()` 封装成函数，`bot.on('end')` 非主动退出时 10s 后 `createBot()` 重连
- `process.on('uncaughtException')` 兜底：粒子/PartialReadError 类错误 → 结束旧连接 + 10s 重连；未知异常才 exit
- `SIGTERM`/`SIGINT` 优雅退出（manualQuit 标志阻止重连）
- ⚠️ 别用 `const bot = createBot()` 顶层一次性创建——重连无法重新赋值；必须函数化

## 模板与参考
- `templates/minecraft-bot.js` — 完整可用脚本（**含粒子 patch + 自动重连**）：连接/自动注册/待机心跳/聊天命令（!tp !pos !stats）
- `templates/build-house.js` — OP 身份 `/setblock` 搭房子（7×7×6 小屋实测 7/7 验证通过：地基/墙/门/窗/屋顶）
- `templates/listen.js` — 监听玩家消息（chat 公屏 + message 私信），聊天交互起点
- `scripts/portal-cmd.js` — 传送门命令执行器（bot 玩家身份跑 `/portal` 系列命令，RCON 无玩家身份）：`node portal-cmd.js <端口> "<命令>"`
- `scripts/portal-probe.js` — 传送门方块探测器（blockAt 扫描 portal/obsidian/gold_block）：`node portal-probe.js <端口> <中心x> <中心y> <中心z>`
- `scripts/portal-transfer-test.js` — transfer 触发测试（跳+前进穿过 portal 方块；⚠️ 已知 mineflayer 位置同步限制不触发，仅服务端链路观察用）
- `scripts/perm-check.js` — 权限系统验证（bot 玩家身份跑 LP 查询捕获输出；RCON 不回显 LP 命令的替代方案）：`node perm-check.js <端口> [密码]`
- `scripts/perm-tier-test.js` — 权限分级测试（三档 bot 自动测 default/member/builder 的 /fly /gamemode //wand；判定=拒绝消息存在与否）：`node perm-tier-test.js <端口>`
- `references/entity-diagnostics.md` — 服务器侧实体统计与卡顿定位（/paper entity list 双计数、Spark entityCounts、选择器坑、FPS vs TPS、清理分级）
- `references/orzmc-plugin-hangar.md` — OrzMC 插件版本渠道（Hangar API / dev-pr 版本体系）+ 本地 jar 替换升级流程
- `references/plugin-sources.md` — 插件发布渠道清单（哪些插件不能从 Modrinth/Hangar 升级 + 手动渠道 + 精确 slug 验证方法）

## Pitfalls
- ⚠️ **`bot.look` 的 yaw 方向映射与直觉相反（实测）**：yaw=0 → 朝 **-z** 方向，yaw=π（≈3.14）→ 朝 **+z**。想让 bot 朝 +z 走必须 `bot.look(Math.PI, 0, true)`，朝 -z 用 `bot.look(0, 0, true)`。用错方向 bot 会背对目标跳走（传送门测试踩过）——**写移动脚本前先小步验证方向**，别假设 yaw=0 朝 +z
- ⚠️ **`setControlState('jump')` + `('forward')` 组合可让 bot 跳进上方非固体方块层**（如 nether_portal，跳跃碰撞箱顶 y≈+2 格可触及 portal 方块 y+1~+3 层）——比 `bot.creative.flyTo`/`placeBlock` 可靠；跳跃时长用 `setTimeout 350-500ms` 短跳，避免穿过去
- ⚠️ **部署目录别放 /tmp**（重启丢失）；持久化到 `~/minecraft-bot/`
- ⚠️ 长驻进程用 `terminal(background=true)` 启动，勿用 `&` 前台后台化（macOS 会拒）
- ⚠️ macOS 无 `timeout` 命令；测试限时用脚本内 `setTimeout(() => { bot.quit(); process.exit(0) }, 60000)`
- ⚠️ 同名 bot 重复连接会被顶下线；先 kill 旧进程再连
- ⚠️ 被踢时读取 `reason.toString()` 前 200 字符判断原因（白名单/注册/keepalive）
- ✅ keepalive 超时踢出是网络问题（服务器侧日志 `kicked due to keepalive timeout`），bot 重连即可
- ✅ 心跳日志间隔 60s 便于观察在线状态

## 验证
- `bot.on('spawn')` 触发 + 服务器日志玩家上线 = 进服成功
- 服务器日志 `X issued server command` = 玩家身份命令成功
