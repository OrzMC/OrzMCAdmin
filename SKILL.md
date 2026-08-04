---
name: paper-mc-server-admin
description: "PaperMC 服务器全生命周期运维：创建/升级/插件管理/备份/状态监控/配置对齐，一套动作适配 local / Exaroton / MCSManager 三种部署后端。"
version: 1.0.0
author: OrzMC
tags: [minecraft, papermc, server, devops, exaroton, mcsm, automation]
platforms: [macos, linux]
required_commands: [java, curl, python3]
when_to_use: >
  用户要求操作 Minecraft Paper 服务器（创建、升级、装/卸插件、备份、看状态、改配置、
  三端配置对齐、插件版本对比）时。适用于本地目录部署、Exaroton 云服务器、
  MCSManager 面板托管的任意组合。
---

# PaperMC 服务器运维技能（通用版）

> 由 OrzMC 实战沉淀（2026-08）：本地 + Exaroton + MCSM 三后端统一运维。
> 本文件是**通用可复用版**，所有私有信息（域名/账号/服务器 ID）已占位化，
> 使用者通过环境变量注入自己的部署信息。

## 架构：一套动作，三种后端

```
统一动作: create / status / start / stop / restart / logs
         upgrade / plugin / backup / command / config-sync
              │
    ┌─────────┼──────────┐
    ▼         ▼          ▼
  local    exaroton    mcsm
  本机目录   云端API    面板API
```

后端通过环境变量选择（`scripts/adapters/*.sh` 均从环境变量读取）：

| 后端 | 必需环境变量 | 可选 |
|:--|:--|:--|
| `local` | `PAPER_DIR`（服务器目录） | `PAPER_JAVA` |
| `exaroton` | `EXAROTON_API_KEY`、`EXAROTON_SERVER_ID` | — |
| `mcsm` | `MCSM_URL`、`MCSM_API_KEY`、`MCSM_DAEMON_ID`、`MCSM_INSTANCE_ID` | — |

**凭据建议**：写入 `~/.hermes/.env`（或用户目录 `.env`）并 `chmod 600`，脚本自动读取；
也支持直接 export 环境变量。**禁止在脚本/文档中硬编码凭据**。

## 快速开始

```bash
SKILL_DIR=/path/to/paper-mc-server-admin

# 本地服务器状态
PAPER_DIR=~/minecraft-server $SKILL_DIR/scripts/adapters/local.sh status

# Exaroton 状态
EXAROTON_API_KEY=xxx EXAROTON_SERVER_ID=yyy $SKILL_DIR/scripts/adapters/exaroton.sh status

# MCSM 状态（玩家数）
$SKILL_DIR/scripts/adapters/mcsm.sh status
```

## 关键事实（2026-08 实测，三端通用）

- **旧 API `api.papermc.io/v2` 已废弃（410 Gone）**——不要再用。新下载机制唯一正解：
  官网下载页 `https://papermc.io/downloads/paper` 内嵌每个构建 sha256 → 直链
  `https://fill-data.papermc.io/v1/objects/{sha256}/{jar名}`（`scripts/parse_papermc.py` 已封装）
- **PaperMC 26.x 需要 Java 25**（老版本需旧 JDK）
- **插件升级机制（plugins/update/）**：新 jar 放入 `plugins/update/` → 重启时 PaperMC 自动
  原子替换 `plugins/` 下同名插件 → update/ 自动清空。**升级无需备份 jar**（官方源可重下）
- **插件对齐判定 = sha256**：文件名相同 ≠ 内容相同，必须对比 sha256
- **下载 jar 后校验 sha256sum 与页面一致**

详细 API 参考见：
- `references/exaroton-api.md` — Exaroton 29 端点 + 平台要点
- `references/mcsm-api.md` — MCSManager 面板 API + 平台要点
- `references/papermc-versioning.md` — PaperMC 版本/构建机制

## 操作步骤

### 1. 获取最新版本信息
```bash
curl -s https://papermc.io/downloads/paper | python3 $SKILL_DIR/scripts/parse_papermc.py
# 输出: paper-26.2-92 <sha256>
# 直链: https://fill-data.papermc.io/v1/objects/{sha256}/paper-26.2-92.jar
```

### 2. 创建服务器（local）
```bash
PAPER_DIR=~/minecraft-server $SKILL_DIR/scripts/adapters/local.sh create
```
创建：下载最新 jar → eula.txt=true → 生成 server.properties → 生成启动脚本。

### 3. 升级核心（local）
```bash
PAPER_DIR=~/minecraft-server $SKILL_DIR/scripts/adapters/local.sh upgrade
```
升级：解析最新版 → 备份旧 jar（`backups/`）→ 下载新 jar（sha256 校验）→ 替换 → 重启 →
验证日志 `Done`。幂等（已最新不重复下载）。

### 4. 插件安装/更新/卸载
```bash
$SKILL_DIR/scripts/plugin_manager.sh install essentialsx      # Modrinth 搜索安装
$SKILL_DIR/scripts/plugin_manager.sh install https://...jar   # URL 安装
$SKILL_DIR/scripts/plugin_manager.sh update                   # 全部更新（plugins/update/）
$SKILL_DIR/scripts/plugin_manager.sh remove essentialsx.jar   # 卸载
```
- ⚠️ 插件必须匹配 MC 版本（Modrinth API 用 `game_versions` 过滤）
- ⚠️ Exaroton **运行中禁止写文件**（API 返回 File access unavailable），上传插件/升级须先停服
- ✅ MCSM 运行中可上传到 `plugins/update/`（jar 上传不触发锁定，仅读取被锁）

### 4b. 自有插件升级（Hangar 发布，2026-08-04 实测）

自有插件（如 OrzMC，GitHub 仓库 `OrzMC/OrzMCPlugin`）不走 Modrinth/PaperMC，**发布渠道特殊**：
- ✅ **Hangar 活跃**：CI 每天自动发布 dev 版（`主.次.补丁-dev.[构建号]`，如 `1.0.14-dev.237`；`pr` 后缀 = PR 构建）
- ⚠️ GitHub Release 滞后（手动打 tag 才出正式版）
- ⚠️ Modrinth 发布报错（项目搜不到）——**查版本/下载一律用 Hangar API**

```bash
# 1. 查最新版本
curl -s "https://hangar.papermc.io/api/v1/projects/<项目>/versions?limit=5" | jq -r '.result[] | .name + " | " + .createdAt'
# 2. 拿下载链接
curl -s "https://hangar.papermc.io/api/v1/projects/<项目>/versions/<版本>" | jq -r '.downloads[].downloadUrl'
#    → https://hangarcdn.papermc.io/plugins/<项目>/<项目>/versions/<版本>/PAPER/<项目>-<版本>.jar
# 3. 下载 + 校验：unzip -p xxx.jar paper-plugin.yml | head 看 version 字段
# 4. 停服（全杀 java + rm -f world/session.lock）→ 备份旧 jar → 替换
# 5. ⚠️ 删旧 jar！plugins/ 下同名插件两个 jar 会冲突（勿留两个 OrzMC-*.jar）
# 6. 重启 → 日志 `[OrzMC] Loading server plugin OrzMC v1.0.14` 验证
```

### 5. 备份（local）
```bash
PAPER_DIR=~/minecraft-server $SKILL_DIR/scripts/backup.sh
```
打包 world/ + plugins/ + server.properties 到 `backups/`，保留最近 24 份。
> 备份分层：插件无需备 jar；核心 jar 升级自动备份；**世界/玩家数据/配置必须定期备份**。

### 6. 状态/日志/命令
```bash
PAPER_DIR=~/minecraft-server $SKILL_DIR/scripts/adapters/local.sh status
PAPER_DIR=~/minecraft-server $SKILL_DIR/scripts/adapters/local.sh logs 50
PAPER_DIR=~/minecraft-server $SKILL_DIR/scripts/adapters/local.sh command "say Hello"
```

### 7. 三端配置对比与同步（scripts/cmp3/）

配置一致性治理工具集（多服务器对齐场景）：

```bash
CMP=$SKILL_DIR/scripts/cmp3
# 1. 拉取配置到本地目录（Exaroton 用 files/data GET；MCSM 用 download 两步法）
# 2. 全量语义对比（核心+插件，排除数据文件）
python3 $CMP/cmp3_configs.py /tmp/exa_configs /tmp/mcsm_configs ~/minecraft-server
# 3. 插件 jar sha256 对比（三端一致判定）
python3 $CMP/cmp3_plugins_sha.py
# 4. Exaroton 批量改配置（PUT files/data 全量覆盖）→ 验证
python3 $CMP/exa_apply_config.py    # 按需编辑脚本内 apply() 列表
python3 $CMP/exa_verify_config.py
# 5. MCSM 插件热更新（上传 plugins/update/ + 验证）
python3 $CMP/mcsm_upload_update.py pluginA.jar pluginB.jar
python3 $CMP/mcsm_verify_update.py
# 6. MCSM 批量改配置（M1-M10 类型任务：改后重启生效）
python3 $CMP/mcsm_backup_download.py        # 改前快照（MCSM_BACKUP_DIR 指定备份目录）
python3 $CMP/mcsm_apply_config.py           # 读→替换→PUT 写回（按需编辑脚本内替换列表）
python3 $CMP/mcsm_verify_config.py          # 真实 GET 读回验证
```

**MCSM 文件操作注意**：download 凭证 API 对不存在文件也返回 200，**必须真实 GET**
（500=不存在、`PK` 头=真实 jar）；运行中 jar 读取会 500（锁定），对比版本用日志 `Enabling X vY` 行。

## 环境变量模板

见 `templates/env.example`——复制为 `.env` 填入自己的值即可。

## 专题知识（详细文档）

| 主题 | 文档 |
|:--|:--|
| Spark 性能分析（命令/JSON/判断/踩坑） | `references/spark-analysis.md` |
| 快速实体统计（paper entity list / Spark / 计分板） | `references/entity-statistics.md` |
| 机器人玩家 Mineflayer（搭建/坑/常用操作） | `references/mineflayer-bot.md` |
| Exaroton 29 端点 + 平台要点 | `references/exaroton-api.md` |
| MCSManager 面板 API + 平台要点 | `references/mcsm-api.md` |
| PaperMC 版本/构建机制 | `references/papermc-versioning.md` |

> Spark 是 Paper 内置（无需装插件）的卡顿排查首选：`/spark health` → `/spark gc` → `/spark profiler --only-ticks-over 100` → `?raw` 拿 JSON。实体统计最快一行命令：`/paper entity list * minecraft:overworld`。

## Pitfalls（跨后端通用）

- ⚠️ 旧 v2 API 410 Gone；一律用 fill-data 新机制
- ⚠️ 下载必须校验 sha256
- ⚠️ 服务器运行中不要替换 jar（先 stop 再升级）
- ⚠️ eula.txt 不写 `eula=true` 拒绝启动
- ⚠️ Java 25 只能跑 26.x
- ⚠️ macOS bash 3.2：`$var` 后接全角字符要写 `${var}`（无 timeout 命令）
- ⚠️ 有玩家在线时严禁破坏性操作（stop/restart/改配置/文件写）——先查玩家数
- ⚠️ MCSM 操作端点全为 **GET + `/api/protected_instance/` 前缀**（open/stop/restart/command），误用 POST 会 404
- ⚠️ MCSM 读文件两步法：POST /api/files/download 拿凭证 → GET {addr}/download/{pwd}/{文件名}
- ⚠️ **MCSM 写文件（PUT /api/files/）三要点**（2026-08-03 实测）：① **必须带 `daemonId`+`uuid` 参数**——只带 apikey → 403「参数不正确或非法访问实例」；② **只能写已存在的文件**——新文件路径 → 500 `Illegal access path`；③ **body 字段是 `text`**——用 `content` 返回 200 但实际不生效。改配置后**需重启才生效**
- ⚠️ Exaroton 写配置：`POST files/config` 仅支持白名单 35 项（白名单外假成功）；**全量写用 `PUT files/data + {"text": 全文}`**；`POST files/data` 假成功（返回旧内容）
- ⚠️ Exaroton start/stop/restart 是 **GET**（POST 触发 Cloudflare 人机验证）
- ⚠️ Exaroton 高频调用触发 Cloudflare 风控（error 1010 全端点 403），冷却 30s+，脚本间隔 ≥5s
- ⚠️ Exaroton 大文件（>10MB）上传易 524，停服重试
- ⚠️ Exaroton 无备份 API（面板功能）；MCSM daemon 文件操作不稳定（list/mkdir/move 常 500）

## 验证

- `curl -s localhost:25565` 返回 Minecraft 协议字节 = 在线
- 日志 `Done (Xs)!` = 启动成功
- `ls plugins/` 见 jar = 插件已装
