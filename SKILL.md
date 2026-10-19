---
name: orzmc
description: "Minecraft 运维统一技能（唯一入口）：三端服务器运维/插件构建升级/性能诊断/权限体系/测试/基岩支持（含 NetherNet 迁移），74 份参考文档 + 170+ 脚本。"
version: 2.1.0
author: Hermes Agent
tags: [minecraft, papermc, server, maintenance, upgrade, plugin, exaroton, mcsm, luckperms, testing]
platforms: [macos, linux, windows]
required_commands: [java, curl, tar]
---

# OrzMC Minecraft 运维（统一技能）

> **技能治理（2026-08-11 用户决策，已合并）**：与 MC 运维强相关的技能一律**合并进本技能**维护迭代（references + scripts），不再单独立技能；新增强相关知识直接落这里。已合并：easybot-gateway-ops（→ references/easybot-gateway.md）、deployment-config-sync（→ references/config-sync.md）、git-submodule-sync（→ references/git-submodule-sync.md，OrzMC monorepo 子模块同步）、java-test-pitfalls（→ references/java-test-pitfalls.md，插件单测编译坑）、**ai-coding-agents（→ references/coding-agents.md，2026-08-29：编程交给 Claude Code 编排工作流 + 合并前一次 review 时机 + acceptEdits 坑）**、**grimac-config-tuning（→ references/grimac-tuning.md，2026-09-12：GrimAC 配置语义/官方文档获取/误报源对照/工具坑）**、**bukkit-plugin-testing（→ references/java-test-pitfalls.md，2026-09-12：Mockito 运行时陷阱/Bukkit mock 限制/Jacoco 覆盖率工作流）**、**paper-26-plugin-dev（→ references/plugin-build.md + references/papermc-tabcomplete-testing.md，2026-09-12：Brigadier 命令注册/迁移 8 坑/deprecation 清零）**；模组托管（minecraft-modpack-server）已清理，与原生 PaperMC 场景无关。

> **知识分类索引**：本 SKILL.md 只留决策路径；详细知识在 `references/`（后端 API 表 / Spark / 实体统计 / 机器人）：
>
> | 主题 | 文档 |
> |:--|:--|
> | 本机服务器操作（创建/升级/备份/状态） | `references/local-backend.md` |
> | Exaroton 云端（API 端点表 + 平台要点） | `references/exaroton-backend.md` |
> | MCSM 面板（API 端点表 + 平台要点 + 适配器） | `references/mcsm-backend.md` |
> | **EasyBot IM 网关运维（docker 容器/健康检查/QQ token/投递诊断 API 版 `scripts/easybot_deliveries.py`；0.0.33 起投递记录在 messages 表；原 easybot-gateway-ops 技能合并）** | `references/easybot-gateway.md` |
> | **部署配置同步（config drift 判定/fallback 判断/补键同步；原 deployment-config-sync 技能合并）** | `references/config-sync.md` |
> | **Git 子模块全量同步（OrzMC monorepo 15 子模块；默认分支探测/发布后指针/分支清理/独立 clone 去重；原 git-submodule-sync 技能合并）** | `references/git-submodule-sync.md` |
> | **Java 测试编译陷阱 + 单测运行时陷阱（Mockito 泛型捕获/SuppressWarnings 位置/CI warnings 清零；**2026-09-12 并入 bukkit-plugin-testing**：Mockito UnfinishedStubbing/Stub 顺序/argThat null/异步进行中模拟、Bukkit API mock 限制（Material.isSolid 依赖注册表、Vector.clone 返回 null）、Jacoco 覆盖率缺口定位工作流）** | `references/java-test-pitfalls.md` |
> | **AI 编码智能体协作（编程交给 Claude Code + Hermes 编排；三模式/acceptEdits 坑/合并前一次 review；原 ai-coding-agents 技能合并）** | `references/coding-agents.md` |
> | Spark 性能分析（命令/JSON/判断/踩坑） | `references/spark-analysis.md` |
> | 快速实体统计（paper entity list / Spark / 计分板） | `references/entity-statistics.md` |
> | 机器人玩家 Mineflayer（运维视角；开发细节见独立技能 `minecraft-bot-mineflayer`；**挂机脚本 stay-with-joker.js：5 bot 跟随真人玩家 + IPv4/IPv6 分流绕 per-IP 限制**） | `references/mineflayer-bot.md` |
> | DeathChest 回归测试（死亡瞬间下线→物品丢失 ✅fix1；**动画 progress 越界卡服 ✅fix3 已合入 main 71d2571**；复现法见 ref） | `references/deathchest-regression.md` |
> | **NetherNet 迁移（基岩新传输层：TCP 信令 + WebRTC/UDP；2.12 配置结构反编译实证 / A-B-C 三方案 / HTTPS 三做法 / 官方错误对照表 / 本机 Clash TUN 假阳性验证法；⚠️ 2026-10-27 基岩客户端停用 RakNet）** | `references/nethernet.md` + `~/OrzMC/proxy/scripts/nethernet_check.py`（已并入 OrzMCProxy main，v1.1.0，退出码 0=可用/1=不可达/2=用法/3=降级；`--signal-port` `--scheme https` `--json` `--self-test` `--no-emoji`） |
> | **Geyser 基岩支持（当前 offline 直连模式；floodgate 已回退 2026-08-05）** | `references/geyser-floodgate.md` |
> | **实例端口模型与审计（docker 实例必须逐条发布 `宿主:容器/协议`；端口以实例实际配置为准而非默认 25565/19132；多实例共享宿主时 UDP 错开 19132/19133；宿主≠容器 时 `clone-remote-port` 必须 false；Cloudflare Tunnel 不支持 UDP；脚本 `scripts/port-audit.py` 核对期望端口 vs 已发布 + 真实协议探测）** | `references/instance-ports.md` |
> | **公网入口排障（域名+路由器映射+防火墙都"配好了"外网仍连不上）：根因常是本机 Clash TUN 抢默认路由 → 入站应答源地址被定成 198.18.0.1/钻进隧道；修法 = WSL 内加通用策略路由 `ip rule add from <LAN IP> table 100`（任意端口零维护，脚本 `scripts/orzmc-mc-reply-route.sh` + Windows 计划任务 OrzMC-MC-Reply-Route 每 10min 自愈）；⚠️ 老板坚持防火墙/路由器逐端口配置，勿再提 DMZ/端口段；含「ICMP 通但 TCP 全超时」判定法与外部节点验证法（勿在本机测）** | `references/public-ingress-clash-tun.md` |
> | **插件源码构建/开发（构建工具选择、Gradle/Maven 坑、PR 流程、发布规范；**2026-09-12 并入 paper-26-plugin-dev**：Paper 26.x Brigadier 命令注册（LifecycleEvents.COMMANDS）、幽灵命令/greedyString 参数类型等迁移 8 坑、deprecation 零警告清理）** | `references/plugin-build.md` |
> | **GrimAC 反作弊配置调优（配置三层体系/config.yml 官方模板零漂移/punishments 阈值=300s 窗口违规次数非 VL/per-check 豁免三兄弟/官方 mods 兼容表/误报源与工具坑；**2026-09-12 并入 grimac-config-tuning**；部署现状与决策史见本 SKILL.md 的 GrimAC 段）** | `references/grimac-tuning.md` |
> | **插件升级与配置迁移（三端范式、Exaroton/MCSM API 坑、EzShops 存储、Geyser 排查）** | `references/plugin-mgmt.md` |
> | **商店经济防刷（EzShops 实例：纯禁卖方案/漏洞分类学/审计脚本/bot 验收/结算取价机制/交易记录三层根因链；原 minecraft-shop-economy-hardening 技能 2026-08-30 合并）** | `references/shop-economy.md` + `scripts/shop_arbitrage_check.py` |
> | **WorldEdit 防崩服（Litematica 投影调研/崩服机制/限额+物理方块禁用方案 A+B/验证方法/三端同步状态）** | `references/worldedit-safety.md` |
> | **插件权限/指令清单（21 插件按组分组：指令全量+权限全量+组分配标注；脚本 `scripts/plugin_inventory.py` 可重复生成+定时更新；JSON 全量在 `~/.hermes/state/plugin_inventory.json`）** | `references/plugin-inventory.md` |
> | **三端配置差异审计（2026-08-11 三次全量对比；2026-08-12 起每周一 9:15 cron `ab06b886c39f`「三端配置审查」**v2：只审查不重启；**v3（2026-09-03 迁 MCSM 后）：本地端 = 本机 MCSM Paper 实例目录直读 + Exa + 远程 MCSM 三路并发**；脚本 `~/.hermes/scripts/orzmc_config_audit.sh`；保留最近两次报告；⚠️ 远程 MCSM 连续三周「未开启API密钥创建功能」= 远程面板 enableApiKey 未开，待老板远程修复；cmp3 工具链用法）** | `references/three-end-config-drift.md` |
> | **版本巡检 cron（每日 10:00，job `0b4298821a86`）：脚本 `~/.hermes/scripts/mc_version_check.py` 查核心+19 插件各渠道最新版 vs 本地部署 → 有差异发飞书询问用户** | 本 SKILL.md「版本巡检」段 |
> | **测试服 jar 升级 + 配置迁移 SOP（2026-09-12 实测沉淀）：双实例 MCSM API 全流程——内容寻址直链换核心 / `plugins/update` 换插件 / 插件 schema 自动迁移后按新版定义补键（`scripts/config_merge_defaults.py`，注释保留）/ jar sha256 回读验收 / 备份与 .bak 残留清理；含「Windows 栈 + Mac 副本」「easybot.yml 遗留键勿补」等坑；**2026-10-05 增补：投递统一走 `download_from_url`（upload 通道 403）、核心版本化命名 + `/start.sh` 自动识别（须 `exec java`；启动命令变更需老板面板操作）** | `references/test-server-upgrade-sop.md` |
> | **Docker 服务清单 / 重启自愈 / MCSM 实例手动启停（autoStart 回写坑、自动登录断点）** | `references/docker-service-lifecycle.md` |
> | **交上游的问题清单（已修/待修索引）** | `references/upstream-issues.md` |
> | **性能诊断（Spark 五步法、实体审计、Aikar Flags、修复方案）** | `references/performance.md` |
> | **MCA 级世界工具链（槽位粒度合并 `scripts/merge_worlds.py` / 加速命令方块扫描 `scripts/mca_scan_fast.py` / 区块高度分析 `scripts/mca_height_scan.py`；上游 OrzMCBackup 权威实现对应关系）** | `references/mca-toolchain.md` |
> | **插件 Bug 排查（本地复现、命令/权限分离、实体事件、版本兼容）** | `references/plugin-debugging.md` |
> | **测试体系（分层原则、三大通道、Paper 26 陷阱、跨服 transfer；**2026-09-03 迁 MCSM 本机栈后拓扑/五连坑/启停规范见该文头部与「MCSM 本地栈」节**）** | `references/testing.md` |
> | **LuckPerms 权限体系（API 集成、审计验收、三端同步、Bootstrap）** | `references/permission.md` |
> | **实体/传送门行为（事件继承、原版规则、白名单策略）** | `references/entity-portal.md` |
> | OrzMC 统一代码仓库（submodule 资产地图：插件源码/配置库/备份工具/世界瘦身；**Bot 命令调试 orzdebug + $e 输出捕获机制 + Log4J 坑**） | `references/orzmc-repo.md` |
> | OrzMC 真实环境验收报告（2026-08-06：全功能测试矩阵 + 双服 transfer + 发现的 bug） | `references/orzmc-acceptance-20260806.md` |
> **玩家手册（官方站 orzmc.{SERVER_NAME}.cn/user/ = OrzMCSite `content/user.md`）**：2026-08-15 合并新手指南（进服 3 步/基本操作/协作生态/四级权限成长/避坑FAQ/自定义皮肤），服务器地址用 server-status 组件动态卡片（不写死 IP）；site 是独立仓库 OrzMCSite，改手册 = 改 user.md → 单独 push main → CI 自动发布（Pages），主仓只 bump submodule 指针；本地 Hugo 用 **brew 版**（`/usr/local/bin/hugo` → Cellar 0.165.0，`+extended+withdeploy` 已在 PATH）；`./preview` 用 `command -v hugo` 查路径，**2026-09-12 实测 `hugo -d` 构建通过（93 页产物）**；（历史：`~/usr/local/bin/hugo` 孤儿副本 119MB —— brew 被 go pin 卡住时期的替代品，2026-09-12 已清理，brew 版同版本且多 withdeploy）；⚠️ **Hugo 默认静默省略 raw HTML（`<br>` 不渲染）**——排版别用 HTML 标签，纯 Markdown 列表/表格（移动端友好）；**2026-08-30 四级玩家指南发布**：四组各含职责/指令表/✅可做/❌不可做（独立小节+bullet）/升级路径，与权限重规划（L0 23/L1 19/L2 35/L3 37）联动；⚠️ **server-status shortcode 用 `tags=` 分组过滤（单点维护）**：params.toml 每台服配 `tags = ["players"]`/`["dev"]`，文档只写 `{{< server-status tags="players" >}}`——名称/地址变化只改 params.toml，文档零改动（2026-08-15 方案 B 落地 b80d8a7）；❌ 勿用旧 `servers=` 参数（按 name/host 精确匹配，中文名带 emoji 匹配不上 → `servers:[]` 空数组卡片空白；且名称/域名变化需改文档，多页面成本高）
> | OrzMC 功能测试用例（28 项，玩家命令/Bot 命令/事件拦截，含前置条件/步骤/预期） | 插件仓库 `plugin/docs/test-cases.md`（OrzMCPlugin） |
> | OrzMC 端到端测试报告（2026-08-06：机器人+真实玩家，28/28 通过，transfer 闭环） | 插件仓库 `plugin/docs/e2e-test-report-20260806.md`（OrzMCPlugin） |
> | RCON 客户端（`scripts/rcon.py <命令> [端口]`，密码从环境变量 RCON_PASSWORD 读） | `scripts/rcon.py` |
> | **实例端口审计（`scripts/port-audit.py [DATA_ROOT] [--probe] [--json]`：解析 InstanceConfig docker.ports + server.properties + Geyser config.yml 得出期望端口，标出必发布缺口/宿主端口冲突，可实时探测 Java+基岩双通道；退出码 1=有缺口）** | `scripts/port-audit.py` |
> | **基岩版连通性诊断（`~/OrzMC/proxy/scripts/bedrock_host_check.sh` bash 跨平台 / `.ps1` Win）**：双模式——本机诊断（默认，RakNet 握手+端口监听+进程+防火墙五项）与远程探测（传 host 即可，端口默认 19132，纯数字第一参=端口）；用法 `bash bedrock_host_check.sh [host] [port]`、PS `.\bedrock_host_check.ps1 [-HostAddr x] [-Port n]`；-h/--help 帮助；**定位法：本机 PASS+监听✅ → 问题在外部 UDP 转发；FAIL → Geyser 本身**；使用说明/修复记录文档同目录（基岩诊断脚本_使用说明.md、脚本问题修复记录_平台注意事项.md，v1.1 含 7 条真机坑）；坑：macOS netstat `udp46 *.19132` 格式、BSD pgrep 只出 pid 不能二次 grep（统一 ps aux+grep）、Windows Store python3 stub 检测、PS 需 UTF-8 BOM+`${Var}:` 写法、RakNet Pong MOTD 从偏移 34 到包尾 UTF-8（长度字段不可靠）；**2026-10-19 新增 `nethernet_check.py`（NetherNet 信令探测：UDP RakNet 基线 + TCP 信令 HTTP 探测 + 结论 + 退出码 0/1，`python3 nethernet_check.py [host] [port]`）**；⚠️⚠️ **本机经 Clash TUN 测 TCP 必假阳性**——域名被 fake-IP 成 `198.18.x.x`，TCP 握手被 TUN 本地接管后「接受并立即关闭」（脚本显示 `OPEN_NO_HTTP`，误判为端口可达）→ **必须用真实公网 IP（DoH 查：`https://1.1.1.1/dns-query?name=<域名>&type=A`）+ 外部节点验证**（`check-host.net/check-tcp?host=IP:PORT` 取 request_id 后查 `check-result/<id>`；外部节点一律 `Connection timed out` = TCP 未转发/未监听，若已转发但无监听则为 refused）；UDP 侧 check-udp 无意义（普通 UDP 包 Geyser 不回，只有 RakNet 专有包才 Pong） | `~/OrzMC/proxy/`（OrzMCProxy 子模块） |
| LP 权限命令清单生成（`scripts/gen_perm_commands.py`：从仓库 `plugin/docs/permission-groups.md` 唯一权威文档解析生成 lp set 命令；方案① 2026-08-12） | `scripts/gen_perm_commands.py` |
> | LoginSecurity 注册状态查询（`scripts/check_lsdb.py [db路径] [玩家名]`） | `scripts/check_lsdb.py` |
> | **GrimAC 最近作弊记录查询（`scripts/grim_history.py [--limit N] [--player 名] [--hours N] [--kicked-only] [--config]`；数据源=history.v1.db grim_violations JOIN grim_players/grim_checks，处理方式判定=日志 ±10s 内 GrimAC kick 记录；2026-08-31 建）** | `scripts/grim_history.py` |
> | LoginSecurity→AuthMe 数据迁移（`scripts/migrate_loginsecurity_to_authme.py [--ls-db X --authme-db Y] [--dry-run]`；BCrypt 哈希直接复用，AuthMe 须改 passwordHash: BCRYPT） | `scripts/migrate_loginsecurity_to_authme.py` |
> | GetMeHome→EssentialsC 数据迁移（`scripts/migrate_getmehome_to_essentialsc.py [--yml X --db Y] [--dry-run]`；homes.yml YAML→homes.db SQLite，字段一一映射） | `scripts/migrate_getmehome_to_essentialsc.py` |
> | PaperMC 插件 E2E 测试方案调研（MockBukkit/WatchWolf/GameTest/真实环境/容器化 + 推荐组合） | `references/plugin-e2e-testing.md` |
> | **命令方块/方块实体扫描（2026-08-18 入库；2026-08-22 并入 mc_cb_scan.py 第三套工具）：`scripts/scan_cmdblocks.py <世界目录> <out.json> [workers=8] [min_size=0]` 流式 NBT 解析提取命令方块+block_entities（workers=1 串行最稳，内存紧张宿主勿用多进程）；`scripts/analyze_cmdblocks.py <json>` 输出分类统计（类型/auto/维度/命令词频/被禁命令依赖/区域分布）；`scripts/mc_cb_scan.py run --world <世界> --out-dir <dir>` 一体化扫描→CSV→自动 Markdown 报告（统计/集群/指令分类/异常/迁移要点，自带 Folia 禁用指令交叉核对，纯标准库零依赖）；三件套对比与用法见 `references/command-block-inventory.md`** | `scripts/scan_cmdblocks.py` + `scripts/analyze_cmdblocks.py` + `scripts/mc_cb_scan.py` |
> | **ExecutableEvents 实测（2026-08-19，3.26.8.10+SCore 5.26.8.10 on Folia 26.2-4）：加载✅ 事件监听不触发❌（PLAYER_WALK/PLAYER_JUMP_EVENT/debug 全零输出，sevents 与 Folia 分区线程不兼容）→ 插件替代命令方块方案整体不可行；⚠️ SCore 硬依赖（plugin.yml 注释 depend 但代码需要）；⚠️ events/ 一文件一事件；⚠️ 防重登限制=GriefPrevention3D Spam.LoginCooldownSeconds** | `references/folia-experiment.md` |
> | **群消息样式规范（2026-08-19 PR #197 统一）：表情标题+33 连字符分割线+版块式排版；四类消息模板键与格式表；聚合摘要空版块省略/单人无人数/多人(N)；改模板 4+1 联动清单（templates.yml+Templates.java+ReviewNotifierAdapter fallback+占位符白名单+测试）；存量服改键值须手动同步 templates.yml+reload；真实环境验证法（bot 触发+easybot 投递查询）；Folia 测试服操作坑（screen stuff stop 不可靠→RCON、防多实例、--rerun-tasks 强制重打）** | `references/group-message-style.md` |
> | **跨网互联/中转方案（电信服×联通移动玩家；FRP 中转 + PROXY protocol 真实 IP 透传；部署资产在 `OrzMC/proxy` 子模块 = OrzMCProxy 仓库：install-frp.sh/ps1 一键安装、verify-tunnel.sh、health-check.sh、bedrock_ping.py、mc_login.py、**relay-monitor.sh 外部隧道监控（formal/temp 双档看门狗，2026-08-14 本地双模式验收 100% 通过）**、configs 模板、systemd/launchd/Windows 计划任务、manual-apply-windows.md 手动改法）** | `references/cross-carrier-networking.md` |
> | **平台层迁移（orzmc-deploy 栈换机/Windows 全新部署：端口架构 8080 归属 easybot 只 expose、打包命令序列 + backup dump 竞态坑（先等 mariadb ping 再 backup）、Windows 旧独立 easybot 占 8080 冲突、macOS SMB 共享名中文坑 + 选项启用账户；Windows 还原两坑：restore.sh 大归档 SIGPIPE(exit 141，手工还原绕过)+ mariadb 冷数据 healthcheck 缺 `mysql@localhost` socket 账号(补建即 healthy)；2026-09-09 Mac→Windows 迁移实录，执行提示词 `~/hermes-windows-migration-prompt.md`；**末节 = OrzMusic 生产升级实操**（gh 下载包原生路径坑、Windows 无 make 直接调脚本、IMAGE_REF/BACKUP_DIR 必传、preflight 单跑假 FAIL、smoke 第 3 节 curl 23 假 FAIL））** | `references/platform-migration.md` |
> | **世界高度调整（1.18+ 高度是 worldgen 属性非服务器配置；CustomWorldHeight 插件方案 2026-08-15 本地实测通过 height=1088；硬限制 min_y≥-2032/height≤4064/min_y+height≤2032；RCON setblock 边界验证法）** | `references/world-height.md` |
> | **Folia 迁移实验（2026-08-17 本地双服实测：兼容矩阵 20 jar→18 全绿；9 不兼容插件平替方案含合并策略；LoginSecurity→AuthMe 359 账号 / GetMeHome→EssentialsC 879 home 数据迁移；❌ Hangar API 不能查 Folia（supportedPlatforms 只标 PAPER），检索用 Modrinth loaders 含 folia；Folia 26.2 目前仅 BETA；2026-08-18 全面接管原测试服（端口 25565/19132 + 地图 symlink + 配置/权限/白名单全量同步）；⚠️ ~~两服共享 world symlink（folia→paper），严禁同跑~~ → **2026-09-11 更正：容器化后两实例已是两套独立地图，可同时运行**（容器各挂自己的 `InstanceData/<uuid>`；同宿主并存时只需错开宿主端口，详见 `references/instance-ports.md`）；⚠️ 命令方块被 Folia 架构性禁用（#429/#485 not_planned）；⚠️⚠️ log4j2 自定义配置必须 start.sh JVM 参数 -Dlog4j2.configurationFile 指定（config/ 下不会自动加载）；CustomWorldHeight 已移除（全量扫描 0 高空数据，1088 格式区块随加载自然收敛 384）；Essentials tpa 漏配 tpaccept 已修复；**PlayerPortalEvent Folia 不触发已解决（PR #195 合并 b7d4b86：PlayerMoveEvent 补偿路径，几何=内部格脚底+1 起须身体两格匹配+水平精确命中，5s 双路径共享冷却，详见「传送门 transfer 补偿方案」小节）**）** | `references/folia-experiment.md` |

> **附录索引 · 其余参考文档（按主题分组）**：主索引已列常用文档，以下是专题/历史类文档，按需查阅：
>
> | 主题 | 文档 | 内容 |
> |:--|:--|:--|
> | 巡检报告与案例复盘 | `references/config-drift-report-20261005.md` | 巡检日期：2026-10-05（周一 9:00 周巡检，脚本 cmp3 自动生成，基准端 = MCSM jokerh |
> | 巡检报告与案例复盘 | `references/config-drift-report-20261012.md` | 巡检日期：2026-10-12（周一 周巡检 · 补跑版，脚本 cmp3 自动生成，基准端 = MCSM joker |
> | 巡检报告与案例复盘 | `references/config-drift-report-20261019.md` | 两端配置漂移报告 · 2026-10-19（周巡检） |
> | 巡检报告与案例复盘 | `references/context-trap-case-study.md` | 上下文脏数据根因链（joker / TestMember 案例实录） |
> | 巡检报告与案例复盘 | `references/deathchest-fix.md` | DeathChest 3.0.1 修复案例（死亡瞬间下线 → 物品永久丢失） |
> | Rank 与权限体系 | `references/lp-api-bootstrap-correction.md` | LuckPermsBootstrap 校正模式 + 权限名核实（2026-08-08 实战） |
> | Rank 与权限体系 | `references/luckperms-api-integration.md` | LuckPerms API 软依赖集成（2026-08-07 权限链重构实战） |
> | Rank 与权限体系 | `references/luckperms-track-api.md` | LuckPerms track API 与权限链设计（2026-08-07 决策记录） |
> | Rank 与权限体系 | `references/orzmc-rank-system.md` | OrzMC 权限系统（rank-promotion 二期）细节 |
> | Rank 与权限体系 | `references/perm-group-config.md` | 权限组配置（指针版 — 2026-08-12 方案①收敛） |
> | Rank 与权限体系 | `references/plugin-default-perms.md` | 插件默认开启权限盘点（2026-08-08） |
> | Rank 与权限体系 | `references/rank-lp-integration.md` | OrzMC Rank 模块 LP 集成：幂等与状态验证（2026-08-07 实测） |
> | Rank 与权限体系 | `references/rank-playtime-data-source.md` | OrzMC Rank 玩家在线时长数据源调研（2026-08-07 实测，最终方案已验证） |
> | Rank 与权限体系 | `references/rank-status-display.md` | 权限状态展示动态化 + LP track 数据卫生（2026-08-07 权限二期收尾实测） |
> | Bot 与测试 | `references/easybot-delivery-verify.md` | 验证 EasyBot 通知发送（API，0.0.33+） |
> | Bot 与测试 | `references/orzmc-bot-command-testing.md` | OrzMC Bot 命令测试 & 控制台注入（2026-08-06 实测） |
> | Bot 与测试 | `references/orzmc-e2e-robot-testing.md` | OrzMC 权限审核框架 · 机器人自动化 E2E 测试（2026-08-07） |
> | Bot 与测试 | `references/papermc-26-testing-pitfalls.md` | Paper 26 测试踩坑明细（2026-08-07 权限系统二期 E2E 实测） |
> | 构建与升级 | `references/dependency-upgrade-audit.md` | 插件依赖升级核查（发版前审计，2026-08-07 实测方法） |
> | 构建与升级 | `references/ezshops-maven-build.md` | EzShops 本地构建与部署（2026-08-09） |
> | 构建与升级 | `references/loginsecurity-build.md` | LoginSecurity 构建与 AuthModeChangedEvent 排查（2026-08-10） |
> | 构建与升级 | `references/upgrade-playbook.md` | OrzMCDeploy 版本升级规程（实战：0.0.3 → 0.0.4，0.0.4 → 0.0.6） |
> | 实体 / 传送门 / 传送弓 | `references/entity-diagnostics.md` | 服务器侧实体统计与卡顿定位（配合 bot 使用，2026-08-04 实测） |
> | 实体 / 传送门 / 传送弓 | `references/orzmc-entity-teleport-tnt.md` | OrzMC 实体传送可配置化 + TNT 通知聚合（2026-08-09） |
> | 实体 / 传送门 / 传送弓 | `references/teleport-bow-chunk-analysis.md` | 传送弓「未加载区块无法传送」根因分析（2026-08-08 实测定案） |
> | 插件来源与发布 | `references/orzmc-plugin-hangar.md` | OrzMC 插件版本渠道与升级（2026-08-04 实测，本地测试服） |
> | 插件来源与发布 | `references/plugin-sources.md` | 插件发布渠道清单（Modrinth / Hangar 覆盖情况） |
> | 代码审查与验收 | `references/orzmc-review-acceptance.md` | OrzMC 审核框架本地验收（2026-08-07，已全部闭环） |
> | 代码审查与验收 | `references/orzmc-review-framework.md` | OrzMC 通用审核框架（权限系统二期，2026-08-07 落地） |
> | 代码审查与验收 | `references/pr-review-checklist.md` | OrzMC 插件 PR 代码审查清单（2026-08-07 PR #160 review 沉淀） |
>
> **📁 脚本位置约定（找脚本前先看这里）**：
> - `scripts/…`（不带 `~/` 前缀）= **随本技能分发**的脚本，真实路径 `~/.hermes/skills/gaming/orzmc/scripts/`
> - `~/.hermes/scripts/…` = **主机级 cron 脚本**（版本巡检 `mc_version_check.py`、配置审查 `orzmc_config_audit.sh`、`grim_kick_ban.py` 等），不在技能目录内
> - `~/OrzMC/proxy/scripts/…` = **OrzMCProxy 仓库**脚本（`bedrock_host_check.sh/.ps1`、`bedrock_ping.py`、`nethernet_check.py`、`relay-monitor.sh` 等）
> - `~/minecraft-bot/…` = 机器人测试脚本（mineflayer）
> - `scripts/skill_self_check.py` = **本技能自检**（frontmatter / 死链 / 孤儿文档 / 超长行 / 私有信息计数），改完技能跑一次，期望 `结果: PASS`
>
## 最近变更（v2.x）

| 版本 | 日期 | 变更 |
|:--|:--|:--|
| 2.1.0 | 2026-10-19 | 全面 review：30 篇专题/历史文档补齐分组索引（0 孤儿 0 死链）；7783 字「插件基线」巨型条目外置为 `references/plugin-baseline-legacy.md`（零信息丢失）；修正 26.3 口径（ALPHA→STABLE、Folia 26.3 已出、Geyser 已可用）；新增「脚本位置约定」 |
| 2.0.7 | 2026-10-19 | 第四轮测试服升级基线（Paper 26.3-205 / WE 7.4.6 / WG 7.0.20 / Geyser 2.12.0）+ 新增 `references/nethernet.md`（NetherNet 迁移）+ 升级包交付规范 §2g + Exaroton 核心面板托管事实 |
| 2.0.6 | 2026-09 | 第三轮升级（26.3 实验态）+ 多处巡检/权限/商店知识合并 |

## 三端拓扑（2026-10-19 老板确认，权威）

| 端点 | 域名 | 托管方式 | 角色 / 说明 |
|:--|:--|:--|:--|
| **本地测试服** | `dev.{SERVER_NAME}.cn` | 本机 MCSM 面板（Win 宿主 `E:/orzmc`；实例 `papermc-test` + `folia-test`） | 升级/插件/基岩/NetherNet 的实测场；家宽动态 IP + DDNS；官网 `show_address=false`（地址隐藏） |
| **国内服（线上生产）** | `{SERVER_HOST}` | **MCSM 面板托管** | 国内玩家生产环境；运维走 MCSM API |
| **海外服（线上生产）** | `paper.{SERVER_NAME}.cn` | **Exaroton 托管** | 海外玩家生产环境；核心由面板管理（不能上传核心 jar），插件走 `plugins/update/` |

**已下线**：腾讯云中转机 2 台（正式 + 试用，2026-10-19 老板确认销毁）→ **frps 中转链路不再运行**；`references/cross-carrier-networking.md` 中的方案/工具链仍可复用，重建时按该文顶部清单执行。
**已核实（2026-10-19，本机 Windows 宿主实查）**：无 frpc 计划任务（`schtasks` 无匹配）、无 frpc 服务（`sc query` 无匹配）、无 `~/OrzMC/proxy` 目录 → **该宿主未部署 frpc 客户端，不存在指向旧中转 IP 的残留配置**。

**查询现状的可靠方法**（本机 Clash TUN 会把域名解析成 `198.18.x` fake-IP，`ping`/`nslookup` 结果不可信）：
```bash
curl -s -H 'accept: application/dns-json' \
  'https://1.1.1.1/dns-query?name=<域名>&type=A'
```

## 使用时机
- 用户要创建新的 PaperMC 服务器（本机/Exaroton/MCSM）
- 用户要升级 PaperMC 服务端版本或构建
- 用户要安装/更新/卸载插件
- 用户要备份或查看服务器状态/日志
- 用户要排查性能/卡顿（→ `references/spark-analysis.md`）
- 用户要统计实体或定位 FPS 问题（→ `references/entity-statistics.md`）
- 用户要机器人玩家/自动操作（→ `references/mineflayer-bot.md`）

## 架构：一套动作，三种后端

```
统一动作: create / status / start / stop / restart / logs
         upgrade / plugin / backup / command
              │
    ┌─────────┼──────────┐
    ▼         ▼          ▼
  local    exaroton    mcsm
  本机目录   云端API    面板API
```

后端通过环境变量 `PAPER_BACKEND` 选择（默认 `local`）：
- `local` — 本机目录操作（`PAPER_DIR`）→ `references/local-backend.md`
- `exaroton` — Exaroton 云端（`EXAROTON_API_KEY` + `EXAROTON_SERVER_ID`）→ `references/exaroton-backend.md`
- `mcsm` — MCSManager 面板（`MCSM_URL` + `MCSM_API_KEY` + `MCSM_INSTANCE_ID`）→ `references/mcsm-backend.md`

## 关键事实（滚动更新，最新基线 2026-10-19）

> 🔄 **本地测试服拓扑 = MCSM 本机栈（2026-09-03 全量迁移完成）**：原裸跑 `~/minecraft-server`/`~/folia-test`（start.sh/screen 启动）已删除，测试服改由本机 MCSM 面板 **mcs.{SERVER_NAME}.cn** 管理——双 Docker 实例 **`papermc-test`**（uuid `716c2fb712154c36ba5ab0f1480d3f87`，Paper 26.2）与 **`folia-test`**（uuid `8A932DD47F4D42AAAD6A6A9A5FAD2A91`，Folia 26.2），**各自独立地图，可同时运行**（2026-09-11 核实：两容器各挂自己的 `InstanceData/<uuid>`，无共享 world 卷；`world` 目录 inode 不同、各 ~2.1G；实测 Paper 25565/19132 + Folia 25566/19133 同时在线双通道均通）。实例数据在宿主 `/Users/Shared/orzmc/mcsmanager/daemon/data/InstanceData/<uuid>/`（含 server.properties/plugins/logs 完整服务端，**宿主侧直接可见可操作**）。**本 SKILL 中所有「本地测试服/本地双服/本地已改+重启」如无特别说明均指这两个实例**（jar/插件部署 = 直接 cp 实例目录 + 面板重启实例；启停 = 面板操作）。五连坑/克隆实例法/详细路径见 `references/testing.md`「MCSM 本地栈 Docker 实例」节。
>
> ⚠️⚠️ **2026-09-12 拓扑更正：面板栈本体已迁 Windows（`E:/orzmc`，见 `references/platform-migration.md`）** —— `mcs.{SERVER_NAME}.cn` 现指向 Windows 上的 MCSM（web `10.18.0` / daemon `4.18.0`），Mac 上 `/Users/Shared/orzmc/...` 只是**迁移前的历史副本（勿直读、勿据此判断线上状态）**；Mac 已无 docker。**操作一律走 MCSM API**（凭据 `~/.hermes/.env` 的 `MCSM_LOCAL_*`）：`instance.status` 3=运行中 / `files/list|download|mkdir|copy|move|delete` / `files/download_from_url` / `files/upload` / `protected_instance/open|stop|command`。升级实测流程 + 配置迁移 + 备份清理 → `references/test-server-upgrade-sop.md`；配置补键工具 `scripts/config_merge_defaults.py`。
> ⚠️ **面板可达性依赖 Windows 侧 `cloudflared` 隧道**：2026-09-28 / 10-12 两次 `HTTP 530 + error 1033`（Argo Tunnel error）故障 → **周巡检静默空转**（配置拉取 0 文件、版本巡检部署侧全空，脚本仍报 `ok`）。**老板已于 2026-10-12 在 Windows 侧加自愈守护**。排查法：`curl -o /dev/null -w '%{http_code}' https://mcs.{SERVER_NAME}.cn/`（同域 `orzmc.{SERVER_NAME}.cn` 200 而 mcs 530 = 仅面板隧道故障）；⚠️ **巡检报告若出现「MCSM 端 0 文件 / 全部插件未部署」= 故障信号，须先探面板再下结论**。
>
> **测试服版本基线（⚠️ 历史快照 2026-09-20，仅作演进参考；**当前权威 = 本段 2026-10-19 基线行**）**：两实例均 **26.2 线 + Java 25**，插件走 **dev/beta 轨道**（老板决策：测试服用于开发测试验证插件功能）——**Geyser-Spigot build 1245（2.11.3）**、**LuckPerms 5.5.85**、**ViaVersion/ViaBackwards 5.12.0**、**ViaRewind 4.2.0**、**WorldGuard 7.0.19**；OrzMC paper **1.0.27-dev.422**（启动自更新确认「已是最新」）/ folia **1.0.25-dev.416**（启动后未落自更新日志，**待手动补或下次重启确认**）；papermc-test 额外 Paper **26.2-126**（STABLE）+ voicechat **2.6.23**；folia-test 额外 Folia **26.2-7**（该分支最新，**Folia 尚无 26.3**）+ AxGraves **1.31.0** + EssentialsC **4.3.0** + GriefPrevention3D **18.4.4** + ExecutableEvents **3.26.9.17** + SCore **5.26.9.17** + VaultUnlocked **2.20.3**。
> 🆕🆕 **2026-10-19 第四轮升级后基线（最新权威，实测自启动日志）**：**papermc-test** = Paper **26.3-205（STABLE）+ WorldEdit 7.4.6 正式版 + WorldGuard 7.0.20 + Geyser 2.12.0-b1265（26.3 上首次成功启用）+ OrzMC 1.0.29-dev.427 + LuckPerms 5.5.87 + Via 5.12.1 + packetevents 2.14.0 + grimac 2.3.74-abb95b6 + voicechat 2.6.24**；**folia-test** = Folia **26.2-7**（26.3 仅 ALPHA 未采用）+ Geyser 1265 + EssentialsC 4.3.4 + ExecutableEvents 3.26.10.17 + SCore 5.26.10.17 + GriefPrevention3D 18.4.14 + **WorldEdit 7.4.5 / WorldGuard 7.0.19（故意不升：WG 7.0.20 元数据只标 26.3）**。→ **26.3 就绪门槛 6 项已解除 2 项（WE 正式版 ✅ / Geyser ✅）**，仍缺 EssentialsX 正式版、GrimAC 正式 release、F3F4Perms/SimpleLogin 元数据；实录与 8 条新坑见 `references/test-server-upgrade-sop.md` §2f。
> 🆕 **2026-10-12 第三轮升级后基线（历史，实测自 `logs/latest.log`）**：**papermc-test** = **⚠️ 已按老板决策切到 26.3 实验态：Paper 26.3-177 + WorldEdit 7.4.6-beta-02（Geyser 1251 在 26.3 上不可用被迫禁用；**2026-10-19 已由 b1265 解决**）**（26.3 之前的 26.2 态 = Paper 26.2-133 + WE 7.4.5，两者产物与备份均在 `/upgrade-bak-20261012-263/` 与 `/tmp/orzmc_263_check/`；详见 `references/test-server-upgrade-sop.md` §2e「26.3 实测 + 决策」）；**folia-test** = Folia **26.2-7**（**Folia 当时无 26.3**（2026-10-19 已出 26.3-3，仅 ALPHA））+ Geyser-Spigot **build 1251** + Via 双件 **5.12.1** + EssentialsC **4.3.3** + ExecutableEvents **3.26.10.10** + SCore **5.26.10.10** + GriefPrevention3D **18.4.12** + AxGraves 1.32.1 + OrzMC 1.0.29-dev.427。26.3 前的两实例 26.2 态：paper 26.2-133 + Geyser 1251 + Via 5.12.1 + OrzMC 1.0.29-dev.427 + LuckPerms 5.5.87 + packetevents 2.14.0 + voicechat 2.6.24 + WorldEdit 7.4.5 + WorldGuard 7.0.19 + GrimAC 2.3.74-abb95b6。备份 `/upgrade-bak-20261012` 保留、实例停回停止态；升级实录与 6 条新坑 → `references/test-server-upgrade-sop.md` §2d。
> 🔴 **Exaroton（生产端）jar 严重落后（2026-10-12 首次盘点，此前巡检**从不查 Exa 侧 jar**——只对比配置）**：⚠️ **Exaroton 核心由面板管理（根目录只有 `.paper` 目录、无核心 jar）→ 核心版本只能面板选，不能上传 jar**；插件仍走 `plugins/update/`。2026-10-19 复核现状：OrzMC **1.0.24**（config-version 12）、Geyser-Spigot-**1230**、ViaVersion/ViaBackwards **5.11.0**、ViaRewind 4.1.3、LuckPerms **5.5.77**、packetevents **2.13.0**、worldguard-bukkit-7.0.18、GetMeHome 3.0.0-4、SkinsRestorer.jar（无版本名）；**无 GrimAC（老板决策：生产端不加反作弊）**、无 voicechat。→ 已建「有意差异白名单 + 待执行表」见 `references/three-end-config-drift.md`；**建议给周巡检加 Exaroton jar 盘点**（缺口项）。
> 🔴 **Via 三件套必须 ≥ 5.12.0**：5.11.0 只支持到 MC 26.2，**5.12.0 才支持 26.3 客户端**——玩家官方启动器自动升级到 26.3 后旧版接不住（比升核心更紧急）。
> 🔴🔴 **但 26.3 客户端目前「能进却会被 GrimAC 踢」（2026-09-20 实测）**：GrimAC 2.3.74 内置（shaded/relocated）packetevents 只到 26.2 → 26.3 客户端一进服就 `Unknown entity metadata type id: 105 version V_26_2`，GrimAC 状态被污染后**误报 BadPacketsN 并踢人**。上游 packetevents 的 26.3 支持 09-19 才合入 main（**未发版**，最新 release 仍 v2.13.0）、GrimAPI 最新 v1.6.0.12（09-03）早于该合并 → **GrimAC 目前无解**。
> 🔄 **2026-10-12 事实更新（巡检实测，老板确认）**：packetevents **v2.14.0（09-23）已发版并支持 26.3**；**GrimAC main 分支 2026-09-28 已合 `support 26.3 (#2888)`** —— 老板原话「**有开发版支持 26.3，不过不是稳定发行版**」（Modrinth alpha 2.3.74-f5bbe9c 10-07 metadata 仍只到 26.2，最新 **release 仍 v2.3.73**）→ **主干可用、无正式 release**；**Paper 26.3-177 已于 2026-10-12 转 STABLE 通道**（通道不再是阻塞）。→ 处置结论：**三端维持 26.2 线**（paper 26.2-**133**），Via 用 `block-versions: [">26.2"]` 干净拒绝 26.3 客户端，**等 GrimAC 正式版解禁**。**执行方式**：Via `config.yml` 的 `block-versions: [">26.2"]` + `block-disconnect-msg` 自定义提示（改后 `/viaversion reload`）干净拒绝 26.3 客户端；⚠️ 生产端若最终要升 Via 三件套，**必须与 block 配置同时上**，否则 26.3 客户端从「被干净拒绝」变成「进来后被误踢」（体验更差）。详见 `references/upstream-issues.md`「26.3 协议生态缺口」。
> ⚠️ **核心通道纪律（老板 2026-09-20 拍板）**：核心只升 **STABLE**（当时 = 26.2-126）；**26.3 线当时（09-20）仅为 ALPHA**；**2026-10-17 起 26.3 已转 STABLE**（26.3-205），测试服已采用，生产端待门槛全绿。paper 实例 `im.yml` = `backend: builtin`（QQ/飞书凭据）+ `i18n.default_lang: en-US`；folia 实例 = `backend: easybot` + `zh-CN` —— **⚠️ 此差异是老板 2026-09-12 明确确认的刻意设计（paper 专测英文语言包 + 内置直连通道，folia 测 EasyBot 网关），两条 IM 通道并行保留：勿统一、勿改语言（`default_lang` 只管群消息/广播/维护文案，游戏内文案跟随客户端 locale）**。

- **旧 API `api.papermc.io/v2` 已完全废弃（410 Gone）**——用 fill-data 新机制（`parse_papermc.py` 封装）
- **最新稳定版（2026-09-20 实测）**：**paper-26.2-126**（STABLE 通道；本地 papermc-test 已升，`Paper version 26.2-126-ver/26.2@c646faf`，sha256 `9c95eb08…`；同线 124/125 亦为 STABLE）；**26.3 已于 2026-10-17 转 STABLE（最新 26.3-205）**；09-20 当时为 ALPHA，老板拍板暂不采用，10-19 测试服已升级采用；**Folia 26.2-7**（folia-test 部署中，Folia **尚无 26.3**）；**Java 要求**：26.x 需要 Java 25；远程三端（Exaroton/MCSM）仍需按需同步
- ⚠️ **PaperMC 通道判定（新）**：fill API 的 build 对象带 `channel` 字段（STABLE/BETA/ALPHA）——「最新版」不等于「可上线版」，升级前先看 channel；本会话脚本查询：`https://fill.papermc.io/v3/projects/paper/versions/26.2/builds/latest`
- **插件基线（历史快照 2026-08~09，完整版已外置）**：OrzMC 1.0.17→1.0.24 演进、EzShops 2.5.9（yaml 存储）、voicechat 2.6.21、**GrimAC 渠道/处罚阈值/VL 语义/误报源/6 分类 kick 实测**、LoginSecurity `ls.bypass` 事件、LuckPerms/SkinsRestorer/WE 限额等全部细节 → `references/plugin-baseline-legacy.md`；GrimAC 调优专项 → `references/grimac-tuning.md`。**当前版本一律以上方 2026-10-19 基线行为准。**
- **GeoIP 内网误拦截（2026-08-06 修复，OrzMC 1.0.15）**：MCSM allow_country_code=[CN,JP,TW] 时内网玩家（192.168.x/10.x）被拦截——geojs.io 无法解析私有段返回未知国家码。1.0.15 加内网 IP 短路（RFC1918/环回/CGNAT 直接放行，公网仍检查）。OrzMC 配置读取为实时（改 config.yml 后 **`/config reload` 即生效**，无需重启；⚠️ 2026-08-11 修正：命令是 **`/config reload`（根命令 `config`，别名 `cfg`，源码 FeatureModule.java `commands.register(node, "配置管理", List.of("cfg"))`）**，技能旧写 `/orzconfig reload` 是错的——实际执行返回 Unknown）；临时缓解=allow_country_code 改 []。⚠️ **`/config set` 改不了国家限制（2026-08-13 源码实证）**：`geoip.allow_country_code` 未注册进 `ConfigPath` 注册表（22 项只覆盖 whitelist/maintenance/tnt/command_policies/easybot/templates），且 `OrzConfigCommand.parseValue` 只支持 Boolean/Integer/Long/Double/String **不支持 List** → 只能改 config.yml + `/config reload`。同理 **`permission.yml` 的 `config.member-threshold-hours`（default→member 自动晋升阈值，默认 10 小时）也改不了 `/config set`（未注册），且是构造注入**（FeatureModule 装配时 `RankService(permissionStore, ..., memberThresholdHours(), ...)` final 字段）→ 改文件后**必须重启**才生效（reload 无效）；时长数据源是服务器原生 stats（`world/players/stats/<uuid>.json` 的 `minecraft:play_time`，tick÷1200=分钟）。`command_policies.tpbow.admin_only`（Boolean）是**唯一能 `/config set` 的注册路径**（`/config set command_policies.tpbow.admin_only true`=普通玩家禁用传送弓），但拦截器链装配时固定 → 同样**需重启生效**
- ⚠️⚠️ **改 `permission.yml` 必须「先 reload 再重启」，否则修改被回写覆盖（2026-08-15 源码实证）**：`permission` 配置在 `ConfigService.setup()` 被 `markAlwaysSave("permission")`；服务器停止时 `onDisable→tearDown→configService.tearDown→saveDirtyConfigs()`（ConfigManager L101）会遍历 alwaysSave 配置**用内存快照整体写回磁盘**；而内存快照是启动时 `registerConfig` 加载的旧值 → 运行中手动改文件不 reload，重启时旧值覆盖新值，修改丢失。**且运行中 `PermissionStore.save()`（玩家提交审核）也调 `saveConfig` 同理会覆盖**。正确流程：① 改 permission.yml → ② `/config reload permission`（磁盘新值读进内存）→ ③ 重启（写回新值+装配生效）。验证：重启后 grep 日志或 `/config dump` 确认新值
- ⚠️⚠️ **`member-threshold-hours` 的隐藏语义（2026-08-15 源码实证，OrzMC 1.0.17）**：① **0 值 = 进服秒升 member**——`checkPromotion()`（玩家上线异步触发，OrzRankEvent.onPlayerJoin）判定 `playtime < memberThresholdMinutes()`（=0×60=0）永远 false，新玩家（无 stats 文件返回 0）也满足 → 只要当前组是 default 立即 `promote()`；LP track 幂等（已是 member+ 不重复升），一次性不回退。② **不支持小数**——`PermissionStore.memberThresholdHours()` 返回 `int`（`cfg.getInt`），YAML 写 `2.5` 被 Bukkit **静默截断**为 `2`（Number.intValue() 不四舍五入）；写 `"2.5"`（字符串）parseInt 失败**回退默认 10**；`0.5` 截断成 `0` = 秒升。想要半小时级粒度需改源码（RankService L28 `final int` → double + L86 `* 60L`）。判定链路：RankService.checkPromotion L65-77 → OrzRankEvent.onPlayerJoin（异步，不阻塞主线程）→ stats 时长源 `world/players/stats/<uuid>.json`
- **维护文案模板化（2026-09-02，#236 已合，OrzMC 1.0.24-dev）**：维护 MOTD 文案从 config.yml maintenance 段迁到 **templates.yml**（`maintenance_motd_backup/optimize/manual` 场景文案 + `maintenance_motd_progress_line` 进度行，占位符 `{stage}/{percent}/{eta}`）；**MOTD/登录拦截/踢人 4 处统一走 `MaintenanceModeService.renderMotdText`**（无进度时占位符自动清空防字面量；场景模板含占位符则不追加独立进度行；未写占位符且 backup/optimize 有进度自动追加 progress_line 行；默认值带场景词：backup=「服务器地图备份中，请稍后再试」）；**改文案 = 编辑 templates.yml 4 键 → `/config reload` 热生效**（不再支持 /config set）；⚠️ 升级时旧 config.yml `maintenance.*_maintenance_motd` 自定义值须手动搬运到 templates.yml；模板缺失走代码 fallback 零告警（同 prison 键策略，不入 TemplateKeys.ALL）
- **prison 坐牢权限组（2026-09-02，#235 已合，OrzMC 1.0.24-dev）**：作弊玩家过渡手段——坐牢=全禁权限（仅聊天+牢房传送），不封号。**操作**：`/prison <玩家> on|off`（管理员；恢复玩家原组+原位置）；**配置**：config.yml `prison.cell_location: world,x,y,z[,yaw,pitch]`（各服独立，改后 /config reload；默认 world,0,100,0 是空中示例值正式须配封闭牢房；未配置/世界未加载/坐标非法回退玩家世界出生点）；**特性**：坐牢玩家走 LuckPerms prison 组（独立 track，重进**不自动回四级**——RankService.checkPromotion 跳过 prison 玩家；原组存 meta 键 `prisoner_original_group`）；**守卫/拦截（review 加固）**：LuckPermsPromoter promote/demote 对坐牢玩家拒绝（防手动升降级删节点放出牢房）；PrisonDenyInterceptor 拦截 tpbow/guide/menu/portal/apply/rank 等移动工具命令；LP 落库失败内存回滚；join 延迟 tp 兜底；**群消息**：prison_imprisoned/prison_released 模板键（templates.yml，排除 TemplateKeys.ALL 缺失走代码 fallback 零告警）；⚠️ 管理员升降级坐牢玩家须先 /prison off 释放
- **备份/优化完成消息耗时中文可读化（2026-08-13，PR #171，OrzMC 1.0.17-dev）**：`WorldMaintenanceService.formatDuration(ms)` 毫秒→中文分级（<1秒=`854毫秒`、<1分=`35秒`、<1小时=`2分35秒`、≥1小时=`1小时2分3秒`；秒四舍五入、负值按0、小时级补0分占位如`1小时0分5秒`）。done/error 模板新增变量 `duration_human`（**保留 `duration_ms` 兼容旧模板**）；模板键=4 处联动：`templates.yml` 默认值 + `Templates.java` fallback + `TemplatePlaceholderValidator` 白名单 + `WorldMaintenanceService` 传参（⚠️ **漏注册白名单 → ConfigHealthCheck 测试挂**，报「模板变量未知: templates.maintenance_backup_done {duration_human}」）
- **MC 26.2 原生命令/聊天防刷（2026-08-12 反编译实证）**：server.properties `command-spam-threshold-seconds` / `chat-spam-threshold-seconds`（26.2-pre1 起，默认 10）。**真实机制（勿被名字误导）**：不是「每秒 N 条」，而是**爆发计数器**——`TickThrottler(20, 20×N)`：每条命令计数 +20，每 tick 衰减 -1（排水≈1 命令/秒），计数 ≥20×N 时踢出 `Kicked for spamming`。→ 任何持续 >1 条/秒的命令流迟早踢；45 条/秒时阈值 100 也只撑 ~2.3s。**OP/单人房主豁免**（bytecode：isOp 检查跳过踢出）→ 管理员永远遇不到。⚠️ **设 0 反而每条命令都被踢**（TickThrottler.isIncrementAndUnderThreshold 缺 0 保护，GitHub issue #14114）→ 要放宽用大数值，别设 0。触发实例：Litematica 粘贴原理图默认走 `pasteUseFillCommand`（/fill 流 45-104 条/秒）→ 反复被踢（阈值 100 只撑 ~2.3s，治标不治本）。**配置解法（2026-08-12 已落地三端）**：踢出时间 t=N/(R−1) 秒，要解决需 **N > 峰值速率 × 最长连续粘贴秒数**；三端 server.properties 已统一设 **100000**（104 条/秒时连续 ~16 分钟才触发，正常建筑完全无感）；替代解：WorldEdit `//paste`（一条命令）、关 pasteUseFillCommand 改逐方块放置、或给玩家 OP（豁免）。另：server 启动会重写 server.properties 头部时间戳但保留值（PUT 改文件→重启流程安全）。
- **权限系统（2026-08-06 实施，LuckPerms 4 组）**：default(新手生存)→member(进阶飞行)→builder(创造+WE)→admin(全权限)；坑：RCON 不回显 LP 命令输出（用 bot 玩家身份验证）、default 勿显式设 false 覆盖子组 true、Essentials 权限默认拒绝。**2026-08-29 实测补：gamemode 权限真值（essentials.gamemode 子权限独立）+ admin 补 essentials.gamemode.spectator（PR#229）+ builder/admin 降级后 gamemode 矫正方案立项**。**2026-08-30 实测补：builder 组无 `worldedit.limit` 权限（//limit 显示 Unknown/被隐藏）→ 单次编辑 100 万方块为硬上限，玩家无法调大（配合 WE 限额方案 A）**。**2026-08-30 重规划（老板审核通过）**：四组增量 L0 23/L1 19/L2 35/L3 37——L0 +10 生存工具（rules/motd/list/depth/compass/getpos/recipe/hat/near/seen）、L1 +5（tpdeny/tpacancel/ptime/pweather/abandonclaim，**tpdeny 原缺失**）、L2 +2（speed/f3f4perms.use）、L3 +4 运营工具（mute/tempban/banip/unbanip）；/nick 不开放、/kit 维持 member、siege/GetMeHome 保持默认；⚠️ **Essentials IP 封禁命令是 `/banip`（无连字符，不是 /ban-ip）**；测试服已落地+bot 四组实测全通过，Exaroton/MCSM 21 条待同步。详见 references/permission-system.md
- **force-gamemode 三端已统一 false（2026-08-06）**：MCSM 原为 true（玩家每次登录被强制回 survival，切创造后退出重登丢失模式），已改 false 与本地/Exaroton 对齐；改 server.properties 用 `PUT /api/files/`（保留 CRLF），重启生效，不影响在线玩家
- ⚠️ **死亡位置传送覆盖关系（2026-08-05 反编译实证）**：**Essentials `/back` 不能覆盖 BackOnDeath**——`/back` 传送目标是 `LastLocation`（只在 `PlayerTeleportEvent` PLUGIN/COMMAND 原因时更新），**死亡事件不更新 LastLocation** → `/back` 回的是「最后传送点」**不是死亡点**。BackOnDeath 监听死亡事件记录死亡位置。**线上依赖 BackOnDeath 回死亡点功能 → 保留**（仅 SpigotMC 渠道，无 Hangar/Modrinth）。同理 GetMeHome 保留（线上 60+ 玩家用，迁移 Essentials 需脚本转换+多 home 权限，方案未成熟前不动）；**GetMeHome Tab 补全冲突（2026-08-31 最终修复）**：Paper 26.x 上执行走 Bukkit 命令表（GetMeHome 正常）但**补全走 Brigadier 树被 Essentials 抢占**（Essentials 2.22 SyncCommands 注册 /home）→ `/home` Tab 显示 Essentials 内容（`玩家名:` 前缀）而非家名。**两段式根因**：3.0.0 旧 api（1.21.7）补全完全不生效（无列表）→ 升 3.0.1 后补全恢复但被 Essentials 抢（内容乱）。**最终修复（源码层，PR #7 已合，3.0.2）**：① **api 升级 26.2**（`gradle.properties` `paper_api_version=26.2.build.119-stable` 对齐 OrzMC 主插件 + plugin.yml `api-version: '26.2'`）；② **命令注册改 Brigadier**（新增 `CommandRegistrar.java`：`plugin.getLifecycleManager().registerEventHandler(LifecycleEvents.COMMANDS, event -> event.registrar().register(...))`，6 命令含别名 h/homes，`.requires()` 权限 + `.suggests()` 补全，执行体复用原 executor）；③ **删 plugin.yml `commands:` 段**（⚠️ 关键坑：Paper 26.x 下 Bukkit CommandMap 声明会生成**无 executor 的幽灵命令**——onEnable 不再 setExecutor 时执行返回 false → 打印 plugin.yml usage 如 `/home [home name]`，且与 Brigadier 树冲突；OrzMC 主插件同款做法「插件模式忽略 YAML 命令声明」）；④ Essentials disabled-commands 保留（双保险）。⚠️⚠️ **Brigadier 参数类型大坑（实测）**：`word()`/`string()` 的 unquoted 字符集**不含中文和 `:`**（只允许 `[0-9A-Za-z._+-/<>^=]`）——`/sethome 验收点`、`/home 测试:家` 报「Expected whitespace to end one argument, but found trailing data」（原版 Bukkit 按空格 split 中文家名完全可用=行为回归）→ **全部参数必须用 `greedyString()`**（读所有非空格字符，空格天然分隔参数，1 参/2 参形式均正常）；greedy 模式下**补全建议绝不能加引号**（引号会被吞进参数值）。**验证**（本地测试服 1.21.10/协议 776）：`/home ` Tab → `["test1","验收点"]`（家名列表）、`/homes ` → `["-global"]`、中文/冒号家名 sethome/home/delhome 全通过、/home 无参 = 设计行为。⚠️ mineflayer 协议验证 tab_complete 的坑：1.21 包格式是 `{transactionId, text}`（旧 assumeCommand 字段已移除），用 1.21.10 同协议版本测（高版本 ViaVersion 降级可能不通），脚本 `~/minecraft-bot/tab-single-1210.js`

## 操作步骤

### 1. 获取最新版本信息
```bash
curl -s https://papermc.io/downloads/paper | python3 ~/.hermes/skills/gaming/orzmc/scripts/parse_papermc.py
# 输出: paper-26.2-92 059d00bbce0fa1707739618b3276f5c80b9655dc0f964306fa799a9c7cb01cc2
```

### 2. 创建/升级/备份/状态（local）
> ⚠️ 2026-09-03 起：本机 OrzMC 测试服已迁 MCSM 面板管理（local 仅适用临时本机目录服，如 ~/minecraft-server）；MCSM 实例的 jar 升级 = 直接替换实例目录 jar（`InstanceData/<uuid>/`）+ 面板重启实例
```bash
# 创建
PAPER_BACKEND=local PAPER_DIR=~/minecraft-server \
  ~/.hermes/skills/gaming/orzmc/scripts/adapters/local.sh create
# 升级核心 jar（自动备份旧 jar 可回滚）
PAPER_BACKEND=local PAPER_DIR=~/minecraft-server \
  ~/.hermes/skills/gaming/orzmc/scripts/adapters/local.sh upgrade
# 备份 world + plugins + server.properties（保留 24 份）
PAPER_DIR=~/minecraft-server ~/.hermes/skills/gaming/orzmc/scripts/backup.sh
# 状态 / 日志 / 命令
PAPER_DIR=~/minecraft-server ~/.hermes/skills/gaming/orzmc/scripts/adapters/local.sh status
PAPER_DIR=~/minecraft-server ~/.hermes/skills/gaming/orzmc/scripts/adapters/local.sh logs 50
```
> 详细（含 local 坑：无 rcon、运行时改 whitelist 不生效、macOS 无 timeout）→ `references/local-backend.md`

### 3. 插件安装/更新/卸载
```bash
~/.hermes/skills/gaming/orzmc/scripts/plugin_manager.sh install essentialsx
~/.hermes/skills/gaming/orzmc/scripts/plugin_manager.sh install https://example.com/plugin.jar
~/.hermes/skills/gaming/orzmc/scripts/plugin_manager.sh update   # 全部更新
~/.hermes/skills/gaming/orzmc/scripts/plugin_manager.sh remove essentialsx.jar
```

**插件安装/升级机制（PaperMC 官方，两条路径要分清）**：
- 🆕 **新插件首次安装** → jar **直接放 `plugins/`**（重启时扫描加载；放 update/ 无效/非标准）
- 🔄 **已有插件升级** → 新 jar 放 `plugins/update/` → 重启时 PaperMC **按插件名（jar 内 plugin.yml 的 name）匹配**已加载插件并原子替换（update/ 自动清空）
- ✅ **update/ 按插件名匹配，不要求文件名一致**（2026-08-08 实测：plugins/OrzMC-1.0.15.jar + update/OrzMC-1.0.16-dev.jar 不同文件名，重启后替换成功、plugins/ 只剩新 jar、update/ 清空）
- ✅ **升级绝不动 plugins/ 下旧 jar**（官方文档原文：「do not remove or modify any plugins outside the update folder」）——**先删旧 jar 是错误做法**：删了旧 jar 后 update/ 匹配不到已加载插件 → 不应用 → 插件缺失（Exaroton 2026-08-08 实测翻车）
- ⚠️ Exaroton **运行中禁止写文件**，上传/升级必须先停服
- ✅ MCSM 端 plugins/update 实测可用（`mcsm_upload_update.py` 上传 → restart → 自动替换）
- ⚠️ **三端插件对齐必须对比 sha256**（文件名相同≠内容相同）；MCSM 运行中 jar 读取 500（锁定），对比用启动日志 `Enabling X vY` 行

### 3b. OrzMC 自定义插件升级（Hangar + update 机制）

```bash
# 1. 查最新版（Hangar API：dev=每日构建，pr=PR 构建）
curl -s "https://hangar.papermc.io/api/v1/projects/OrzMC/versions?limit=5" | jq -r '.result[] | .name'
# 2. 下载：curl -s ".../versions/<版本>" | jq -r '.downloads[].downloadUrl' → 校验
# 3. 新 jar 放 plugins/update/（按插件名 name=OrzMC 匹配，绝不动 plugins/ 旧 jar）→ 重启自动替换
```
⚠️ 三件套：① 新版本新增模板键 → jar 升级≠配置升级，三端 diff 后上传本地版覆盖；② 权限继承链须手动校正（`lp group member parent set default` / builder→member / admin→builder）；③ 完整流程见 `references/plugin-mgmt.md`

### 4. 三端配置对比与同步（scripts/cmp3/）

```bash
CMP=~/.hermes/skills/gaming/orzmc/scripts/cmp3
python3 $CMP/cmp3_configs.py <exa配置目录> <mcsm配置目录> <本地目录>   # 语义对比
python3 $CMP/cmp3_plugins_sha.py                                        # jar sha256 对齐
python3 $CMP/exa_apply_config.py && python3 $CMP/exa_verify_config.py   # Exaroton 改配置
python3 $CMP/mcsm_upload_update.py <jar名...>                           # MCSM 插件更新
```
**凭据约定**：全部从 `~/.hermes/.env` 读取（`mcsm_env.py` 共享模块），**禁止硬编码 API key**。

### 5. MCSM / Exaroton 日常操作

```bash
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh status|players|logs 50|start|stop|restart|command "list"
python3 $CMP/mcsm_delete.py /plugins/xxx.jar      # 删除（{"targets":[...]}）
python3 $CMP/mcsm_list_filter.py                  # 列目录（需 file_name 过滤）
```
> 端点表/认证/踩坑 → `references/mcsm-backend.md`、`references/exaroton-backend.md`

### 6. 版本巡检（cron 每日 10:00）

```bash
# 手动触发
python3 ~/.hermes/scripts/mc_version_check.py
```

- **cron job**：`MC 三端版本巡检`（`0b4298821a86`，每日 10:00，attach_to_session，skills=orzmc，toolsets=terminal/file/web）
- **脚本逻辑**：`~/.hermes/scripts/mc_version_check.py` 查 **Paper + Folia 双核心**（parse_papermc.py 支持 `[paper|folia]` 参数，Folia 输出含本地对比）+ 21 插件各官方渠道最新版（Modrinth/Hangar/GitHub/metadata.luckperms.net/geysermc）vs 本地 MCSM 实例（`InstanceData/<uuid>/plugins/`）部署版本（读 jar 内 plugin.yml/paper-plugin.yml）
- **输出**：对比表 + 状态（✅一致 / ⚠️有更新 / ➖本地构建 / ➖稳定 / ❓查询失败）+ 差异汇总
- **渠道映射**（CHANNEL dict）：OrzMC=hangar；EzShops/LoginSecurity/DeathChest/GetMeHome=**local**（本地打包，不提示升级）；BackOnDeath/Vault=**stable**（无渠道）；Essentials=github；Geyser-Spigot=geyser；CustomWorldHeight=**modrinth**（Hangar 无此插件，2026-08-15 修正）；**F3F4Perms=modrinth（slug: f3f4perms）；packetevents=modrinth（⚠️ CHANNEL key 必须小写 `packetevents`——jar 内 plugin.yml name 是小写，deploy dict 以 pname 为 key 会匹配不上大写 key）**；其余=modrinth
- **已知坑**：① Geyser jar 内 plugin.yml 固定显示 `2.11.1-SNAPSHOT`，版本以文件名构建号为准（正则 `-(\d+)\.jar$`）；**2026-08-12 已修复：脚本按 build 号比较部署 vs 最新（同 build 即 ✅，不再假阳性）**；② OrzMC 用 `paper-plugin.yml`（非 plugin.yml）；③ Modrinth SkinsRestorer 需 loaders 过滤（否则返回 neoforge 假阳性）；④ WorldEdit/WorldGuard 版本带构建后缀（`7.4.4+7546-...`）需 strip；⑤ **CustomWorldHeight 只在 Modrinth（slug: customworldheight），Hangar 无此插件**（2026-08-15 实测：Hangar 查询失败 → Modrinth 正常 2.2.0）；⑥ LuckPerms 官方渠道是 metadata.luckperms.net（`downloads.bukkit` 直链），Modrinth 滞后（5.5.76 时 Modrinth 只有 5.5.71-bukkit）；⑦ Geyser build 号频繁更新（1222→1223 一天内），升级前必须查最新；⑧ **packetevents 多平台发布（fabric/velocity/sponge/spigot/bungeecord），须 loaders=["paper","spigot","bukkit","folia"] 过滤，否则返回第一个 fabric 版（version_number 形如 `2.13.0+spigot`，strip_build 剥离 `+...` 后比较）**；⑨ **自带版本号文件名变更（2026-09-14 修复）**：OrzMC 升到 `OrzMC-1.0.27-dev.422.jar` 后精确映射表 FNAME_NAME 未命中 → 该行显示「未部署」+ 未识别 jar 告警（假阴性）。已加 `PREFIX_NAME` 前缀兜底 + `resolve_name()`（精确表优先→最长前缀匹配），Geyser build 号改用扫描到的真实文件名（`RAW_FNAME`）解析——**升级插件后无需再改脚本**；**⑩ 2026-10-12 补｜`PREFIX_NAME` 自身也会漏**：`GriefPrevention3D-18.4.8.jar` / `SkinsRestorer-15.12.6.jar` 改名后仍报「未识别 jar」（SkinsRestorer 因此误报「未部署」；**GriefPrevention3D 的 18.4.8→18.4.12 升级项被整条吞掉**）→ 已补 `GriefPrevention3D-`/`GriefPrevention-`/`SkinsRestorer-`/`deathchest-`/`BackOnDeath-`/`Vault-` 前缀。⚠️ **纪律：凡出现「未识别 jar」告警必须当场补映射**，否则静默漏报升级项；补完当场跑一次脚本确认告警消失。**另：本脚本只扫 MCSM 侧 jar，Exaroton 端 jar 版本从不检查**（2026-10-12 才发现 Exa 落后一大截）→ 待补 Exa 侧盘点；有差异时 cron agent 发飞书询问用户是否升级，升级走两端顺序：MCSM（测试）→ Exaroton（生产）（无玩家窗口）

### 6b-2. ⚠️ MCSM 面板「账号级限流」与大文件投递（2026-09-19 实测血泪）

**限流事实**：面板 files API（list/download 签发/upload 签发）**账号级 ~3s/次**（管理员绕过）。高频脚本会把面板/daemon 拖到「签署 OK 但拉流 0 bytes、输出超时」的迟钝状态（实测：连续 30 分钟高频投递后，`outputlog`/`instance`/`files/list` 全部超时，`sign` 仍 200）。
- 对策：**一切 files 操作串行 + ≥3.5s 间隔**；大批量分阶段跑；出现迟钝立刻停手等几分钟，别重试风暴。
- 备用日志端点：`GET /api/protected_instance/outputlog?daemonId&uuid`（**绕开 daemon 拉流**，起服验证首选，比读 latest.log 稳）。

**URL 拼接坑（吃了 40 分钟）**：`cfg["url"].rstrip("/") + path` 时 **path 必须带前导 `/`**，否则拼成 `mcs.{SERVER_NAME}.cnapi/files/mkdir`（主机名非法）→ 报错却是 **`SSLEOFError: EOF occurred in violation of protocol`**（不是「域名不存在」！）→ 排查清单第一条：把 URL 打出来看斜杠。
```python
url = cfg["url"].rstrip("/") + "/" + path.lstrip("/") + "?" + urllib.parse.urlencode(params)
```
**写操作载荷位置**：`files/mkdir`、`files/copy`、`files/download_from_url` 的字段走 **JSON body**（仅 apikey/daemonId/uuid 在 query）；`files/upload` 的 `upload_dir` 走 **query**。写操作会偶发 SSL EOF/handshake timeout/BrokenPipe → **必须多重试 + 指数退避**（实测 6 次退避能穿过）。

**大文件别走 upload**：Cloudflare 对上传有 ~100s 上限 → 41MB Geyser 上传 `HTTPError 524`（**同一文件偶发成功**）；61MB 核心必超时。**大件一律用 daemon 侧直传**：
```python
post_json(cfg, "api/files/download_from_url", {"url": 官方直链(内容寻址更佳), "file_name": "/paper.jar"})
```
实测 paper 核心 61.5MB、Geyser 41MB 均一次成功（daemon 有外网），落盘后 `files/list` 看 size 即可初验。

**双实例交付次序**：先小件 upload → 再大件 URL 直传 → `files/list` 核 size → 启动（**启动后 update/ 被消费**，故 sha 回读要么启动前做、要么启动后按 `plugins/` 新名回读）。

### 6c. MC 定时任务清单（统一管理入口，2026-08-12 起）

| 任务 | job_id | 计划 | 脚本 | 模式 | 行为 |
|:--|:--|:--|:--|:--|:--|
| MC 三端版本巡检 | `0b4298821a86` | 每日 10:00 | `~/.hermes/scripts/mc_version_check.py` | 脚本输出 + agent 解读（skills=orzmc, toolsets=terminal/file/web）| 查核心+19 插件最新版 vs 本地部署 → 有差异发飞书询问用户 |
| 三端配置审查 | `ab06b886c39f` | 每周一 9:15 | `~/.hermes/scripts/orzmc_config_audit.sh` | 同上（toolsets=terminal/file）| 只审查不重启：Exa+MCSM 并发拉取 77 配置 → cmp3 对比 → 报告落盘 references/ |

- 两者脚本均读 `~/.hermes/.env` 凭据；cron 精简 PATH 实测通过（2026-08-12 全量体检）
- 脚本维护记录：audit 脚本 `Bearer ***` bug 已修（2026-08-12）；version_check Geyser build 号比较已修（2026-08-12）

## Pitfalls（跨后端通用）

- ⚠️ **配置重建升级（OrzMC/EzShops 等）备份必须隔离目录**：旧配置备份与"拉新配置"严禁写同一目录——拉新强制用 `*_new/` 独立目录（2026-08-09 实测教训：复用同一 outdir 导致旧备份被新默认配置覆盖，迁移依据永久丢失；/tmp 无 Time Machine/APFS 快照兜底）。备份后**立即打印内容摘要（key: value）核对**，并二次复制到 `~/backups/`；迁移前先 diff 新旧确认依据完整
- ⚠️ **破坏性升级（删配置重建）前**：先 `skill_view` 查技能已有脚本/端点结论（mcsm_delete.py 用 `{"targets":[...]}`、MCSM 重启用 `api/protected_instance/restart`、Exaroton 上传用 PUT+UA），不凭记忆手写；备份/迁移清单先列给用户确认（plan-first）
- ⚠️ 下载必须校验 sha256，防止损坏 jar
- ⚠️ **备份分层**：插件升级无需备份 jar；服务器核心 jar 升级需备份旧 jar 回滚（upgrade 自动做）；**世界/玩家/LuckPerms H2/配置必须定期备份**
- ⚠️ 服务器运行中不要替换 jar（先 stop 再升级）
- ⚠️ 插件必须匹配 MC 版本（Modrinth API 用 `game_versions` 过滤）
- ⚠️ eula.txt 不写 `eula=true` 服务器拒绝启动
- ⚠️ Java 25 只能跑 26.x；老版本需要旧 JDK
- ⚠️ macOS bash 3.2：`$var` 后接全角字符（如 `（`）会报 unbound variable，必须写 `${var}`
- ⚠️ MCSM 有玩家在线时严禁 stop/restart/command/文件操作（先查 `info.currentPlayers`）
- ⚠️ **MCSM 升级跨大版本（如 26.1→26.2）**：世界数据首次启动自动转换（日志 `Starting upgrade for world`），确认无玩家时段操作

## 验证
- `curl -s localhost:25565` 返回 Minecraft 协议字节 = 服务器在线
- 日志出现 `Done (Xs)! For help, type "help"` = 启动成功
- `ls plugins/` 看到 jar = 插件已安装
- 三端对齐：插件 sha256 一致 + 版本号一致
