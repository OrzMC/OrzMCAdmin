# 权限组节点配置表（四级：default/member/builder/admin）— 2026-08-08 最小化重梳版

> 来源：OrzMC 权限系统实战（本地测试服与线上 16 插件一致：EssentialsX 2.22 /
> GetMeHome 3.0.0-4 / GriefPrevention / WorldEdit 7.4.4 / WorldGuard 7.0.18 /
> EzShops 2.5.9 / BackOnDeath / deathchest / LoginSecurity 3.3.2 / Vault / OrzMC 等）。
> 配置命令：`lp group <组> permission set <节点> true`；继承链 admin→builder→
> member→default，**各组只配增量**。同步前 `lp export` 备份。
> 权威版在仓库 `docs/permission-groups.md`（含每项验证指令）。

## 设计原则

1. **最小化**：能用父权限/通配符合并的绝不分列——`getmehome.user`（父权限，children
   含全部 5 个家命令）、`worldedit.selection.*` 等系列通配、`worldguard.region.claim.*`
2. **只配插件真实检查的权限名**：逐项核对 plugin.yml + jar 字节码（见下）——无效节点
   一律剔除（essentials.reply/craft/teleport 不存在；baltop 应为 balancetop）
3. **不含管理侧**：任何通配符避开管理分支（worldedit.reload、worldguard.region.bypass、
   essentials.gamemode.others 等）
4. **权限组内其它细节由线上自管**：配置表只保证「定位功能可用」

## L0 default（访客）— 生存基础体验（13 项）

`ls.bypass`（登录豁免）、`essentials.afk/back/msg`（社交——reply 无此权限随 msg）、
`essentials.balance/balancetop/pay/spawn`（经济+回城）、`bod.back`（死亡回档）、
`ezshops.shop`、`ezshops.shop.buy/sell`、`ezshops.playershop.browse`
**不给**：`getmehome.user`（家功能属 member）、`deathchest.command.report`
（管理命令——在 DeathChest admin 包，default 不该有）

## L1 member（成员）— 完整玩家功能（13 项）

`getmehome.user`（**父权限一个替代 5 个 command.* 分列**）、
`essentials.tpa/tpahere/warp/warp.list/kit/mail/mail.send`（**warp.list 与 mail.send
是独立子权限**——/warp 列表、/mail send 各自需要）、`griefprevention.createclaims/trapped`、
`ezshops.playershop.create/buy/sell`

## L2 builder（建造者）— WE/WG 裁剪子集 + 建造便利 + Litematica 投影（31 项）

WorldEdit：`worldedit.wand`、`worldedit.selection.*`、`worldedit.region.*`、
`worldedit.clipboard.*`、`worldedit.history.*`、`worldedit.brush.*`、
`worldedit.tool.*`、`worldedit.utility.*`、`worldedit.help`、`worldedit.schematic.*`、
`worldedit.navigation.*`、`worldedit.analysis.*`
WorldGuard：`worldguard.region.claim.*`（**通配含 claim.own**）、
`worldguard.region.define/remove/addmember/removemember/setparent`、
`worldguard.region.flag.*`、`worldguard.region.list/info/teleport`
Essentials 建造便利：`essentials.gamemode`（**父权限=命令基础权限，08-12 实测：
子权限 .creative/.survival 不足于使用 /gamemode 命令**；父权限含全模式切换
spectator/adventure，无破坏性风险）+ `essentials.gamemode.creative/survival`（子权限，
随父权限生效）+ **`essentials.gamemode.others` 显式 false**（父权限含 .others，
必须显式拒绝防改他人模式）+ `essentials.fly/heal/workbench/top`（craft 无此权限——
/craft 是 /workbench 别名）
**Litematica 投影粘贴（2026-08-12 新增，方案 A）**：`minecraft.command.setblock`（/setblock 粘贴核心）、
`minecraft.command.fill`（/fill 连续区域）、`minecraft.command.data`（/data NBT 恢复）——
原版命令模式三件套；**不授予 `minecraft.command.summon`**（可召危险实体/刷物品，客户端
`pasteIgnoreEntities` 跳过）；WE 模式（客户端 commandUseWorldEdit=true）无需新增权限
（worldedit.selection.pos/region.set 已覆盖）；安全前置：三端 enable-command-block=false
**不给**：`worldedit.reload`、`worldguard.region.bypass` 等管理侧节点

## L3 admin（管理员）— 精确管理节点（32 项，无通配无 op）

`orzmc.admin`、`minecraft.command.kick/ban/pardon/whitelist/gamemode/effect/tp/give/save-all`、
`bukkit.command.gamemode/kick/ban/whitelist`、
`essentials.kick/ban/unban/gamemode/give/tp/time/time.set/weather`
（time.set 独立子权限——/time set 需要；heal 已清理冗余——继承 builder）、
`griefprevention.admin.*`、`griefprevention.restorenature`、`worldguard.region.bypass/override`、
`vault.admin`、`ezshops.shop.admin`、`ezshops.playershop.admin`、`deathchest.admin`、`bod.bypass`

## 高危节点（任何组都不授予）

`*`、`luckperms.*`、`minecraft.command.op`、`bukkit.command.op`、
`essentials.stop`、`essentials.reload`

## 权限名核实方法（plugin.yml 权威 + jar 字节码）

1. **plugin.yml 权威**：`unzip -p <jar> plugin.yml | grep -E "^  essentials\.[a-z.]*:"`
   ——确认权限名真实存在。实测剔除：`essentials.reply`（无）、`essentials.craft`（无，
   /craft 是 /workbench 别名）、`essentials.teleport`（无，/tp 已够）、
   `essentials.baltop`（正确名 `essentials.balancetop`）
2. **jar 字节码兜底**（权限在代码注册，plugin.yml 无）：解压后
   `grep -rao "essentials\.spawn[a-z.]*"` 等。`ls.bypass`（LoginSecurity 代码注册——
   plugin.yml 只有 login/register/changepassword/logout/unregister/lac）
3. **父权限检查**：`getmehome.user` 在 plugin.yml 有 children（5 个家命令全含）——
   配置一个即可；`ezshops.shop` 无 children（buy/sell 独立，需分别给）
4. **子权限陷阱（LP check true ≠ 命令可用）**：`essentials.mail/warp/time` 是基础权限，
   `/mail send` 需 `essentials.mail.send`、`/warp`（列表）需 `essentials.warp.list`、
   `/time set` 需 `essentials.time.set`——**子功能是独立子权限，必须实测命令确认**
   （验收实测：/mail send 报「没有 essentials.mail.send 的权限」、/warp 报「没有列出
   传送点的权限」、/time set day 报「无权设置时间」——补子权限后放行）

## bot 全量验收方法（命令可用性唯一权威）

LP check 只证明节点存在，**命令可执行性必须 bot 实测**（mineflayer 聊天流在本场景
可靠——非流式命令响应）：

1. **账号对应组**：HermesBot=member（含 default 继承）/ TestNewbie=builder /
   TestMember=admin——每组一个测试账号实测
2. **目标用不存在的玩家**（如 NoSuchPlayer）：/kick NoSuchPlayer 报「找不到玩家」=
   权限放行 + 命令存在，无副作用
3. **判定标准**：Unknown = 命令未注册（非权限问题，单独标注，如 /spawn 在 Paper
   26.2 兼容问题）；「没有 X 权限」= 配置缺失（补子权限后复测）；静默执行 = 放行
4. **测试账号密码重设**（LoginSecurity）：`lc unregister` 命令不可靠——直接
   `sqlite3 <插件目录>/LoginSecurity.db "DELETE FROM ls_players WHERE last_name='X';"`
   （表名 ls_players，列 last_name）后 /register 新密码，LP 用户组不受影响
5. 白名单拦新账号：OrzMC 白名单未含的新号被踢「不在服务器白名单中」——用现有
   账号（member 测 default 项靠继承 + 组级 LP check 已验）

## 验收发现并修复（2026-08-08，全部复测放行）

| 项 | 问题（初测） | 修复 |
|:--|:--|:--|
| member mail.send | /mail send 拒绝 | 补 `essentials.mail.send` |
| member warp.list | /warp 拒绝 | 补 `essentials.warp.list` |
| admin time.set | /time set day 拒绝 | 补 `essentials.time.set` |
| admin heal | 冗余（继承 builder 已有） | 移除配置项 |

遗留标注（非权限问题）：`//tool` Unknown（无参需 //tool <类型>）、`//unstuck` Unknown
（WE 7.4.4 注册异常，同 /spawn 26.2 兼容）、`/spawn` Unknown（Essentials 26.2 未注册
命令）、`/msg` 被反垃圾拦截（移动后可聊天）。

## 实测验证方法

`lp user <X> permission check <node>`（群 $e 通道）输出中文描述：
「在環境 global 中，X 從 <组> 繼承的權限 <node> 被設為 true/false」；
grep `繼承的權限|沒有設定權限` 判断。组对象同理（`lp group default permission check X`）。
去 op 化验证三连：`minecraft.command.op`=false、`luckperms.user`=false、`orzmc.admin`=true。
