# 上游问题清单（交上游用）

> 完整版（含证据/复现/建议）在站点目录：`E:/deploy/upstream-issues-20260911.md`。
> 本文只做索引与结论，避免技能与文档双维护。

## 已提交的 issue（2026-09-11，账号 wangzhizhou，均已回读核对）

| 编号 | 要点 | 状态 |
|---|---|---|
| [OrzGeeker/OrzMusic#2](https://github.com/OrzGeeker/OrzMusic/issues/2) | 所有服务 `restart` 默认 no → 重启不自愈 | CLOSED（0.0.8 修） |
| [OrzGeeker/OrzMusic#3](https://github.com/OrzGeeker/OrzMusic/issues/3) | `ADMIN_API_TOKEN` 跨平台静默取空 | CLOSED（0.0.8 修） |
| [OrzGeeker/OrzMusic#4](https://github.com/OrzGeeker/OrzMusic/issues/4) | `db` 5432 暴露宿主 | CLOSED（0.0.8 修） |
| [OrzGeeker/OrzMusic#7](https://github.com/OrzGeeker/OrzMusic/issues/7) | `release-smoke.sh` 硬依赖 python3 且吞错 → health 假 FAIL | CLOSED（0.0.9 修，实测通过） |
| [OrzGeeker/OrzMusic#8](https://github.com/OrzGeeker/OrzMusic/issues/8) | MSYS 路径转换毁 db-backup 容器内 /tmp → upgrade 第 3 步中止 | CLOSED（0.0.9 修，备份恢复产出） |
| [OrzGeeker/OrzMusic#10](https://github.com/OrzGeeker/OrzMusic/issues/10) | `release-smoke.sh` 用 `-o /dev/null` → MSYS curl 退出 23，静态交付三项假 FAIL + 静默跳过 4/5 节 | CLOSED（0.0.10 修，14/14 PASS） |
| [OrzMC/OrzMCDeploy#9](https://github.com/OrzMC/OrzMCDeploy/issues/9) | `DAEMON_PORTS` 应自动忽略（#6 后续） | OPEN |
| [OrzMC/OrzMCDeploy#10](https://github.com/OrzMC/OrzMCDeploy/issues/10) | daemon 512m 上限 vs 8192 堆上限 | OPEN |
| [OrzMC/OrzMCDeploy#11](https://github.com/OrzMC/OrzMCDeploy/issues/11) | 站点增量挂载点（compose.site.yaml） | OPEN |
| [OrzMC/OrzMCDeploy#12](https://github.com/OrzMC/OrzMCDeploy/issues/12) | 实例启停姿势 / autoStart 语义 docs | OPEN |
| [EasyIndie/EasyBot#121](https://github.com/EasyIndie/EasyBot/issues/121) | 同一问题已存在（老板 09-09 自提）→ **改为补评论**：根因=DB 属主 root vs uid 10001（非 bind mount 固有）+ 已验证 chown 修法 + 日志风暴 21.7万条/health 仍绿证据 | 评论已发 |

**无法代提的项（原因）**：MCSManager 本体行为（daemon 内存回写、面板 API 无清单接口）—— `githubyumao` 在 GitHub 不存在（镜像只在 Docker Hub），`MCSManager/MCSManager` 只有 READ 权限；Docker Desktop 两条观察同理。需 fork+PR 或由有权限者代发。

**提交纪律**：必先查重（EasyBot#121 正是查重后改为补评论而非重复提）；每条三件套 = 现象 + 原始日志证据 + 最小复现，附建议修法；三个 Orz 仓均为中文项目且当前账号为 ADMIN，中文提报即可。

## 待上游修（本机均为临时处置，换包/重建会复发）

| 仓库 | 问题 | 严重度 | 本机绕过 |
|---|---|---|---|
| easyindie/easybot | DB 初始化失败即静默降级内存库：无告警、无速率限制、**health 仍报 healthy**，导致数据不落盘 + 日志风暴 | 高 | 手工 `chown 10001:10001` |
| easyindie/easybot | `secure existing DB` 只 chmod 不纠属主，报错无指引 | 中 | 同上 |
| orzgeeker/orzmusic | 官方 compose 所有服务 `restart` 默认 `no` → 重启不自愈（实测静默宕机 12h） | 高 | ✅ 0.0.8 已修（#2 CLOSED，已贴自愈实测：restarts 0→1）；本地 `restart.yml` + `docker update` 补丁已撤 |
| orzgeeker/orzmusic | `ADMIN_API_TOKEN` 取值链含 macOS `~/.bash_history` → 跨平台静默取空 | 中 | 未补（待用户提供） |
| OrzMCDeploy | `DAEMON_PORTS` 与 docker 型实例冲突，0.0.3 仅告警不自动跳过 | 中 | `.env` 置空 |
| OrzMCDeploy | daemon `--memory 512m` vs 镜像 `--max-old-space-size=8192` 不匹配（重负载可能 OOM kill） | 中 | 暂无（实测空闲 51MB/512MB） |
| orzgeeker/orzmusic | `release-smoke.sh` 硬依赖 `python3` 且 `2>/dev/null || echo ""` 吞错 → 缺解析器时 health 整片假 FAIL（易误读成服务故障） | 中 | ✅ 0.0.9 已修（#7 CLOSED，实测 `JSON parser available: python`）；垫片已撤 |
| orzgeeker/orzmusic | MSYS 路径转换把 db-backup 容器内 `/tmp/x.dump` 改写成宿主路径 → `release-upgrade` 第 3 步安全中止 | 中 | ✅ 0.0.9 已修（#8 CLOSED，实测备份 612K 产出）；不需再 `MSYS_NO_PATHCONV` |
| orzgeeker/orzmusic | `release-smoke.sh` 三处 `-o /dev/null` 在 MSYS/mingw curl 上退出 23 → 静态交付 3 项假 FAIL，且 `PASS=false` 后第 4/5 节静默无输出 | 中 | ✅ 0.0.10 已修（#10 CLOSED，实测 14/14 PASS、exit 0）；`native-up/native-status` 同类问题一并修 |
| OrzMCDeploy | 站点增量（FEISHU 凭据）无官方 override 挂载点，换包即丢 | 中 | 手工补 compose.yaml |
| MCSManager | 实例配置由 daemon 内存持有，运行中改文件被回写覆盖 | 中 | 停 daemon→改→起 |
| MCSManager | `autoStart`/`autoRestart` 语义与状态持久化无文档 | 中 | 实测摸清（见 docker-service-lifecycle.md §7） |
| MCSManager | 面板 API 无法列举 daemon/实例 | 低 | 手工取 ID |
| Docker Desktop | `docker system df` 把在用镜像算可回收 | 低 | 技能里标注“别信” |
| Docker Desktop | json-file 日志无默认上限 | 低 | 全局 `log-opts` |

## 已确认修好（0.0.3 实测无回归，勿再提）

OrzMCDeploy `#4`（Windows daemon 缺 `MCSM_DOCKER_WORKSPACE_PATH`）、`#5`（`restore.sh` 大归档 SIGPIPE）、`#6`（`DAEMON_PORTS` 冲突告警）、`#7`（MariaDB 冷数据还原 healthcheck 误报）。

## 上报纪律

- 每条坚持三件套：**现象 + 原始日志证据 + 最小复现**，附“建议修法”而非仅吐槽。
- 报之前先去仓库查重（本文所列均未在 0.0.3 修复清单中）。
- 用户偏好原版实现，**不要在本地改上游脚本**，改动一律放站点增量（`E:/deploy/site/`）或 `.env`。
