# 上游问题清单（交上游用）

> 完整版（含证据/复现/建议/实测数据）在站点目录：`E:/deploy/upstream-issues-20260911.md`。
> 本文只做索引与结论，避免技能与文档双维护。状态以 2026-09-11 回读为准。

## 状态总览

- 两个自研仓（OrzGeeker/OrzMusic、OrzMC/OrzMCDeploy）**全部 issue 已 CLOSED/COMPLETED**，本机在 0.0.10 / 0.0.4 上实测无回归。
- 第三方：MCSManager 新提 2 条（#2346/#2347）；EasyBot 根因由我们定位后上游**已修并合入**（[PR #122](https://github.com/EasyIndie/EasyBot/pull/122) + [PR #123](https://github.com/EasyIndie/EasyBot/pull/123) 均 MERGED，#121 已 CLOSED/COMPLETED），镜像已发 `:latest`（`sha256:1c02c337…`，含 #122+#123；`/api/v1/ready` 已出现 `message_storage` 字段且未就绪返 503）；本机 A/B 实测验证通过。
- 本机当前**无待上报**问题；**待落地**：EasyBot 修复需等 OrzMCDeploy 下一版包 bump digest（[#14](https://github.com/OrzMC/OrzMCDeploy/issues/14)）。

## 已提交 issue

| 编号 | 要点 | 状态 |
|---|---|---|
| [OrzMusic#2](https://github.com/OrzGeeker/OrzMusic/issues/2) | 所有服务 `restart` 默认 no → 重启不自愈（实测静默宕机 12h） | ✅ CLOSED（0.0.8 修） |
| [OrzMusic#3](https://github.com/OrzGeeker/OrzMusic/issues/3) | `ADMIN_API_TOKEN` 取值链含 macOS `~/.bash_history` → 跨平台静默取空 | ✅ CLOSED（0.0.8 修） |
| [OrzMusic#4](https://github.com/OrzGeeker/OrzMusic/issues/4) | `db` 5432 无条件暴露宿主 | ✅ CLOSED（0.0.8 修；0.0.10 实测宿主无 5432） |
| [OrzMusic#7](https://github.com/OrzGeeker/OrzMusic/issues/7) | `release-smoke.sh` 硬依赖 python3 且吞错 → health 假 FAIL | ✅ CLOSED（0.0.9 修） |
| [OrzMusic#8](https://github.com/OrzGeeker/OrzMusic/issues/8) | MSYS 路径转换毁 db-backup 容器内 /tmp → upgrade 第 3 步中止 | ✅ CLOSED（0.0.9 修） |
| [OrzMusic#10](https://github.com/OrzGeeker/OrzMusic/issues/10) | `release-smoke.sh` 用 `-o /dev/null` → MSYS curl 退出 23，3 项假 FAIL + 跳过 4/5 节 | ✅ CLOSED（0.0.10 修，14/14 PASS） |
| [OrzMCDeploy#9](https://github.com/OrzMC/OrzMCDeploy/issues/9) | `DAEMON_PORTS` 应自动忽略（docker 型实例） | ✅ CLOSED（0.0.4 修） |
| [OrzMCDeploy#10](https://github.com/OrzMC/OrzMCDeploy/issues/10) | daemon 512m 上限 vs 镜像 8192 堆上限 | ✅ CLOSED（0.0.4 修） |
| [OrzMCDeploy#11](https://github.com/OrzMC/OrzMCDeploy/issues/11) | 站点增量挂载点（`compose.site.yaml`） | ✅ CLOSED（0.0.4 修） |
| [OrzMCDeploy#12](https://github.com/OrzMC/OrzMCDeploy/issues/12) | 实例启停姿势 / `autoStart` 语义 docs | ✅ CLOSED（0.0.4 修） |
| [EasyBot#121](https://github.com/EasyIndie/EasyBot/issues/121) | DB 属主 root vs uid 10001 → `EPERM` 后静默降级内存库（非 bind mount 固有） | ✅ CLOSED/COMPLETED 2026-09-11：PR #122（核心修复）+ #123（内存回退不再静默）均 MERGED；镜像经 `:latest` 发布（`sha256:341ea707…`）；本机 A/B 实测通过（见站点文档末节）。本机绕过待升级后撤除 |
| [MCSManager#2346](https://github.com/MCSManager/MCSManager/issues/2346) | 运行中改 `InstanceConfig/*.json` 被内存回写覆盖（静默丢改动） | OPEN（本机：停 daemon→改→起） |
| [MCSManager#2347](https://github.com/MCSManager/MCSManager/issues/2347) | `autoStart`/`autoRestart` 语义与状态持久化无文档、两次重启行为不一致 | OPEN（实测摸清，见 docker-service-lifecycle.md §7） |
| [OrzMCDeploy#14](https://github.com/OrzMC/OrzMCDeploy/issues/14) | easybot digest bump 到含 #121 修复的构建（`cd0b4e44` → `1c02c337`） | OPEN（等下一版包） |

## 仍待上游（本机为临时绕过，换包/重建会复发）

| 仓库 | 问题 | 本机绕过 |
|---|---|---|
| EasyBot | ~~DB 初始化失败即静默降级内存库~~（#121） | ✅ **上游已修完毕**（PR #122+#123）；本机 `chown 10001:10001` 绕过**仍生效**（生产轮旧 digest），**升级镜像后再撤** |
| EasyBot | ~~`secure existing DB` 只 chmod 不纠属主，报错无指引~~ | ✅ 同 #122/#123 一并修 |
| MCSManager | 见 #2346 / #2347 | 停 daemon→改文件→起 daemon |

## 明确不提

- Docker Desktop：`docker system df` 把在用镜像算可回收（技能里已标"别信"）；json-file 无默认上限（已用全局 `log-opts` 兜底）。价值有限，不上报。

## 已确认修好（勿再提）

OrzMusic `#2`/`#3`/`#4`/`#7`/`#8`/`#10`；OrzMCDeploy `#4`（Windows daemon 缺 `MCSM_DOCKER_WORKSPACE_PATH`）、`#5`（`restore.sh` SIGPIPE）、`#6`（`DAEMON_PORTS` 冲突告警）、`#7`（MariaDB healthcheck 误报）、`#9`/`#10`/`#11`/`#12`。均实测无回归。

## 提交纪律与教训

- 三件套：**现象 + 原始日志证据 + 最小复现**，附"建议修法"而非吐槽；报前必查重（EasyBot #121 即查重后改为补评论）。
- **提 issue 只需 token 有 `repo` scope，不需要目标仓 push 权限**；先看 `has_issues`。别把 Docker Hub 发布者名当 GitHub 仓名——MCSManager 的正式仓是 `MCSManager/MCSManager`，`githubyumao` 只是镜像发布者（这条曾导致误判"无法上报"）。
- 断言"某功能不存在"前先查源码路由（D3 误判：`remote_service_instances` 早已存在）。
- 引用上游 issue 状态前**必须回读**：本次发现 EasyBot PR #122 在我们记录"未修"之后已被 MERGED。
- 用户偏好原版实现，**不要本地改上游脚本**；改动一律放站点增量（`E:/orzmc/compose.site.yaml`）或 `.env`。
