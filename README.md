# OrzMCAdmin

服主自动化管理 PaperMC 服务器的**可复用 AI 技能包**——丢给任何 AI Agent（Claude Code / Hermes / OpenClaw / Cursor 等）即可处理 Minecraft Paper 服务器运维。

一套动作，三种部署后端：**本地目录 / Exaroton 云服务器 / MCSManager 面板**。

## 能力

- ✅ 服务器创建 / 状态 / 启动 / 停止 / 重启 / 日志 / 命令
- ✅ PaperMC 核心升级（fill-data 新机制 + sha256 校验）
- ✅ 插件安装 / 更新（plugins/update 热更新）/ 卸载
- ✅ 备份（world + plugins + 配置）
- ✅ 多服务器**配置对齐**（语义级 diff）与**插件版本一致性**（sha256 对比）
- ✅ 跨后端统一动作（`create/status/start/stop/restart/logs/upgrade/plugin/backup/command`）
- ✅ **MCSManager 文件 API 全集**（2026-08-06 源码对照 + 12/12 端点实测）：读 / 写 / 删 / 列目录 / 建文件 / 建目录 / 复制 / 移动 / 压缩 / 解压 / 上传 / URL 直传
- ✅ 基岩版玩家支持（Geyser，三端 offline 直连模式）

## 目录结构

```
OrzMCAdmin/
├── SKILL.md                  # 技能主文件（frontmatter + 决策路径 + 操作步骤）
├── references/               # 背景知识（按主题拆分，全部实测沉淀）
│   ├── local-backend.md      #   本地服务器（创建/升级/备份/坑）
│   ├── exaroton-backend.md   #   Exaroton 云端（29 端点 API 表 + 平台要点）
│   ├── mcsm-backend.md       #   MCSManager 面板（12 文件端点 + 实例 API + 踩坑）
│   ├── geyser-floodgate.md   #   基岩支持（Geyser offline 直连；floodgate 回退记录）
│   ├── spark-analysis.md     #   Spark 性能分析（命令/JSON/判断标准）
│   ├── entity-statistics.md  #   快速实体统计（paper entity list / Spark / 计分板）
│   ├── deathchest-regression.md  # DeathChest 回归测试记录（修复验证）
│   └── mineflayer-bot.md     #   机器人玩家（运维视角）
├── scripts/
│   ├── adapters/             # 三后端适配器（local.sh / exaroton.sh / mcsm.sh）
│   ├── cmp3/                 # 多服务器配置对比/同步/文件操作工具集
│   ├── plugin_manager.sh     # 插件管理（Modrinth/URL）
│   ├── backup.sh             # 备份
│   ├── parse_*.py            # 版本/日志解析
│   ├── bot/                  # 机器人玩家脚本
│   └── regression/           # 回归测试（DeathChest / Geyser UDP）
└── templates/
    └── env.example           # 环境变量模板
```

## 快速开始

```bash
# 1. 配置凭据（复制模板填值）
cp templates/env.example ~/.hermes/.env   # 或 export 环境变量

# 2. 服务器状态
PAPER_DIR=~/minecraft-server scripts/adapters/local.sh status
scripts/adapters/exaroton.sh status       # Exaroton（读 .env）
scripts/adapters/mcsm.sh status           # MCSM（读 .env）

# 3. 升级 PaperMC 核心
PAPER_DIR=~/minecraft-server scripts/adapters/local.sh upgrade

# 4. 插件管理
scripts/plugin_manager.sh install essentialsx
scripts/plugin_manager.sh update

# 5. 三端配置对比
python3 scripts/cmp3/cmp3_configs.py /tmp/exa_configs /tmp/mcsm_configs ~/minecraft-server

# 6. MCSM 文件操作（DELETE /api/files/ 标准方案）
python3 scripts/cmp3/mcsm_delete.py /plugins/xxx.jar
python3 scripts/cmp3/mcsm_list_filter.py   # 列目录（file_name 过滤）
```

## 给 AI Agent 的使用说明

1. **加载 `SKILL.md`** 作为技能定义（标准 frontmatter：name/description/version）
2. `references/` 是背景知识，需要 API 细节时按需读取
3. `scripts/` 是可执行逻辑，**不要改脚本内部逻辑**，通过环境变量/参数注入自己的部署信息
4. 凭据统一从 `.env` 读取，**禁止硬编码**

## 兼容性

| Agent 生态 | 支持 | 说明 |
|:--|:--|:--|
| Hermes（本技能来源） | ✅ | skill 目录直接可用 |
| Claude Code Skills | ✅ | frontmatter + markdown 格式兼容 |
| OpenClaw | ✅ | 同类 skill 结构 |
| Cursor / 通用 | ✅ | SKILL.md + scripts 可读 |

## 环境要求

- Python 3.8+ / bash / curl
- Java 25（PaperMC 26.x 运行需要）
- macOS / Linux（Windows 需适配 bash 环境）

## 迭代

本仓库由实战持续沉淀。新增实测经验会同步更新 `SKILL.md` 与 `references/`。
发现坑点欢迎补充到 Pitfalls。
