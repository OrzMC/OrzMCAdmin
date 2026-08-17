# 三端配置差异审计报告（2026-08-17·❌ 审查失败：脚本超时 3600s，无新数据）

> **本次结论：❌ FAIL（脚本未产出报告即被 cron 超时杀死）**。本文件为失败标记 + 基线快照（差异明细沿用上一轮 2026-08-11/12 成功审计数据，详见 `config-drift-report-20260812.md`），**不代表 2026-08-17 三端实际配置状态**。

## 〇、本次运行证据（/tmp/orzmc_config_audit.log，09:15:11 启动）

| 阶段 | 结果 |
|:--|:--|
| 脚本启动 | ✅ 2026-08-17 09:15:11 |
| 1. 三端状态 | MCSM ❌ API 报「未开启API密钥创建功能」；Exa ✅ status=0(OFFLINE)（未重启）；本地未重启（设计） |
| 2. 并发拉取 | ❌ 启动后 60 分钟内无任何文件落盘（/tmp/exa_configs2、/tmp/mcsm_configs2 均 0 文件），被 cron 3600s 超时杀死 |
| 3. 报告生成 | ❌ /tmp/cmp3_report_latest.md 不存在（脚本未走到 cmp3_report.py） |
| STATUS 行 | 未输出（脚本被 kill，无成败标记）→ 按约定判为 ❌ FAIL |

## 一、失败原因分析

1. **直接原因**：`orzmc_config_audit.sh` 在拉取阶段（fetch3_configs.fetch_all 并发拉取）挂死，超过 cron 3600s 上限被杀。
2. **前置异常**：MCSM 状态查询返回「未开启API密钥创建功能」——面板侧 API 密钥权限/开关问题（2026-08-12 上轮未出现，疑似面板侧变更或 key 失效，需人工查面板）。
3. **不可见性**：python 输出重定向到文件为块缓冲，进程被 kill 后缓冲丢失 → 日志停在「--- 2. 三端配置审查 ---」，无法定位卡在 Exa 还是 MCSM。各单请求虽有超时（Exa GET 60s / MCSM POST 20s×3 重试 / MCSM 下载 GET 60s×4 重试），但 **MCSM 侧 77 文件 × 多轮重试最坏总时长可达数小时，整脚本无总时长护栏**。
4. **无成败标记**：脚本设计末尾输出 STATUS 行，但被 kill 时不会执行 → cron 侧需要「无 STATUS 行 / 无报告文件」即判 FAIL 的兜底。

## 二、审查汇总（基线：2026-08-11 成功审计，本次无新数据）

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

**插件差异（4 个）**：
- `GetMeHome/limit.yml`（limit：10/10/30，MCSM 家上限保留）
- `OrzMC/config.yml`（allow_country_code：[]/[]/[CN,JP,TW,DE]）
- `OrzMC/easybot.yml`（api_key / api_server / ws_server / qq_group_id / discord_server_link，各端独立预期）
- `bStats/config.yml`（serverUuid 实例标识）

**运行时数据（8 个，正常）**：BackOnDeath/config.yml、GetMeHome/homes.yml、EzShops/player-shops.yml、EzShops/shop-rotations.yml、EzShops/transactions.yml、OrzMC/permission.yml、OrzMC/ip_blacklist.yml、Essentials/upgrades-done.yml

## 四、对齐项验证

本次未验证（无拉取数据）。上轮结论维持：Exa `sync-chunk-writes` 平台保留 false（非白名单键重启被平台重写）；SkinsRestorer connectionOptions / DeathChest debug+sound / paper-global 等 2026-08-11 对齐项三端已生效。

## 五、修复建议

1. MCSM 面板检查 API 密钥：「未开启API密钥创建功能」→ 确认密钥权限/重新生成，并同步 `~/.hermes/.env`
2. 脚本加**总时长护栏**：整脚本外层超时（如 perl alarm / 后台 wait+超时杀），超时即输出 STATUS ❌ 并 exit 非 0
3. fetch3 失败快速失败：MCSM 错误响应（非 200 status）直接 fail，勿耗尽多轮重试
4. cron 侧兜底：「无 STATUS 行 / 无报告文件」直接判 FAIL（本次即此情形）
