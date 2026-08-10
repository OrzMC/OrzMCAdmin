# 三端配置差异审计（2026-08-11 三次审计）

> 触发：全量拉取三端（本地 ~/minecraft-server / Exaroton / MCSM）核心+插件配置，语义对比。
> 工具：`scripts/cmp3/fetch3_configs.py`（拉取）+ `cmp3_configs.py`（对比）+ `cmp3_diff_detail.py`（明细）+ `cmp3_report.py`（完整报告生成）+ `cmp3_trend.py`（新旧报告变化跟踪）。
> 基线：77 个配置文件（核心 7 + 插件 70），**真实配置差异 10 个文件，8 个运行时数据文件，59 个完全一致**。
> **完整报告（保留最近两次，最新为准）**：
> - `references/config-drift-report-20260811.md`（三次审计·最新）
> - `references/config-drift-report-20260810.md`（二次审计·用于变化跟踪）
>
> **变化跟踪（20260810 → 20260811）**：唯一变化 = OrzMC/config.yml `allow_country_code` MCSM `[CN,JP,TW]` → `[CN,JP,TW,DE]`（2026-08-11 为德国玩家加白名单，`/config reload` 热更新）。其余 76 个文件差异项全部无变化。

## 对比工具链（新增/修复）

| 脚本 | 作用 |
|:--|:--|
| `fetch3_configs.py` | 以本地插件清单为基准，从 Exaroton + MCSM 拉全量配置到 /tmp（**2026-08-10 修复：MCSM 改串行拉取+失败自动重试（指数退避 3s×3），一次 77/77 全成功，不再有并发 500**；空文件判定用 `data is None`，0B 文件正常落盘） |
| `cmp3_configs.py` | 语义对比（已修复：server.properties 用 `=` 解析，之前假一致） |
| `cmp3_diff_detail.py` | 逐 key 输出三方值明细 |
| `mcsm_refetch.py` | MCSM 失败文件串行补拉（并发→500） |

**API 坑（拉取时实测）**：
- MCSM `/api/files/list` **必须传 `file_name`（可空串）否则返回 total=0**；page_size ≤50（200 触发 500）
- Exaroton `files/info` 用 `isDirectory` 字段（不是 `type`）
- ⚠️ **Exaroton 的 server.properties 曾被 JSON 包装写入残留**：文件尾多一行 `{"text"="server-ip\=..."}`（2009B 转义块），Java 解析为垃圾 key 无害；对比时前 73 行真实配置仍有效。**根因已定位并修复（2026-08-10）**：`exa_apply_config.py` 的 put_file 曾用 `{"text": content}` JSON 包装 PUT → 改共享模块 `scripts/exa_file.py`（GET 自动解包、PUT 裸文本）；`fix_exaroton_cfg.py` 坏依赖 /tmp/exa_file.py 已改为引用共享模块

## 一、核心配置差异（真实差异）

### server.properties（17 项真实差异，vs Exa 19 处 / vs MCSM 12 处）

| key | 本地 | Exa | MCSM | 判定 |
|:--|:--|:--|:--|:--|
| difficulty | normal | easy | easy | ⚠️ 本地测试难度与云端不同（云端 easy） |
| enable-jmx-monitoring | false | true | true | ⚠️ 云端开 JMX，本地关 |
| enable-query / query.port | false | true / 9898 | true / 9898 | ⚠️ 云端开 query，本地关 |
| enable-rcon / rcon.password | true / orztest2026 | false / 空 | false / 空 | ✅ 本地测试开 RCON（预期） |
| management-server-enabled | false | true | false | ⚠️ 仅 Exa 开管理服务器（0.0.0.0:9900） |
| management-server-secret | 本地值 | Exa 值 | MCSM 值 | ✅ 每端独立密钥（预期） |
| max-players | 20 | 20 | 150 | ⚠️ **MCSM 150 vs 本地/Exa 20**（定位差异，用户决策保留） |
| max-tick-time | 60000 | 600000 | 60000 | ⚠️ Exa 放大 10 倍（允许单 tick 长时间卡顿） |
| motd | 本地测试 | 海外服 | 国内服 | ✅ 定位差异（预期） |
| pause-when-empty-seconds | -1 | 60 | -1 | ⚠️ Exa 无人 60s 停（省钱），本地/MCSM 不停 |
| server-port | 25565 | 39742 | 25565 | ✅ 定位差异（预期） |
| simulation-distance | 6 | 5 | 3 | ⚠️ 三端都不同（本地 6 / Exa 5 / MCSM 3） |
| sync-chunk-writes | true | false | true | ⚠️ Exa 关（性能优化，崩溃丢档风险） |
| view-distance | 8 | 10 | 6 | ⚠️ 三端都不同（本地 8 / Exa 10 / MCSM 6） |
| enable-command-block | false | 无键 | 无键 | ✅ 缺省同 false |
| previews-chat | 无键 | false | 无键 | ✅ 缺省同 false |
| resource-pack-prompt | 无键 | "" | "" | ✅ 无实质差异 |

**一致性亮点**：online-mode=false（三端离线）、force-gamemode=false（三端已统一）、white-list/enforce-whitelist=true、allow-flight=true、spawn-protection=0、op-permission-level=4、enable-rcon 以外全部对齐。

### bukkit.yml
- `connection-throttle`：本地 **0** / Exa 4000 / MCSM 4000 —— ✅ 本地测试关登录冷却（预期，testing.md 记载）

### spigot.yml / paper-global.yml（行为一致，文件形态差异）
- spigot.yml：**Exa 369 行（全量展开版，显式写出 entity-activation-range animals:32/monsters:32/raiders:64 等默认值）** vs 本地/MCSM 184 行（精简版，缺省用 Paper 默认）——cmp3 交集对比确认本地显式配置的 key 三端值相同，**行为一致**，非真实差异
- paper-global.yml：三端一致 ✅

### config/paper-world-defaults.yml
- `engine-mode`：本地 **2** / Exa **1** / MCSM **2** —— ⚠️ **Exa 用原版红石引擎（1），本地/MCSM 用 Alternate Current（2）**（性能差异）

## 二、插件配置差异（真实差异）

| 插件文件 | key | 本地 | Exa | MCSM | 判定 |
|:--|:--|:--|:--|:--|:--|
| DeathChest/config.yml | debug | true | false | false | ✅ 本地调试开（预期） |
| DeathChest/config.yml | sound | `minecraft:block.chest.locked;1.0;1.0` | `BLOCK_CHEST_LOCKED;1.0;1.0` | 同 Exa | ⚠️ sound 格式不同（本地新格式 vs 云端旧枚举） |
| DeathChest/config.yml | exclude-died-player | false | 无键 | 无键 | ✅ 缺省同 false |
| GetMeHome/limit.yml | limit | 10 | 10 | **30** | ⚠️ **MCSM 家上限 30 vs 本地/Exa 10** |
| OrzMC/config.yml | allow_country_code | [] | [] | [CN, JP, TW] | ⚠️ **仅 MCSM 配 GeoIP 白名单**（1.0.15 内网短路后无害但未对齐） |
| OrzMC/config.yml | qq_group_id / title / ups | 空/占位 | 空 | '902452859' + 3 个 B站 UP | ⚠️ **仅 MCSM 配 UP 关注推广** |
| OrzMC/easybot.yml | api_server / ws_server | test-bot.{SERVER_NAME}.cn | bot.{SERVER_NAME}.cn | bot.{SERVER_NAME}.cn | ✅ 本地测试网关 vs 云端正式（预期） |
| OrzMC/easybot.yml | api_key | 各自 | 各自 | 各自 | ✅ 每端独立 key（预期） |
| OrzMC/easybot.yml | qq_group_id | 1082305302 | 1012877775 | 753649704 | ✅ 各端群不同（预期） |
| OrzMC/easybot.yml | discord_server_link | 空 | discord.gg/9JAb9vpvUE | 空 | ⚠️ 仅 Exa 有 Discord 链接 |
| SkinsRestorer/config.yml | connectionOptions | sslMode=trust | verifyServerCertificate=false&useSSL=false | 同 Exa | ⚠️ 本地 MySQL 连接参数不同（无 SSL 验证 vs 显式关 SSL） |
| SkinsRestorer/config.yml | perSkinPermissionsConsent | 'I will follow the rules'（带引号） | 无引号 | 无引号 | ✅ YAML 引号差异，值相同 |
| SkinsRestorer/config.yml | ifNoServerBlockCommand | true | false | false | ⚠️ 本地 true vs 云端 false（无皮肤时禁命令） |
| bStats/config.yml | serverUuid | 各自 | 各自 | 各自 | ✅ 实例标识（预期） |

## 三、非配置差异（玩家数据/运行时，正常，勿"对齐"）

- BackOnDeath/config.yml：玩家 UUID → 死亡坐标（三端玩家不同）
- GetMeHome/homes.yml：玩家家数据（三端玩家不同）
- EzShops/shop-rotations.yml：商店轮换 next-change 时间戳
- OrzMC/permission.yml：builder-promotion 审批请求记录（仅 MCSM 有历史）
- OrzMC/ip_blacklist.yml：空列表格式差异
- Essentials/userdata、EzShops/shop/*（价格/菜单为配置，玩家商店为数据）

## 四、结论与建议（按用户三端配置决策原则：默认对齐、定位保留）

**建议对齐（功能类，非定位）**：
1. GetMeHome limit：MCSM 30 → 10（或决策统一值）——需玩家通知（已有 30 上限用户）
2. DeathChest sound 格式：本地 `minecraft:` 前缀（新版格式）→ 云端同步
3. SkinsRestorer ifNoServerBlockCommand：云端 false → 按意愿对齐（本地 true 是测试态？）
4. OrzMC allow_country_code：三端统一 []（1.0.15 已有内网短路，白名单无必要）或统一 [CN,JP,TW]
5. OrzMC UP 推广（qq_group_id/title/ups）：确认是否三端都要，若只 MCSM 保留则记录为定位差异

**建议保留（定位/环境差异）**：
- motd、server-port、max-players、view-distance/simulation-distance（性能档）、pause-when-empty-seconds（Exa 省钱）、enable-rcon（本地测试）、enable-jmx/query（云端监控）、management-server（Exa）、easybot 网关/群/api_key、bStats UUID

**风险提示**：
- Exa `sync-chunk-writes=false` + `max-tick-time=600000`：性能优先配置，崩溃可能丢 chunk 数据
- Exa `engine-mode=1`（原版红石）：与本地/MCSM 的 AC 红石行为不同，**跨服传送后红石机器行为可能不一致**

## 附：复现命令

```bash
# 1. 拉取（改配置前跑，落 /tmp/exa_configs2 /tmp/mcsm_configs2）
python3 ~/.hermes/skills/gaming/orzmc/scripts/cmp3/fetch3_configs.py
# MCSM 并发失败后补拉：
python3 ~/.hermes/skills/gaming/orzmc/scripts/cmp3/mcsm_refetch.py
# 2. 对比
python3 ~/.hermes/skills/gaming/orzmc/scripts/cmp3/cmp3_configs.py /tmp/exa_configs2 /tmp/mcsm_configs2 ~/minecraft-server
# 3. 明细
python3 ~/.hermes/skills/gaming/orzmc/scripts/cmp3/cmp3_diff_detail.py > /tmp/diff_detail.txt
```

## 附2：Exaroton JSON 包装污染修复记录（2026-08-10）

**问题**：早期脚本用 `{"text": 全文}` JSON 包装 PUT 写 Exaroton 配置 → 被原样存为文件内容：
- YAML 文件尾残留 `text: "..."` 折叠块（整个配置的转义副本，Paper 解析为垃圾 key）
- server.properties 尾残留 `{"text"="..."}` 单行

**污染源**：`exa_apply_config.py` 的 put_file 用 JSON 包装 PUT（2026-08-09 文档已修正但脚本漏改）

**修复**：
1. 新建共享模块 `scripts/exa_file.py`：GET 自动解包（yaml.safe_load 取 text / json 解包），**PUT 必须裸文本**
2. `exa_apply_config.py` / `fix_exaroton_cfg.py`（原依赖 /tmp/exa_file.py 已坏）改用共享模块
3. 新增 `scripts/exa_recover_residue.py`：从残留块解出原始完整配置并覆盖恢复
4. 线上已恢复 3 个文件：paper-global.yml（160 行完整版）、paper-world-defaults.yml（328 行完整版）、server.properties（删残留行）

**原则（用户拍板 2026-08-10）**：残留块 text 值 = 配置文件原始完整内容，**以原始内容为准恢复**。
⚠️ 例外：server.properties 的残留块是旧快照（force-gamemode=true 等废弃值）→ 只删残留行保留当前真实段。

**残留块解包方法**：`yaml.safe_load(整个文件)` 取 `text` 键 → 再解 `\n`→换行、`\=`→`=`、`\"`→`"`（双重转义）

**修复后对比更真实**（残留块曾干扰 cmp3 判定）：
- paper-global.yml：恢复出 timings 段等 11 键（此前被残留块掩盖）
- paper-world-defaults.yml：despawn-ranges 显式值、anti-xray hidden-blocks 差异（Exa 无 raw_copper_block/raw_iron_block 等）
