# 三端配置差异审计报告（2026-08-11 三次·工具链修复后）

## 审计范围：77 个配置文件

| 类别 | 数量 |
|:--|:--|
| 核心配置（服务端） | 7 |
| 插件配置 | 70 |
| **合计** | **77** |

三端：**本地** ~/minecraft-server / **Exa** Exaroton（海外服） / **MCSM**（国内服）
判定口径：**交集语义**（三端共同 key 值全同=完全一致；单端独有 key 另计）

---
## 一、核心配置（服务端 7 个）

### ❌ server.properties — 差异 18 处，另有单端独有 key 2 个

| key | 本地 | Exa | MCSM |
|:--|:--|:--|:--|
| 0@difficulty | normal | easy | easy |
| 0@enable-jmx-monitoring | false | true | true |
| 0@enable-query | false | true | true |
| 0@enable-rcon | true | false | false |
| 0@management-server-enabled | false | true | false |
| 0@management-server-host | localhost | 0.0.0.0 | localhost |
| 0@management-server-port | 0 | 9900 | 0 |
| 0@management-server-secret | yhWIDznPC2Co8ujuLwDMT5W6HrK8lw9izvcnFnMu | oyPS1MgZ9TyywXnMm1TyUzzvzXYm6NhkUpMnwGA7 | 89GCEpIcbJw16Q8WlJe8UbNP4Owfma4rdzOg6mB3 |
| 0@management-server-tls-enabled | true | false | true |
| 0@max-players | 20 | 20 | 150 |
| 0@max-tick-time | 60000 | 600000 | 60000 |
| 0@motd | §b§lPaperMC Server §8|§a welcome | §b🗡 §7欢迎来到§a{SERVER_NAME}§7的§e海外§7服务器！§b⛏ | §b🗡🗡 §7欢迎来到§a{SERVER_NAME}§7的§b国内§7服务器！§b⛏ |
| 0@pause-when-empty-seconds | -1 | 60 | -1 |
| 0@query.port | 25565 | 9898 | 9898 |
| 0@rcon.password | orztest2026 |  |  |
| 0@server-port | 25565 | 39742 | 25565 |
| 0@simulation-distance | 6 | 5 | 3 |
| 0@view-distance | 8 | 10 | 6 |

### ❌ bukkit.yml — 差异 1 处

| key | 本地 | Exa | MCSM |
|:--|:--|:--|:--|
| 2@connection-throttle | 0 | 4000 | 4000 |

### ✅ spigot.yml — 三端完全一致（Exa 为全量展开版 369 行/本地 MCSM 精简版 184 行，交集配置值全同，行为一致）

### ✅ commands.yml — 三端完全一致

### ❌ config/paper-global.yml — 差异 4 处，另有单端独有 key 11 个

| key | 本地 | Exa | MCSM |
|:--|:--|:--|:--|
| 10@-minecraft | damage | damage | lodestone_tracker |
| 2@no-permission | <red>I'm sorry, but you do not have permission to perform this command. | <red>I'm sorry, but you do not have permission to perform this command. | <red>I'm sorry, but you do not have permission to perform this |
| 4@max-packet-rate | 500.0 | 500.0 | 10000 |
| 4@secret | '' | '' | "" |

### ❌ config/paper-world-defaults.yml — 差异 2 处，另有单端独有 key 5 个

| key | 本地 | Exa | MCSM |
|:--|:--|:--|:--|
| 8@hard | default | 128 | default |
| 8@soft | default | 32 | default |

### ✅ wepif.yml — 三端完全一致

---
## 二、插件配置（70 个，按插件分组）

### ✅ BackOnDeath（1 个：0 一致 / 0 差异 / 1 数据）

- ℹ️ `config.yml` 运行时数据（玩家/交易/记录，三端独立属正常）

### ✅ DeathChest（2 个：2 一致 / 0 差异 / 0 数据）

- ✅ `blacklist.yml` 三端完全一致
- ✅ `config.yml` 三端完全一致

### ✅ Essentials（6 个：5 一致 / 0 差异 / 1 数据）

- ✅ `config.yml` 三端完全一致
- ✅ `custom_items.yml` 三端完全一致
- ✅ `kits.yml` 三端完全一致
- ✅ `tpr.yml` 三端完全一致
- ℹ️ `upgrades-done.yml` 运行时数据（玩家/交易/记录，三端独立属正常）
- ✅ `worth.yml` 三端完全一致

### ✅ EzShops（36 个：33 一致 / 0 差异 / 3 数据）

- ✅ `config.yml` 三端完全一致
- ℹ️ `player-shops.yml` 运行时数据（玩家/交易/记录，三端独立属正常）
- ℹ️ `shop-rotations.yml` 运行时数据（玩家/交易/记录，三端独立属正常）
- ✅ `shop.yml` 三端完全一致
- ✅ `stock-gui.yml` 三端完全一致
- ✅ `stock-prices.yml` 三端完全一致
- ℹ️ `transactions.yml` 运行时数据（玩家/交易/记录，三端独立属正常）
- ✅ `shop/prison/menu.yml` 三端完全一致
- ✅ `shop/prison/rotations/daily-specials.yml` 三端完全一致
- ✅ `shop/prison/categories/building.yml` 三端完全一致
- ✅ `shop/prison/categories/daily_specials.yml` 三端完全一致
- ✅ `shop/prison/categories/decorations.yml` 三端完全一致
- ✅ `shop/prison/categories/enchantments.yml` 三端完全一致
- ✅ `shop/prison/categories/farming.yml` 三端完全一致
- ✅ `shop/prison/categories/fishing.yml` 三端完全一致
- ✅ `shop/prison/categories/food.yml` 三端完全一致
- ✅ `shop/prison/categories/mining.yml` 三端完全一致
- ✅ `shop/prison/categories/mob_drops.yml` 三端完全一致
- ✅ `shop/prison/categories/redstone.yml` 三端完全一致
- ✅ `shop/prison/categories/spawners.yml` 三端完全一致
- ✅ `shop/prison/categories/valuables.yml` 三端完全一致
- ✅ `shop/prison/categories/wood.yml` 三端完全一致
- ✅ `shop/smp/menu.yml` 三端完全一致
- ✅ `shop/smp/rotations/daily-specials.yml` 三端完全一致
- ✅ `shop/smp/categories/building.yml` 三端完全一致
- ✅ `shop/smp/categories/daily_specials.yml` 三端完全一致
- ✅ `shop/smp/categories/decorations.yml` 三端完全一致
- ✅ `shop/smp/categories/enchantments.yml` 三端完全一致
- ✅ `shop/smp/categories/farming.yml` 三端完全一致
- ✅ `shop/smp/categories/fishing.yml` 三端完全一致
- ✅ `shop/smp/categories/food.yml` 三端完全一致
- ✅ `shop/smp/categories/mining.yml` 三端完全一致
- ✅ `shop/smp/categories/mob_drops.yml` 三端完全一致
- ✅ `shop/smp/categories/redstone.yml` 三端完全一致
- ✅ `shop/smp/categories/valuables.yml` 三端完全一致
- ✅ `shop/smp/categories/wood.yml` 三端完全一致

### ❌ GetMeHome（4 个：2 一致 / 1 差异 / 1 数据）

- ✅ `config.yml` 三端完全一致
- ✅ `delay.yml` 三端完全一致
- ℹ️ `homes.yml` 运行时数据（玩家/交易/记录，三端独立属正常）
- ❌ `limit.yml` 差异 1 处：
  - `2@limit`：本地=`10` Exa=`10` MCSM=`30`

### ✅ Geyser-Spigot（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致

### ✅ GriefPreventionData（2 个：2 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致
- ✅ `messages.yml` 三端完全一致

### ✅ LoginSecurity（2 个：2 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致
- ✅ `database.yml` 三端完全一致

### ✅ LuckPerms（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致

### ❌ OrzMC（7 个：3 一致 / 2 差异 / 2 数据）

- ❌ `config.yml` 差异 1 处：
  - `2@allow_country_code`：本地=`[]` Exa=`[]` MCSM=`[CN, JP, TW, DE]`
- ❌ `easybot.yml` 差异 5 处：
  - `0@api_key`：本地=`'eb_a0522efd80be4b338e6af2ab8207b448'` Exa=`'eb_96c91c255f1343f0a2ae2b3160a4c8b0'` MCSM=`'eb_f80d55d73c8d4b66a17384c0e62655f1'`
  - `0@api_server`：本地=`'https://test-bot.{SERVER_NAME}.cn'` Exa=`'https://bot.{SERVER_NAME}.cn'` MCSM=`'https://bot.{SERVER_NAME}.cn'`
  - `0@discord_server_link`：本地=`''` Exa=`'https://discord.gg/9JAb9vpvUE'` MCSM=`''`
  - `0@qq_group_id`：本地=`'1082305302'` Exa=`'1012877775'` MCSM=`'753649704'`
  - `0@ws_server`：本地=`'wss://test-bot.{SERVER_NAME}.cn'` Exa=`'wss://bot.{SERVER_NAME}.cn'` MCSM=`'wss://bot.{SERVER_NAME}.cn'`
- ✅ `guide_book.yml` 三端完全一致
- ℹ️ `ip_blacklist.yml` 运行时数据（玩家/交易/记录，三端独立属正常）
- ℹ️ `permission.yml` 运行时数据（玩家/交易/记录，三端独立属正常）
- ✅ `portals.yml` 三端完全一致
- ✅ `templates.yml` 三端完全一致

### ❌ SkinsRestorer（1 个：0 一致 / 1 差异 / 0 数据）

- ❌ `config.yml` 差异 1 处：
  - `4@connectionOptions`：本地=`sslMode=trust&serverTimezone=UTC` Exa=`verifyServerCertificate=false&useSSL=false&serverTimezone=UTC` MCSM=`verifyServerCertificate=false&useSSL=false&serverTimezone=UTC`

### ✅ Vault（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致

### ✅ ViaBackwards（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致

### ✅ ViaRewind（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致

### ✅ ViaVersion（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致

### ✅ WorldEdit（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致

### ✅ WorldGuard（1 个：1 一致 / 0 差异 / 0 数据）

- ✅ `config.yml` 三端完全一致

### ❌ bStats（1 个：0 一致 / 1 差异 / 0 数据）

- ❌ `config.yml` 差异 1 处：
  - `0@serverUuid`：本地=`60e5974b-c66c-4c8b-931b-9384a86c271f` Exa=`02c94a29-7bc2-4ace-ae32-a071decbe58f` MCSM=`636149f0-778e-462a-92af-5cce902501da`

---
## 三、汇总

| 状态 | 核心 | 插件 | 合计 |
|:--|:--|:--|:--|
| ✅ 三端完全一致 | 3 | 57 | 60 |
| ❌ 配置差异 | 4 | 5 | 9 |
| ℹ️ 运行时数据差异（正常） | 0 | 8 | 8 |
| **合计** | **7** | **70** | **77** |

> 注：运行时数据文件 = 玩家家/死亡点/交易记录/审批记录等随玩家变化的内容，三端独立属预期，不算配置漂移。
