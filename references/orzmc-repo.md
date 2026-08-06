# OrzMC 统一代码仓库（运维资产地图）

> **仓库**：`https://github.com/OrzMC/OrzMC`（monorepo 总仓，Apache 2.0）
> **克隆**：`git clone --depth 1 --recurse-submodules --shallow-submodules https://github.com/OrzMC/OrzMC.git`（11 个 git submodule）
> **用途**：Minecraft Geek 工程总仓——本技能涉及的插件源码、插件配置库、运维工具、自维护 fork 全部以 submodule 挂在此仓下。运维场景先在 `~/OrzMC/` 找对应子模块。

## 运维相关子模块

**插件源码**（`plugin/` = 自研主插件；`tools/` = 其他插件 fork + 工具）：

| 子模块路径 | 子仓库 | 运维用途 |
|:--|:--|:--|
| `plugin/` | OrzMCPlugin | **OrzMC 自研插件源码**（EasyBot 多平台机器人/白名单/跨服传送门/GeoIP 安全/传送弓/世界维护/玩家通知）。PR 开发走 GitHub Actions build（产物命名 `OrzMC-{ver}-pr.{n}.{build}.jar`）、Hangar CI 每日 dev 版、GitHub Release 滞后。测试 800+、覆盖率 64% |
| `tools/DeathChest/` | OrzMC/death-chest | **DeathChest 插件源码（fork）**：自编译修复版（死亡+下线丢物品双修复，详见 deathchest-regression.md）；本地 `~/death-chest` 同源 |
| `tools/GetMeHome/` | OrzMC/GetMeHome | **GetMeHome 插件源码（fork）**：自维护，线上 60+ 玩家依赖 |
| `tools/LoginSecurity/` | OrzMC/LoginSecurity | **LoginSecurity 插件源码（fork）**：自维护；含 `src/main/resources/lang` 子模块 |

**工具**：

| 子模块路径 | 子仓库 | 运维用途 |
|:--|:--|:--|
| `paper_plugins_config/` | paper_plugins_config | **三端插件配置"官方版"**（15 个插件：BackOnDeath/DeadChest/Essentials/GetMeHome/Geyser-Spigot/GriefPreventionData/LoginSecurity/LuckPerms/OrzMC/SkinsRestorer/Vault/ViaBackwards/ViaVersion/WorldEdit 等）。配置对齐/基线核对时以此为参考 |
| `tools/OrzMCBackup/` | OrzMC/OrzMCBackup | **Kotlin 世界优化/备份 CLI**：按 InhabitedTime 阈值/强制加载列表/矩形范围保留区块并重写 MCA，支持 `--zip-output` 压缩、`--report-file` JSON/CSV 报告。构建 `./gradlew :app:shadowJar --no-daemon` → `app/build/libs/backup-<ver>.jar` |
| `tools/thanos/` | aternosorg/thanos | **世界瘦身 PHP 库**：按 inhabited time 删除未使用 chunk，体积可减 50%+（非 blocklist 法，兼容 mod/插件）|
| `tools/rust-thanos/` | OrzMC/rust-thanos | thanos 的 Rust 实现（性能更好）|
| `python/` | OrzPythonMC | **OrzMC CLI**（PyPI 可装 `pip install orzmc`）：一键部署 MC 私服（Vanilla/Paper/Spigot/Forge）+ 启动客户端，支持 1.13+ 正式版，Ubuntu/macOS |
| `scripts/` | （本地目录非子模块）| 运维脚本：`crontab/mc_cron.sh`（定时任务）、`ubuntu/`（nginx + SSL、面板 setup、mcs_service、qqbot 服务）、`raspberrypi/`（树莓派 qqbot）、`rsync`（同步）|

## 非运维模块（了解即可）

| 模块 | 说明 |
|:--|:--|
| `app/` (OrzMCApp) | macOS/iOS Minecraft Java 启动器（Swift）|
| `webmc/` (OrzWebMC) | Web 浏览器连 MC 探索（proxy 指向 {SERVER_HOST}）|
| `site/` (OrzMCSite) | **官方网站源码**（Hugo + ananke 主题）|
| `profile/` (.github) | GitHub 组织首页 |
| `skins/` | 玩家皮肤 |

## 关联操作

- **插件 PR 测试**：产物从 GitHub Actions `gh run download` 拿 → 部署见 SKILL.md「OrzMC 自定义插件升级」（文件名带版本号 → 删旧 jar 直放 plugins/，勿用 update/）
- **配置对齐**：三端 config 与 `paper_plugins_config/` 对照（cmp3 脚本工作流）
- **世界瘦身**：`thanos`/`rust-thanos`/`OrzMCBackup` 均可离线处理 world 目录，处理前必须备份
- **备份**：OrzMCBackup CLI 可替代/补充 `backup.sh`（按 inhabited time 而非全量）

## Bot 命令调试（orzdebug，2026-08-06 实测）

- **模拟群里发 Bot 命令**：测试服控制台输入 `orzdebug $h`（等价群里用户发 `$h`）→ 插件以管理员身份处理，结果打到服务器日志（`cmd debug:` 开头）。
- ⚠️ **不要用 `debug` 前缀**（PR #159 修复前）：Paper 1.20+ 原版 `/debug` 命令抢占前缀 + **未注册命令不触发 ServerCommandEvent** → `debug $h` 报 `Incorrect argument`，功能完全不可用。修复 = 前缀改 `orzdebug` + FeatureModule 注册该命令。
- ⚠️ **ServerCommandEvent 只对真实控制台 stdin 触发**：RCON 通道、玩家 `/orzdebug` 都不触发（命令执行但监听器收不到）→ 必须用 screen 喂 stdin：`screen -S mc -p 0 -X stuff 'orzdebug $h\r'`（后台裸 java 进程 stdin=/dev/null，喂不进去）。
- **9 个 Bot 命令实测**（Paper 26.2 + 1.0.14-dev.237）：`$h` 帮助 / `$l` 在线 / `$w` 白名单（分页）/ `$a <名>` 加白 / `$r <名>` 移白 / `$d` 黑名单（**语法：`$d IP` 添加、`$d -IP` 移除、`$d` 查询**——不是 `add/remove` 子命令）/ `$b` 地图备份（三阶段进度）/ `$e <命令>` 控制台命令 / `$o` 地图优化（配置关则提示"已禁用"）——全部通过。
- **RCON 注入**：`server.properties` 开 `enable-rcon=true` + 密码（本机测试服已开 orztest2026）；用 `/tmp/rcon.py`（简易 Python RCON 客户端）发命令。注意 RCON 不触发 ServerCommandEvent。
