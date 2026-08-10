# 插件测试体系（testing）

> 合并自：papermc-plugin-e2e-testing + papermc-cross-server-testing（2026-08-10 阶段二整合）
> 触发：本地测试服对插件做 E2E 自动化验证；跨服传送门 transfer / 双服行为验证。

## 测试策略分层原则（用户规范）

> **「哪些逻辑可以用单元测试和集成测试保证的，优先使用单元测试和集成测试；其他情况必须要真实验收的，再使用机器人做端到端真实测试。」**

| 逻辑类型 | 手段 |
|:--|:--|
| 业务状态机 / 纯逻辑 | 单测（JUnit+Mockito，mock 端口） |
| 命令分发 / 权限校验 | 单测（mock 依赖服务） |
| YAML 持久化 | 单测 |
| 平台行为（Paper 26 命令事件、LP 真实授权、EasyBot 网关、RCON 链路） | **必须真实验收**（MockBukkit 模拟不了） |

验收顺序：先 `./gradlew test` 全绿 → 再 bot E2E 覆盖平台行为层。

## 三大测试通道

| 通道 | 用途 | 入口 |
|:--|:--|:--|
| **RCON** | 控制台命令 | `scripts/rcon.py '<cmd>' <mc-port> <rcon-pw>`；node 原生 `scripts/rcon-node.js` |
| **orzdebug** | 模拟群管理员发 Bot 命令（isAdmin=true） | **游戏内**（Mineflayer bot 执行 `/orzdebug <bot命令>`）——Paper 26 Brigadier 命令不触发 RCON 事件 |
| **Mineflayer bot** | 真实玩家身份执行游戏内命令 | `~/minecraft-bot/` 下 bot 脚本 |

## 关键陷阱（Paper 26 + 异步链路）

- **Brigadier 注册的命令【不触发】ServerCommandEvent**：`/orzdebug` 的 `.executes()` 正常执行但监听器收不到事件——修复：`.executes()` 里直接调 `botInboundHandler().handleMessage(...)`
- **LP 命令必须主线程 dispatch**：异步线程抛 `IllegalStateException: Asynchronous Command Dispatched Async`——`scheduler.runSync` 回主线程；runSync 吞异常需 `CompletableFuture.join()` 传播
- **RCON 包 length** = id(4)+type(4)+payload+2 null 总长（payload.length+10）；node 实现漏算 8 字节服务器立即断连
- **`$` 防 shell 展开**：`$v l` 经双引号被 bash 展开成空——node spawnSync 数组参数/原生 net；bash 单引号
- **测试环境配置漂移掩盖生产 bug**：E2E 前先 diff 测试服配置与仓库默认资源（`diff ~/minecraft-server/plugins/OrzMC/templates.yml src/main/resources/templates.yml`）
- **部署后必验**：`ls -la build/libs/*.jar` 与 plugins/ jar 时间戳一致 + `grep "Enabling X"` 确认版本；时间戳一致仍不够——python zipfile 读 .class 字节搜修复符号
- **测试账号密码重置（LoginSecurity）**：`lc/lac unregister` 不可靠——直接 `sqlite3 plugins/LoginSecurity/LoginSecurity.db "DELETE FROM ls_players WHERE last_name='X';"`（表 ls_players）→ 重进服 `/register <pw> <pw>`
- **mockStatic 泄漏**：@BeforeEach 开不关 → 后续测试污染——每个测试 try-with-resources 包住
- **登录冷却**：bukkit.yml `settings.connection-throttle` 改 0 + 重启可关；LoginSecurity「此用户已经在线」是会话残留时序（等 2-3s 再重连）
- **LP check true ≠ 命令可用（子权限陷阱）**：`/mail send` 需 `essentials.mail.send`、`/warp` 需 `essentials.warp.list`、`/time set` 需 `essentials.time.set`——最终验收必须 bot 实测命令

## 跨服/双服测试（transfer）

### 双服搭建（复制法）
```bash
cd ~/minecraft-server && tar --exclude='logs' --exclude='cache' --exclude='world/session.lock' -cf - . | (mkdir -p ~/minecraft-server2 && cd ~/minecraft-server2 && tar -xf -)
# ⚠️ 必改：start.sh 双路径（cd + jar）+ server.properties（server-port=25566、rcon.port=25576、motd）
rm -f world/session.lock && screen -dmS mc2 ./start.sh
```
- 坑：start.sh 没改路径 → `DirectoryLock$LockException`（锁的是主服 world）；screen stuff 不可靠 → **stop 用 RCON**；第二服复制 Geyser 配置会端口冲突（无害）；easybot 连同一网关 409（无害）

### transfer 机制（核心认知）
- OrzMC `PlayerPortalEvent` → `findTarget` → `transfer <host> <port> <player>`——**由玩家客户端主动去连目标**
- ⚠️⚠️ **目标 IP 必须是玩家可达地址**：`127.0.0.1` 只有本机客户端能通（远程玩家收到会连自己电脑 → `finishConnect failed Connection refused`）；局域网玩家用服务器局域网 IP；公网玩家用公网 IP/域名
- **mineflayer 无法完成 transfer**：不支持 transfer 协议包；跳跃+前进能触发 PlayerPortalEvent 但插件 findTarget 未命中（位置同步差 1-2 格）→ 原版传送接管。**transfer 端到端只有真实玩家能完整验证**；bot 只能做部分链路
- mineflayer yaw 映射：`yaw=0 → -z`、`yaw=π → +z`（与直觉相反）
- pathfinder 默认 `canDig: true` 会挖方块——必须 `mc.canDig = false; mc.allow1by1towers = false;`
- bot 跳跃进门可能掉刷怪区被打死——先清怪或临时和平模式

### 传送门结构（实测）
```
y=68 obsidian（顶梁）/ y=65-67 nether_portal / y=64 obsidian（底梁）/ y=63 gold_block（pad）
```
- **传送门内部（框架内）禁止放置方块**：setblock 会触发结构有效性判定 → 所有 NETHER_PORTAL 方块消失只剩框架
- /portal 命令：`portal <host> <port>`（**不带 create 字面量**）；必须玩家执行（RCON 报 requirePlayerTip）
- **portals.yml 会被覆盖**：手写后只要再执行任何 /portal 命令就被内存状态覆盖——正确改法：命令操作（remove+create）或手写后重启前不再执行 /portal 命令
- 判断门有效：RCON `testforblock <x> <y> <z> minecraft:nether_portal`（比 bot blockAt 可靠）

### LoginSecurity 干扰（未登录玩家）
- 未登录玩家站传送门：插件 `isAuthenticated=false` → 取消传送（设计正确）；**测试流程必须先 `/login` 再进传送门**
- LoginSecurity 3.3.2 `SessionManager` 没有 `isAuthenticated(Player)`（只有 getPlayerSession + isLoggedIn）——反射回退失败则 fail-open 放行

## 支持文件

- `references/papermc-26-testing-pitfalls.md`：Paper 26 测试踩坑明细
- `references/luckperms-track-api.md`：LP track API 原生钳位语义 + 权限链设计决策链
- `references/pr-review-checklist.md`：插件 PR 代码审查清单
- `references/dependency-upgrade-audit.md`：发版前依赖升级核查
- `references/easybot-delivery-verify.md`：EasyBot 通知送达验证
- `references/entity-diagnostics.md`：实体统计与卡顿定位
- `scripts/rcon-node.js` / `rcon.py`：RCON 客户端
- 验收交付物：`~/OrzMC/plugin/docs/test-cases.md`（28 项用例）+ `e2e-test-report-20260806.md`
