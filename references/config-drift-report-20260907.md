# 三端配置差异审计报告（2026-09-07·❌ 审查失败：脚本超时 3600s（连续四周）；v3 拓扑首跑——本地端 93/93 + Exa 79 成功落盘，远程 MCSM 0 文件挂死）

> **本次结论：❌ FAIL（脚本未产出 cmp3 报告即被 cron 3600s 超时杀死，连续第四周：0817/0824/0831/0907）**。本文件为失败标记 + 部分数据快照：**本地端（本机 MCSM 栈实例目录直读）93 文件完整落盘**、**Exaroton 侧 79 文件完整落盘**（均为本次新鲜数据，已用于 Exa vs 本地端对齐项核对），**远程 MCSM 侧 0 文件**（面板 API 密钥异常致拉取线程挂死，**连续四周同因**）。cmp3 语义对比与完整报告未执行。差异基线沿用 2026-08-11/12 成功审计数据（详见 `config-drift-report-20260812.md`），**不代表 2026-09-07 三端实际配置状态**。
> ⚠️ **口径变更提醒**：本次为 v3（2026-09-03 迁移）后首次运行，「本地端」= 本机 MCSM 栈 Paper 实例（`InstanceData/716c2fb7…`，目录直读），**不再是 0811/0831 基线中的 ~/minecraft-server**。本地列数值与旧基线不可直接同比，凡涉及「本地变化」的判定须以本次新口径为准。

## 〇、本次运行证据（/tmp/orzmc_config_audit.log 09:15:41 启动 + /tmp 目录实测）

| 阶段 | 结果 |
|:--|:--|
| 脚本启动 | ✅ 2026-09-07 09:15:41 |
| 1. 三端状态 | MCSM(远程) ❌ 报「未开启API密钥创建功能」（**与 0817/0824/0831 同因，连续四周**）；MCSM(本机栈/本地) ❌ 报「**API 响应异常**」（**首次出现的新信号**）；Exa ✅ status=0(OFFLINE)（未重启）；三端均未重启 |
| 2. 并发拉取 | ⚠️ 部分成功：**本地端=93/93 完整落盘**（/tmp/mcsm_local_configs2 实测 93 文件，目录直读不受面板 API 影响）；**Exa=79 文件落盘**（/tmp/exa_configs2 实测 79 文件，约 14 个路径缺失/失败，详见下）；**远程 MCSM=0 文件**（/tmp/mcsm_configs2 实测 0 文件）；python fetch_all 未返回 → 整脚本被 cron 3600s 超时杀死 |
| 3. 报告生成 | ❌ /tmp/cmp3_report_latest.md 不存在（脚本未走到 cmp3_configs.py/cmp3_report.py） |
| STATUS 行 | 未输出（脚本被 kill，无成败标记）→ 按约定判为 ❌ FAIL |

> Exa=79 vs 本地=93 差异约 14 个路径：本地实例独有的 GrimAC 全套（config/database/discord/messages + databases/×5）、CustomWorldHeight/config.yml（插件已移除的配置残留）、OrzMC/ip_blacklist.yml、EzShops/shop-dynamic.yml、EzShops/daily-sells/*.yml 等——多为本地清单里 Exa 端不存在/未部署的文件；具体失败明细随进程被 kill 丢失（python 块缓冲），无法逐一确认。

## 一、失败原因分析

1. **直接原因（连续四周，完全同构）**：`fetch3_configs.fetch_all` 三线程并发，主线程 `f2.result()` 等**远程 MCSM 线程**永不返回（77/93 文件 × 3 次重试 × 单请求超时最坏数小时）→ 超过 cron 3600s 上限被杀。本周 Exa 与本地端均已完成落盘，**卡点第三次精确定位 = 远程 MCSM 线程**（唯一未完成者）。
2. **前置异常 ①（连续四周，未修复）**：远程 MCSM 面板「未开启API密钥创建功能」（enableApiKey=false + 用户 apiKey 未配）。**0817 首次出现，0824/0831 两次建议修复均未落地**，需在远程 Win11 面板操作。
3. **前置异常 ②（本周新增）**：本机 MCSM 面板（mcs.{SERVER_NAME}.cn）状态查询报「**API 响应异常**」——本地面板 API 侧异常（容器/服务/dns/密钥任一可能），但目录直读（InstanceData 宿主文件系统）不受影响、93/93 成功。**需人工检查本地 MCSM 面板服务健康度**。
4. **无总时长护栏**：整脚本仍无外层超时（v2 去 GNU timeout 后未补等价机制；fetch3 注释声称「内部超时已由 urllib/curl 兜底」，已被连续四周实测证伪——远程 MCSM 线程内部请求超时叠加重试后仍 >3600s）。**0824/0831 建议（总时长护栏 + 错误响应 fast-fail + MCSM 失败时保留两端数据出部分报告）三周未落地，本周照挂。**
5. **不可见性**：python 输出块缓冲，进程被 kill 后 stdout 丢失 → 日志停在「--- 2. 三端配置审查 ---」；本次靠 /tmp 三个目录文件数反证 Exa/本地端已完成。

## 二、审查汇总（基线：2026-08-11 成功审计，本次无新对比数据）

| 状态 | 核心 | 插件 | 合计 |
|:--|:--|:--|:--|
| ✅ 三端完全一致 | 3 | 58 | 61 |
| ❌ 配置差异 | 4 | 4 | 8 |
| ℹ️ 运行时数据差异（正常） | 0 | 8 | 8 |
| **合计** | **7** | **70** | **77** |

> ⚠️ 基线口径为旧拓扑（本地=~/minecraft-server）。v3 本地端（MCSM 实例）清单扩容至 93 文件，下次成功审计需重建基线。cmp3 未运行，本次无可比差异数。

## 三、基线差异文件清单（沿用 20260812/20260831，供下次对比参考）

**核心差异（4 个）**：`server.properties`（约 20 处定位/平台差异）、`bukkit.yml`（connection-throttle 本地 0 vs 云端 4000）、`config/paper-global.yml`（max-packet-rate：MCSM 10000 防攻击调高）、`config/paper-world-defaults.yml`（despawn hard/soft：Exa 128/32）。
**插件差异（4 个）**：GetMeHome/limit.yml（10/10/30）、OrzMC/config.yml（allow_country_code []/[]/[CN,JP,TW,DE]）、OrzMC/easybot.yml（各端独立预期）、bStats/config.yml（serverUuid 实例标识）。
**运行时数据（8 个，正常）**：BackOnDeath/config.yml、GetMeHome/homes.yml、EzShops/player-shops.yml、EzShops/shop-rotations.yml、EzShops/transactions.yml、OrzMC/permission.yml、OrzMC/ip_blacklist.yml、Essentials/upgrades-done.yml。

## 四、对齐项验证（本次部分验证：Exa 今日新鲜数据 vs 本地端（新口径）今日实测；远程 MCSM 无法验证）

| 对齐项 | 本地(本机MCSM实例, 09-05 启动) | Exa(09-06 14:47 平台重写) | 判定 |
|:--|:--|:--|:--|
| sync-chunk-writes | true | **false** | ⚠️ Exa 平台保留差异（非白名单键重启被平台重写，0811 结论维持） |
| command-spam-threshold-seconds | 100000 | 100000 | ✅ 2026-08-12 三端对齐值，Exa/本地均确认生效 |
| chat-spam-threshold-seconds | 10 | 10 | ✅ 一致（默认值） |
| force-gamemode | false | false | ✅ 2026-08-06 统一 false 生效 |
| allow-flight / online-mode / enforce-whitelist / accepts-transfers | true/false/true/true | true/false/true/true | ✅ 一致 |
| difficulty / enable-jmx-monitoring / enable-query | easy/true/true | easy/true/true | ✅ 一致（注意：0811 基线「本地 normal/false」为旧口径 ~/minecraft-server，新口径本地实例已与云端同值，非本次对齐动作） |
| max-tick-time | 60000 | 600000 | ⚠️ 已知平台差异（Exa 放大 10 倍） |
| resource-pack-prompt | 空 | `""` | ✅ 无实质差异（require-resource-pack=false 不显示提示） |
| view-distance / simulation-distance | 6 / 3 | 10 / 5 | ⚠️ 维持差异（0831 观察项复核：新口径本地端仍 6/3，待人工确认是否有意） |
| enable-rcon / rcon 密码 | true / 测试密码 | false / 空 | 定位差异（本地测试态开 RCON） |
| management-server-* | enabled=false/localhost | enabled=true/0.0.0.0:9900 | ⚠️ Exa 平台自动开启（已知差异） |
| pause-when-empty-seconds | -1 | 60 | ⚠️ Exa 平台默认 60（空服暂停），本地 -1 不暂停 |
| max-players / server-port / motd / pvp | 150 / 25565 / 测试服 / false | 20 / 39742 / 海外服 / 缺省 | 定位差异（预期保留） |
| **远程 MCSM 侧全部对齐项** | — | — | ❌ 无法验证（0 文件，连续四周） |

> Exa status=0(OFFLINE) 未重启，本次拉取为最新磁盘内容（server.properties 头时间戳 = 平台最近启动 09-06 14:47 CST）。

## 五、本次新增观察（需人工处理/确认）

1. **🆕 本机 MCSM 面板 API「API 响应异常」（新信号）**：mcs.{SERVER_NAME}.cn 状态查询失败；本地测试服实例目录（InstanceData）完好可直读，但**面板 API 服务异常需人工检查**（web/daemon 容器健康、端口、密钥）。不影响本次目录直读拉取。
2. **远程 MCSM 密钥问题连续第四周**（0817/0824/0831/0907）：「未开启API密钥创建功能」，需远程 Win11 面板 enableApiKey=true + 用户 apiKey；**不修则每周审查必挂**。
3. **脚本缺陷三周未修**：无总时长护栏 + 远程 MCSM 无 fast-fail → 每周必挂；本周 Exa/本地端均已完成仍被拖死，是「MCSM 失败时保留两端口径出部分报告」建议的最强论据。
4. **0831 观察项复核（新口径维持）**：本地端（本机 MCSM papermc-test 实例）view-distance=6 / simulation-distance=3 持续存在（Exa 10/5）。
5. **Exa 配置文件清单变化**：Exa 拉取成功 79 文件（旧基线 77），本地新清单 93——下次成功审计时 cmp3 输出文件数将变化，属 v3 口径正常调整，非配置漂移。
