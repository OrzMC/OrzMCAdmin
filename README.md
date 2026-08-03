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

## 目录结构

```
OrzMCAdmin/
├── SKILL.md                  # 技能主文件（frontmatter + 使用指引 + 操作步骤）
├── references/               # 背景知识（按后端拆分）
│   ├── exaroton-api.md       #   Exaroton 29 端点 + 平台要点
│   ├── mcsm-api.md           #   MCSManager API + 平台要点
│   └── papermc-versioning.md #   PaperMC 版本/构建机制
├── scripts/
│   ├── adapters/             # 三后端适配器（local.sh / exaroton.sh / mcsm.sh）
│   ├── cmp3/                 # 多服务器配置对比/同步工具集
│   ├── plugin_manager.sh     # 插件管理（Modrinth/URL）
│   ├── backup.sh             # 备份
│   └── parse_*.py            # 版本/日志解析
└── templates/
    └── env.example           # 环境变量模板
```

## 快速开始

```bash
# 1. 配置凭据（复制模板填值）
cp templates/env.example ~/.hermes/.env   # 或 export 环境变量

# 2. 服务器状态
PAPER_DIR=~/minecraft-server scripts/adapters/local.sh status
EXAROTON_API_KEY=xxx EXAROTON_SERVER_ID=yyy scripts/adapters/exaroton.sh status
scripts/adapters/mcsm.sh status           # MCSM（读 .env）

# 3. 升级 PaperMC 核心
PAPER_DIR=~/minecraft-server scripts/adapters/local.sh upgrade

# 4. 插件管理
scripts/plugin_manager.sh install essentialsx
scripts/plugin_manager.sh update

# 5. 三端配置对比
python3 scripts/cmp3/cmp3_configs.py /tmp/exa_configs /tmp/mcsm_configs ~/minecraft-server
```

## 给 AI Agent 的使用说明

1. **加载 `SKILL.md`** 作为技能定义（标准 frontmatter：name/description/when_to_use/version）
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
