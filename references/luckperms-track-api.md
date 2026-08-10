# LuckPerms track API 与权限链设计（2026-08-07 决策记录）

OrzMC 权限系统二期「升降级 + 权限链生命周期」的设计决策与 API 证据。未来做权限链/等级系统时先读本文。

## 一、LP track API 原生钳位语义（反编译证据，LP api 5.4）

从 `repo1.maven.org/maven2/net/luckperms/api/5.4/api-5.4.jar` 反编译（`javap -p`）：

**PromotionResult$Status**：`SUCCESS`、`ADDED_TO_FIRST_GROUP`（不在 track 上 → 加入首组）、`MALFORMED_TRACK`、`END_OF_TRACK`（链顶再 promote = 失败，**不绕回**）、`AMBIGUOUS_CALL`、`UNDEFINED_FAILURE`

**DemotionResult$Status**：`SUCCESS`、`REMOVED_FROM_FIRST_GROUP`（链底 demote = 移除首组回 default）、`MALFORMED_TRACK`、`NOT_ON_TRACK`（不在 track = 已是 default）、`AMBIGUOUS_CALL`、`UNDEFINED_FAILURE`

**Track 接口**：`getGroups()`（链定义）、`promote(User, ContextSet)` / `demote(User, ContextSet)`、`getNext/getPrevious(Group)`、`containsGroup`、`appendGroup/insertGroup/removeGroup/clearGroups`

**UserManager**：`getUser(UUID)` 同步查缓存（在线）、`loadUser(UUID)` 异步 CompletableFuture（离线）、`getPrimaryGroup()`

## 二、设计决策链（用户评审驱动）

1. **用户问「升级/降级到链底/链顶时后续如何处理」** → 最初假设 LP track 绕圈 → 用显式 parent add/remove 钳位。**反编译证伪该假设** → LP track API 原生钳位，一行调用即可。
2. **用户问「为什么要标记 admin」** → 本地 admin 标记会造成**双写漂移**：管理员手动 `lp user X parent add admin` 时本地无标记（$l 显示错误）；`$p u` 升 admin 后 LP 手动移除，本地标记残留（幽灵权限）。结论：**当前组快照必须以 LP 为准，本地不存**。
3. **用户要求「配置文件中尽量以最少的记录信息完成功能」** → promoted/demoted/admin 本地标记全删，permission.yml 只留 config + reviews 两段。
4. **用户拍板「$v 纯审核、$p 权限管理」** → 审核命令（l/y/n 裁决申请）与管理命令（u/d 管理员主动操作）语义分离；`$d` 已被黑名单占用故用 `$p`。
5. **用户要求「玩家权限变化需群广播」** → 通知双通道：游戏内消息（在线玩家）+ 群广播（所有人可见）。复用 `ReviewNotifier`（已有 gameMessage + groupEvent 两方法）。
6. **用户要求「兼容无 LuckPerms」** → `RankPromoter.isAvailable()` 守卫；无 LP 时 `promote/demote/checkPromotion` 跳过且**不写本地状态**（防「本地已升 LP 未变」脱节）；`$p` 明确提示「未检测到 LuckPerms，权限管理功能不可用」；/rank 时长、/apply 记录仍可用。

## 三、事件标记 vs 状态快照（核心概念）

- **promoted/demoted 是「一次性事件标记」**：记录「发生过自动晋升/降级」，可以本地存（幂等用）。
- **admin 是「当前组状态快照」**：反映「现在是什么组」，必须查 LP 真实组，本地存必然漂移。
- 判断标准：标记记录「发生了什么」（事件）可本地化；记录「现在是什么」（状态）必须权威源查询。

## 四、LP API 查询的线程安全注意

- 在线玩家 `getUser(uuid)` 有缓存，同步安全。
- 离线玩家 `loadUser(uuid)` 异步：`$p` 低频操作可在异步线程 `.get(3, SECONDS)` 阻塞；主线程严禁阻塞等待（Paper 主线程卡顿）。
- LP 命令派发仍须主线程（`Asynchronous Command Dispatched Async`），见 SKILL.md 陷阱 #2。

## 五、LP API 直调实现骨架（LuckPermsPromoter 重写版，2026-08-07 实测，含类加载三连坑修正）

**build.gradle.kts**：
```kotlin
compileOnly("net.luckperms:api:5.4")          // 软依赖：不打进 jar（见下方类加载规则）
testImplementation("net.luckperms:api:5.4")   // 单测 mock Track/User/结果枚举需要
```
依赖在 `repo1.maven.org` 可解析（repo.luckperms.net 常被墙，不要用）。

**paper-plugin.yml（Paper 26 新格式，旧 `softdepend:` 不提供类加载器可见性）**：
```yaml
dependencies:
  server:
    LuckPerms:
      required: false
```

**shadowJar 必须排除 LP 包**（否则 child-first 加载自带 Provider 副本 → `LuckPermsProvider$NotLoadedException`）：
```kotlin
shadowJar { exclude("net/luckperms/**") }
```

**类加载安全（无反射，用户明确拒绝反射）**：`RankPromoter` 接口只用纯业务类型（String/UUID/boolean，promote/demote 返回目标组名）；装配处条件实例化——
```java
RankPromoter promoter = Bukkit.getPluginManager().isPluginEnabled("LuckPerms")
    ? new LuckPermsPromoter(resolver, sched)
    : new NoopRankPromoter();  // 返回 null/false，$p 提示不可用
```
JVM 类加载惰性：`if` 为假时永不加载 LuckPermsPromoter 类（其方法签名含 LP 类型），LP 缺失时插件正常启动。**不要用 Class.forName/Method.invoke 反射**——脆弱难维护。

**⚠️ 注入接口必须独立文件**：`PlayerNameResolver`/`ServerScheduler` 若定义为 `LuckPermsPromoter` 的嵌套接口，装配层引用 `LuckPermsPromoter.PlayerNameResolver` 符号会加载 LuckPermsPromoter 类（嵌套成员在外部类加载时定义）→ 破坏惰性加载。两个注入接口都提为独立顶层文件（`PlayerNameResolver.java`、`ServerScheduler.java`）。

**核心调用模式**（全部走 API，废弃控制台命令 dispatch）：
```java
// 1. 拿 track（未加载返回 null）
Track track = LuckPermsProvider.get().getTrackManager().getTrack("rank"); // "rank": default→member→builder→admin

// 2. 加载用户（在线缓存同步 / 离线异步阻塞 3s）
User user = LuckPermsProvider.get().getUserManager().getUser(uuid);       // 在线
if (user == null) user = LuckPermsProvider.get().getUserManager().loadUser(uuid).get(3, TimeUnit.SECONDS);

// 3. 升降级（钳位由 LP 原生保证，返回结果枚举）
// ⚠️ 第二参数是 ContextSet 不是 QueryOptions！用用户上下文或空集：
ImmutableContextSet ctx = LuckPermsProvider.get().getContextManager().getContext(user)
        .orElse(ImmutableContextSet.empty());
PromotionResult r = track.promote(user, ctx);  // 或 track.demote(user, ctx)
// r.wasSuccessful() 判断；r.getGroupTo() / r.getGroupFrom() 是 Optional<String>（翻译提示用）
// END_OF_TRACK → 链顶提示；REMOVED_FROM_FIRST_GROUP / NOT_ON_TRACK → 链底提示

// 4. ⚠️⚠️ 成功后必须显式持久化——LP API 变更只改内存 User 对象，不自动落库！
//    （游戏内 lp 命令路径会自动保存，API 直调不会。漏掉 = SUCCESS 假成功，组查询不变）
if (r.wasSuccessful()) {
    LuckPermsProvider.get().getUserManager().saveUser(user).get(3, TimeUnit.SECONDS);
}

// 5. isInGroup 真实现：getInheritedGroups(QueryOptions) 返回 Collection<Group>，取组名用 group.getName()
Collection<Group> groups = user.getInheritedGroups(user.getQueryOptions());
boolean in = groups.stream().anyMatch(g -> g.getName().equalsIgnoreCase(groupName));

// 6. 必须在主线程调用！复用现有 scheduler.runSync + CompletableFuture.join 模式（SKILL.md #2）
```

**RankService 侧**（翻译结果 + 双通道通知）：
- `promote/demote` 返回 `String`（目标组名）：`result.getGroupTo().orElse(currentGroup(playerId))`；`!wasSuccessful()` 或结果 null → 返回 null（调用方提示「已在最高/最低等级」）
- `checkPromotion` 幂等由 LP 保证：`promoter.currentTrackGroup(id)` 为 null 或 "default" 且时长达标才 promote（无需本地 promoted 标记）
- 通知双通道：`notifier.gameMessage(uuid, "你的权限已升级：X。")` + `notifier.groupEvent("rank_promoted"/"rank_demoted", Map.of("player", name, "group", displayName))`（复用 ReviewNotifier 两个方法即可，无需新端口）。⚠️ 新增 groupEvent 调用点必须同步登记到 `ReviewNotifierAdapter.groupEvent` 的 fallback switch + templates.yml 默认键 + 单测断言 fallback（漏了群消息原样输出 `{message}`，详见 SKILL.md「群广播模板 fallback 陷阱」整节）
- `groupDisplayName` 补全四档：admin→管理员、builder→建造者、member→会员、default→访客
- `RankPromoter` 接口加 `playerName(UUID) → Optional<String>`（群广播要玩家名，resolvePlayerId 的反向）

**RankStore 瘦身**：只剩 `getPlaytimeMinutes(UUID)`（读 stats），promoted/demoted 全部方法删除；PermissionStore 只实现 ReviewStore + playtime。
