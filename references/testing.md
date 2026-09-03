# 插件测试体系（testing）

> 合并自：papermc-plugin-e2e-testing + papermc-cross-server-testing（2026-08-10 阶段二整合）
> 触发：本地测试服对插件做 E2E 自动化验证；跨服传送门 transfer / 双服行为验证。

## 测试策略分层原则（用户规范）

> **「哪些逻辑可以用单元测试和集成测试保证的，优先使用单元测试和集成测试；其他情况必须要真实验收的，再使用机器人做端到端真实测试。」**

> **⚠️ 当前测试服拓扑（2026-09-03 起全部迁 MCSM 本机栈）**：双 Docker 实例 **`papermc-test`**（uuid 716c2fb7，LoginSecurity）与 **`folia-test`**（uuid 8A932DD4）由本机 MCSM 面板 **mcs.{SERVER_NAME}.cn** 管理（节点 orzmc-local），启停走面板（实例配置/数据在宿主 `/Users/Shared/orzmc/mcsmanager/daemon/data/`，目录 `InstanceData/<uuid>/` 含 server.properties/plugins/ 完整服务端）。旧裸跑目录 `~/minecraft-server`/`~/folia-test` 与 start.sh/screen 启动**已废弃删除**。详见下文「MCSM 本地栈 Docker 实例」节（2026-09-03 迁移实测 + 五连坑）。
> **⚠️⚠️ 共享 world、严禁同跑**：物理地图一份（`/Users/Shared/orzmc/worlds/test`，extraVolumes 挂载两实例容器 `/server/world`，2026-08-20 优化裁剪后 ~2.1G），玩家存档/建筑/level.dat 全部共享。**两实例绝不能同时运行**（同抢 25565 + world 双写毁档；daemon 软关闭会跳过 docker 实例不自动停）。切换规则：面板先停另一台 → 再启目标实例（docker ps 确认无 MCSM 容器残留后启动）。
> **E2E 套件 = 插件仓库 `plugin/e2e/`**（2026-08-19 建立）：`bash e2e/run-all.sh [-c NN] [-r]` 一键跑；**双核心支持**：`ORZMC_CORE=folia|paper` 显式指定 + 测试服目录/日志/备份路径环境变量注入（run-all.sh 不再自动检测核心——Docker 实例 java 进程在容器内，宿主 ps 不可见；MCSM 对接层由技能 wrapper 脚本 `scripts/e2e-mcsm-wrapper.sh` 负责：确认实例状态 + 注入全部环境变量 + 调仓库 run-all.sh，2026-09-03 起）——**05-groupmsg.js 群消息场景**（2026-08-19 加入，PR #201）：whitelist_block 拦截/player_join 上线/player_digest 双 bot 下线聚合/player_quit 单发/ip_blacklist_block——**日志断言**（Notifier.routeEvent 统一 `[群消息:<key>]` 日志 + ⏎ 转义换行，JUL→log4j 只输出首行）+ 占位符残留检查（防 {online_list} 类模板回归）；Folia 11/11 + Paper 11/11 双绿；**06-permission-msg.js 权限/审核消息**（2026-08-19 加入，PR #202）：review_submitted 申请发起 / review_approved 审核通过（含审核人）/ rank_promoted 晋升（🎉「建造者」中文显示名）/ review_rejected 拒绝 / review_cancelled 撤回——**关键坑**：LP 设组须**先建后设**（parent set 对不存在用户创建的虚拟用户会被首登覆盖：先进服建用户→quit→parent+group set→重进）；**登录节流 20s**（login_rate_limit 5/min + LoginSecurity 冷却 13s+，Folia SimpleLogin 无此坑）；/review 仅玩家可用 + isOp/orzmc.admin（自建 op 审核人 RCON op+deop 还原）；异常路径 try/finally quit（防残留 bot 触发 per-IP 限流）；Folia 19/19 + Paper 19/19 双绿；`lib/rcon.js`（Promise RCON + waitLog tail 3000 防刷屏挤出）+ `lib/bot.js`（spawnBot 自适应 SimpleLogin/LoginSecurity 登录：probeLogin 先发 /login 探测、未注册转 /register；⚠️ 成功判定只认「登录成功/注册成功」，勿匹配「Welcome! just joined」首登广播否则过早 resolve 命令被拦）；用例自包含（专用账号自动注册+清理白名单）。测试账号密码：SimpleLogin 版 E2E 专用 E2EPass123（旧 LoginSecurity 版 TestNewbie/NewbiePass123 已不适用）。
> **BUG-E2E-001（✅ 已修复并双核心验证 2026-08-19）**：`$w` 白名单分页在 Folia 上抛 `IllegalArgumentException: Delay ticks may not be <= 0`——Paginator.paginatePages L71 `i * delayTicks` 在 i=0 时 delay=0，Paper BukkitScheduler 允许 0 tick、**Folia FoliaGlobalRegionScheduler.runDelayed 要求 ≥1**（`delayTicks<=0?5L` 保护只覆盖配置值不覆盖 i=0 首页）→ $w 分页 Folia 完全不可用。**修复**：Paginator 两处 `Math.max(1L, (long) i * ...)` + ServerFacade.runLater 钳位 ≥1 + PaginatorTest 回归护栏（首页 delay≥1）。验证：Folia `$w` 输出 123 人 ✅、Paper 01 用例 8/8 ✅。记录：`plugin/e2e/buglog.md`。
> **BUG-E2E-002（✅ 已修复并端到端验证 2026-08-19，backup-core v0.2.2 = PR #46+#47）**：大世界（Paper 服 317 万 chunk）`$b` 备份极慢+失败误报——**不是新压缩格式**！三层坑：①compression byte 非法（如 49）②**长度字段荒谬但 compression 合法**（如 0x789c=ZLIB 但长度 20 亿 → dataBytes 读 20 亿字节卡死）③**offset 越过文件末尾 → BufferedRafAccess readFully avail<=0 死循环（CPU 100% 无进度）**。修复：McaEntry `UNKNOWN` 枚举 + 长度 >8MB 短路 + readFully EOF 保护 + pattern 异常安全保留。插件侧 errorHandler 聚合（Pattern/Write-损坏不报失败，Done 汇总）。**验证：Paper 服 $b 14分21秒完成 + zip 2.03GB + 「264 个损坏区块已安全保留」**。E2E 04 备份断言用「阶段进度 + .zip 落盘」（大世界全量备份 ~15min）。
> **BUG-E2E-003（✅ 已修复验证 2026-08-19）**：CommandGuard「危险命令放行」WARN 刷屏（命令方块循环 20 条/tick → 21 万条/53MB）→ `ThrottledNotifier` WARN 日志 5s 限频（其余降 fine）+ BLOCK 通知 10s 限频；验证 4 分钟 13 条（修复前 4800+）。**备份并行化**：WorldMaintenanceService `RuntimeOptions(0)`（单线程）→ `RuntimeOptions(CPU 核数)`——Paper 服 $b **14分21秒→5分59秒**（速率 5 倍）。
> **BUG-E2E-004（✅ 修复 PR 已提 2026-08-20，backup-core #50 main/#51 0.2.x）**：symlink 世界 $b 备份**空跑假完成**——Folia 测试服 world 是 symlink（→papermc-test/world），backup-core `RealFileSystem.walk` 用 `Files.walk` 不跟随符号链接 → `dimensions/*/region/*.mca` 全不可见 → 0 chunk、431ms "完成"、zip 22 字节、进度 2/2（zip 固定项）**无任何报错**。修复=`Files.walk(path, FOLLOW_LINKS)`+`RealFileSystemSymlinkTest`。验证：修复版 Folia $b 3170460/3170460、6分16秒、zip 1.42GB。**连带**：walk 跟随链接后 worldContainer 内备份残留目录（旧布局 plugins/OrzMC/backup/tempDir）会被扫入备份源 → 保持 worldContainer 内无备份中间目录。
> **⚠️ 备份=优化式备份（设计语义，非缺陷）**：backup-core 对备份也应用 InhabitedTime 阈值过滤（插件传 optimizeTickTimeThreshold 默认 300 秒，剔除活跃 ≤15 秒 chunk）→ 17G 世界备份 zip 仅 ~1.4G（region 946/6380）。features.md 已如实标注。**完整备份磁盘硬约束**：全量保留需 ~17G+ 临时空间，本机 13Gi 不够 → 本机只能验证备份功能链路；线上磁盘充足。
> **备份收尾期登录被拒**：$b 维护模式踢人+拒登，E2E 05/06 在备份收尾期跑会零输出 exit 0（汇总假绿）——等「地图备份 完成」+ zip 落盘后补跑 `-c 05 -c 06`。
> **⚠️ 备份完成判定陷阱（2026-08-20 复验踩坑）**：**zip 出现 ≠ 备份完成**——backup-core zip 边写边落盘，进行中 zip 可能只有 64M（完成时 1.1G），tempDir 也在场；判定「备份完成」必须等日志「地图备份 完成」（或 zip mtime 稳定 + tempDir 消失），勿用「新 zip 出现」提前 break（会误判未完成/误判失败）。
> **发布闭环（2026-08-20 1.0.19 经验）**：代码 PR 合并后 → 更新 CHANGELOG（1.0.19 条目：修复/新功能/依赖/⚠️升级注意）+ 清理陈旧文档（验收报告版本表 sha256、世界大小、备份目录描述）→ docs PR（CI 绿后文档直接合并）→ `git tag 1.0.19`（**严格 SemVer 无 v 前缀**）+ push → Publish workflow（GitHub Release + Hangar + Modrinth）自动触发，`gh run list` 看 headBranch=tag 的 Publish run=success 即发布完成。
> **测试服世界裁剪（磁盘空间管理，2026-08-20）**：本机磁盘 13Gi 可用，17G 测试世界完整备份放不下 → 用 backup-core CLI 优化裁剪：`java -jar backup.jar -t 300 --parallelism=4 --report --report-file=/tmp/opt.json <world_dir> <output_dir>`（**v0.2.x CLI 无 `optimize` 子命令**——"optimize" 会被当 WORLD_DIR 静默零输出，直接 `backup.jar <WORLD_DIR> [OUTPUT_DIR]`；jar 构建：`cd OrzMCBackup && ./gradlew :app:shadowJar`，产物 `app/build/libs/backup.jar`）。阈值 300 秒 → 17G → ~2G（剔除低活跃 chunk，**破坏性操作**，测试服可接受）。切换：验证新 world → 删旧 → rename。优化只写 ~2G 临时输出（峰值额外 +2G），磁盘够；完整备份要复制全部 17G → 不够（O5）。
> **backup-core 0.3.1 + 备份目录最终方案（✅ 2026-08-20 插件 1.0.19 已发布）**：插件适配要点——① `IOOptions(fs, ioFactory, syncOnFinalize=true)` 三参（0.3.0+ API，第三参=跳过 fsync，非 zipOutput）；② 0.3.x overlap 校验：input/output 不得重叠 → **input 用世界目录**（`getWorldFolder()`，优先含 dimensions/region 的真实世界目录，防 getWorlds 顺序把非主世界排前），output=`backup/tempDir`（`backup/` 是世界目录的兄弟路径，天然不重叠）；③ zip 直接落 `backup/`（output 父目录），无移动环节；④ 备份成功判定=最新 zip mtime 变化（同名覆盖不误判）；⑤ 崩溃/断电残留 `backup/tempDir` 由 MaintenanceModule.setup **异步启动清理**；⑥ `$o` 优化需 `maintenance.optimize_enabled=true`（默认 false），实测 31s/190526 chunk；⑦ 备份目录=服务器核心根目录 `backup/`（非插件数据目录），E2E 04 BACKUP_DIR 与 run-all.sh ORZMC_BACKUP_DIR=`$TEST_DIR/backup` 同步；阈值保持原逻辑 300 不动。
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
- **测试环境配置漂移掩盖生产 bug**：E2E 前先 diff 测试服配置与仓库默认资源（`diff /Users/Shared/orzmc/mcsmanager/daemon/data/InstanceData/<运行实例uuid>/plugins/OrzMC/templates.yml src/main/resources/templates.yml`）——**2026-08-19 实测踩坑**：Paper 服 templates.yml 是 #197 群消息样式统一前的旧版（player_join 含 `{online_list}`），新代码渲染不传该变量 → 群消息出现 `{online_list}` 字面量（Folia 新版模板正常）→ 修复：`cp src/main/resources/templates.yml <服>/plugins/OrzMC/` + RCON `/config reload`（templates 热重载）。**已自动化（PR #200/#213）**：run-all.sh 前置模板一致性检查（ORZMC_CORE 显式指定 > 环境注入路径；日志/备份/模板路径全部环境变量注入——PR #213 2026-08-20，2026-09-03 迁 MCSM 后不再进程检测）+ diff 拦截，`ORZMC_SKIP_TEMPLATE_CHECK=1` 临时跳过；**群消息模板变更后仍须同步所有测试服**（检查只拦截不自动修复）
- **部署后必验**：`ls -la build/libs/*.jar` 与 plugins/ jar 时间戳一致 + `grep "Enabling X"` 确认版本；时间戳一致仍不够——python zipfile 读 .class 字节搜修复符号
- **测试账号密码重置（LoginSecurity）**：`lc/lac unregister` 不可靠——直接 `sqlite3 plugins/LoginSecurity/LoginSecurity.db "DELETE FROM ls_players WHERE last_name='X';"`（表 ls_players）→ 重进服 `/register <pw> <pw>`
- **mockStatic 泄漏**：@BeforeEach 开不关 → 后续测试污染——每个测试 try-with-resources 包住
- **登录冷却**：bukkit.yml `settings.connection-throttle` 改 0 + 重启可关；LoginSecurity「此用户已经在线」是会话残留时序（等 2-3s 再重连）
- **⚠️ vanilla per-IP 在线限制（压测天花板，2026-08-13 实测）**：同 IP 已登录玩家 ≥5 时第 6+ 被踢（`Sorry, there are too many players logged in with your IP address`）→ **单出口 IP 压测上限 = 5 bot 真实在线**（40 bot 尝试全成功但峰值在线仅 3-6）。**macOS 禁 bind 127.0.0.x**（Errno 49，lo0 虽 /8 掩码但内核只认 127.0.0.1；Linux 可行）→ 多回环 IP 方案 macOS 死路（无 sudo 加不了 lo0 alias）。真实玩家各 IP 不同，此限制不影响线上容量
- **⚠️ 压测在线数统计**：mineflayer `spawn` 事件计数只增不减会虚高（被踢也算"进入"）——用 Set 维护真实在线（spawn 增 / end 减），采样打 `在线=N/总数`
- **⚠️ 登录风暴：冷区块首登崩、热世界不崩**（2026-08-13 实测）：冷启动后首轮登录加载全冷 chunk → 10 bot 就 TPS 4.2；预热后（同轮测试后半程）40 bot 登录风暴 TPS 最低 16.1 稳定 18+，0 次 Can't keep up → **活动当天必须预热 spawn 区域**（提前登录/加载），登录风暴本身不是杀手，冷 chunk 生成才是
- **LP check true ≠ 命令可用（子权限陷阱）**：`/mail send` 需 `essentials.mail.send`、`/warp` 需 `essentials.warp.list`、`/time set` 需 `essentials.time.set`——最终验收必须 bot 实测命令
- **RCON 发 LP 命令偶发丢失 + mtime 验证不可靠（2026-08-30 沉淀）**：LP 命令经 RCON 偶发不生效；且**文件 mtime 变化 ≠ 命令成功**（插件后台定时保存/玩家数据写入也会写库写盘，mtime 被刷新是假阳性）——验证必须以 bot 实测（权限/命令真值）为准，必要时重复执行命令
- **测试服启停规范（2026-09-03 MCSM 版，替代裸跑流程）**：实例启停一律走面板（docker 实例 daemon 软关闭不自动停——共享 world 严禁同跑，切换前手动停另一台）；启动成功判定 = 日志 `Done (` + 端口监听（`docker ps --filter name=MCSM-` 确认容器名）+ **jar mtime 变化**（换 jar 升级后）；重启/切换前检查共享 world `session.lock` 残留（异常崩溃遗留锁会拒启，需清）。⚠️ 裸跑期流程（RCON stop → kill -0 → 删锁）已废弃，仅适用于旧裸跑/进程模式实例

## 跨服/双服测试（transfer）

### 双服搭建（复制法）
```bash
cd /Users/Shared/orzmc/mcsmanager/daemon/data/InstanceData/<源实例uuid> && tar --exclude='logs' --exclude='cache' --exclude='world/session.lock' -cf - . | (mkdir -p ~/tmp-second-server && cd ~/tmp-second-server && tar -xf -)
# ⚠️ 必改：server.properties（server-port=25566、rcon.port=25576、motd）；第二服 world 须独立（勿指向共享 world）
```
- **✅ 测完即删（2026-08-15 老板决策）**：双服测试是临时动作，完成后必须清理防占磁盘（先确认无进程、无 cron 引用）
- 坑：两服严禁同跑共享 world（session.lock/数据双写）；第二服复制 Geyser 配置会端口冲突（无害）；easybot 连同一网关 409（无害）
- ⚠️ **MCSM 环境推荐克隆实例法**：双服测试目标服用「手工克隆实例」（见「MCSM 本地栈」节坑 5：uuidgen → rsync InstanceData → cp 实例 JSON 改 nickname/端口/独立 world 目录 → 重启 daemon），比目录复制 + 裸跑更贴合当前栈

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

## MCSM 本地栈 Docker 实例（2026-09-03 迁移实测，五连坑）

本地测试服（Paper/Folia）已迁入本机 MCSM 栈（mcs.{SERVER_NAME}.cn）管理，**双 Docker 实例共享 world**：
- 实例 `papermc-test`（uuid 716c2fb7）/ `folia-test`（uuid 8A932DD4），共享 world `/Users/Shared/orzmc/worlds/test`（extraVolumes 挂两实例容器 `/server/world`），**严禁同跑**（同 25565 + world 双写毁档；daemon 软关闭 skip docker 实例——切实例前必须面板手动停另一台）
- 面板 UI 建实例默认**进程模式**（模板误导）；改 Docker 走 InstanceConfig JSON：停实例 → 改 `daemon/data/InstanceConfig/<uuid>.json` → 重启 daemon 容器 → 面板启动
- **五连坑**：
  1. `extraVolumes` 元素分隔符是 **`|`（竖线）**：`"宿主路径|容器路径"`（daemon 源码 `item.split("|")` 实证；用 `:` 或加 `:rw` 报"额外挂载路径配置长度不正确"）
  2. daemon 容器必须设 env **`MCSM_DOCKER_WORKSPACE_PATH=<宿主 InstanceData 绝对路径>`**，否则 docker 实例 cwd bind 用容器内路径（`/opt/mcsmanager/daemon/data/...`）→ 宿主引擎报 `bind source path does not exist`（ADR-019 移除旧 instances 时把此 env 一起删了，macOS/Linux compose 也需；已补进 kit compose.yaml daemon environment）
  3. 容器 `memory`（MB）必须 **> Xmx + JVM overhead**：Xmx2G + limit 2048MB → JVM 无内存余量跑 ~2min 后 SIGSEGV 崩溃（`hs_err_pid1.log` 的 `method_hash` 崩溃实证）→ 2G 堆配 4096
  4. `docker.ports` 字符串数组 `["25565:25565/tcp"]`、memory 单位 MB、`pty:true` 防日志乱码（papermc-template.md 已有）；UI 建完手工改 JSON 字段：processType=docker、image、ports、memory、networkMode=orzmc_default、workingDir=/server、changeWorkdir=true、extraVolumes
  5. **手工克隆实例**：uuidgen → mkdir InstanceData/<uuid> → rsync 数据（排除 world/logs/cache/backups）→ cp 现有实例 JSON 改 nickname/cwd/startCommand/jar 名 → 重启 daemon 即注册（面板出现，无需 UI 建）
- 迁移数据注意：jar 复制成固定名（paper.jar/folia.jar，升级换 jar 不动命令）；各实例 `plugins/OrzMC/easybot.yml` 是**独立拷贝**——逐个核对 api_server 指向（Folia 曾残留旧 `test-bot.{SERVER_NAME}.cn` → 502，改 `easybot.{SERVER_NAME}.cn` + 重启实例生效）

## 支持文件

- `references/papermc-26-testing-pitfalls.md`：Paper 26 测试踩坑明细
- `references/luckperms-track-api.md`：LP track API 原生钳位语义 + 权限链设计决策链
- `references/pr-review-checklist.md`：插件 PR 代码审查清单
- `references/dependency-upgrade-audit.md`：发版前依赖升级核查
- `references/easybot-delivery-verify.md`：EasyBot 通知送达验证
- `references/entity-diagnostics.md`：实体统计与卡顿定位
- `scripts/rcon-node.js` / `rcon.py`：RCON 客户端
- 验收交付物：`~/OrzMC/plugin/docs/test-cases.md`（28 项用例）+ `e2e-test-report-20260806.md`
