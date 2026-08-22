---
name: orzmc
description: "Minecraft 运维统一技能（唯一入口）：三端服务器运维/插件构建升级/性能诊断/权限体系/测试/基岩支持，46 个知识体系 + 31 个脚本。"
version: 2.0.1
author: Hermes Agent
tags: [minecraft, papermc, server, maintenance, upgrade, plugin, exaroton, mcsm, luckperms, testing]
platforms: [macos, linux]
required_commands: [java, curl, tar]
---

# OrzMC Minecraft 运维（统一技能）

> **技能治理（2026-08-11 用户决策，已合并）**：与 MC 运维强相关的技能一律**合并进本技能**维护迭代（references + scripts），不再单独立技能；新增强相关知识直接落这里。已合并：easybot-gateway-ops（→ references/easybot-gateway.md）、deployment-config-sync（→ references/config-sync.md）、git-submodule-sync（→ references/git-submodule-sync.md，OrzMC monorepo 子模块同步）、java-test-pitfalls（→ references/java-test-pitfalls.md，插件单测编译坑）；模组托管（minecraft-modpack-server）已清理，与原生 PaperMC 场景无关。

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
> | **Java 测试编译陷阱（Mockito 泛型捕获/SuppressWarnings 位置/CI warnings 清零；原 java-test-pitfalls 技能合并）** | `references/java-test-pitfalls.md` |
> | Spark 性能分析（命令/JSON/判断/踩坑） | `references/spark-analysis.md` |
> | 快速实体统计（paper entity list / Spark / 计分板） | `references/entity-statistics.md` |
> | 机器人玩家 Mineflayer（运维视角；开发细节见独立技能 `minecraft-bot-mineflayer`；**挂机脚本 stay-with-joker.js：5 bot 跟随真人玩家 + IPv4/IPv6 分流绕 per-IP 限制**） | `references/mineflayer-bot.md` |
> | DeathChest 回归测试（死亡瞬间下线→物品丢失 ✅fix1；**动画 progress 越界卡服 ✅fix3 已合入 main 71d2571**；复现法见 ref） | `references/deathchest-regression.md` |
> | Geyser 基岩支持（当前 offline 直连模式；floodgate 已回退 2026-08-05） | `references/geyser-floodgate.md` |
> | **插件源码构建/开发（构建工具选择、Gradle/Maven 坑、PR 流程、发布规范）** | `references/plugin-build.md` |
> | **插件升级与配置迁移（三端范式、Exaroton/MCSM API 坑、EzShops 存储、Geyser 排查）** | `references/plugin-mgmt.md` |
> **三端配置差异审计（2026-08-11 三次全量对比；2026-08-12 起每周一 9:15 cron `ab06b886c39f`「三端配置审查」v2：只审查不重启 + Exa/MCSM 并发拉取，脚本 `~/.hermes/scripts/orzmc_config_audit.sh`；保留最近两次报告；cmp3 工具链用法）** | `references/three-end-config-drift.md` |
> | **版本巡检 cron（每日 10:00，job `0b4298821a86`）：脚本 `~/.hermes/scripts/mc_version_check.py` 查核心+19 插件各渠道最新版 vs 本地部署 → 有差异发飞书询问用户** | 本 SKILL.md「版本巡检」段 |
> | **性能诊断（Spark 五步法、实体审计、Aikar Flags、修复方案）** | `references/performance.md` |
> | **插件 Bug 排查（本地复现、命令/权限分离、实体事件、版本兼容）** | `references/plugin-debugging.md` |
> | **测试体系（分层原则、三大通道、Paper 26 陷阱、跨服 transfer）** | `references/testing.md` |
> | **LuckPerms 权限体系（API 集成、审计验收、三端同步、Bootstrap）** | `references/permission.md` |
> | **实体/传送门行为（事件继承、原版规则、白名单策略）** | `references/entity-portal.md` |
> | OrzMC 统一代码仓库（submodule 资产地图：插件源码/配置库/备份工具/世界瘦身；**Bot 命令调试 orzdebug + $e 输出捕获机制 + Log4J 坑**） | `references/orzmc-repo.md` |
> | OrzMC 真实环境验收报告（2026-08-06：全功能测试矩阵 + 双服 transfer + 发现的 bug） | `references/orzmc-acceptance-20260806.md` |
> **玩家手册（官方站 orzmc.{SERVER_NAME}.cn/user/ = OrzMCSite `content/user.md`）**：2026-08-15 合并新手指南（进服 3 步/基本操作/协作生态/四级权限成长/避坑FAQ/自定义皮肤），服务器地址用 server-status 组件动态卡片（不写死 IP）；site 是独立仓库 OrzMCSite，改手册 = 改 user.md → 单独 push main → CI 自动发布（Pages），主仓只 bump submodule 指针；本地 Hugo 预编译装 `~/usr/local/bin/hugo`（brew 被 go pin 卡住，GitHub release 新版只有 .pkg 用 installer -target CurrentUserHomeDirectory）；⚠️ **server-status shortcode 用 `tags=` 分组过滤（单点维护）**：params.toml 每台服配 `tags = ["players"]`/`["dev"]`，文档只写 `{{< server-status tags="players" >}}`——名称/地址变化只改 params.toml，文档零改动（2026-08-15 方案 B 落地 b80d8a7）；❌ 勿用旧 `servers=` 参数（按 name/host 精确匹配，中文名带 emoji 匹配不上 → `servers:[]` 空数组卡片空白；且名称/域名变化需改文档，多页面成本高）
> | OrzMC 功能测试用例（28 项，玩家命令/Bot 命令/事件拦截，含前置条件/步骤/预期） | 插件仓库 `plugin/docs/test-cases.md`（OrzMCPlugin） |
> | OrzMC 端到端测试报告（2026-08-06：机器人+真实玩家，28/28 通过，transfer 闭环） | 插件仓库 `plugin/docs/e2e-test-report-20260806.md`（OrzMCPlugin） |
> | RCON 客户端（`scripts/rcon.py <命令> [端口]`，密码从环境变量 RCON_PASSWORD 读） | `scripts/rcon.py` |
> | **基岩版连通性诊断（`~/OrzMC/proxy/scripts/bedrock_host_check.sh` bash 跨平台 / `.ps1` Win）**：双模式——本机诊断（默认，RakNet 握手+端口监听+进程+防火墙五项）与远程探测（传 host 即可，端口默认 19132，纯数字第一参=端口）；用法 `bash bedrock_host_check.sh [host] [port]`、PS `.\bedrock_host_check.ps1 [-HostAddr x] [-Port n]`；-h/--help 帮助；**定位法：本机 PASS+监听✅ → 问题在外部 UDP 转发；FAIL → Geyser 本身**；使用说明/修复记录文档同目录（基岩诊断脚本_使用说明.md、脚本问题修复记录_平台注意事项.md，v1.1 含 7 条真机坑）；坑：macOS netstat `udp46 *.19132` 格式、BSD pgrep 只出 pid 不能二次 grep（统一 ps aux+grep）、Windows Store python3 stub 检测、PS 需 UTF-8 BOM+`${Var}:` 写法、RakNet Pong MOTD 从偏移 34 到包尾 UTF-8（长度字段不可靠） | `~/OrzMC/proxy/`（OrzMCProxy 子模块） |
| LP 权限命令清单生成（`scripts/gen_perm_commands.py`：从仓库 `plugin/docs/permission-groups.md` 唯一权威文档解析生成 lp set 命令；方案① 2026-08-12） | `scripts/gen_perm_commands.py` |
> | LoginSecurity 注册状态查询（`scripts/check_lsdb.py [db路径] [玩家名]`） | `scripts/check_lsdb.py` |
> | LoginSecurity→AuthMe 数据迁移（`scripts/migrate_loginsecurity_to_authme.py [--ls-db X --authme-db Y] [--dry-run]`；BCrypt 哈希直接复用，AuthMe 须改 passwordHash: BCRYPT） | `scripts/migrate_loginsecurity_to_authme.py` |
> | GetMeHome→EssentialsC 数据迁移（`scripts/migrate_getmehome_to_essentialsc.py [--yml X --db Y] [--dry-run]`；homes.yml YAML→homes.db SQLite，字段一一映射） | `scripts/migrate_getmehome_to_essentialsc.py` |
> | PaperMC 插件 E2E 测试方案调研（MockBukkit/WatchWolf/GameTest/真实环境/容器化 + 推荐组合） | `references/plugin-e2e-testing.md` |
|> | **命令方块/方块实体扫描（2026-08-18 入库）：`scripts/scan_cmdblocks.py <世界目录> <out.json> [workers=8] [min_size=0]` 流式 NBT 解析提取命令方块+block_entities（workers=1 串行最稳，内存紧张宿主勿用多进程）；`scripts/analyze_cmdblocks.py <json>` 输出分类统计（类型/auto/维度/命令词频/被禁命令依赖/区域分布）** | `scripts/scan_cmdblocks.py` + `scripts/analyze_cmdblocks.py` |
|> | **命令方块全量梳理成文档（2026-08-20 入库）：`scripts/mc_cb_scan.py` 一体化 扫描→CSV→自动 Markdown 报告（统计/空间集群/指令分类/异常风险[OP提权·超大坐标残留·超大fill]/Folia 禁用指令交叉核对）；子命令 `run`/`scan`/`report`（`--dims`/`--jobs`/`--cluster-threshold`/`--max-coord`）；纯标准库零依赖；原理=流式 NBT 只解析 block_entities 跳过 Sections（10GB 全图约 49 分钟）；Folia 架构性禁用命令方块（#429/#485）故盘点用于找替换方案** | `references/command-block-inventory.md` + `scripts/mc_cb_scan.py` |
> | **ExecutableEvents 实测（2026-08-19，3.26.8.10+SCore 5.26.8.10 on Folia 26.2-4）：加载✅ 事件监听不触发❌（PLAYER_WALK/PLAYER_JUMP_EVENT/debug 全零输出，sevents 与 Folia 分区线程不兼容）→ 插件替代命令方块方案整体不可行；⚠️ SCore 硬依赖（plugin.yml 注释 depend 但代码需要）；⚠️ events/ 一文件一事件；⚠️ 防重登限制=GriefPrevention3D Spam.LoginCooldownSeconds** | `references/folia-experiment.md` |
> | **群消息样式规范（2026-08-19 PR #197 统一）：表情标题+33 连字符分割线+版块式排版；四类消息模板键与格式表；聚合摘要空版块省略/单人无人数/多人(N)；改模板 4+1 联动清单（templates.yml+Templates.java+ReviewNotifierAdapter fallback+占位符白名单+测试）；存量服改键值须手动同步 templates.yml+reload；真实环境验证法（bot 触发+easybot 投递查询）；Folia 测试服操作坑（screen stuff stop 不可靠→RCON、防多实例、--rerun-tasks 强制重打）** | `references/group-message-style.md` |
> | **跨网互联/中转方案（电信服×联通移动玩家；FRP 中转 + PROXY protocol 真实 IP 透传；部署资产在 `OrzMC/proxy` 子模块 = OrzMCProxy 仓库：install-frp.sh/ps1 一键安装、verify-tunnel.sh、health-check.sh、bedrock_ping.py、mc_login.py、**relay-monitor.sh 外部隧道监控（formal/temp 双档看门狗，2026-08-14 本地双模式验收 100% 通过）**、configs 模板、systemd/launchd/Windows 计划任务、manual-apply-windows.md 手动改法）** | `references/cross-carrier-networking.md` |
> | **世界高度调整（1.18+ 高度是 worldgen 属性非服务器配置；CustomWorldHeight 插件方案 2026-08-15 本地实测通过 height=1088；硬限制 min_y≥-2032/height≤4064/min_y+height≤2032；RCON setblock 边界验证法）** | `references/world-height.md` |
> | **Folia 迁移实验（2026-08-17 本地双服实测：兼容矩阵 20 jar→18 全绿；9 不兼容插件平替方案含合并策略；LoginSecurity→AuthMe 359 账号 / GetMeHome→EssentialsC 879 home 数据迁移；❌ Hangar API 不能查 Folia（supportedPlatforms 只标 PAPER），检索用 Modrinth loaders 含 folia；Folia 26.2 目前仅 BETA；2026-08-18 全面接管原测试服（端口 25565/19132 + 地图 symlink + 配置/权限/白名单全量同步）；⚠️ **两服共享 world symlink（folia→paper），严禁同跑**（session.lock + 数据损坏风险，切换先停另一台，详见 testing.md）；⚠️ 命令方块被 Folia 架构性禁用（#429/#485 not_planned）；⚠️⚠️ log4j2 自定义配置必须 start.sh JVM 参数 -Dlog4j2.configurationFile 指定（config/ 下不会自动加载）；CustomWorldHeight 已移除（全量扫描 0 高空数据，1088 格式区块随加载自然收敛 384）；Essentials tpa 漏配 tpaccept 已修复；**PlayerPortalEvent Folia 不触发已解决（PR #195 合并 b7d4b86：PlayerMoveEvent 补偿路径，几何=内部格脚底+1 起须身体两格匹配+水平精确命中，5s 双路径共享冷却，详见「传送门 transfer 补偿方案」小节）**）** | `references/folia-experiment.md` |

## 使用时机
- 用户要创建新的 PaperMC 服务器（本机/Exaroton/MCSM）
- 用户要升级 PaperMC 服务端版本或构建
- 用户要安装/更新/卸载插件
- 用户要备份或查看服务器状态/日志
- 用户要排查性能/卡顿（→ `references/spark-analysis.md`）
- 用户要统计实体或定位 FPS 问题（→ `references/entity-statistics.md`）
- 用户要机器人玩家/自动操作（→ `references/mineflayer-bot.md`）
- 用户要盘点某世界/地图的命令方块（数量/坐标/指令/触发方式）或为 Paper→Folia 迁移评估命令方块影响（→ `references/command-block-inventory.md`，工具 `scripts/mc_cb_scan.py`）

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

## 关键事实（2026-08 实测）

- **旧 API `api.papermc.io/v2` 已完全废弃（410 Gone）**——用 fill-data 新机制（`parse_papermc.py` 封装）
- **最新稳定版**：paper-26.2-112（2026-08-10 三端实测；**26.2-92 与 111 行为可能不同**，本地复现必须与线上同构建）；**Java 要求**：26.x 需要 Java 25；**2026-08-15 本地+Exaroton 已升 112**（Exaroton 平台会自动升级核心，version_history.json 111→112 平台自动完成）→ 三端核心版本天然可漂移
- **插件基线**（三端对齐，2026-08-15 更新；⚠️ 2026-08-13 **正式发布 1.0.17**（tag 1.0.17，含 #171 耗时中文可读化 + #172 $e 输出捕获 + 群指令帮助改版）；**本地测试服 + Exaroton 已部署正式 1.0.17**（sha256 91b185aeda9a1f27730ff3745f88700ee471581b1bf08d57f0845d18874b0aff，2675041B），**MCSM 仍 1.0.16 未部署**——三端插件对比须注意；**2026-08-18 本地双服已换 OrzMC 1.0.18-dev.296**（Hangar 渠道，folia-supported: true，sha256 5e1eae18a1e1d41d97dfbdb34597c4522af3c32de130017e65472bc1827cf649））：OrzMC **1.0.17→dev.296（本地）** / EzShops 2.5.9（storage.type: **yaml**，无 MySQL）/ Geyser **2.11.2-b1230**（基岩 26.0-26.45 支持；2026-08-15 由 1222 升 1223，**2026-08-22 本地 Paper+Folia 由 1225 升 1230**：Paper 走 update/ 机制重启生效（RCON `/geyser version` 验证 2.11.2-b1230 无更新可用），Folia 停服状态直接替换 plugins/ jar 下次启动生效；⚠️ 版本巡检按 build 号比较）/ LoginSecurity 3.3.2-SNAPSHOT（**本地修复版**：getPlayer null 防御，Gradle 构建）/ LuckPerms **5.5.77**（官方渠道 metadata.luckperms.net 下载，2026-08-15 由 5.5.71→76→77；本地+Exaroton 已部署）/ EssentialsX 2.22.0（⚠️ 26.2 不兼容：/spawn 未注册 + op 全拒）/ ViaVersion 系列 5.11.0 稳定版不升 SNAPSHOT / BackOnDeath 0.4 / DeathChest 3.0.1 / GetMeHome 3.0.0 / GriefPrevention 16.18.7 / SkinsRestorer 15.12.5（**三端 `login.offlineModeWarning.enabled: false` 2026-08-11 关闭**——离线混合服对全玩家发「盗版Minecraft/TLauncher」警告纯噪音，与具体启动器无关，SkinsRestorer 无法检测实际启动器；恢复 = 改 true + `/skin reload`）/ Vault 1.7.3-b131 / ViaBackwards 5.11.0 / ViaRewind 4.1.3 / WorldEdit **7.4.5**（2026-08-11 由 7.4.4 升级）/ WorldGuard 7.0.18 / **CustomWorldHeight 2.2.0 已移除（2026-08-18 两端，世界回 384 生态；全量扫描 0 高空数据故零丢失）**
- **GeoIP 内网误拦截（2026-08-06 修复，OrzMC 1.0.15）**：MCSM allow_country_code=[CN,JP,TW] 时内网玩家（192.168.x/10.x）被拦截——geojs.io 无法解析私有段返回未知国家码。1.0.15 加内网 IP 短路（RFC1918/环回/CGNAT 直接放行，公网仍检查）。OrzMC 配置读取为实时（改 config.yml 后 **`/config reload` 即生效**，无需重启；⚠️ 2026-08-11 修正：命令是 **`/config reload`（根命令 `config`，别名 `cfg`，源码 FeatureModule.java `commands.register(node, "配置管理", List.of("cfg"))`）**，技能旧写 `/orzconfig reload` 是错的——实际执行返回 Unknown）；临时缓解=allow_country_code 改 []。⚠️ **`/config set` 改不了国家限制（2026-08-13 源码实证）**：`geoip.allow_country_code` 未注册进 `ConfigPath` 注册表（22 项只覆盖 whitelist/maintenance/tnt/command_policies/easybot/templates），且 `OrzConfigCommand.parseValue` 只支持 Boolean/Integer/Long/Double/String **不支持 List** → 只能改 config.yml + `/config reload`。同理 **`permission.yml` 的 `config.member-threshold-hours`（default→member 自动晋升阈值，默认 10 小时）也改不了 `/config set`（未注册），且是构造注入**（FeatureModule 装配时 `RankService(permissionStore, ..., memberThresholdHours(), ...)` final 字段）→ 改文件后**必须重启**才生效（reload 无效）；时长数据源是服务器原生 stats（`world/players/stats/<uuid>.json` 的 `minecraft:play_time`，tick÷1200=分钟）。`command_policies.tpbow.admin_only`（Boolean）是**唯一能 `/config set` 的注册路径**（`/config set command_policies.tpbow.admin_only true`=普通玩家禁用传送弓），但拦截器链装配时固定 → 同样**需重启生效**
- ⚠️⚠️ **改 `permission.yml` 必须「先 reload 再重启」，否则修改被回写覆盖（2026-08-15 源码实证）**：`permission` 配置在 `ConfigService.setup()` 被 `markAlwaysSave("permission")`；服务器停止时 `onDisable→tearDown→configService.tearDown→saveDirtyConfigs()`（ConfigManager L101）会遍历 alwaysSave 配置**用内存快照整体写回磁盘**；而内存快照是启动时 `registerConfig` 加载的旧值 → 运行中手动改文件不 reload，重启时旧值覆盖新值，修改丢失。**且运行中 `PermissionStore.save()`（玩家提交审核）也调 `saveConfig` 同理会覆盖**。正确流程：① 改 permission.yml → ② `/config reload permission`（磁盘新值读进内存）→ ③ 重启（写回新值+装配生效）。验证：重启后 grep 日志或 `/config dump` 确认新值
- ⚠️⚠️ **`member-threshold-hours` 的隐藏语义（2026-08-15 源码实证，OrzMC 1.0.17）**：① **0 值 = 进服秒升 member**——`checkPromotion()`（玩家上线异步触发，OrzRankEvent.onPlayerJoin）判定 `playtime < memberThresholdMinutes()`（=0×60=0）永远 false，新玩家（无 stats 文件返回 0）也满足 → 只要当前组是 default 立即 `promote()`；LP track 幂等（已是 member+ 不重复升），一次性不回退。② **不支持小数**——`PermissionStore.memberThresholdHours()` 返回 `int`（`cfg.getInt`），YAML 写 `2.5` 被 Bukkit **静默截断**为 `2`（Number.intValue() 不四舍五入）；写 `"2.5"`（字符串）parseInt 失败**回退默认 10**；`0.5` 截断成 `0` = 秒升。想要半小时级粒度需改源码（RankService L28 `final int` → double + L86 `* 60L`）。判定链路：RankService.checkPromotion L65-77 → OrzRankEvent.onPlayerJoin（异步，不阻塞主线程）→ stats 时长源 `world/players/stats/<uuid>.json`
- **备份/优化完成消息耗时中文可读化（2026-08-13，PR #171，OrzMC 1.0.17-dev）**：`WorldMaintenanceService.formatDuration(ms)` 毫秒→中文分级（<1秒=`854毫秒`、<1分=`35秒`、<1小时=`2分35秒`、≥1小时=`1小时2分3秒`；秒四舍五入、负值按0、小时级补0分占位如`1小时0分5秒`）。done/error 模板新增变量 `duration_human`（**保留 `duration_ms` 兼容旧模板**）；模板键=4 处联动：`templates.yml` 默认值 + `Templates.java` fallback + `TemplatePlaceholderValidator` 白名单 + `WorldMaintenanceService` 传参（⚠️ **漏注册白名单 → ConfigHealthCheck 测试挂**，报「模板变量未知: templates.maintenance_backup_done {duration_human}」）
- **MC 26.2 原生命令/聊天防刷（2026-08-12 反编译实证）**：server.properties `command-spam-threshold-seconds` / `chat-spam-threshold-seconds`（26.2-pre1 起，默认 10）。**真实机制（勿被名字误导）**：不是「每秒 N 条」，而是**爆发计数器**——`TickThrottler(20, 20×N)`：每条命令计数 +20，每 tick 衰减 -1（排水≈1 命令/秒），计数 ≥20×N 时踢出 `Kicked for spamming`。→ 任何持续 >1 条/秒的命令流迟早踢；45 条/秒时阈值 100 也只撑 ~2.3s。**OP/单人房主豁免**（bytecode：isOp 检查跳过踢出）→ 管理员永远遇不到。⚠️ **设 0 反而每条命令都被踢**（TickThrottler.isIncrementAndUnderThreshold 缺 0 保护，GitHub issue #14114）→ 要放宽用大数值，别设 0。触发实例：Litematica 粘贴原理图默认走 `pasteUseFillCommand`（/fill 流 45-104 条/秒）→ 反复被踢（阈值 100 只撑 ~2.3s，治标不治本）。**配置解法（2026-08-12 已落地三端）**：踢出时间 t=N/(R−1) 秒，要解决需 **N > 峰值速率 × 最长连续粘贴秒数**；三端 server.properties 已统一设 **100000**（104 条/秒时连续 ~16 分钟才触发，正常建筑完全无感）；替代解：WorldEdit `//paste`（一条命令）、关 pasteUseFillCommand 改逐方块放置、或给玩家 OP（豁免）。另：server 启动会重写 server.properties 头部时间戳但保留值（PUT 改文件→重启流程安全）。
- **权限系统（2026-08-06 实施，LuckPerms 4 组）**：default(新手生存)→member(进阶飞行)→builder(创造+WE)→admin(全权限)；坑：RCON 不回显 LP 命令输出（用 bot 玩家身份验证）、default 勿显式设 false 覆盖子组 true、Essentials 权限默认拒绝。详见 references/permission-system.md
- **force-gamemode 三端已统一 false（2026-08-06）**：MCSM 原为 true（玩家每次登录被强制回 survival，切创造后退出重登丢失模式），已改 false 与本地/Exaroton 对齐；改 server.properties 用 `PUT /api/files/`（保留 CRLF），重启生效，不影响在线玩家
- ⚠️ **死亡位置传送覆盖关系（2026-08-05 反编译实证）**：**Essentials `/back` 不能覆盖 BackOnDeath**——`/back` 传送目标是 `LastLocation`（只在 `PlayerTeleportEvent` PLUGIN/COMMAND 原因时更新），**死亡事件不更新 LastLocation** → `/back` 回的是「最后传送点」**不是死亡点**。BackOnDeath 监听死亡事件记录死亡位置。**线上依赖 BackOnDeath 回死亡点功能 → 保留**（仅 SpigotMC 渠道，无 Hangar/Modrinth）。同理 GetMeHome 保留（线上 60+ 玩家用，迁移 Essentials 需脚本转换+多 home 权限，方案未成熟前不动）

## 操作步骤

### 1. 获取最新版本信息
```bash
curl -s https://papermc.io/downloads/paper | python3 ~/.hermes/skills/gaming/orzmc/scripts/parse_papermc.py
# 输出: paper-26.2-92 059d00bbce0fa1707739618b3276f5c80b9655dc0f964306fa799a9c7cb01cc2
```

### 2. 创建/升级/备份/状态（local）
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
- **脚本逻辑**：`~/.hermes/scripts/mc_version_check.py` 查 PaperMC 核心（parse_papermc.py）+ 19 插件各官方渠道最新版（Modrinth/Hangar/GitHub/metadata.luckperms.net/geysermc）vs 本地 `~/minecraft-server/plugins/` 部署版本（读 jar 内 plugin.yml/paper-plugin.yml）
- **输出**：对比表 + 状态（✅一致 / ⚠️有更新 / ➖本地构建 / ➖稳定 / ❓查询失败）+ 差异汇总
- **渠道映射**（CHANNEL dict）：OrzMC=hangar；EzShops/LoginSecurity/DeathChest/GetMeHome=**local**（本地打包，不提示升级）；BackOnDeath/Vault=**stable**（无渠道）；Essentials=github；Geyser-Spigot=geyser；CustomWorldHeight=**modrinth**（Hangar 无此插件，2026-08-15 修正）；**F3F4Perms=modrinth（slug: f3f4perms）；packetevents=modrinth（⚠️ CHANNEL key 必须小写 `packetevents`——jar 内 plugin.yml name 是小写，deploy dict 以 pname 为 key 会匹配不上大写 key）**；其余=modrinth
- **已知坑**：① Geyser jar 内 plugin.yml 固定显示 `2.11.1-SNAPSHOT`，版本以文件名构建号为准（正则 `-(\d+)\.jar$`）；**2026-08-12 已修复：脚本按 build 号比较部署 vs 最新（同 build 即 ✅，不再假阳性）**；② OrzMC 用 `paper-plugin.yml`（非 plugin.yml）；③ Modrinth SkinsRestorer 需 loaders 过滤（否则返回 neoforge 假阳性）；④ WorldEdit/WorldGuard 版本带构建后缀（`7.4.4+7546-...`）需 strip；⑤ **CustomWorldHeight 只在 Modrinth（slug: customworldheight），Hangar 无此插件**（2026-08-15 实测：Hangar 查询失败 → Modrinth 正常 2.2.0）；⑥ LuckPerms 官方渠道是 metadata.luckperms.net（`downloads.bukkit` 直链），Modrinth 滞后（5.5.76 时 Modrinth 只有 5.5.71-bukkit）；⑦ Geyser build 号频繁更新（1222→1223 一天内），升级前必须查最新；⑧ **packetevents 多平台发布（fabric/velocity/sponge/spigot/bungeecord），须 loaders=["paper","spigot","bukkit","folia"] 过滤，否则返回第一个 fabric 版（version_number 形如 `2.13.0+spigot`，strip_build 剥离 `+...` 后比较）**；有差异时 cron agent 发飞书询问用户是否升级，升级走三端顺序：本地测试服 → Exaroton → MCSM（无玩家窗口）

### 6b. MC 定时任务清单（统一管理入口，2026-08-12 起）

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
