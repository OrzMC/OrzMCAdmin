# OrzMC 权限审核框架 · 机器人自动化 E2E 测试（2026-08-07）

> 场景：用户要求「用机器人自动化的做测试」——验证通用审核框架全链路：
> 玩家 `/apply` 提交 → 群通知 → `$v l` 待审列表 → `$v y` 通过 → LP 授权 → 玩家游戏内收到结果。

## 通道选择（EasyBot 无模拟入站 API，两条真实通道）

| 通道 | 身份 | 用途 | 实现 |
|:--|:--|:--|:--|
| RCON + orzdebug | 群管理员（isAdmin=true） | 测群指令 `$v l/y/n` | `python3 rcon.py 'orzdebug $v l'` 或 `node scripts/rcon.js "orzdebug $v l"` |
| Mineflayer bot | 真实玩家 | 测玩家命令 `/apply /rank /apply status` | `~/minecraft-bot/review-e2e.js`（模板，见下） |

- EasyBot `/api/v1/messages/ingest|inject|emit` 均 404——无法 API 伪造群消息（见 easybot-gateway-ops 技能）
- **OrzDebugEvent 需已修复 RCON 支持**（2026-08-07）：双事件监听 `ServerCommandEvent` + `RemoteServerCommandEvent` + 剥前导斜杠；否则 RCON 的 orzdebug 只走 Brigadier 分支（回显「debug 已受理」）不触发 Bot 模拟
- 测试服 easybot.yml 连 test-bot 测试网关（飞书测试群），不会打扰生产群——自动化测试前先确认目标群

## 测试账号（本地测试服）

| 账号 | 密码 | LP 组 | 用途 |
|:--|:--|:--|:--|
| TestNewbie | NewbiePass123 | default（本地 promoted 标记=member 资格） | 提交 builder 申请 |
| TestMember | MemberPass123 | member | 补充测试 |
| TestAdmin | AdminPass123 | admin | — |

- 资格预检基于**本地状态**（permission.yml promoted 标记 / APPROVED 记录），不是 LP 实际组——测试前确认玩家在 permission.yml 有 member 资格
- 通过审核后玩家变 builder → 无法再申请（资格预检拦截），重测需重置：停服 → 清 permission.yml reviews 节 + LP 移除 builder 组 → 重启

## 自动化脚本模式（review-e2e.js）

```js
// 关键结构：async 主流程 + 原生 node RCON（不经 shell，$ 安全）
const net = require('net');
function rcon(cmd) { /* 见 scripts/rcon.js 实现，返回 Promise */ }
(async () => {
  console.log(await rcon('orzdebug $v l'));        // 阶段0：待审列表
  const bot = mineflayer.createBot({...});          // 阶段1：bot 进服 + /login
  bot.on('message', m => { if (/请输入 \/login/.test(m)) bot.chat('/login ...'); });
  await spawn; bot.chat('/apply builder 想用WorldEdit建造');
  await sleep(6000);
  console.log(await rcon('orzdebug $v y TestNewbie'));  // 阶段3：管理员通过
  bot.chat('/apply status'); bot.chat('/rank');     // 阶段4/5：玩家查结果
})();
```

- bot 进服会被出生点怪物杀（spawn 重复触发）——主流程用 async/await 顺序控制，别依赖 spawn 事件驱动阶段
- 阶段判定看**游戏内消息**（bot.on('message')）+ **服务器日志**（grep `cmd debug`）+ **LP 日志**（`[LP] xxx 繼承 builder 的權限` = 授权真实生效）

## 验证闭环（按此顺序取证）

1. **玩家侧**：bot 收到「申请已提交」→ `/apply status` 显示 `⏳ 待审核` → `/rank` 显示当前组+进度+下一步可申请
2. **管理员侧**：`$v l` 列表含 `[晋升建造者] 玩家（当前组：member）：申请晋升 builder：理由（X分钟前 提交）`
3. **结果通知**：`$v y` 后 bot 收到「你的「晋升建造者」申请已通过！」→ `/apply status` 变 `✅ 已通过（群管理员）`
4. **LP 真实授权**：服务器日志 `[luckperms-command-executor/INFO]: [LP] testnewbie 現在從環境 global 中繼承 builder 的權限`（LP 命令回显中文 locale）
5. **群通知**：EasyBot gateway.db deliveries 全 succeeded（outbound 链路）

## 踩坑记录（本会话实测）

1. **OrzDebugEvent 不响应 RCON**：Paper 26 RCON 命令触发 `RemoteServerCommandEvent`（ServerCommandEvent 子类），但原监听只有父类且 `startsWith("orzdebug")` 遇前导 `/` 失配 → 修复双事件 + 剥斜杠（已合入插件）
2. **异步 dispatchCommand 崩溃**：`$v y` 走 runTaskAsynchronously → handler 调 LP 命令抛 `IllegalStateException: Asynchronous Command Dispatched Async`，**审核状态已 APPROVED 但 LP 未授权**（状态与权限不一致的隐蔽 bug）→ 修复注入 ServerScheduler 回主线程
3. **shell 展开 $v**：`execSync("python3 rcon.py 'orzdebug $v l'")` → bash 把 `$v` 展开为空，服务器收到 `orzdebug  l` 静默无效 → 用 spawnSync 数组参数或原生 net
4. **node RCON length 字段**：`writeInt32LE(payload.length)` 少算 8 字节（id+type 头）→ 服务器立即断开 `read_packet: unpack requires 4 bytes` → 必须 `payload.length + 8`（含 2 null 共 +10）
5. **markAlwaysSave 覆盖**：运行中清 permission.yml reviews 节 → 重启后数据回来（关服保存内存态）→ 必须先停服再改文件
6. **python 子进程环境差异**：node spawnSync 调系统 python3 与 shell 直跑结果不同（PATH/环境）——测试脚本内用原生实现最稳，别依赖子进程

## 复用

- `scripts/rcon.js` — 通用 node RCON 客户端（`$` 安全），任何测 Bot 命令场景直接用
- `~/minecraft-bot/review-e2e.js` — 完整审核链路 E2E 模板（改 BOT_NAME/密码/命令即可适配新审核类型）
