# OrzMC Rank 模块 LP 集成：幂等与状态验证（2026-08-07 实测）

背景：Rank 自动晋升通过 `server.dispatchCommand(consoleSender, "lp user <name> promote rank")` 执行（零 API 依赖）。本文件记录**幂等设计**与**状态验证手段**的实测结论。

## ⚠️ 核心教训：`lp promote <track>` 没有天然幂等

- `lp promote rank` 每次调用都沿 track **升一级**（default→member→builder→admin），不是"确保达到某组"。
- 多调一次 = 多升一级。**没有任何幂等保护**。

## 实测 bug：isInGroup 预判失效 → 连升两级

### 症状
TestNewbie（default，达标 600min）两次 join 后 LP 显示 **builder**（预期 member）。

### 根因
```java
// ❌ 错误实现（占位判断，不是真 LP 查询）
public boolean isInGroup(UUID id, String group) {
    return DEFAULT_GROUP.equals(group) && server.getPlayer(id) != null; // 在线即认为在 default
}
```
控制台执行 LP 命令的结果**无法回读**（RCON 不回显 Adventure 组件输出），isInGroup 只能退化成"玩家在线"占位 → 每次 join 都满足"在 default"→ 每次达标都 promote → 两次 join 升了两级。

### ✅ 正确方案：自有持久化标记保证幂等
```java
// RankStore 接口新增
boolean hasPromoted(UUID playerId);
void markPromoted(UUID playerId);

// RankService.checkPromotion
if (store.hasPromoted(playerId)) return;          // 已晋升过不重复处理
if (store.getPlaytimeMinutes(playerId) >= threshold) {
    promoter.promoteToNext(playerId);
    store.markPromoted(playerId);                  // 标记落盘 ranks.yml
}
```
- isInGroup 改为**恒 false**（不做预判，语义改成"不依赖 LP 查询"），预判职责完全交给 hasPromoted。
- ranks.yml：`players.<uuid>.promoted: true`（markAlwaysSave 持久化）。
- 注意：手动把玩家调回 default 重测时，**旧 promoted 标记会阻止再晋升**——重测前清标记（或对测试账号直接预置标记）。

## LP 状态验证三手段（实测排序）

| 手段 | 适用 | 坑 |
|:--|:--|:--|
| **bot 玩家身份 `lp user X info`** | 常规验证 | **Adventure 组件截断输出**：`[LP] - Parent Groups:` 与内容 `[LP]     > builder` 是**两条独立消息**，grep 关键词只见标题不见内容——必须连后续行一起抓（如 grep -A2 或监听多条消息拼接） |
| **H2 mtime** | 判断命令是否执行 | `stat -f %m .../luckperms-h2-v2.mv.db` 前后对比；**运行中 H2 被 LuckPerms 独占锁定**，外部连库报 `Database may be already in use ... [90020-214]`，只能停服后查 |
| LP 命令回显 | 中文 locale | `> default`/`> member` 等行，注意 locale 差异 |

## 测试账号重置流程（重测自动晋升前）✅ 已实测（2026-08-07）

```bash
# 用 TestAdmin（admin 组）执行：
#   lp user TestNewbie parent remove builder
#   lp user TestNewbie parent add default
# 然后验证：lp user TestNewbie info → Parent Groups: > default
# 最后清/预置 ranks.yml 的 promoted 标记
```
实测：重置回 default + 清 promoted 标记 → 上线 join → **只升一级到 member**（LP info 确认 `> member`）→ 再 join 不再升（标记生效）。

## LP 软依赖检测（2026-08-07 用户拍板实现，防无 LP 服静默失败）

插件未在 plugin.yml 声明 LP 依赖（软依赖），`lp ...` 命令在无 LP 服务器上执行**静默失败**（无报错无晋升）。已实现运行时检测：

```java
// LuckPermsPromoter
public boolean isLuckPermsEnabled() {
    PluginManager pm = Bukkit.getPluginManager();
    return pm != null && pm.isPluginEnabled("LuckPerms");
}
public void promoteToNext(UUID playerId) {
    String name = nameResolver.resolve(playerId);
    if (name == null || !isLuckPermsEnabled()) return;  // LP 未装 → 跳过晋升
    dispatch("lp user " + name + " promote " + TRACK);
}
```
- FeatureModule 装配时检测：未装打警告日志「未检测到 LuckPerms，Rank 晋升功能禁用（时长查询/申请记录仍可用）」
- 降级行为：无 LP 服 `/rank` 时长、`/apply` 申请记录仍可用，仅晋升动作跳过
- 测试：`LuckPermsPromoterTest`（mockStatic Bukkit + try-with-resources 包住；LP 装载/缺失 × isLuckPermsEnabled/promoteToNext/promoteToBuilder）
- ⚠️ mockStatic 泄漏教训：`mockStatic(Bukkit.class)` 必须在每个测试的 `try(...)` 内开启，@BeforeEach 里开不关会让 stub 泄漏到后续测试

## 关联
- `references/rank-playtime-data-source.md`（时长数据源：stats 文件读取）
- SKILL.md「OrzMC 新 feature 开发坑」章节
- minecraft-bot-mineflayer `scripts/perm-check.js`（LP 权限验证 bot）
