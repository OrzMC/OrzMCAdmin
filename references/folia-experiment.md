# Folia 迁移实验（2026-08-17，本地双服实测）

> 场景：评估本地测试服插件迁移 PaperMC Folia 核心的兼容性，并完成平替替换 + 数据迁移。
> 结论先行：**8/9 插件不兼容 Folia 均已被平替覆盖，17 个插件全绿；唯一例外是自家 OrzMC（folia-supported: false 显式声明），需源码改造才支持。**

## 环境

| 项目 | 原测试服 | Folia 测试服 |
|:--|:--|:--|
| 核心 | Paper 26.2-112 | Folia 26.2-4 BETA（2026-08-11） |
| 路径 | `~/minecraft-server` | `~/folia-test` |
| Java 端口 | 25565 | 25566 |
| RCON | 25575（密码 orztest2026） | 25576（同密码） |
| Geyser UDP | 19132 | 19133 |
| Geyser auth-type | offline | offline（2026-08-18 对齐 Paper；原 online 会触发 `MinecraftProfileNotFoundException 404`，offline 直连不查 XBL） |
| MOTD | `§e[Paper] 测试服-验证地图恢复状况` | `§e[Folia] OrzMC Test` |
| SkinsRestorer 警告 | `offlineModeWarning.enabled: false` | false（2026-08-18 对齐 Paper：屏蔽离线玩家「第三方启动器可能覆盖皮肤」警告，纯噪音；原 true 每次登录都发） |
| 白名单 | 开 | **关**（`white-list=false` `enforce-whitelist=false`） |
| 启动 | `./start.sh`（java -Xms2G -Xmx2G -jar folia-26.2-4.jar nogui） | 同左 |

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
| **OrzMC 1.0.18** | ❌ **无平替** | — | 自家定制逻辑，需源码适配 Folia（另行排期） |

**最终**：20 jar → 17 全绿（OrzMC 留目录但不加载）。

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
**待定**：OrzMC 配置（config/permission/portals/templates/easybot/ip_blacklist）——等 Folia 改造时随代码迁移。

### 迁移脚本（技能 scripts/，均已参数化 + --dry-run）
```bash
python3 ~/.hermes/skills/gaming/orzmc/scripts/migrate_loginsecurity_to_authme.py [--ls-db X --authme-db Y] [--dry-run]
python3 ~/.hermes/skills/gaming/orzmc/scripts/migrate_getmehome_to_essentialsc.py [--yml X --db Y] [--dry-run]
```

### 迁移后验证
- AuthMe：日志 `AuthMe 6.0.0 successfully enabled!` + `SELECT COUNT(*) FROM authme` = 359
- 密码校验需真实登录测试（迁移工具无法验证 BCrypt 密码本身）
- EssentialsC：`SELECT COUNT(*) FROM homes` = 879；坐标样本与原 yml 一致

## 坑与经验

1. **Folia 拒载是加载期错误**，非运行时错误——`plugins` 列表红色 = 未启用，jar 可以留在目录
2. **改 Folia 服配置后必须重启**（MOTD/白名单/Geyser 端口同理）
3. **Geyser 双服共存要改 UDP 端口**（19132→19133），否则 bind Address already in use
4. **AuthMe 是库重插件**：首次启动要下 maven 库（mysql/argon2/bcrypt 等 20+ jar），启动时间显著变长
5. **SQLite 迁移时目标服可在线**（WAL 模式），但保险起见迁移后重启一次让插件重载
6. F3F4Perms 依赖 **packetevents**（硬依赖 depend），两者都支持 Folia；权限 `f3f4perms.use` 默认 op，让有 /gamemode 权限的玩家用 F3+F4/F3+N 热键

## 相关文档
- 兼容性调研方法论 + 替代品清单 → 本文件
- 三端配置对比 → `three-end-config-drift.md`
- EasyBot 网关（Folia 服无 OrzMC 时无机器人链路）→ `easybot-gateway.md`
