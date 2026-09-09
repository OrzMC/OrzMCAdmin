# 两端配置差异审计报告（2026-09-09 v3·迁移后两端模型）

> 巡检端：**MCSM**（{SERVER_NAME}.cn Windows 运行栈，原本地测试服迁移后） + **Exaroton**（海外服）。

## 审计范围：7 个核心 + 58 个插件配置文件

| 类别 | 数量 |
|:--|:--|
| 核心配置（服务端） | 7 |
| 插件配置 | 58 |
| **合计** | **65** |

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

### ❌ server.properties — 差异 16 处，另有单端独有 key 2 个

| key | MCSM({SERVER_NAME}) | Exa |
|:--|:--|:--|
| 0@enable-rcon | true | false |
| 0@management-server-enabled | false | true |
| 0@management-server-host | localhost | 0.0.0.0 |
| 0@management-server-port | 0 | 9900 |
| 0@management-server-secret | 89GCEpIcbJw16Q8WlJe8UbNP4Owfma4rdzOg6mB3 | owsKQa02LxnFv0murSfWeok5vr3dBKvERk9ZNx04 |
| 0@management-server-tls-enabled | true | false |
| 0@max-players | 150 | 20 |
| 0@max-tick-time | 60000 | 600000 |
| 0@motd | §e[Paper] 测试服-验证地图恢复状况 | §b🗡 §7欢迎来到§a{SERVER_NAME}§7的§e海外§7服务器！§b⛏ |
| 0@pause-when-empty-seconds | -1 | 60 |
| 0@rcon.password | orztest2026 |  |
| 0@resource-pack-prompt |  | "" |
| 0@server-port | 25565 | 39742 |
| 0@simulation-distance | 3 | 5 |
| 0@sync-chunk-writes | true | false |
| 0@view-distance | 6 | 10 |

### ✅ spigot.yml — 两端完全一致

### ✅ wepif.yml — 两端完全一致

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

### ✅ LoginSecurity（2 个：2 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致
- ✅ `database.yml` 两端完全一致

### ✅ LuckPerms（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ❌ OrzMC（10 个：3 一致 / 6 差异 / 2 数据）

- ✅ `access_rules.yml` 两端完全一致
- ❌ `config.yml` 差异 5 处：
  - `0@config-version`：MCSM=`14` Exa=`12`
  - `2@cell_location`：MCSM=`world,-18,72,-75,0,0` Exa=`world,0,100,0,0,0`
  - `2@channel`：MCSM=`beta` Exa=`release`
  - `2@discord_server_link`：MCSM=`''` Exa=`'https://discord.gg/9JAb9vpvUE'`
  - `2@qq_group_id`：MCSM=`'1082305302'` Exa=`'1012877775'`
- ❌ `easybot.yml` 差异 4 处：
  - `0@api_key`：MCSM=`eb_a0522efd80be4b338e6af2ab8207b448` Exa=`'eb_96c91c255f1343f0a2ae2b3160a4c8b0'`
  - `0@api_server`：MCSM=`http://easybot:8080` Exa=`https://bot.{SERVER_NAME}.cn`
  - `0@config-version`：MCSM=`14` Exa=`12`
  - `0@ws_server`：MCSM=`ws://easybot:8080` Exa=`wss://bot.{SERVER_NAME}.cn`
- ✅ `guide_book.yml` 两端完全一致
- ❌ `im.yml` 差异 5 处：
  - `0@backend`：MCSM=`builtin` Exa=`easybot`
  - `4@app_id`：MCSM=`'cli_aa11b7bc4c789cc8'            # 飞书开放平台 App ID（cli_ 前缀）` Exa=`''            # 飞书开放平台 App ID（cli_ 前缀）`
  - `4@app_secret`：MCSM=`'2jEWVHW279LHnRoir1rQAckPiI1jRWpy'        # 飞书开放平台 App Secret` Exa=`''        # 飞书开放平台 App Secret`
  - `4@client_secret`：MCSM=`'k0HYq9Sm6Rm8UrEc0PoEf6Y0TwQuPuQw'` Exa=`''`
  - `4@enabled`：MCSM=`true` Exa=`false`
- ❌ `im_bindings.yml` 差异 1 处：
  - `0@sessions`：MCSM=`` Exa=`{}`
- ℹ️ `ip_blacklist.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ℹ️ `permission.yml` 运行时数据（玩家/交易/记录，两端独立属正常）
- ✅ `portals.yml` 两端完全一致
- ❌ `templates.yml` 差异 34 处：
  - `0@config-version`：MCSM=`14` Exa=`12`
  - `2@command_admin_required`：MCSM=`'{message}'` Exa=`"{message}"`
  - `2@command_backup`：MCSM=`'{message}'` Exa=`"{message}"`
  - `2@command_blacklist_add`：MCSM=`'{message}'` Exa=`"{message}"`
  - `2@command_blacklist_error`：MCSM=`'{message}'` Exa=`"{message}"`
  - `2@command_blacklist_list`：MCSM=`'{patterns}'` Exa=`"{patterns}"`
  - `2@command_blacklist_remove`：MCSM=`'{message}'` Exa=`"{message}"`
  - `2@command_help`：MCSM=`'{help}'` Exa=`"{help}"`
  - `2@command_optimize`：MCSM=`'{message}'` Exa=`"{message}"`
  - `2@command_optimize_disabled`：MCSM=`'{message}'` Exa=`"{message}"`
  - …等共 34 处

### ✅ SkinsRestorer（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ✅ Vault（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ✅ ViaBackwards（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ✅ ViaRewind（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ✅ ViaVersion（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ❌ WorldEdit（1 个：0 一致 / 1 差异 / 0 数据）

- ❌ `config.yml` 差异 1 处：
  - `4@-"minecraft`：MCSM=`lava"` Exa=`bedrock"`

### ✅ WorldGuard（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 两端完全一致

### ❌ bStats（1 个：0 一致 / 1 差异 / 0 数据）

- ❌ `config.yml` 差异 2 处：
  - `0@enabled`：MCSM=`false` Exa=`true`
  - `0@serverUuid`：MCSM=`60e5974b-c66c-4c8b-931b-9384a86c271f` Exa=`02c94a29-7bc2-4ace-ae32-a071decbe58f`

---
## 三、汇总

| 状态 | 核心 | 插件 | 合计 |
|:--|:--|:--|:--|
| ✅ 两端完全一致 | 5 | 28 | 33 |
| ❌ 配置差异 | 2 | 23 | 25 |
| ℹ️ 运行时数据差异（正常） | 0 | 8 | 8 |
| **合计** | **7** | **59** | **66** |

> 注：运行时数据文件 = 玩家家/死亡点/交易记录/审批记录等随玩家变化的内容，两端独立属预期，不算配置漂移。
