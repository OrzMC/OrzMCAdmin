# 插件默认开启权限盘点（2026-08-08）

场景：OrzMC 权限最小化重梳后「joker 是 default 却能用 sethome」——最终根因是
**插件权限默认值**（GetMeHome `default: true`），与残留 member 组并存（残留组贡献
tpa，插件默认贡献 sethome）。

## 盘点方法

- 脚本：`scripts/scan_default_perms.py`（python zipfile+yaml 遍历插件 plugin.yml，
  过滤 `default: True` 的权限）
- **WE/WG 权限在代码注册**（plugin.yml 无 permissions 段）——不在此列，
  默认按 false/op 处理（builder/admin 显式配置才可用）

## 盘点结果（本地 16 插件，default: true）

| 插件 | 权限 | 配置表声明 | 实际影响 |
|:--|:--|:--|:--|
| GetMeHome | `getmehome.user`（父——含 sethome/home/delhome/listhomes/setdefaulthome） | L0 未声明 | **所有玩家可用全部家功能**——禁需 default 组 6 条显式 false（父+5 命令，插件默认不吃父 false） |
| GetMeHome | `bstats` | - | 统计（无关） |
| EssentialsX | `essentials.back.onteleport` | 未声明 | 传送后死亡点回档 |
| EssentialsX | `essentials.teleport.cooldown.bypass.tpa` / `.back` | 未声明 | tpa/back 冷却豁免 |
| EzShops | `ezshops.playershop.create` / `.buy` | L1（冗余） | default 也能创建/购买玩家商店 |
| EzShops | `ezshops.stock.view` / `teamshop` / `teamshop.market` / `teamshop.treasury.withdraw` | 未声明 | 库存/团队商店默认开 |
| GriefPrevention | `createclaims` | L1（冗余） | default 也能圈地 |
| GriefPrevention | `claims` / `trapped` / `ignore` / `givepet` / `unlockdrops` / `buysellclaimblocks` / `abandonallclaims` | 部分未声明 | 领地基本功能默认开 |
| GriefPrevention | `siege` | 未声明 | **攻城默认开**（风险项） |
| BackOnDeath | `bod.back` | L0 已声明 | 一致 |

## 关键结论

1. **LP check undefined ≠ 不可用**：组无节点时 LP check 显示 undefined，但插件默认
   true 实际可用——命令可用性唯一权威是 bot 实测命令（default 玩家实测：
   /sethome ✅ 可用、/rg claim ✅ 权限放行、/tpa ❌ 无权限——对齐）
2. **插件默认不吃父权限 false**：`getmehome.user false` 不覆盖子权限默认 true——
   必须逐项显式 `set <node> false`
3. **风险项建议**（需用户决策）：GP `siege`（攻城）、`abandonallclaims`（一键弃全部
   领地）——如不允许需 default 组显式禁
4. **命令未注册 ≠ 权限问题**（反例标注）：`essentials.spawn`、`worldedit.navigation`
   （//unstuck）在 Paper 26.2 命令未注册——权限节点有效（LP check true）但命令
   Unknown，标注「当前不可用」保留节点（命令恢复后即生效）

## 文档对齐原则

权限组配置文档须反映**实际可用状态** = LP 组声明 ∪ 插件默认清单；
不可用项（命令未注册）在配置表标注「当前不可用」而非删除节点。
