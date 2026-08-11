---
name: orzmc
description: "Minecraft 运维统一技能（唯一入口）：三端服务器运维/插件构建升级/性能诊断/权限体系/测试/基岩支持，45 个知识体系 + 29 个脚本。"
version: 2.0.0
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
> | **EasyBot IM 网关运维（docker 容器/健康检查/QQ token/gateway.db 诊断；脚本 easybot_deliveries.py；原 easybot-gateway-ops 技能合并）** | `references/easybot-gateway.md` |
> | **部署配置同步（config drift 判定/fallback 判断/补键同步；原 deployment-config-sync 技能合并）** | `references/config-sync.md` |
> | **Git 子模块全量同步（OrzMC monorepo 14 子模块；默认分支探测/发布后指针/分支清理；原 git-submodule-sync 技能合并）** | `references/git-submodule-sync.md` |
> | **Java 测试编译陷阱（Mockito 泛型捕获/SuppressWarnings 位置/CI warnings 清零；原 java-test-pitfalls 技能合并）** | `references/java-test-pitfalls.md` |
> | Spark 性能分析（命令/JSON/判断/踩坑） | `references/spark-analysis.md` |
> | 快速实体统计（paper entity list / Spark / 计分板） | `references/entity-statistics.md` |
> | 机器人玩家 Mineflayer（运维视角；开发细节见独立技能 `minecraft-bot-mineflayer`） | `references/mineflayer-bot.md` |
> | DeathChest 回归测试（死亡瞬间下线→物品丢失；✅已修复 v3.0.1-fix1；脚本 scripts/regression/） | `references/deathchest-regression.md` |
> | Geyser 基岩支持（当前 offline 直连模式；floodgate 已回退 2026-08-05） | `references/geyser-floodgate.md` |
> | **插件源码构建/开发（构建工具选择、Gradle/Maven 坑、PR 流程、发布规范）** | `references/plugin-build.md` |
> | **插件升级与配置迁移（三端范式、Exaroton/MCSM API 坑、EzShops 存储、Geyser 排查）** | `references/plugin-mgmt.md` |
> | **三端配置差异审计（2026-08-11 三次全量对比；保留最近两次报告：config-drift-report-20260811.md 最新 / 20260810.md 变化跟踪；cmp3 工具链用法）** | `references/three-end-config-drift.md` |
> | **性能诊断（Spark 五步法、实体审计、Aikar Flags、修复方案）** | `references/performance.md` |
> | **插件 Bug 排查（本地复现、命令/权限分离、实体事件、版本兼容）** | `references/plugin-debugging.md` |
> | **测试体系（分层原则、三大通道、Paper 26 陷阱、跨服 transfer）** | `references/testing.md` |
> | **LuckPerms 权限体系（API 集成、审计验收、三端同步、Bootstrap）** | `references/permission.md` |
> | **实体/传送门行为（事件继承、原版规则、白名单策略）** | `references/entity-portal.md` |
> | OrzMC 统一代码仓库（submodule 资产地图：插件源码/配置库/备份工具/世界瘦身） | `references/orzmc-repo.md` |
> | OrzMC 真实环境验收报告（2026-08-06：全功能测试矩阵 + 双服 transfer + 发现的 bug） | `references/orzmc-acceptance-20260806.md` |
> | OrzMC 功能测试用例（28 项，玩家命令/Bot 命令/事件拦截，含前置条件/步骤/预期） | 插件仓库 `plugin/docs/test-cases.md`（OrzMCPlugin） |
> | OrzMC 端到端测试报告（2026-08-06：机器人+真实玩家，28/28 通过，transfer 闭环） | 插件仓库 `plugin/docs/e2e-test-report-20260806.md`（OrzMCPlugin） |
> | RCON 客户端（`scripts/rcon.py <命令> [端口]`，密码从环境变量 RCON_PASSWORD 读） | `scripts/rcon.py` |
> | LoginSecurity 注册状态查询（`scripts/check_lsdb.py [db路径] [玩家名]`） | `scripts/check_lsdb.py` |
> | PaperMC 插件 E2E 测试方案调研（MockBukkit/WatchWolf/GameTest/真实环境/容器化 + 推荐组合） | `references/plugin-e2e-testing.md` |

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

## 关键事实（2026-08 实测）

- **旧 API `api.papermc.io/v2` 已完全废弃（410 Gone）**——用 fill-data 新机制（`parse_papermc.py` 封装）
- **最新稳定版**：paper-26.2-111（2026-08-10 三端实测；**26.2-92 与 111 行为可能不同**，本地复现必须与线上同构建）；**Java 要求**：26.x 需要 Java 25
- **插件基线**（三端对齐，2026-08-10 更新）：OrzMC **1.0.16** / EzShops 2.5.9（storage.type: **yaml**，无 MySQL）/ Geyser **2.11.1-b1214**（基岩 26.40 支持，b1208 不支持）/ LoginSecurity 3.3.2-SNAPSHOT（**本地修复版**：getPlayer null 防御，Gradle 构建）/ LuckPerms 5.5.71（官方渠道，平台滞后 12 版）/ EssentialsX 2.22.0（⚠️ 26.2 不兼容：/spawn 未注册 + op 全拒）/ ViaVersion 系列 5.11.0 稳定版不升 SNAPSHOT / BackOnDeath 0.4 / DeathChest 3.0.1 / GetMeHome 3.0.0 / GriefPrevention 16.18.7 / SkinsRestorer 15.12.5 / Vault 1.7.3-b131 / ViaBackwards 5.11.0 / ViaRewind 4.1.3 / WorldEdit 7.4.4 / WorldGuard 7.0.18
- **GeoIP 内网误拦截（2026-08-06 修复，OrzMC 1.0.15）**：MCSM allow_country_code=[CN,JP,TW] 时内网玩家（192.168.x/10.x）被拦截——geojs.io 无法解析私有段返回未知国家码。1.0.15 加内网 IP 短路（RFC1918/环回/CGNAT 直接放行，公网仍检查）。OrzMC 配置读取为实时（改 config.yml 后 **`/config reload` 即生效**，无需重启；⚠️ 2026-08-11 修正：命令是 **`/config reload`（根命令 `config`，别名 `cfg`，源码 FeatureModule.java `commands.register(node, "配置管理", List.of("cfg"))`）**，技能旧写 `/orzconfig reload` 是错的——实际执行返回 Unknown）；临时缓解=allow_country_code 改 []
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
