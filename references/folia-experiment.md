# Folia 迁移实验（2026-08-17，本地双服实测）

> 场景：评估本地测试服插件迁移 PaperMC Folia 核心的兼容性，并完成平替替换 + 数据迁移。
> 结论先行：**9 个不兼容插件全部解决（8 平替 + OrzMC 升级 Folia 版 1.0.18-dev.296 后自身支持），18 插件全绿；2026-08-18 起 Folia 服全面接管原测试服（端口 25565/19132 + Paper 地图 symlink + 全量配置/权限/白名单同步）。**

## 迁移全流程（总览，按序执行）

```
阶段 1 兼容性评估 → 阶段 2 平替选型 → 阶段 3 数据迁移 → 阶段 4 配置同步 → 阶段 5 全面接管 → 阶段 6 已知限制
```

| 阶段 | 关键动作 | 产物/结论 |
|:--|:--|:--|
| **1. 兼容性评估** | 复制全部 jar 到 Folia 服启动，看拒载清单 | 20 jar → 🟢12/🔴8；拒载=加载期错误（无标记即拒） |
| **2. 平替选型** | Modrinth `loaders=folia` 检索 + 功能覆盖验证 | 8 平替定稿（见插件矩阵）；OrzMC 等官方 Folia 版 |
| **3. 数据迁移** | 账号（BCrypt 复用）+ home（YAML→SQLite） | 359 账号 + 879 home，脚本化可复用 |
| **4. 配置同步** | 全量 diff → 定制值合并 + 关键文件复制 | paper-global/world-defaults/ops/封禁/usercache 等 |
| **5. 全面接管** | 端口换 Paper 的 + 地图 symlink | 25565/25575/19132 + 17G 世界零拷贝共享 |
| **6. 已知限制** | 命令方块被 Folia 架构性禁用 | 需插件/数据包替代（见下文） |

## 环境（2026-08-18 更新：Folia 已接管原测试服端口）

| 项目 | 原测试服 | Folia 测试服 |
|:--|:--|:--|
| 核心 | Paper 26.2-112（**已停运**） | Folia 26.2-4 BETA（2026-08-11） |
| 路径 | `~/minecraft-server` | `~/folia-test` |
| Java 端口 | ~~25565~~（已让出） | **25565**（接管 Paper 的） |
| RCON | ~~25575~~ | **25575**（接管，密码 orztest2026） |
| Geyser UDP | ~~19132~~ | **19132**（接管 Paper 的） |
| Geyser auth-type | offline | offline（2026-08-18 对齐 Paper；原 online 会触发 `MinecraftProfileNotFoundException 404`，offline 直连不查 XBL） |
| MOTD | `§e[Paper] 测试服-验证地图恢复状况` | `§e[Folia] OrzMC Test`（保留区分标识） |
| SkinsRestorer 警告 | `offlineModeWarning.enabled: false` | false（2026-08-18 对齐 Paper：屏蔽离线玩家「第三方启动器可能覆盖皮肤」警告，纯噪音；原 true 每次登录都发） |
| 白名单 | 开 | 开关**关**（`white-list=false` `enforce-whitelist=false`），但**列表已同步 139 玩家**（whitelist.json 复制） |
| 世界 | `~/minecraft-server/world`（17G） | **symlink → Paper 世界**（`~/folia-test/world → ~/minecraft-server/world`，零拷贝，2026-08-18） |
| 启动 | `./start.sh`（java -Xms2G -Xmx2G **-Dlog4j2.configurationFile="config/log4j2.xml"** -jar folia-26.2-4.jar nogui） | 同左（Paper start.sh 也已加同参数） |
| CustomWorldHeight | **已移除（2026-08-18 两端）**，jar 在 `plugins/.disabled/` | 已移除（同左） |

- ⚠️ **两服共享同一份世界（symlink）**：**绝不允许两服同时启动**（会损坏地图）；Paper 服若再启动需先删 `world/session.lock`，且 Paper 服端口已让出需另行规划
- Folia 核心下载：`https://papermc.io/downloads/folia` 页面内嵌 JSON（fill-data 直链，sha256 校验）
- ⚠️ Folia 26.2 目前只有 **BETA**（26.1.2 才是 STABLE）；Folia 版本节奏比 Paper 慢

## Folia 兼容机制（实测验证）

- **无 `folia-supported: true` 标记 → 直接被拒载**（连加载都不尝试）：
  `DirectoryProviderSource Error loading plugin: Could not load plugin 'X' as it is not marked as supporting Folia!`
- **标记 true ≠ 真兼容**：PaperMC 文档明示「声明标记不足以保证支持」——WorldGuard 官方承认 experimental
- **连带依赖效应**：依赖插件被拒载 → 依赖方也无法加载
  （实测：Vault 被拒载 → EzShops `UnknownDependencyException: [Vault]` 连带挂）
- **检索 Folia 插件必须用 Modrinth `loaders` 含 folia**；❌ Hangar API `supportedPlatforms` 只标 PAPER（WorldEdit 支持 Folia 也只显示 PAPER），不可用作 Folia 检索依据

## 插件兼容矩阵（20 jar → Folia 实测）

### 🟢 原声明支持（10）→ 保留
WorldEdit 7.4.5 / WorldGuard 7.0.18（experimental）/ LuckPerms 5.5.77 / Geyser 2.11.1 / ViaVersion / ViaBackwards / ViaRewind（5.11.0）/ SkinsRestorer 15.12.5 / EzShops 2.5.9（依赖 Vault，平替后恢复）/ CustomWorldHeight 2.2.0

### 🔴 不兼容（9）→ 平替方案

| 原插件 | 平替 | 版本 | 合并策略 |
|:--|:--|:--|:--|
| EssentialsX 2.22.0 | **EssentialsC** | 4.2.8 | 🔀 吸收 GetMeHome（自带 /home 多 home） |
| Vault 1.7.3 | **VaultUnlocked** | 2.20.2 | ✅ drop-in 平替，顺带恢复 EzShops |
| GriefPrevention 16.18.7 | **GriefPrevention3D** | 18.3.4 | ✅ GP 官方 fork + Folia fix + 3D 分区 |
| LoginSecurity 3.3.2 | **AuthMeReloaded** | 6.0.0-Folia | ✅ 官方明确 Folia 版 |
| DeathChest 3.0.1 | **AxGraves** | 1.29.0 | 🔀 吸收 BackOnDeath（死亡箱 + 回死亡点） |
| BackOnDeath 0.4 | ↑ 并入 AxGraves | — | /axgraves tp 回死亡点 |
| GetMeHome 3.0.0 | ↑ 并入 EssentialsC | — | /home 多 home |
| EzShops（连带） | VaultUnlocked 后恢复 | — | 依赖链修复验证 ✅ |
| **OrzMC 1.0.18** | **升级 1.0.18-dev.296**（2026-08-17 发布，PR #191 Folia CI smoke） | — | jar 内 `folia-supported: true` 确认；**Folia 服已加载运行**（创建默认配置 + 权限组自动初始化） |

**最终**：20 jar → 18 全绿（无拒载）。

### 平替关键细节
- EssentialsC：`Successfully hooked into Vault`；home/tpa/warp/kits 全套；数据在 `databases/homes.db`（SQLite）
- VaultUnlocked：`Registered Vault permission & chat hook`（LuckPerms 桥接）
- AuthMe：首次启动经 SpigotLibraryLoader 下载 MySQL/BCrypt 等库；`passwordHash` 默认 SHA256 **必须改 BCRYPT**（见迁移）；GeoLite 下载失败=可选 GeoIP 无 MaxMind 凭据，无害
- AxGraves：`/axgraves tp` 无参=传送回最近坟墓

## 数据迁移（2 项已完成，其余无数据）

| 源插件 → 目标 | 数据量 | 方法 |
|:--|:--|:--|
| LoginSecurity → AuthMe | 359 账号 | BCrypt 哈希**直接复用**（LS 算法 7=`$2a$10$`，AuthMe 原生 BCRYPT），改 `passwordHash: BCRYPT`，复制 username/password/ip/regdate/lastlogin |
| GetMeHome → EssentialsC | 186 玩家 / 879 home | homes.yml (YAML) → homes.db (SQLite)，字段一一映射，同名冲突跳过 |

**无需迁移**：Vault（纯 API）/ DeathChest（临时容器+审计）/ BackOnDeath（内存态）/ EssentialsX（原服从未真正用起来，userdata 0 homes）/ GriefPrevention（ClaimData 空，无领地）。
**OrzMC 配置**：2026-08-18 已迁移（config 定制值合并 + easybot.yml 完整复制，见「全面接管」章节）。

### 迁移脚本（技能 scripts/，均已参数化 + --dry-run）
```bash
python3 ~/.hermes/skills/gaming/orzmc/scripts/migrate_loginsecurity_to_authme.py [--ls-db X --authme-db Y] [--dry-run]
python3 ~/.hermes/skills/gaming/orzmc/scripts/migrate_getmehome_to_essentialsc.py [--yml X --db Y] [--dry-run]
```

### 迁移后验证
- AuthMe：日志 `AuthMe 6.0.0 successfully enabled!` + `SELECT COUNT(*) FROM authme` = 359
- 密码校验需真实登录测试（迁移工具无法验证 BCrypt 密码本身）
- EssentialsC：`SELECT COUNT(*) FROM homes` = 879；坐标样本与原 yml 一致

## 全面接管原测试服（2026-08-18）

Folia 服实验成功后全面接管原测试服（两服停运 → 单服运行）。

### 1. 地图（磁盘不足方案：symlink 零拷贝）
- 磁盘仅剩 7.9G < 17G 地图 → **不能复制**，用符号链接：`~/folia-test/world → ~/minecraft-server/world`
- Folia 原有全新世界备份为 `world.orig-newgen`（14M，可删）
- 启动前必须删 `world/session.lock`
- ⚠️ **两服共享地图，绝不同时启动**；Paper 服再启动需先让出端口

### 2. 端口接管（Folia 改用原 Paper 端口）
`server.properties`: `server-port=25565`、`rcon.port=25575`；Geyser `port: 19132`（改后 Java/Bedrock/RCON 三端口均与原 Paper 一致）

### 3. LuckPerms 四档权限系统（H2 数据库替换）
- 两服同版 LuckPerms 5.5.77 → **停服后直接复制** `plugins/LuckPerms/luckperms-h2-v2.mv.db`（229KB）
- 备份原 Folia db 为 `.folia-orig`；删除 `luckperms-h2-v2.trace.db`（锁文件）
- 验证：启动后 OrzMC **无「已创建组」日志** = 四档组（default→member→builder→admin + rank track）已从 Paper 库加载，未重复创建；Vault/F3F4Perms/AuthMe 均成功 hook
- ⚠️ LP 命令经 RCON 不回显（异步 dispatch），验证靠日志

### 4. OrzMC 配置迁移（新版模板为基底合并）
- **config.yml**：Folia 新版模板（含 guard/chat/login_rate_limit/player_notify 等新键）为基底，应用 Paper 定制值：`backup_retention_count: 1`、`entity_teleport_enabled: false`（Paper 旧版模板缺新键，不能整文件覆盖）
- **easybot.yml**：完整复制（网关 api_server/ws_server/api_key、QQ 群、飞书/QQ 平台会话）→ Folia 直连 EasyBot 认证成功
- guide_book/ip_blacklist/permission/portals/templates：0 差异或新版已含旧版内容，不动
- ⚠️ 两服同时连同一 EasyBot 网关，消息互通（测试期可接受）
- ⚠️ `whitelist.kick_message.qq_group_id` 未配置警告无害（easybot.qq_group_id 兜底，Paper 同样）

### 5. 服务端配置全量同步
| 文件 | 处理 |
|:--|:--|
| ops.json | **合并**（Paper 24 OP + joker = 25，勿覆盖） |
| banned-players.json / banned-ips.json | 复制（3 玩家 + 4 IP） |
| usercache.json | 复制（356 条） |
| help.yml | 复制 |
| config/paper-world-defaults.yml | 4 处对齐：anti-xray（enabled/engine-mode=2）、tracking-range-y.enabled、prevent-moving-into-unloaded-chunks、enderpearl exploit |
| config/paper-global.yml | proxies 段对齐：bungee-cord online-mode **true**（Paper 实值）、velocity false；`threaded-regions` 是 Folia 特有段**必须保留** |
| spigot.yml / bukkit.yml / wepif.yml | 语义一致，不动（仅 YAML 数值格式 -1 vs -1.0） |
| server.properties | 仅 MOTD 保留 `[Folia]` 标识 |

- ⚠️ **坑：`paper-global.yml` 的 `online-mode` 是 proxies（Bungee/Velocity）认证，≠ server.properties 的 online-mode**——前者 Paper 实值 true（默认），曾误改成 false，后修正
- ⚠️ `banlist` 命令被 EssentialsC 接管（显示 EssC 自己的存储），原版封禁文件已由 Bukkit 启动时加载生效，验证看文件格式 + 日志

## 坑与经验

1. **Folia 拒载是加载期错误**，非运行时错误——`plugins` 列表红色 = 未启用，jar 可以留在目录
2. **改 Folia 服配置后必须重启**（MOTD/白名单/Geyser 端口同理）
3. **Geyser 双服共存要改 UDP 端口**（19132→19133），否则 bind Address already in use
4. **AuthMe 是库重插件**：首次启动要下 maven 库（mysql/argon2/bcrypt 等 20+ jar），启动时间显著变长
5. **SQLite 迁移时目标服可在线**（WAL 模式），但保险起见迁移后重启一次让插件重载
6. F3F4Perms 依赖 **packetevents**（硬依赖 depend），两者都支持 Folia；权限 `f3f4perms.use` 默认 op，让有 /gamemode 权限的玩家用 F3+F4/F3+N 热键
7. ⚠️ **CustomWorldHeight 配置必须同步**：Folia 若沿用默认模板（example-world-name）→ 世界按 384 高度解析 Paper 的 1088 世界 → `Ignoring heightmap data ... expected: 37, got: 52` 错误 + 命令方块传送等跨区块操作异常。同步后错误方向反转（expected: 52, got: 37）= 世界内新旧区块高度图混存（CustomWorldHeight 2026-08-15 才启用，旧区块 384 生成）——**无害**（高度图只是缓存，忽略后自动重算，Paper 服同样存在）
   - **⚠️⚠️ log4j2 过滤最大坑（2026-08-18 实测修正）**：`config/log4j2.xml` **不会自动加载**！光放文件重启无效（日志格式无 [%logger] 即未加载）。**必须 start.sh JVM 参数显式指定**：`-Dlog4j2.configurationFile="config/log4j2.xml"`。此前「放 config/ 重启即可」的结论是假象（当时 CustomWorldHeight 在位警告本来就少/方向匹配，并非过滤生效）
   - **⚠️⚠️⚠️ paperclip 必须绝对路径（2026-08-18 实测）**：Folia 是 paperclip bootstrap（`folia-26.2-4.jar` 下载/解包真实 jar 到 `versions/26.2/` 后另起子进程），`-Dlog4j2.configurationFile="config/log4j2.xml"` **相对路径在子进程下解析失败 → 回退内置配置 → 过滤无效**（实测 976 条警告刷屏）。**必须绝对路径**：`-Dlog4j2.configurationFile="/Users/bot/folia-test/config/log4j2.xml"`（Paper 是普通 jar 直接加载，相对路径可用；但两服统一用绝对路径最稳）。验证法：召唤实体到 1088 格式 region（如 r.-5.-54）强制加载 → 警告数仍 0 = 生效
   - **根治（日志层，2026-08-18 实测归零）**：`config/log4j2.xml` 用 **Paper 官方模板**（GitHub master `paper-server/src/main/resources/log4j2.xml`）+ Root 级 `RegexFilter regex="Ignoring heightmap data for chunk" onMatch="DENY" onMismatch="NEUTRAL"` → 警告归零（加 JVM 参数后实测 9108 → 0）
   - **易踩坑**：① 必须 JVM 参数加载（见上）；② **Logger level 挡不住具体消息**，必须 RegexFilter（放 Root `<filters>` 段，官方模板的 MarkerFilter 旁）；③ 改配置后必须重启
   - 警告反复刷的机制：磁盘旧格式高度图加载时被忽略 → 内存重算 → **不写回磁盘**（除非区块 dirty）→ 每次重启/新区块加载都重新警告
   - **✅ CustomWorldHeight 已移除（2026-08-18 两端 Paper+Folia）**：全量扫描（nbtlib 解析 6380 region / 1,471,866 区块，scan_final.py）实证 **0 个区块含高空方块数据**（Y>319 的 section 有壳无 block_states=纯空气）→ 去掉零数据丢失。1088 格式区块 17,296（1%，83 个 region，玩家新探索区+出生点重载）**不会自动恢复也不会消失**——随玩家活动「加载→保存」循环自然收敛为 384 格式；未加载的保持 1088 文件但读取按 384 解析，游戏无影响
   - ⚠️ 扫描脚本坑（2026-08-18）：字节解析 sections 定位偏移 **idx+11**（1+2+8，idx+10 会指到名字末字符 's' 0x73 全失败）；`sections` 只存非空 section 且空 section 无 block_states 字段（「有 section」≠「有方块」）；可靠方案用 `nbtlib.File.parse(io.BytesIO(raw))` 全量解析（慢但准，6380 region 约 48 分钟，8 进程）
8. ⚠️⚠️ **命令方块在 Folia 被架构性禁用**（2026-08-18 实证）：官方 issue #429「fundamentally disabled」+ #485 请求加 `force-enable-command-blocks` 开关被关 `not_planned`。**无论 `enable-command-block` 怎么配，命令方块都不会执行任何命令**（含传送）——迁移后命令方块传送失效是此原因，非配置问题。替代：支持 Folia 的传送插件 / 数据包函数（触发机制受限）/ 接受限制
9. ⚠️ **`paper-global.yml` 的 `online-mode` ≠ server.properties 的 online-mode**：前者是 proxies（Bungee/Velocity）段认证，Paper 实值 true（默认）；曾误把 Folia 改成 false 造成不一致，已修正
10. ⚠️ **迁移服务端 JSON 文件看语义不看字节**：ops.json 要**合并**（Paper 24 OP + joker = 25，直接覆盖会丢 joker）；banned-* 直接复制（Bukkit 启动时加载，`banlist` 命令被 EssentialsC 接管显示其自身存储，验证看文件 + 日志）
11. **磁盘不足时地图用 symlink 零拷贝**：`ln -s paper/world folia/world`（17G 无法复制时唯一方案）；⚠️ 两服共享地图绝不同时启动（session.lock + 数据损坏风险）
12. **Folia 启动前必须删 `world/session.lock`**（symlink 共享场景下尤其重要，Paper 停服会残留）
13. ⚠️ **Essentials tpa「没有授受传送请求的权限」（2026-08-18 修复）**：现象 = 玩家 `/tpa <玩家>` 后提示「没有授受传送请求的权限」（Essentials 消息 `teleportNoAcceptPermission`）。根因 = **OrzMC 权威权限文档 `plugin/docs/permission-groups.md` member 组漏配 `essentials.tpaccept`**（只有 tpa/tpahere 发请求/邀请，无接受权限；Essentials 权限无默认值=非 op 默认拒绝；与 OrzMC 实体传送拦截 `entity_teleport_enabled: false` 无关）。修复 = 文档补行 + `gen_perm_commands.py` 重新生成 + RCON 执行 `lp group member permission set essentials.tpaccept true`（H2 落库验证）。⚠️ 三端同步

## 已知限制（Folia 架构性，无法配置解决）

| 限制 | 官方依据 | 影响 | 替代方案 |
|:--|:--|:--|:--|
| **命令方块被禁用** | issue #429「fundamentally disabled」+ #485 `not_planned` | 所有命令方块不执行（含传送/红石触发逻辑） | 支持 Folia 的插件 / 数据包函数 / 接受限制 |
| **PlayerPortalEvent 不触发**（2026-08-18 实测+反编译实证） | 下界传送门走 `portalAsync` 新路径，`callPlayerPortalEvent` 无任何调用者 | 依赖该事件的跨服 transfer 完全失效（玩家踩传送门只触发原版维度传送） | OrzMC PR #195：PlayerMoveEvent 补偿路径（方块坐标变化+interiorTargets 命中→transfer 命令+5s 冷却；仅 Folia 生效，Paper 保持原路径）。`EntityPortalReadyEvent` 语义不符（只能改目标世界不能替换 transfer） |
| EssentialsC Scoreboard 不支持 | Folia 分区线程模型 | 计分板功能不可用（启动 WARN） | 其他计分板插件 |
| OrzMC 需 Folia 版 | 旧版无 `folia-supported` 标记 | 1.0.18-dev.296 起已解决 | ✅ 已升级 |

## 相关文档
- 兼容性调研方法论 + 替代品清单 → 本文件
- 三端配置对比 → `three-end-config-drift.md`
- EasyBot 网关（Folia 服无 OrzMC 时无机器人链路）→ `easybot-gateway.md`
