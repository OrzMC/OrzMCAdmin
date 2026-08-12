# OrzMC 权限系统设计（LuckPerms 4 组方案，2026-08-06 本地验证）

## 组结构（继承链）
```
admin (全权限) → builder (创造建造) → member (进阶) → default (新手)
```

| 组 | 定位 | 关键权限 | 验证结果 |
|:--|:--|:--|:--|
| default | 新手生存 | sethome/home/back/spawn/tpa/msg/kit + griefprevention 圈地 | fly=false ✅ gamemode 拒绝 ✅ |
| member | 进阶 | +tpa/warp/kit/mail/getmehome 家 + playershop + GP 圈地 | 进阶功能 ✅ |
| builder | 创造建造 | +gamemode.creative/survival +worldedit 系列通配 +worldguard 区域 +**Litematica 粘贴（setblock/fill/data）** | gamemode=true ✅ worldedit=true ✅ |
| admin | 管理 | +luckperms.* +* | — |

## 关键命令
```bash
# 创建组 + 继承
lp creategroup <name>
lp group member parent add default
lp group builder parent add member
lp group admin parent add builder
# 权限设置（组）——以 perm_commands.txt / docs/permission-groups.md 为唯一参考
lp group builder permission set worldedit.selection.* true   # 系列通配（不用大通配 worldedit.*）
lp group builder permission set minecraft.command.setblock true   # Litematica 粘贴（2026-08-12）
# 全量对齐：lp group <G> permission clear + 逐条 set（permission set 是加法，不会移除旧节点）
# 玩家分配
lp user <name> parent add builder
lp user <name> parent set default
```

## ⚠️ 核心坑（实测 2026-08-06）
1. **LuckPerms 继承优先级：子组设置 > 父组设置，但同一权限在父子组都设时，查的是最具体的**。default 设 `fly false` + member 设 `fly true` → 玩家**继承 false**（default 赢了，因为"具体权限优先于通配"，且 LP 的 DirectProcessor 取**第一个匹配**）。**修正：default 不显式设 false**（Essentials 的 fly 默认拒绝，PermissionMapProcessor 返回 false），让 member 的 true 生效
2. **RCON 不回显 LuckPerms 命令输出**（LP 用 Adventure 组件发到 sender，Paper RCON 丢弃）——命令**实际执行**（H2 数据库 mtime 变化），但看不到输出。验证必须用 **bot 进服（玩家身份）** 或数据库
3. **LP 命令执行验证法**：`stat -f %m plugins/LuckPerms/luckperms-h2-v2.mv.db` 前后对比（mtime 变化 = 命令执行写库）
4. **H2 数据库读不了**（运行中被锁 + 文件密码），停服也读不了（未知密码）——别浪费时间，用 bot 验证
5. Essentials 大部分权限**默认拒绝**（非默认授予）——不设权限 = 无权限，`fly`/`gamemode` 都是
6. **⚠️ `parent set` 语法坑（实测）**：`lp user X parent set admin` 会把玩家**只保留 default 组**（set=替换为指定组，但 admin 没被正确加？实测结果是 X 只剩 default）。**正确用 `parent add` 追加 + `parent remove` 移除**：`lp user X parent add admin` + `lp user X parent remove default`
7. **⚠️ Bukkit `*` 通配符只对 OP 生效**：`lp group admin permission set * true` 不赋予非 OP 玩家全权限——OP 级命令（/kick /ban /stop）需要 `minecraft.command.*` 显式权限或玩家在 ops.json。admin 组实测：LP 管理命令（luckperms.*）✅，但 /gamemode 靠继承 builder 的 essentials.gamemode，/kick 需额外 `minecraft.command.kick`（当前测试显示命令执行但找不到玩家=权限有，待确认具体节点）
8. **/gamemode 是 Essentials 命令**（需 `essentials.gamemode`），不是原版 `minecraft.command.gamemode`（Paper 上原版命令被接管，`/minecraft:gamemode` 会 Unknown）；**//wand 是双斜杠**（单斜杠 /wand 不存在）

## 测试账号分配（本地测试服）
- joker → builder（测试创造/WE/Litematica 粘贴）
- TestNewbie → builder（权限验收）
- TestPlayer → member（测试进阶功能）
- Newbie → default（新手基线）
- HermesBot → default（运维 bot，不用特权）

## 验证方法（bot 玩家身份）
```bash
cd ~/minecraft-bot && node perm-check.js 25565
# 输出: [LP] Permission check for essentials.fly: Result: true/false
```
