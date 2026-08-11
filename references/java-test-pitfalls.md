# Java 测试编译陷阱（2026-08-11 从 java-test-pitfalls 技能合并）

> 场景：写/修 OrzMC 系插件 Java 单元测试时的编译错误、javac 警告、GitHub Actions warnings 排查。

## 触发条件

- `when(mock.method()).thenReturn(x)` 编译报「找不到合适的方法」且错误信息含 `CAP#1` / `? extends` 捕获
- 想用 `@SuppressWarnings` 消警告但 CI 还在报
- CI 日志出现 `##[warning]`（unchecked / rawtypes 类），Checks 区和 Files changed 行内都有 ⚠️ 标记

## Pitfall 1：Mockito thenReturn 与通配符泛型捕获

**症状**：mock 的 API 返回 `Collection<? extends Player>`（Bukkit `getOnlinePlayers()` 等），写：

```java
java.util.Collection<? extends Player> online = List.of(p1);
when(mock.getOnlinePlayers()).thenReturn(online);  // 编译错
```

javac 报：`thenReturn(Collection<CAP#1>) 找不到合适的方法`——`when()` 捕获出 CAP#1，`thenReturn` 期望的 `OngoingStubbing<Collection<? extends Player>>` 是另一个捕获 CAP#2，两个捕获互不匹配。

**修复**：改用 `doReturn`（接受 raw Object，绕开泛型捕获推断）：

```java
java.util.Collection<? extends Player> online = List.of(p1);
doReturn(online).when(mock).getOnlinePlayers();   // ✅
```

- `doReturn` 不产生 unchecked 警告（它签名是 `OngoingStubbing<T> doReturn(Object)`）
- 需要 `import static org.mockito.Mockito.doReturn;`
- 注意：`Collection<Player>`（无通配符）也不行——`thenReturn` 要求精确匹配捕获类型

## Pitfall 2：@SuppressWarnings 注解位置

**症状**：`@SuppressWarnings({"unchecked", "rawtypes"})` 标在局部变量声明上，但 CI 仍报 unchecked 警告。

**原因**：局部变量声明上的注解**只抑制该声明本身**，不覆盖后续语句。典型场景：

```java
@SuppressWarnings({"unchecked", "rawtypes"})   // ❌ 无效：只盖住这行声明
java.util.Collection online = List.of(p1);
when(mock.getOnlinePlayers()).thenReturn(online);  // ⚠️ 警告发生在这行
```

**正确修法（优先级从高到低）**：
1. 消除 raw type 本身（改泛型类型）——最干净，见 Pitfall 1 的 `? extends` + doReturn 组合
2. `@SuppressWarnings` 移到**方法级**或直接标在出警告的**语句上**
3. 确认警告真正产生的位置：`./gradlew compileTestJava 2>&1 | grep warning` 看行号，别只看注解在哪

## Pitfall 3：GitHub Actions 编译警告排查与清零

**事实**：javac 的 `-Xlint` 警告（unchecked/rawtypes/deprecation）在 GitHub Actions 日志里以 `##[warning]` 行出现，会同时显示在：
- Checks 页面的 warning 数
- PR **Files changed 里对应代码行的 ⚠️ 行内标记**（用户常把这两处叫「PR 的 Alerts」）

**排查流程**：
1. `gh run view <RUN_ID> --log | grep "##\[warning\]"` 定位警告文件与行号
2. 本地复现：`./gradlew compileJava compileTestJava` 看警告（本地 JDK 与 CI 的 `-Xlint` 默认开关一致时行号对齐）
3. 修复后重跑 CI，**验证清零**：`gh run view <NEW_RUN_ID> --log | grep -c "##\[warning\]"` 应为 0

**注意**：`@SuppressWarnings("removal")` / `("deprecation")` 的既有注解不是问题；只清本次新增的 unchecked/rawtypes。

## 验证步骤

```bash
./gradlew spotlessApply test          # 全量测试
./gradlew check                       # 完整门禁（含集成测试）
# 推送后：
gh run view <id> --log | grep -c "##\[warning\]"   # 期望 0
```

## 关联陷阱（同领域）

- **删配置/删代码时 grep 全引用面**：record 字段、解析器、测试构造器、健康检查（类型校验 + 建议校验常分两处）都要同步删，漏一处编译即挂
- **patch YAML 删段后必须回读结构**：误把相邻段键名改掉的 patch 事故，`grep -n "^\s\s\w*:"` 验证段结构
