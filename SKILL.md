---
name: papermc-server-maintenance
description: "PaperMC 服务器日常维护：创建/升级/插件管理/备份，一套动作适配 local / Exaroton / MCSManager 三种部署。"
version: 1.2.0
author: Hermes Agent
tags: [minecraft, papermc, server, maintenance, upgrade, plugin, exaroton, mcsm]
platforms: [macos, linux]
required_commands: [java, curl, tar]
---

# PaperMC 服务器维护

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
> | OrzMC 统一代码仓库（submodule 资产地图：插件源码/配置库/备份工具/世界瘦身） | `references/orzmc-repo.md` |
> | OrzMC 真实环境验收报告（2026-08-06：全功能测试矩阵 + 双服 transfer + 发现的 bug） | `references/orzmc-acceptance-20260806.md` |
> | OrzMC 功能测试用例（28 项，玩家命令/Bot 命令/事件拦截，含前置条件/步骤/预期） | 插件仓库 `plugin/docs/test-cases.md`（OrzMCPlugin） |
> | OrzMC 端到端测试报告（2026-08-06：机器人+真实玩家，28/28 通过，transfer 闭环） | 插件仓库 `plugin/docs/e2e-test-report-20260806.md`（OrzMCPlugin） |

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
- **插件基线**（三端对齐 17/17 sha256 一致，2026-08-03；OrzMC 2026-08-04 升 1.0.14；Geyser 2026-08-06 升 2.11.1）：BackOnDeath 0.4 / DeathChest 3.0.1 / Essentials 2.22.0 / EzShops 2.5.9 / GetMeHome 3.0.0 / Geyser 2.11.1-SNAPSHOT / GriefPrevention 16.18.7 / LoginSecurity 3.3.2-SNAPSHOT / LuckPerms 5.5.59 / OrzMC 1.0.14 / SkinsRestorer 15.12.5 / Vault 1.7.3-b131 / ViaBackwards 5.11.0 / ViaRewind 4.1.3 / ViaVersion 5.11.0 / WorldEdit 7.4.4 / WorldGuard 7.0.18
- ⚠️ **死亡位置传送覆盖关系（2026-08-05 反编译实证）**：**Essentials `/back` 不能覆盖 BackOnDeath**——`/back` 传送目标是 `LastLocation`（只在 `PlayerTeleportEvent` PLUGIN/COMMAND 原因时更新），**死亡事件不更新 LastLocation** → `/back` 回的是「最后传送点」**不是死亡点**。BackOnDeath 监听死亡事件记录死亡位置。**线上依赖 BackOnDeath 回死亡点功能 → 保留**（仅 SpigotMC 渠道，无 Hangar/Modrinth）。同理 GetMeHome 保留（线上 60+ 玩家用，迁移 Essentials 需脚本转换+多 home 权限，方案未成熟前不动）

## 操作步骤

### 1. 获取最新版本信息
```bash
curl -s https://papermc.io/downloads/paper | python3 ~/.hermes/skills/gaming/papermc-server-maintenance/scripts/parse_papermc.py
# 输出: paper-26.2-92 059d00bbce0fa1707739618b3276f5c80b9655dc0f964306fa799a9c7cb01cc2
```

### 2. 创建/升级/备份/状态（local）
```bash
# 创建
PAPER_BACKEND=local PAPER_DIR=~/minecraft-server \
  ~/.hermes/skills/gaming/papermc-server-maintenance/scripts/adapters/local.sh create
# 升级核心 jar（自动备份旧 jar 可回滚）
PAPER_BACKEND=local PAPER_DIR=~/minecraft-server \
  ~/.hermes/skills/gaming/papermc-server-maintenance/scripts/adapters/local.sh upgrade
# 备份 world + plugins + server.properties（保留 24 份）
PAPER_DIR=~/minecraft-server ~/.hermes/skills/gaming/papermc-server-maintenance/scripts/backup.sh
# 状态 / 日志 / 命令
PAPER_DIR=~/minecraft-server ~/.hermes/skills/gaming/papermc-server-maintenance/scripts/adapters/local.sh status
PAPER_DIR=~/minecraft-server ~/.hermes/skills/gaming/papermc-server-maintenance/scripts/adapters/local.sh logs 50
```
> 详细（含 local 坑：无 rcon、运行时改 whitelist 不生效、macOS 无 timeout）→ `references/local-backend.md`

### 3. 插件安装/更新/卸载
```bash
~/.hermes/skills/gaming/papermc-server-maintenance/scripts/plugin_manager.sh install essentialsx
~/.hermes/skills/gaming/papermc-server-maintenance/scripts/plugin_manager.sh install https://example.com/plugin.jar
~/.hermes/skills/gaming/papermc-server-maintenance/scripts/plugin_manager.sh update   # 全部更新
~/.hermes/skills/gaming/papermc-server-maintenance/scripts/plugin_manager.sh remove essentialsx.jar
```

**插件安装/升级机制（PaperMC 官方，两条路径要分清）**：
- 🆕 **新插件首次安装** → jar **直接放 `plugins/`**（重启时扫描加载；放 update/ 无效/非标准）
- 🔄 **已有插件升级** → 新 jar 放 `plugins/update/` → 重启时 PaperMC **自动替换** `plugins/` 下同名插件（原子操作），update/ 自动清空
- ✅ **插件升级无需备份 jar**：官方源可重下，update 机制原子替换
- ⚠️⚠️ **PaperMC update 按【文件名】覆盖**：带版本号命名的 jar（如 `OrzMC-1.0.13.jar`）升级后文件名变了 → 不覆盖 → **重启后新旧两个 jar 并存冲突**。**先删 plugins/ 下旧 jar 再放 update/**（或重命名新 jar 与旧文件名一致）
- ⚠️ Exaroton **运行中禁止写文件**，上传/升级必须先停服
- ✅ MCSM 端 plugins/update 实测可用（`mcsm_upload_update.py` 上传 → restart → 自动替换）
- ⚠️ **三端插件对齐必须对比 sha256**（文件名相同≠内容相同）；MCSM 运行中 jar 读取 500（锁定），对比用启动日志 `Enabling X vY` 行

### 3b. OrzMC 自定义插件升级（Hangar 发布 + PaperMC update 机制）

**OrzMC 是自有插件**（GitHub `OrzMC/OrzMCPlugin`），发布渠道特殊：**Hangar 活跃（CI 每天自动发布 dev 版）**、GitHub Release 滞后（手动 tag 才出）、Modrinth 发布报错（查不到）。

**升级走 PaperMC 官方 `plugins/update` 机制**（不是手动替换 `plugins/` 下 jar）；**首次新装**则直接放 `plugins/`（无需 update/）：

```bash
# 0. 首次新装（非升级）：jar 直接放 plugins/，重启加载
mv OrzMC-1.0.14-dev.237.jar plugins/
# 升级流程如下：
# 1. 查最新版本（Hangar API；dev=每日自动构建，pr=PR 构建）
curl -s "https://hangar.papermc.io/api/v1/projects/OrzMC/versions?limit=5" | jq -r '.result[] | .name + " | " + .createdAt'
# 2. 拿下载链接
curl -s "https://hangar.papermc.io/api/v1/projects/OrzMC/versions/<版本>" | jq -r '.downloads[].downloadUrl'
#    → https://hangarcdn.papermc.io/plugins/OrzMC/OrzMC/versions/<版本>/PAPER/OrzMC-<版本>.jar
# 3. 下载 + 校验（unzip -p xxx.jar paper-plugin.yml | head 看 version 字段）
# 4. ⚠️ 先删 plugins/ 下旧 jar（PaperMC update 按【文件名】覆盖：OrzMC jar 带版本号，
#    新文件名 ≠ 旧文件名 → 不覆盖 → 重启后新旧两个 jar 并存冲突）
rm plugins/OrzMC-1.0.13-pr.153.394.jar
# 5. 新 jar 放入 plugins/update/（PaperMC 重启时自动原子替换，update/ 自动清空）
mv /tmp/OrzMC-1.0.14-dev.237.jar plugins/update/
# 6. 重启 → 日志 `[OrzMC] Loading server plugin OrzMC v1.0.14` 验证
```

**三端差异**：
- ✅ 本地：删旧 jar + 放 update/ 可不停服（重启时应用），重启用 `start.sh`
- ✅ MCSM：运行中可上传到 `plugins/update/`（jar 上传不触发锁定），玩家下线后 restart 自动替换（`mcsm_upload_update.py` 上传 → restart → 验证）
- ⚠️ Exaroton：**运行中禁止写文件**，须先 stop → 传 update/ → start

> 版本号体系：`主.次.补丁-[dev|pr].[构建号]`（如 `1.0.14-dev.237`）；插件基线已更新到 OrzMC 1.0.14。

### 4. 三端配置对比与同步（scripts/cmp3/）

```bash
CMP=~/.hermes/skills/gaming/papermc-server-maintenance/scripts/cmp3
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
~/.hermes/skills/gaming/papermc-server-maintenance/scripts/adapters/mcsm.sh status|players|logs 50
~/.hermes/skills/gaming/papermc-server-maintenance/scripts/adapters/mcsm.sh start|stop|restart
~/.hermes/skills/gaming/papermc-server-maintenance/scripts/adapters/mcsm.sh command "list"
# MCSM 文件操作（2026-08-06 源码对照+全量实测，12/12 端点可用）
python3 $CMP/mcsm_delete.py /plugins/xxx.jar        # 删除（DELETE /api/files/）
python3 $CMP/mcsm_list_filter.py                     # 列目录（需 file_name 过滤）
```
> 端点表/认证/踩坑 → `references/mcsm-backend.md` 和 `references/exaroton-backend.md`
> **MCSM 文件 API 全面复核（2026-08-06）**：12 个端点全部实测可用（读/写/删/列目录/建文件/建目录/复制/移动/压缩/解压/上传/URL直传）。关键参数坑：list 需 `page=0+page_size+file_name`、move/copy 用二维数组、move 必须 PUT、compress type=1 压缩/type=0 解压。旧结论「无 delete API」「move 不可用」已推翻（详见 mcsm-backend.md）

## Pitfalls（跨后端通用）

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
