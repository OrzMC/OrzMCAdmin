# 机器人玩家（Mineflayer）——运维视角

> **用途**：玩家身份操作（/home、/tps）、触发区块加载、模拟玩家活动、实体统计锚点（无需真人客户端）。
> ⚠️ **bot 测不了 FPS**——headless 无渲染，FPS 是客户端指标；服务端实体统计见 `entity-statistics.md`。
> 📌 **bot 开发细节（mineflayer API、坑链、脚本模板）→ 独立技能 `minecraft-bot-mineflayer`**——本文件只保留运维需要的部分。
> 项目位置：`~/minecraft-bot/`（含 start.sh / stop.sh / minecraft-bot.js）

## 启动（运维视角）

```bash
# 线上（默认连 mc.fantuantim.xyz:25565）
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
- ⚠️ bot 项目持久化在 `~/minecraft-bot/`（勿放 /tmp）

## 常用操作（bot 侧聊天命令，minecraft-bot.js 内置）

```bash
!tp x y z   # 传送（bot.entity.position.set）
!pos        # 报位置
!stats      # 位置+HP
```

> 机器人作为运维工具：用 bot 位置做实体统计锚点（玩家身份上下文正确）。bot 开发/坑链/模板（build-house.js 搭房子、listen.js 收消息、粒子 patch、自动重连）→ `minecraft-bot-mineflayer` 技能。
