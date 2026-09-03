# 三端配置差异审计报告（2026-08-31·❌ 审查失败：脚本超时 3600s（连续三周）；Exa 侧 77/77 成功，MCSM 侧 0 文件挂死）
> ⚠️ **2026-09-03 迁移标注**：本地测试服已迁 MCSM 本机栈（mcs.{SERVER_NAME}.cn Docker 实例，数据在 `/Users/Shared/orzmc/mcsmanager/daemon/data/InstanceData/<uuid>`）。文中 `~/minecraft-server`、`~/folia-test` 路径及裸跑/symlink 机制为迁移前历史状态，已失效；现行拓扑见 `testing.md`。

> **本次结论：❌ FAIL（脚本未产出 cmp3 报告即被 cron 3600s 超时杀死）**。本文件为失败标记 + 部分数据快照：**Exaroton 侧 77/77 配置已完整拉取**（/tmp/exa_configs2，本次新鲜数据，已用于 Exa vs 本地对齐项核对），**MCSM 侧 0 文件**（面板 API 密钥异常致拉取挂死，**连续三周同因：0817/0824/0831**），cmp3 语义对比与完整报告未执行。差异基线沿用 2026-08-11/12 成功审计数据（详见 `config-drift-report-20260812.md`），**不代表 2026-08-31 三端实际配置状态**。

## 〇、本次运行证据（/tmp/orzmc_config_audit.log 09:15:54 启动 + /tmp 目录实测）

| 阶段 | 结果 |
|:--|:--|
| 脚本启动 | ✅ 2026-08-31 09:15:54 |
| 1. 三端状态 | MCSM ❌ API 报「未开启API密钥创建功能」（**与 0817/0824 同因，连续三周**）；Exa ✅ status=0(OFFLINE)（未重启）；本地未重启（设计） |
| 2. 并发拉取 | ⚠️ 部分成功：**Exa=77/77 完整落盘**（/tmp/exa_configs2 实测 77 文件）；**MCSM=0 文件**（/tmp/mcsm_configs2 实测 0 文件）；python fetch_all 未返回，整脚本被 cron 3600s 超时杀死 |
| 3. 报告生成 | ❌ /tmp/cmp3_report_latest.md 不存在（脚本未走到 cmp3_report.py） |
| STATUS 行 | 未输出（脚本被 kill，无成败标记）→ 按约定判为 ❌ FAIL |

## 一、失败原因分析

1. **直接原因**：同 0824——`fetch3_configs.fetch_all` 中 **MCSM 侧拉取挂死**（77 文件 × 多轮重试最坏数小时），超过 cron 3600s 上限被杀。Exa 侧 77/77 再次完整成功落盘，卡点再次明确锁定在 **MCSM 线程**（与 0824 完全同构，无新信息量）。
2. **前置异常（连续三周，未修复）**：MCSM 状态查询返回「未开启API密钥创建功能」——面板侧 API 密钥权限/开关问题自 2026-08-17 起持续存在；文件列表/下载 API 同样不可用 → 拉取在 MCSM 侧反复重试耗尽时间窗。**0824 已建议修复，一周过去未落地，本周照挂。**
3. **不可见性**：python 输出重定向为块缓冲，进程被 kill 后缓冲丢失 → 日志停在「--- 2. 三端配置审查 ---」；本次靠 /tmp/exa_configs2 有 77 文件落盘反证 Exa 线程已完成。
4. **无总时长护栏**：整脚本无外层超时（v2 去掉 GNU timeout 后未补等价机制；0824 建议未落地）。

## 二、审查汇总（基线：2026-08-11 成功审计，本次无新对比数据）

| 状态 | 核心 | 插件 | 合计 |
|:--|:--|:--|:--|
| ✅ 三端完全一致 | 3 | 58 | 61 |
| ❌ 配置差异 | 4 | 4 | 8 |
| ℹ️ 运行时数据差异（正常） | 0 | 8 | 8 |
| **合计** | **7** | **70** | **77** |

## 三、基线差异文件清单（2026-08-11 审计，供下次对比参考）

**核心差异（4 个）**：
- `server.properties`（20 处：difficulty / enable-jmx / enable-query / enable-rcon / management-server / max-players / max-tick-time / motd / pause-when-empty-seconds / server-port / simulation-distance / sync-chunk-writes / view-distance 等，均为已知定位/平台差异）
- `bukkit.yml`（connection-throttle：本地 0 vs 云端 4000，本地测试态）
- `config/paper-global.yml`（max-packet-rate：MCSM 10000 防攻击调高）
- `config/paper-world-defaults.yml`（despawn hard/soft：Exa 128/32 性能优化）

**插件差异（4 个）**：GetMeHome/limit.yml（10/10/30）、OrzMC/config.yml（allow_country_code []/[]/[CN,JP,TW,DE]）、OrzMC/easybot.yml（各端独立预期）、bStats/config.yml（serverUuid 实例标识）

**运行时数据（8 个，正常）**：BackOnDeath/config.yml、GetMeHome/homes.yml、EzShops/player-shops.yml、EzShops/shop-rotations.yml、EzShops/transactions.yml、OrzMC/permission.yml、OrzMC/ip_blacklist.yml、Essentials/upgrades-done.yml

## 四、对齐项验证（本次部分验证：Exa 今日新鲜数据 vs 本地实测）

| 对齐项 | 本地（今日实测） | Exa（今日实测） | 判定 |
|:--|:--|:--|:--|
| sync-chunk-writes | true | **false** | ⚠️ Exa 平台保留差异（非白名单键重启被平台重写，0811 结论维持） |
| command-spam-threshold-seconds | 100000 | 100000 | ✅ 2026-08-12 三端对齐值 Exa/本地均确认生效 |
| max-tick-time | 60000 | 600000 | ⚠️ 已知平台差异（Exa 放大 10 倍） |
| resource-pack-prompt | 空 | `""` | ✅ 无实质差异（require-resource-pack=false 不显示提示） |
| **MCSM 侧全部对齐项** | — | — | ❌ 无法验证（0 文件，连续三周） |

> Exa 今日 status=0(OFFLINE) 未重启，本次拉取为最新磁盘内容（server.properties 头时间戳为平台最近启动时刻）。其余已知差异（difficulty=easy、enable-jmx/query=true、management-server-enabled=true、pause-when-empty-seconds=60、server-port=39742、simulation-distance=5、view-distance=10 等）与基线一致，无新变化。

## 五、本次新增观察（单端变化，需人工确认）

- **0824 观察项复核（持续存在）**：本地测试服 **view-distance=6 / simulation-distance=3**（vs 0811 基线 8/6，今日实测 ~/minecraft-server/server.properties 仍为 6/3）。推测与 2026-08-18 Folia 接管测试服后的性能档调整有关，**需人工确认是否有意为之**，并在下次成功审计中核实三端口径。
- 除上述外无新单端变化可确认（cmp3 未运行，本地/Exa 全量对比未执行）。

## 六、修复建议（0824 已提，本周重申）

1. **优先：修复 MCSM 面板 API 密钥**——「未开启API密钥创建功能」连续三周（0817/0824/0831），面板侧确认密钥权限/重新生成并同步 `~/.hermes/.env`；**不修则每周审查必挂，已连续白跑三周**。
2. 脚本加**总时长护栏**（perl alarm / 后台 wait+超时杀），超时即输出 STATUS ❌ 并 exit 非 0；**MCSM 错误响应 fast-fail**（非 200 直接判失败，勿耗尽 77 文件 × 多轮重试）。
3. 建议 MCSM 侧拉取失败时**保留 Exa 侧数据继续出「双端部分报告」**（Exa vs 本地），避免整轮白跑。
4. cron 侧兜底维持：「无 STATUS 行 / 无报告文件」判 FAIL；本次 /tmp/exa_configs2 有 77 文件可作部分依据。
