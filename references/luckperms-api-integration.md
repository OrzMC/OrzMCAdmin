# LuckPerms API 软依赖集成（2026-08-07 权限链重构实战）

场景：插件内直接调 LP API（`net.luckperms:api`）实现权限链升降级，替代旧的
`dispatchCommand("lp user X ...")` 控制台命令方案。本文记录类加载、持久化、track
语义三块硬坑，全部经本地实测验证。

## 1. 类加载三连坑（按出现顺序，每坑一次部署实测）

### 坑 1：`implementation` 打进 jar → `NotLoadedException: The LuckPerms API isn't loaded yet!`

把 `net.luckperms:api` 作为 `implementation` 打进 shadowJar 后，插件**能启动**，
但运行时报：
```
net.luckperms.api.LuckPermsProvider$NotLoadedException: The LuckPerms API isn't loaded yet!
```
根因：Bukkit 插件类加载器是 **child-first**——插件加载的是**自己 jar 里的**
`LuckPermsProvider` 副本，而 LP 插件注册 provider 用的是**它自己类加载器里**的
`LuckPermsProvider`，两个类不是同一个 → 静态 provider 字段为空。

### 坑 2：`compileOnly` + 旧格式 `softdepend` → `ClassNotFoundException`

改 `compileOnly` 后插件启动即崩：
```
java.lang.ClassNotFoundException: net.luckperms.api.context.ContextSet
```
根因：**Paper 26 的 paper-plugin.yml 不认旧格式 `softdepend:`**——类加载顺序无保证，
OrzMC 先于 LuckPerms 加载，LP API 类尚不存在。

### 坑 3（正确解法）：`compileOnly` + Paper 26 新格式 `dependencies:`

```yaml
# build.gradle.kts
compileOnly("net.luckperms:api:5.4")     # 不打进 jar
testImplementation("net.luckperms:api:5.4")

# shadowJar 显式排除（双保险，防 minimize 误收）
exclude("net/luckperms/**")

# paper-plugin.yml — Paper 26 新格式，保证 OrzMC 在 LP 之后加载且 API 类可见
dependencies:
  server:
    LuckPerms:
      required: false
```
LP 插件运行时向全局 classpath 提供 API 类，依赖插件复用即可。

## 2. `track.promote()/demote()` 只改内存，必须显式 `saveUser()`（最容易漏）

LP API 的 `track.promote(user, ctx)` 返回 `SUCCESS` 但**不落库**——修改的是
`loadUser()` 返回的内存 User 对象。不调用 `saveUser` 的话：日志显示 SUCCESS、
本地显示"已升级"，但 `lp user X parent info` 查组**没变**（假成功）。
```java
PromotionResult r = track.promote(user, contextsFor(user));
if (r != null && r.wasSuccessful()) {
    api.getUserManager().saveUser(user).get(3, TimeUnit.SECONDS); // 必须！
}
```

## 3. track API 关键调用形态

```java
// 顶层入口：Bukkit 主线程外也安全（Provider 已由 LP 插件注册）
LuckPerms api = LuckPermsProvider.get();

// 用户：在线走缓存同步，离线异步加载（阻塞等 3s）
User user = api.getUserManager().getUser(uuid);          // 在线/已缓存
if (user == null) user = api.getUserManager().loadUser(uuid).get(3, SECONDS); // 离线

// track：名 "rank"，组序 default→member→builder→admin
Track track = api.getTrackManager().getTrack("rank");

// 上下文：promote/demote 需要 ContextSet（不是 QueryOptions！）
ImmutableContextSet ctx = api.getContextManager().getContext(user)
        .orElseGet(ImmutableContextSet::empty);

// 组查询：getInheritedGroups 收 QueryOptions，返回 Collection<Group>，
// 组名用 getName()（不是 getGroupName()——那个是 Node 的）
boolean in = user.getInheritedGroups(user.getQueryOptions()).stream()
        .anyMatch(g -> g.getName().equalsIgnoreCase("builder"));
```

## 4. 边界状态枚举（javap 反编译确认，不绕圈）

- `PromotionResult.Status`：SUCCESS / ADDED_TO_FIRST_GROUP（不在 track 自动加首组）/
  END_OF_TRACK（**链顶再 promote = 失败，不绕回**）/ MALFORMED_TRACK / AMBIGUOUS_CALL / UNDEFINED_FAILURE
- `DemotionResult.Status`：SUCCESS / REMOVED_FROM_FIRST_GROUP（链底移除首组回 default）/
  NOT_ON_TRACK / AMBIGUOUS_CALL / ...

**API 语义离线验证法**（网络受限时比 web 搜索可靠）：
```bash
curl -sL -o /tmp/lp-api.jar "https://repo1.maven.org/maven2/net/luckperms/api/5.4/api-5.4.jar"
unzip -o -q /tmp/lp-api.jar -d /tmp/lp-api-extract
javap -p /tmp/lp-api-extract/net/luckperms/api/track/PromotionResult\$Status.class
```

## 5. AMBIGUOUS_CALL：玩家同时挂在 track 多个组上时 promote/demote 失败

存量玩家常见（早期 `parent add` 叠加出 builder+member 双组）。此时 `track.promote`
返回 `AMBIGUOUS_CALL`，插件会误报"已在最高等级"。
**迁移动作**：`lp user X parent remove member`（保留最高组），track 语义要求单组。
涉及多端数据时，迁移脚本要幂等可重跑。

## 6. 为什么本地权限状态可以全删（架构结论）

LP track 成为唯一事实源后：
- `promoted` 标记（防重复自动晋升）→ LP 组本身就是幂等（已在 member 则
  `currentTrackGroup != default` 不触发）
- `demoted` 标记（抑制 APPROVED 记录判定）→ LP 里没有 builder 组 = 自然降级
- `admin` 标记（识别链顶）→ 不需要，LP 真实组直接给出

permission.yml 只剩 config（阈值）+ reviews（审核记录）两段。**唯一保留本地推断的
场景**：LP 未安装时回退（有 APPROVED builder 记录 → builder，否则 default）。

## 7. 软依赖降级：条件实例化 + Noop（用户拍板，禁止反射）

先做了一版反射（Class.forName+Method.invoke）规避类加载，用户否决（「反射容易
出问题，可以不用反射实现吗」）。**最终方案利用 JVM 惰性类加载——不执行 `new`
就不加载类，方法签名里的 LP 类型永不解析**：

```java
// ① 接口零 LP 引用（纯业务类型）——Noop 实现才能零依赖
public interface RankPromoter {
    boolean isAvailable();
    String currentTrackGroup(UUID id);   // 返回目标组名而非 LP 结果对象
    String promote(UUID id);             // null = 链顶/失败/LP 缺失
    String demote(UUID id);
    boolean isInGroup(UUID id, String group);
    UUID resolvePlayerId(String name);
    Optional<String> playerName(UUID id);
}

// ② LP 实现直接 import net.luckperms.api.*（类型安全），结果翻译成 String
// ③ NoopRankPromoter：全 null/false，零 LP 引用
// ④ 装配层：
if (Bukkit.getPluginManager().isPluginEnabled("LuckPerms")) {
    rankPromoter = new LuckPermsPromoter(resolver, serverFacade::runSync);
} else {
    rankPromoter = new NoopRankPromoter();
    log.warning("未检测到 LuckPerms，权限管理功能不可用（时长查询/申请记录仍可用）");
}
```

⚠️ **嵌套接口陷阱**：PlayerNameResolver/ServerScheduler 等辅助端口**必须提为独立
顶层文件**。若作为 `LuckPermsPromoter` 的嵌套接口，装配层引用
`LuckPermsPromoter.PlayerNameResolver` 会**连带加载外层类** → LP 缺失时
NoClassDefFoundError 照样炸（实测踩坑：嵌套接口版无 LP 启动崩溃，独立文件版正常）。

⚠️ **Mockito 测 LP API 的坑**：
- 嵌套 stubbing：`thenReturn(helper(...))` 里 helper 内部再 `when()` →
  UnfinishedStubbing。先构造局部变量再 thenReturn。
- `ImmutableContextSet.empty()` 是真实静态方法（内部调
  `ContextManager.getContextSetFactory()`）——mock 环境直接调用 NPE，连
  `verify(x).promote(user, ImmutableContextSet.empty())` 断言都炸。须 mock
  `ContextManager.getContextSetFactory()`（stub `immutableEmpty()`），verify 用
  `any(ImmutableContextSet.class)`。

**验收证据**（本地 25565）：有 LP——降级 admin→default 3 连 SUCCESS、升级
default→admin 3 连 SUCCESS、链顶 END_OF_TRACK 提示「已在最高等级」、链底
「已在最低等级」，全链真实落库（`lp user X parent info` 双证据）；无 LP（删
LP jar 重启）——插件正常启动、$p 提示「未检测到 LuckPerms，权限管理功能不可用」。
