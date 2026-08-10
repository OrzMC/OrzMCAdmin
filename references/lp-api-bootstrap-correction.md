# LuckPermsBootstrap 校正模式 + 权限名核实（2026-08-08 实战）

## 背景

OrzMC 权限系统：LuckPermsBootstrap 启动自动建 track「rank」（default→member→builder→admin）
与组（member→default、builder→member、admin→builder）。原实现「已有组跳过」导致 1.0.15
遗留组继承错误永不校正（MCSM builder parent=default 缺 member 功能）。改造为「校正继承与
track 链序，权限节点不碰」。

## LP 5.5.71 API 细节（编译/测试踩坑实录）

| API | 事实 | 坑 |
|:--|:--|:--|
| `Group.getParentGroups()` | **不存在** | 想当然写它编译报「找不到符号」 |
| `NodeMap.toMap()` | 返回 `Map<ImmutableContextSet, Collection<Node>>` | key 是上下文集**不是 String**，mock `thenReturn(Map<String,...>)` 编译错 |
| `NodeMap.toCollection()` | 返回扁平 `Collection<Node>` | 读继承/权限节点的正道——遍历 `instanceof InheritanceNode` |
| `NodeMap.clear(Predicate<? super Node>)` | 按谓词清节点 | 清继承：`clear(node -> node instanceof InheritanceNode)`——只动继承不动权限 |
| `Track.getGroups()` | 返回 **`List<String>`**（组名） | 想 stream map `Group::getName` 报「方法引用无效」（元素已是 String） |
| `TrackManager.deleteTrack(Track)` | 存在，返回 CompletableFuture | 链序不一致时 delete 后重建 |
| 继承节点写入 | `api.getNodeBuilderRegistry().forInheritance().group(name).build()` | 静态 `InheritanceNode.builder()` 在测试环境抛 NotLoadedException——必须走注入的 api |

## 校正实现骨架（ensureParent 模式）

```java
// 读当前继承：toCollection 过滤 InheritanceNode
Set<String> current = new HashSet<>();
for (Node node : group.data().toCollection()) {
    if (node instanceof InheritanceNode in) current.add(in.getGroupName());
}
if (current.size() == 1 && current.contains(expectedParent)) return; // 已正确，跳过
// 校正：清继承节点 → 重挂设计 parent → saveGroup
group.data().clear(node -> node instanceof InheritanceNode);
group.data().add(api.getNodeBuilderRegistry().forInheritance().group(expectedParent).build());
api.getGroupManager().saveGroup(group);
```

track 链序校正：`existing.getGroups()`（List<String>）与设计链比对，不一致 →
`deleteTrack(existing)` 后 `createAndLoadTrack` + 逐个 `appendGroup(getGroup(name))`。

## 单测模式（mock 继承节点）

```java
private Group mockGroup(String name, String parent) {
    Group g = mock(Group.class);
    NodeMap nm = mock(NodeMap.class);
    Collection<Node> nodes = new ArrayList<>();
    if (parent != null) {
        InheritanceNode node = mock(InheritanceNode.class);
        when(node.getGroupName()).thenReturn(parent);
        nodes.add(node);
    }
    when(nm.toCollection()).thenReturn(nodes);  // 关键：mock toCollection 而非 toMap
    when(g.data()).thenReturn(nm);
    return g;
}
```

覆盖场景：继承正确→跳过（never saveGroup）；继承错误→只校正目标组（saveGroup times(1)）；
track 链序一致→跳过；不一致→deleteTrack+createAndLoadTrack。

## 权限名核实方法（配置表重梳，避免配无效节点）

**双通道确认权限名真实存在**：
1. **plugin.yml 权威**（权限树 + children 结构）：`unzip -p <jar> plugin.yml | sed -n '/^permissions:/,/^[^ ]/p'`
   - 父权限检查 children：如 `getmehome.user` 的 children 含 5 个家命令——**1 个父权限替代
     5 个分列节点**（LP 展开 children，check command.sethome 也 true）
   - EzShops 的 `ezshops.shop` **无 children**（buy/sell 独立）——不能合并
2. **jar 字节码 grep**（代码注册的权限，plugin.yml 不列）：
   ```bash
   unzip -oq <jar> "*.class" -d /tmp/x && grep -rao "插件前缀\.[a-z.][a-z.]*" /tmp/x | sort -u
   ```
   - 实测确认：LoginSecurity 的 `ls.bypass`、DeathChest 的 `deathchest.command.report` 都在代码里
   - 剔除无效名：`essentials.reply`/`essentials.craft`/`essentials.teleport` 在 EssentialsX 2.22.0
     plugin.yml 与字节码都不存在（/reply 随 /msg；/craft 是 /workbench 别名）；`essentials.baltop`
     真实名是 `essentials.balancetop`

**合并候选规则**：能通配/父权限合并的绝不分列；但**通配避开管理分支**（`worldedit.*` 含 reload、
`worldguard.region.*` 含 bypass/override、`essentials.gamemode.*` 含 others——都用裁剪子集通配
如 `worldedit.selection.*`、`worldguard.region.claim.*`）。

## 验证三连（每项权限配置后）

1. `lp group <组> permission check <节点>`（bot 群 $e 通道，日志 grep「結果: true/undefined」）
2. 实际命令（对应组账号实测——如 `/gamemode creative`、`//wand`、`/sethome`）
3. 越权反查（`lp group admin permission check minecraft.command.op` → false）
