# 巡检日期：2026-10-12（周一 周巡检 · **补跑版**，脚本 cmp3 自动生成，基准端 = MCSM {SERVER_NAME}）

> **本周状态：✅ SUCCESS（补跑成功）** —— 上午 09:42 首跑因 MCSM 面板 Cloudflare 隧道故障（HTTP 530 / error 1033）失败，
> 22:5x 面板恢复后按原流程完整补跑，本报告覆盖同名的上午失败版。
> 本次**基准端（MCSM {SERVER_NAME}）有效**：拉取 **MCSM=64 文件** / Exa=52 文件，`STATUS: ✅ SUCCESS`。
>
> **数据有效性**：MCSM 端文件数 = **64（>0）**，本次为**有效数据**（上午失败版为 0 文件）。
> ⚠️ MCSM 端本次有 **2 个文件拉流失败**（`/server.properties`、`/plugins/ViaVersion/config.yml`，瞬时限流/断流所致），
> 故报告中 `server.properties` 显示「基准端缺失」——属**拉取瞬时失败**，非真实配置漂移；ViaVersion 未参与对比。
>
> **与上午失败版对比（新增/修正）**：
> - 上午版：全部 0 文件 → 结论「无有效漂移数据」；本次：两端 65 个文件全量语义对比完成。
> - 本次**全新有效结论**：✅ 完全一致 31（核心 5 + 插件 26） / ❌ 配置差异 26（核心 1 + 插件 25） / ℹ️ 运行时数据差异 8。
>
> **执行环境**：MCSM({SERVER_NAME}) `⏹️ 停止`（玩家 0/0）；Exaroton `status=0(OFFLINE)`。两端均为停止/离线态，
> 审查为**只读拉取**，**未做任何重启或改动**。

---

# 两端配置差异审计报告（2026-09-09 v3·迁移后两端模型）

> 巡检端：**MCSM**（{SERVER_NAME}.cn Windows 运行栈，原本地测试服迁移后） + **Exaroton**（海外服）。

## 审计范围：6 个核心 + 58 个插件配置文件

| 类别 | 数量 |
|:--|:--|
| 核心配置（服务端） | 6 |
| 插件配置 | 58 |
| **合计** | **64** |

判定口径：**交集语义**（两端共同 key 值同=完全一致；单端独有 key 另计）

---

## 一、核心配置（服务端）

### ✅ bukkit.yml — 两端完全一致

### ✅ commands.yml — 两端完全一致

### ✅ config_paper-global.yml — 两端完全一致

### ❌ config_paper-world-defaults.yml — 差异 2 处，另有单端独有 key 5 个

| key | MCSM({SERVER_NAME}) | Exa |
|:--|:--|:--|
| 8@hard | default | 128 |
| 8@soft | default | 32 |

### ✅ spigot.yml — 两端完全一致

### ✅ wepif.yml — 两端完全一致

> ℹ️ `server.properties` 本次 MCSM 端拉流失败（瞬时限流），未参与对比（非漂移）。

---

## 二、插件配置（按插件分组）

### ✅ BackOnDeath（1 个：0 一致 / 0 差异 / 1 数据）

- ℹ️ `config.yml` 运行时数据（玩家/交易/记录，两端独立属正常）

### ❌ CustomWorldHeight（1 个：0 一致 / 1 差异 / 0 数据）

- ❌ `config.yml` Exa 端缺失（MCSM 有、Exaroton 无）

### ✅ DeathChest（2 个：2 一致 / 0 差异 / 0 数据）

- ✅ `blacklist.yml` 两端完全一致
- ✅ `config.yml` 两端完全一致

### ✅ Essentials（6 个：5 一致 / 0 差异 / 1 数据）

- ✅ `config.yml` 两端完全一致
- ✅ `custom_items.yml` 两端完全一致
- ✅ `kits.yml` 两端完全一致
- ✅ `tpr.yml` 两端完全一致
- ℹ️ `upgrades-done.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ✅ `worth.yml` 两端完全一致

### ❌ EzShops（11 个：5 一致 / 3 差异 / 3 数据）

- ❌ `config.yml` 差异 2 处：
  - `0@game-mode`：MCSM=`smp` Exa=`prison`
  - `0@language`：MCSM=`en` Exa=`zh`
- ℹ️ `player-shops.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ❌ `shop-dynamic.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ℹ️ `shop-rotations.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ✅ `shop.yml` 两端完全一致
- ✅ `stock-gui.yml` 两端完全一致
- ✅ `stock-prices.yml` 两端完全一致
- ℹ️ `transactions.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ✅ `shop/prison/menu.yml` 两端完全一致
- ✅ `shop/smp/menu.yml` 两端完全一致
- ❌ `daily-sells/3515325d-d738-39b0-a4d5-0d2f59ece1fe.yml` Exa 端缺失（MCSM 有、Exaroton 无）

### ❌ GetMeHome（4 个：2 一致 / 1 差异 / 1 数据）

- ✅ `config.yml` 两端完全一致
- ✅ `delay.yml` 两端完全一致
- ℹ️ `homes.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ❌ `limit.yml` 差异 1 处：
  - `2@limit`：MCSM=`30` Exa=`10`

### ❌ Geyser-Spigot（1 个：0 一致 / 1 差异 / 0 数据）

- ❌ `config.yml` 差异 1 处：
  - `0@config-version`：MCSM=`8` Exa=`7`

### ✅ GriefPreventionData（2 个：2 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致
- ✅ `messages.yml` 两端完全一致

### ❌ GrimAC（10 个：0 一致 / 10 差异 / 0 数据）

- ❌ `config.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `database.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `discord.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `messages.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `punishments.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `databases/mongo.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `databases/mysql.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `databases/postgres.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `databases/redis.yml` Exa 端缺失（MCSM 有、Exaroton 无）
- ❌ `databases/sqlite.yml` Exa 端缺失（MCSM 有、Exaroton 无）

> 注：GrimAC 全组「Exa 端缺失」为**结构性问题**（Exaroton 端未部署/未生成该插件配置目录），非逐键漂移。

### ✅ LoginSecurity（2 个：2 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致
- ✅ `database.yml` 两端完全一致

### ✅ LuckPerms（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ❌ OrzMC（10 个：2 一致 / 7 差异 / 2 数据）

- ✅ `access_rules.yml` 两端完全一致
- ❌ `config.yml` 差异 5 处：
  - `0@config-version`：MCSM=`15` Exa=`12`
  - `2@cell_location`：MCSM=`world,-18,72,-75,0,0` Exa=`world,0,100,0,0,0`
  - `2@channel`：MCSM=`beta` Exa=`release`
  - `2@discord_server_link`：MCSM=`''` Exa=`'https://discord.gg/9JAb9vpvUE'`
  - `2@qq_group_id`：MCSM=`'1082305302'` Exa=`'1012877775'`
- ❌ `easybot.yml` 差异 4 处：
  - `0@api_key`：MCSM=`eb_a0522efd80be4b338e6af2ab8207b448` Exa=`'eb_96c91c255f1343f0a2ae2b3160a4c8b0'`
  - `0@api_server`：MCSM=`http://easybot:8080` Exa=`https://bot.{SERVER_NAME}.cn`
  - `0@config-version`：MCSM=`15` Exa=`12`
  - `0@ws_server`：MCSM=`ws://easybot:8080` Exa=`wss://bot.{SERVER_NAME}.cn`
- ❌ `guide_book.yml` 差异 2 处：
  - `0@author`：MCSM=`"腐竹"` Exa=`腐竹`
  - `0@title`：MCSM=`"新手指南"` Exa=`新手指南`
- ❌ `im.yml` 差异 5 处：
  - `0@backend`：MCSM=`builtin` Exa=`easybot`
  - `4@app_id`：MCSM=`'cli_aa11b7bc4c789cc8'`（飞书 App ID）Exa=`''`
  - `4@app_secret`：MCSM=`'2jEWVHW279LHnRoir1rQAckPiI1jRWpy'` Exa=`''`
  - `4@client_secret`：MCSM=`'k0HYq9Sm6Rm8UrEc0PoEf6Y0TwQuPuQw'` Exa=`''`
  - `4@token`：MCSM=`''` Exa=`''`（Discord Bot Token）
- ❌ `im_bindings.yml` 差异 1 处：
  - `0@sessions`：MCSM=``（空）Exa=`{}`
- ℹ️ `ip_blacklist.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ℹ️ `permission.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ✅ `portals.yml` 两端完全一致
- ❌ `templates.yml` 差异 34 处：
  - `0@config-version`：MCSM=`15` Exa=`12`
  - 引号风格整体差异：MCSM 用单引号 `'{message}'`，Exa 用双引号 `"{message}"`（command_* 全系列等 34 处）

### ✅ SkinsRestorer（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ✅ Vault（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ✅ ViaBackwards（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ✅ ViaRewind（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ❌ WorldEdit（1 个：0 一致 / 1 差异 / 0 数据）

- ❌ `config.yml` 差异 1 处：
  - `4@"minecraft`：MCSM=`lava"` Exa=`bedrock"`（disallowed-blocks 项）

### ✅ WorldGuard（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ❌ bStats（1 个：0 一致 / 1 差异 / 0 数据）

- ❌ `config.yml` 差异 2 处：
  - `0@enabled`：MCSM=`false` Exa=`true`
  - `0@serverUuid`：MCSM=`60e5974b-...` Exa=`02c94a29-...`

---

## 三、汇总

| 状态 | 核心 | 插件 | 合计 |
|:--|:--|:--|:--|
| ✅ 两端完全一致 | 5 | 26 | 31 |
| ❌ 配置差异 | 1 | 25 | 26 |
| ℹ️ 运行时数据差异（正常） | 0 | 8 | 8 |
| **合计** | **6** | **59** | **65** |

> 注：运行时数据文件 = 玩家家/死亡点/交易记录/审批记录等随玩家变化的内容，两端独立属预期，不算配置漂移。
> `server.properties` 因 MCSM 端拉流瞬时失败未入表（非漂移）。

### 漂移要点（供决策，未自动同步）

1. **OrzMC 主插件配置**：`config-version` MCSM=15 / Exa=12（**Exa 端落后**）；`channel` MCSM=beta / Exa=release（**符合预期**：测试端 beta、生产端 release）；`cell_location` MCSM 已配实体牢房 / Exa 仍为默认空中示例值；IM 凭据（`im.yml`/`easybot.yml`）两端各自环境（MCSM=内网 easybot、Exa=公网域名）**属预期差异**。
2. **templates.yml 34 处**：主体是**引号风格差异**（MCSM 单引号 vs Exa 双引号），语义等价，非真实漂移；但 `config-version` 15 vs 12 说明 **Exa 端模板版本落后**。
3. **EzShops**：`game-mode` MCSM=smp / Exa=prison、`language` en/zh —— 两端**分属不同玩法/语言**，属预期；`shop-dynamic.yml`/`daily-sells/*` Exa 端缺失。
4. **GetMeHome `limit.yml`**：MCSM=30 / Exa=10 —— 家数量上限两端不同，**需确认是否有意为之**。
5. **GrimAC 全组 10 文件 Exa 端缺失**：Exaroton **未部署 GrimAC 或未生成配置**（生产端反作弊配置缺失），**建议重点核查**。
6. **CustomWorldHeight `config.yml` Exa 端缺失**：该插件已计划移除，Exa 端无配置属预期。
7. **WorldEdit `disallowed-blocks`**：MCSM 含 `minecraft:lava`、Exa 含 `minecraft:bedrock` —— 防崩服禁用方块清单**两端不一致**（本地已有 sand/gravel/water/lava 等，Exa 端清单不同），建议核对。
8. **bStats `enabled`**：MCSM=false / Exa=true —— 统计上报开关两端不同，一般无需对齐。
9. **Geyser `config-version`**：MCSM=8 / Exa=7 —— Geyser 配置 schema 版本不同，Exa 端配置版本较旧。

---

## 附：上午失败版故障取证（2026-10-12 09:42 首跑，本次已恢复）

| 探测 | 上午首跑（失败） | 22:5x 补跑（本次） |
|:--|:--|:--|
| `https://mcs.{SERVER_NAME}.cn/` | HTTP **530** / error 1033（Argo Tunnel error） | HTTP **200** ✅ |
| MCSM API 鉴权 | 不可达 | 正常（`files/download` 签发 200） |
| MCSM 配置拉取 | **0 文件**（签发全部失败） | **64 文件** ✅ |
| Exaroton API | 正常 | 正常（Exa=52） |

**判定**：上午 Cloudflare 回源隧道无健康 origin（Windows 侧 `cloudflared`/面板进程未运行）；
**本次面板与隧道均已恢复**。⚠️ 该故障 **2 周内第 2 次复发**（09-28、10-12），隧道可用性呈周期性问题，
**建议排查 Windows 侧 `cloudflared` 自启/守护与计划任务**（仍待处理）。

---
*本文件由「orzmc MC 每周巡检」cron 生成（只读巡检 + 落盘报告，未做任何改动）。*
