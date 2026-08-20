# 插件测试体系（testing）

> 合并自：papermc-plugin-e2e-testing + papermc-cross-server-testing（2026-08-10 阶段二整合）
> 触发：本地测试服对插件做 E2E 自动化验证；跨服传送门 transfer / 双服行为验证。

## 测试策略分层原则（用户规范）

> **「哪些逻辑可以用单元测试和集成测试保证的，优先使用单元测试和集成测试；其他情况必须要真实验收的，再使用机器人做端到端真实测试。」**

> **⚠️ 当前 E2E 测试服 = 仅 Paper（2026-08-20 老板决策：只运行 Paper 测试服）**：`~/minecraft-server/`（登录插件 LoginSecurity）——Folia 测试服 `~/folia-test/`（SimpleLogin）**已停服**，需要双核心验证时再启动。**⚠️ 端口已统一（2026-08-20）：两服都用 25565/RCON 25575/Geyser 19132**（既然共用地图不能同跑，端口统一后客户端/RCON 地址固定，无需记两套）。日志路径 Paper=`~/minecraft-server/logs/latest.log`、Folia=`~/folia-test/logs/latest.log`。
> **⚠️⚠️ 共用地图、严禁同跑（2026-08-20 确认）**：`~/folia-test/world` 是 **symlink → `~/minecraft-server/world`**（2026-08-18 Folia 接管原测试服时定的方案），物理地图只有一份（18G/317 万 chunk），玩家存档/建筑/level.dat 全部共享。**两台服绝不能同时运行**：Paper 在线时 world 被 session.lock 锁定，Folia 启动报 `DirectoryLock$LockException` 直接拒绝；强制绕过会数据冲突损坏地图。切换规则：停 Paper → 再启 Folia（反之亦然），先查 `lsof -iTCP:25565` 确认无占用（端口已统一，占用即另一台在跑）。paper-transfer-test 目录（transfer 测试临时目标服 25566/RCON 25575，231M）是独立世界，非 symlink，测完即删。
> **E2E 套件 = 插件仓库 `plugin/e2e/`**（2026-08-19 建立）：`bash e2e/run-all.sh [-c NN] [-r]` 一键跑；**双核心支持（2026-08-20 端口统一后改自动检测）**：run-all.sh 前置检查会**自动检测运行中的测试服核心**（`ps` 进程检测 folia-test/papermc-test jar，`ORZMC_CORE=folia|paper` 可显式覆盖），日志路径/模板路径按核心推断，端口统一 25565/RCON 25575 无需再传环境变量——**05-groupmsg.js 群消息场景**（2026-08-19 加入，PR #201）：whitelist_block 拦截/player_join 上线/player_digest 双 bot 下线聚合/player_quit 单发/ip_blacklist_block——**日志断言**（Notifier.routeEvent 统一 `[群消息:<key>]` 日志 + ⏎ 转义换行，JUL→log4j 只输出首行）+ 占位符残留检查（防 {online_list} 类模板回归）；Folia 11/11 + Paper 11/11 双绿；**06-permission-msg.js 权限/审核消息**（2026-08-19 加入，PR #202）：review_submitted 申请发起 / review_approved 审核通过（含审核人）/ rank_promoted 晋升（🎉「建造者」中文显示名）/ review_rejected 拒绝 / review_cancelled 撤回——**关键坑**：LP 设组须**先建后设**（parent set 对不存在用户创建的虚拟用户会被首登覆盖：先进服建用户→quit→parent+group set→重进）；**登录节流 20s**（login_rate_limit 5/min + LoginSecurity 冷却 13s+，Folia SimpleLogin 无此坑）；/review 仅玩家可用 + isOp/orzmc.admin（自建 op 审核人 RCON op+deop 还原）；异常路径 try/finally quit（防残留 bot 触发 per-IP 限流）；Folia 19/19 + Paper 19/19 双绿；`lib/rcon.js`（Promise RCON + waitLog tail 3000 防刷屏挤出）+ `lib/bot.js`（spawnBot 自适应 SimpleLogin/LoginSecurity 登录：probeLogin 先发 /login 探测、未注册转 /register；⚠️ 成功判定只认「登录成功/注册成功」，勿匹配「Welcome! just joined」首登广播否则过早 resolve 命令被拦）；用例自包含（专用账号自动注册+清理白名单）。测试账号密码：SimpleLogin 版 E2E 专用 E2EPass123（旧 LoginSecurity 版 TestNewbie/NewbiePass123 已不适用）。
> **BUG-E2E-001（✅ 已修复并双核心验证 2026-08-19）**：`$w` 白名单分页在 Folia 上抛 `IllegalArgumentException: Delay ticks may not be <= 0`——Paginator.paginatePages L71 `i * delayTicks` 在 i=0 时 delay=0，Paper BukkitScheduler 允许 0 tick、**Folia FoliaGlobalRegionScheduler.runDelayed 要求 ≥1**（`delayTicks<=0?5L` 保护只覆盖配置值不覆盖 i=0 首页）→ $w 分页 Folia 完全不可用。**修复**：Paginator 两处 `Math.max(1L, (long) i * ...)` + ServerFacade.runLater 钳位 ≥1 + PaginatorTest 回归护栏（首页 delay≥1）。验证：Folia `$w` 输出 123 人 ✅、Paper 01 用例 8/8 ✅。记录：`plugin/e2e/buglog.md`。
> **BUG-E2E-002（✅ 已修复并端到端验证 2026-08-19，backup-core v0.2.2 = PR #46+#47）**：大世界（Paper 服 317 万 chunk）`$b` 备份极慢+失败误报——**不是新压缩格式**！三层坑：①compression byte 非法（如 49）②**长度字段荒谬但 compression 合法**（如 0x789c=ZLIB 但长度 20 亿 → dataBytes 读 20 亿字节卡死）③**offset 越过文件末尾 → BufferedRafAccess readFully avail<=0 死循环（CPU 100% 无进度）**。修复：McaEntry `UNKNOWN` 枚举 + 长度 >8MB 短路 + readFully EOF 保护 + pattern 异常安全保留。插件侧 errorHandler 聚合（Pattern/Write-损坏不报失败，Done 汇总）。**验证：Paper 服 $b 14分21秒完成 + zip 2.03GB + 「264 个损坏区块已安全保留」**。E2E 04 备份断言用「阶段进度 + .zip 落盘」（大世界全量备份 ~15min）。
> **BUG-E2E-003（✅ 已修复验证 2026-08-19）**：CommandGuard「危险命令放行」WARN 刷屏（命令方块循环 20 条/tick → 21 万条/53MB）→ `ThrottledNotifier` WARN 日志 5s 限频（其余降 fine）+ BLOCK 通知 10s 限频；验证 4 分钟 13 条（修复前 4800+）。**备份并行化**：WorldMaintenanceService `RuntimeOptions(0)`（单线程）→ `RuntimeOptions(CPU 核数)`——Paper 服 $b **14分21秒→5分59秒**（速率 5 倍）。
> **质量周报 cron（2026-08-19 建立，job `079c34424888` 每周一 9:30）**：`~/.hermes/scripts/orzmc_quality_report.py` 跑 gradlew test/integrationTest/jacoco → 解析用例数/通过率/四类覆盖率 → 对比上周基线（`~/.hermes/state/orzmc_quality.json`）→ Markdown 表格发飞书。基线（2026-08-19 补测后）：1317 用例 / INSTRUCTION 85.4% / BRANCH 74.3% / METHOD 87.4%+ / CLASS 96.6%+；薄弱模块已全部达标：maintenance 66.9%、paging 80.8%、ws 59.0%、review 86.2%、teleport 96.5%。

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
- **测试环境配置漂移掩盖生产 bug**：E2E 前先 diff 测试服配置与仓库默认资源（`diff ~/minecraft-server/plugins/OrzMC/templates.yml src/main/resources/templates.yml`）——**2026-08-19 实测踩坑**：Paper 服 templates.yml 是 #197 群消息样式统一前的旧版（player_join 含 `{online_list}`），新代码渲染不传该变量 → 群消息出现 `{online_list}` 字面量（Folia 新版模板正常）→ 修复：`cp src/main/resources/templates.yml <服>/plugins/OrzMC/` + RCON `/config reload`（templates 热重载）。**已自动化（PR #200/#213）**：run-all.sh 前置模板一致性检查（**核心自动检测推断测试服路径**：ORZMC_CORE 显式指定 > 进程检测 folia/paper，端口统一 25565/25575 无法靠端口区分；日志/备份/模板路径按核心映射 folia→folia-test、paper→papermc-test；非法核心名/目录缺失报错退出、显式值与实际不一致告警——PR #213 2026-08-20）+ diff 拦截，`ORZMC_SKIP_TEMPLATE_CHECK=1` 临时跳过；**群消息模板变更后仍须同步所有测试服**（检查只拦截不自动修复）
- **部署后必验**：`ls -la build/libs/*.jar` 与 plugins/ jar 时间戳一致 + `grep "Enabling X"` 确认版本；时间戳一致仍不够——python zipfile 读 .class 字节搜修复符号
- **测试账号密码重置（LoginSecurity）**：`lc/lac unregister` 不可靠——直接 `sqlite3 plugins/LoginSecurity/LoginSecurity.db "DELETE FROM ls_players WHERE last_name='X';"`（表 ls_players）→ 重进服 `/register <pw> <pw>`
- **mockStatic 泄漏**：@BeforeEach 开不关 → 后续测试污染——每个测试 try-with-resources 包住
- **登录冷却**：bukkit.yml `settings.connection-throttle` 改 0 + 重启可关；LoginSecurity「此用户已经在线」是会话残留时序（等 2-3s 再重连）
- **⚠️ vanilla per-IP 在线限制（压测天花板，2026-08-13 实测）**：同 IP 已登录玩家 ≥5 时第 6+ 被踢（`Sorry, there are too many players logged in with your IP address`）→ **单出口 IP 压测上限 = 5 bot 真实在线**（40 bot 尝试全成功但峰值在线仅 3-6）。**macOS 禁 bind 127.0.0.x**（Errno 49，lo0 虽 /8 掩码但内核只认 127.0.0.1；Linux 可行）→ 多回环 IP 方案 macOS 死路（无 sudo 加不了 lo0 alias）。真实玩家各 IP 不同，此限制不影响线上容量
- **⚠️ 压测在线数统计**：mineflayer `spawn` 事件计数只增不减会虚高（被踢也算"进入"）——用 Set 维护真实在线（spawn 增 / end 减），采样打 `在线=N/总数`
- **⚠️ 登录风暴：冷区块首登崩、热世界不崩**（2026-08-13 实测）：冷启动后首轮登录加载全冷 chunk → 10 bot 就 TPS 4.2；预热后（同轮测试后半程）40 bot 登录风暴 TPS 最低 16.1 稳定 18+，0 次 Can't keep up → **活动当天必须预热 spawn 区域**（提前登录/加载），登录风暴本身不是杀手，冷 chunk 生成才是
- **LP check true ≠ 命令可用（子权限陷阱）**：`/mail send` 需 `essentials.mail.send`、`/warp` 需 `essentials.warp.list`、`/time set` 需 `essentials.time.set`——最终验收必须 bot 实测命令

## 跨服/双服测试（transfer）

### 双服搭建（复制法）
```bash
cd ~/minecraft-server && tar --exclude='logs' --exclude='cache' --exclude='world/session.lock' -cf - . | (mkdir -p ~/minecraft-server2 && cd ~/minecraft-server2 && tar -xf -)
# ⚠️ 必改：start.sh 双路径（cd + jar）+ server.properties（server-port=25566、rcon.port=25576、motd）
rm -f world/session.lock && screen -dmS mc2 ./start.sh
```
- **✅ 测完即删（2026-08-15 老板决策）**：双服测试是临时动作，**完成后必须清理第二服**防占磁盘（~486M）——`rm -rf ~/minecraft-server2`（先确认无进程、无 cron 引用）；需要时随时按本节步骤重建
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
