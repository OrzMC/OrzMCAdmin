# 机器人玩家（Mineflayer）

> 用途：玩家身份操作（/home、/tps）、触发区块加载、模拟玩家活动、实体统计锚点（无需真人客户端）。
> ⚠️ **bot 测不了 FPS**——headless 无渲染，FPS 是客户端指标；实体统计见 `entity-statistics.md`。

## 搭建步骤（2026-08-04 实测）

```bash
# 1. 安装（Node ≥ 18）
mkdir -p ~/minecraft-bot && cd ~/minecraft-bot
npm init -y && npm install mineflayer@4.37.1

# 2. 脚本（模板见 scripts/bot/minecraft-bot.js，含粒子 patch + 自动重连）
#    核心逻辑：createBot({host, port, username, auth:'offline', version:'1.21.11'})
#    spawn 后自动 bot.chat('/register <pwd> <pwd>')（LoginSecurity）

# 3. 白名单（Minecraft 原版即可；部分自定义白名单插件也认原版 whitelist）
#    控制台: whitelist add <bot用户名>
#    本地文件: 改 whitelist.json + 重启（运行时改不生效）

# 4. 启动
cd ~/minecraft-bot && ./start.sh <用户名>
```

## 关键坑（2026-08-04 实测）

- ⚠️ **协议版本**：服务器 MC 26.2（protocol 776），但 mineflayer 4.37.1 的 minecraft-protocol 只支持到 1.21.11 → **用 `version: '1.21.11'` 连接，ViaVersion 自动转换**。直接写 `version:'26.2'` 报 `unsupported protocol version`
- ⚠️ **连接地址**：连服务器公网游戏端口（不是 127.0.0.1 本机）
- ⚠️ **白名单时序**：`whitelist add` 后立即连接可能仍被踢（写入落盘延迟），等 10-30s 再连
- ⚠️ **登录插件**：LoginSecurity `registration.enabled: true` → bot 首次进服必须 `/register`，之后 `/login`；脚本里 spawn 后先 register（幂等）
- ⚠️ **控制台 command API 转发丢玩家上下文**：`execute as <bot> run tp ...` 会被当 CONSOLE 命令简化执行（日志显示 `CONSOLE issued server command`，玩家位置不变）——**需要玩家身份的操作必须由 bot 自己通过 mineflayer 执行**（`bot.chat('/home')`）
- ⚠️ **粒子包解析崩溃（26.2 → 1.21.11 ViaVersion 边界，必现）**：26.2 新增粒子 ID 115(block_crumble)/116(firefly) 在 1.21.11 的 `Particle` 协议 mappings 不存在 → protodef 读错字节 → `PartialReadError` 崩溃。**任何触发新粒子的动作（苦力怕爆炸/新方块粒子）都会杀掉 bot**。**修复**：bot 启动时运行时 patch `node_modules/minecraft-data/.../data/pc/1.21.11/protocol.json` 的 `types.Particle[1][0].type[1].mappings`，补 `"115": "block_crumble", "116": "firefly"`（映射到无数据粒子，protodef 不读附加字节）
- ✅ **玩家身份命令验证**：服务器日志出现 `<bot> issued server command: /tps`（玩家，非 CONSOLE）= 身份正确
- ⚠️ **本地测试服验证价值**：本地测试服出生点有苦力怕等实体，能暴露线上不常触发的崩溃路径（粒子/实体交互），改 bot 后先本地验证再上生产

## 常用操作

```bash
# bot 侧聊天命令（模板内置）
!tp x y z   # 传送（bot.entity.position.set）
!pos        # 报位置
!stats      # 位置+HP

# 服务端配合：用 bot 位置做实体统计锚点（玩家身份上下文正确）
# 但注意：控制台 execute as 会被简化成 CONSOLE——复杂操作让 bot 自己执行
```
