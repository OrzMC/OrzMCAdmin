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

> **知识分类索引**：本 SKILL.md 只留决策路径；详细知识在 `references/`（后端 API 表 / Spark / 实体统计 / 机器人）：
>
> | 主题 | 文档 |
> |:--|:--|
> | 本机服务器操作（创建/升级/备份/状态） | `references/local-backend.md` |
> | Exaroton 云端（API 端点表 + 平台要点） | `references/exaroton-backend.md` |
> | MCSM 面板（API 端点表 + 平台要点 + 适配器） | `references/mcsm-backend.md` |
> | Spark 性能分析（命令/JSON/判断/踩坑） | `references/spark-analysis.md` |
> | 快速实体统计（paper entity list / Spark / 计分板） | `references/entity-statistics.md` |
> | 机器人玩家 Mineflayer（运维视角；开发细节见独立技能 `minecraft-bot-mineflayer`） | `references/mineflayer-bot.md` |
> | DeathChest 回归测试（死亡瞬间下线→物品丢失；✅已修复 v3.0.1-fix1；脚本 scripts/regression/） | `references/deathchest-regression.md` |
> | Geyser 基岩支持（当前 offline 直连模式；floodgate 已回退 2026-08-05） | `references/geyser-floodgate.md` |
> | **插件源码构建/开发（构建工具选择、Gradle/Maven 坑、PR 流程、发布规范）** | `references/plugin-build.md` |
> | **插件升级与配置迁移（三端范式、Exaroton/MCSM API 坑、EzShops 存储、Geyser 排查）** | `references/plugin-mgmt.md` |
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
- **最新稳定版**：paper-26.2-92（2026-08-02）；**Java 要求**：26.x 需要 Java 25
- **插件基线**（三端对齐 17/17 sha256 一致，2026-08-03；**2026-08-06 全面升级**：OrzMC 1.0.14 正式版、LuckPerms 5.5.71（官方 download.luckperms.net，平台滞后官方 12 版）、Geyser 2.11.1-b1209（官方稳定构建）；ViaVersion 系列保持 5.11.0 稳定版不升 SNAPSHOT）：BackOnDeath 0.4 / DeathChest 3.0.1 / Essentials 2.22.0 / EzShops 2.5.9 / GetMeHome 3.0.0 / Geyser 2.11.1-b1209 / GriefPrevention 16.18.7 / LoginSecurity 3.3.2-SNAPSHOT / LuckPerms 5.5.71 / OrzMC 1.0.14 / SkinsRestorer 15.12.5 / Vault 1.7.3-b131 / ViaBackwards 5.11.0 / ViaRewind 4.1.3 / ViaVersion 5.11.0 / WorldEdit 7.4.4 / WorldGuard 7.0.18
- **GeoIP 内网误拦截（2026-08-06 修复，OrzMC 1.0.15）**：MCSM allow_country_code=[CN,JP,TW] 时内网玩家（192.168.x/10.x）被拦截——geojs.io 无法解析私有段返回未知国家码。1.0.15 加内网 IP 短路（RFC1918/环回/CGNAT 直接放行，公网仍检查）。OrzMC 配置读取为实时（改 config.yml 后 /orzconfig reload 即生效，无需重启）；临时缓解=allow_country_code 改 []
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

### 3b. OrzMC 自定义插件升级（Hangar 发布 + PaperMC update 机制）

**OrzMC 是自有插件**（GitHub `OrzMC/OrzMCPlugin`），发布渠道特殊：**Hangar 活跃（CI 每天自动发布 dev 版）**、GitHub Release 滞后（手动 tag 才出）、Modrinth 发布报错（查不到）。

**升级走 PaperMC 官方 `plugins/update` 机制**（不是手动替换 `plugins/` 下 jar）；**首次新装**则直接放 `plugins/`（无需 update/）：

```bash
# 0. 首次新装（非升级）：jar 直接放 plugins/，重启加载
mv OrzMC-1.0.14-dev.237.jar plugins/
# 升级流程（官方标准，2026-08-08 实测验证）：
# 1. 查最新版本（Hangar API；dev=每日自动构建，pr=PR 构建）
curl -s "https://hangar.papermc.io/api/v1/projects/OrzMC/versions?limit=5" | jq -r '.result[] | .name + " | " + .createdAt'
# 2. 拿下载链接
curl -s "https://hangar.papermc.io/api/v1/projects/OrzMC/versions/<版本>" | jq -r '.downloads[].downloadUrl'
#    → https://hangarcdn.papermc.io/plugins/OrzMC/OrzMC/versions/<版本>/PAPER/OrzMC-<版本>.jar
# 3. 下载 + 校验（unzip -p xxx.jar paper-plugin.yml | head 看 version 字段）
# 4. ✅ 新 jar 直接放 plugins/update/（按插件名 name=OrzMC 匹配，文件名任意；
#    绝不动 plugins/ 下旧 jar）→ 重启自动替换，update/ 自动清空
mv /tmp/OrzMC-1.0.14-dev.237.jar plugins/update/
# 5. 重启 → 日志 `[OrzMC] Loading server plugin OrzMC v1.0.14` 验证
# 6. ⚠️ 同步配置文件：新版本新增模板键时（如 templates.yml 的 review_*/rank_*），
#    jar 升级≠配置升级——本地开发时 templates.yml 已更新，但 MCSM/Exaroton 部署 jar 漏同步
#    → 启动健康检查报「缺失: templates.<新键>」（功能有 fallback 兜底不中断，但告警吵人）。
#    2026-08-08 实测：11 个 review/rank 模板键三端 diff 只差新键（无远端自定义）→ 直接上传本地版覆盖即可。
#    修后重启健康检查告警消失（Exaroton 实测验证）。
# 7. ⚠️ 权限同步必须含继承链（parent）：perm_commands.txt 只含 permission set，
#    旧服遗留组（1.0.15）parent 可能仍是 default（LuckPermsBootstrap 幂等不校正已有组）
#    → builder 缺 member 权限（家/传送/商店）。2026-08-08 三端实测修复：
#    `lp group member parent set default` / `lp group builder parent set member` / `lp group admin parent set builder`
#    （MCSM 日志不含 LP 命令输出，验证靠 bot 玩家 orzdebug 或用户控制台）
```

**三端差异**：
- ✅ 本地：删旧 jar + 放 update/ 可不停服（重启时应用），重启用 `start.sh`
- ✅ MCSM：运行中可上传到 `plugins/update/`（jar 上传不触发锁定），玩家下线后 restart 自动替换（`mcsm_upload_update.py` 上传 → restart → 验证）
- ⚠️ Exaroton：**运行中禁止写文件**，须先 stop → 传 update/ → start

> 版本号体系：`主.次.补丁-[dev|pr].[构建号]`（如 `1.0.14-dev.237`）；插件基线已更新到 OrzMC 1.0.14。

### 4. 三端配置对比与同步（scripts/cmp3/）

```bash
CMP=~/.hermes/skills/gaming/orzmc/scripts/cmp3
# 1. 拉取配置到目录（Exaroton: exa_backup_config.py；MCSM: mcsm_download 逐文件拉取）
# 2. 全量语义对比（核心+插件，排除数据文件）
python3 $CMP/cmp3_configs.py /tmp/exa_configs2 /tmp/mcsm_configs2 ~/minecraft-server
# 3. 插件 jar sha256 对比
python3 $CMP/cmp3_plugins_sha.py
# 4. Exaroton 批量改配置（PUT files/data 全量覆盖）
python3 $CMP/exa_apply_config.py && python3 $CMP/exa_verify_config.py
# 5. MCSM 插件更新（上传到 plugins/update/ + 验证）
python3 $CMP/mcsm_upload_update.py deathchest.jar GriefPrevention.jar
python3 $CMP/mcsm_verify_update.py
```

**凭据约定**：全部从 `~/.hermes/.env` 读取（`mcsm_env.py` 共享模块），**禁止硬编码 API key**。

### 5. MCSM / Exaroton 日常操作
```bash
# MCSM（有玩家在线时 stop/restart/command 自动拒绝）
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh status|players|logs 50
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh start|stop|restart
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh command "list"
# MCSM 文件操作（2026-08-06 源码对照+全量实测，12/12 端点可用）
python3 $CMP/mcsm_delete.py /plugins/xxx.jar        # 删除（DELETE /api/files/）
python3 $CMP/mcsm_list_filter.py                     # 列目录（需 file_name 过滤）
```
> 端点表/认证/踩坑 → `references/mcsm-backend.md` 和 `references/exaroton-backend.md`
> **MCSM 文件 API 全面复核（2026-08-06）**：12 个端点全部实测可用（读/写/删/列目录/建文件/建目录/复制/移动/压缩/解压/上传/URL直传）。关键参数坑：list 需 `page=0+page_size+file_name`、move/copy 用二维数组、move 必须 PUT、compress type=1 压缩/type=0 解压。旧结论「无 delete API」「move 不可用」已推翻（详见 mcsm-backend.md）

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
