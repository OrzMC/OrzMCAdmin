# OrzMC 通用审核框架（权限系统二期，2026-08-07 落地）

> 背景：Rank 一期（时长读 stats + default→member 自动晋升 + member→builder 申请）的审核逻辑
> 写死在 rank 模块（`pending_application` 字段），无法复用于白名单/领地等其它审核项。
> 二期抽象出**通用审核框架** `features/review/`，rank 模块退化为消费者。
> **用户明确要求：框架按「未来可单独沉淀为通用审核插件」设计**——拆插件 = 搬 `features/review/` 包
> + `permission.yml` 的 reviews 节 + 补 4 个端口适配器，核心代码零改动。
> 完整方案文档：`~/OrzMC/plugin/docs/permission-system-v2.md`

## 设计要点（用户拍板的架构约束）

| 约束 | 落地 |
|:--|:--|
| 审核请求**携带结构化内容** | `ReviewRequest.data`（Map<String,String>），「审核什么」明确表达，框架不感知业务 |
| 审核类型**注册表驱动** | `ReviewType`（record：id/displayName/commandKey/argsParser/eligibility/summary/handler），消费者模块构建后 `reviewService.register(type)` |
| **handler 由消费者注入**，框架零 LP 依赖 | BUILDER_PROMOTION 的 handler = `rankPromoter::promoteToBuilder`，在 FeatureModule 装配时注入，不在 review 包写死 |
| **端口解耦**（可拆插件） | review 包只依赖 4 个端口接口：`ReviewStore`（持久化）/ `ReviewNotifier`（通知）/ `PlayerLookup`（玩家名↔UUID），实现留在宿主侧 |
| **单一配置文件** | `permission.yml` 三段式（config 阈值 / ranks 晋升状态 / reviews 审核记录），`PermissionStore` 一个类实现 RankStore + ReviewStore 两个接口，替代原 ranks.yml |
| 群指令 + 游戏内命令全通用化 | `$v`（l/y/n）+ `/apply <type> [理由]` + `/apply status|cancel` + `/review approve|reject` + `/rank` 增强 |

## 核心类（features/review/，零宿主依赖）

- `ReviewRequest` — record(id, typeId, applicantId, data, status, createdAt, reviewedAt, reviewerName)；Status 枚举 PENDING/APPROVED/REJECTED/CANCELLED；`reviewed()` 生成审核后新记录
- `ReviewType` — record(id, displayName, commandKey, argsParser, eligibility, summary, handler)；`parseArgs(rawArgs)` / `isEligible(uuid)` / `summarize(data)`
- `ReviewService` — 核心编排：`submit`（资格预检→防重复→PENDING→双端通知）/ `cancel`（仅本人 PENDING）/ `review`（通过时执行 handler）/ `reviewByApplicantName`（按玩家名定位，多条待审提示用类型区分）/ `cancelForApplicant`；通知逻辑收在 service 层，任何入口触发都自动通知
- `ReviewHandler` — `@FunctionalInterface void onApproved(UUID applicantId)`
- 端口接口：`ReviewStore`（save/findById/listPending/listByApplicant/pendingFor/hasPending）、`ReviewNotifier`（gameMessage/groupEvent）、`PlayerLookup`（resolve/name）

宿主侧端口实现：
- `infra/notify/ReviewNotifierAdapter` — 适配 TypedConfigProvider + Notifier
- `infra/player/BukkitPlayerLookup` — 适配 `Bukkit.getOfflinePlayer()`（离线服审核时申请者可能已下线）

## ⚠️ 通知模板必须用 renderTemplate，不能用 renderEvent

`TypedConfigProvider.renderEvent(key, vars)` 走 `TemplateService.templateForEvent()`——**硬编码白名单**（player_join/whitelist_block/...），
**未列入白名单的键渲染成空字符串**（不报错！）。新增事件通知模板必须用
`renderTemplate(key, vars, fallback)`（`TemplateRenderer.resolveTemplate` 直接按配置键读取，带 fallback 兜底）。

```java
// ✅ 正确（ReviewNotifierAdapter.groupEvent）
MessageEnvelope env = configs.renderTemplate(templateKey, vars, fallback); // fallback 含 {player}/{summary}/{reviewer} 占位
notifier.event(templateKey, env);
// ❌ 错误：renderEvent("review_submitted", vars) → 渲染为空，群消息静默丢失
```

## ⚠️⚠️ renderTemplate 第二层坑：模板占位符必须 ⊂ vars 键集（PR review 抓到的 C1 Critical）

用对 `renderTemplate` 也不够——**默认模板占位符与调用方 vars 键集不匹配时，字面 `{message}` 直接透传**：

- `ReviewService.groupEvent` 传 vars `{player, type, summary, reviewer}`（**无 message 键**）
- 仓库默认模板 `review_submitted: "{message}"`（模板文件里只有 `{message}` 占位）
- `TemplateRenderer.render()` 只替换 vars 里**存在的键**，不存在的占位符原样保留 → 群通知推送字面 `{message}`
- **fallback 不救场**：`resolveTemplate` 优先命中模板文件（有 `{message}` 就用它），fallback 只在模板缺失/为空时生效
- **为什么 E2E 没抓到**：测试服 templates.yml 被手工改过（中文文案）→ 全绿；新部署用仓库默认模板 → 必现。**测试环境配置漂移掩盖生产 bug**

**修复模式**：默认模板必须用与 vars 一致的占位符（`📋 [新申请] {player}：{summary}（$v l 查看）`），或调用方补 `message` 键。
**review 检查点**：凡 `renderTemplate(key, vars, fallback)`，核对 vars 键集 ⊇ 模板占位符键集（可用 python 模拟 render 快速验证）。
**✅ 防回归测试已落地（2026-08-07）**：`TemplateResourceSmokeTest.testReviewGroupEventsRenderRealText_notLiteralMessage` ——
用真实 vars 渲染 `review_submitted/approved/rejected` 断言「含玩家名」且「不含字面 `{message}`」。
新增模板键时在此测试补断言（同时记得 4 处注册，见下节）。

## PR 代码 review 检查点（Paper 插件通用，2026-08-07 权限二期 review 实战）

1. **模板/消息渲染**：renderTemplate vars 键 ⊇ 占位符键（上条）；模板键 4 处注册齐全；`command_review_list` 类传 `message` 键所以没事，`review_*` 四键没传所以坏——逐个核对
2. **handler 副作用顺序**：`store.save(APPROVED)` 先于 `handler.onApproved()` 执行 → handler 抛异常（LP 命令失败）时**状态已存但权限未授**，玩家看到「已通过」实际无权限。应 handler 先执行再落状态，或 try-catch + 告警（S3 建议）
3. **ID 生成**：`System.currentTimeMillis() + UUID.randomUUID().hashCode()` —— hashCode 可能为负、同毫秒碰撞概率存在；用完整 UUID 更稳（S1）
4. **语义字段**：`cancel()` 把申请人 UUID 当 reviewer 存（CANCELLED 记录的 reviewer 应是名字或 null，W5）
5. **迁移性能**：循环内每次 `save()` 全量落盘 → 批量迁移攒批一次保存（W3）
6. **旧文件清理**：迁移后 ranks.yml 残留，成功迁移后改名 `.bak`（W4）
7. **异步 dispatch 主线程**（已有）：`$v`/orzdebug 链路 handler 内 dispatchCommand 必须回主线程

## 新增模板键 = 4 处注册（漏一处必踩坑）

1. `TemplateKeys.java`：常量 + 加入 `ALL` 数组（ConfigHealthCheck 校验用）
2. `src/main/resources/templates.yml`：`format:` 段（PLAIN/CODE_BLOCK）+ 消息正文段
3. `src/test/resources/templates-test.yml`：测试资源同样要加
4. `ConfigHealthCheckTest.java`：`requiredCmds` 数组——**文件里有两处相同的数组**（fullValid 与 minimal），
   用 patch 时 `replace_all=true`，只改一处另一处会漏（2026-08-07 实测 test 失败即因此）

## 装配与接线（FeatureModule）

- `PermissionStore(platform.configService())` 注册在 `ConfigService.setup()`：`registerConfig("permission","permission.yml")` + `markAlwaysSave("permission")`
- `migrateLegacyRanks()`：启动时把旧 `ranks.yml` 的 `promoted` 标记和 `pending_application=true` 幂等迁入 permission.yml（已迁移跳过）
- **构造顺序坑**：rankService 必须先于 register() 创建（BUILDER_PROMOTION 的 eligibility lambda 引用 `rankService` 字段，
  final 字段在赋值前被 lambda 捕获 → 编译错误「可能尚未初始化变量rankService」）
- **BotCommandService 注入时机**：BotCommandService 在 BotModule（Phase A）创建，早于 FeatureModule 的 review/rank 服务——
  新群指令 handler 依赖的服务用 **setter 注入**（`setReviewService`/`setRankService`），在 `FeatureModule.setupEventListeners()`
  开头补调用（与 maintenance/blacklist 同一模式）

## 群指令 $v（扩展自 OrzUserCmd 枚举）

- `OrzUserCmd.REVIEW("v", "查看/处理审核申请", true)` → `BotCommandService` handlers map + `handleReview`
- `$v l`（待审列表，带申请人当前组，Paginator 分页）/ `$v y <玩家>`（通过）/ `$v n <玩家>`（拒绝）
- 支持 `$v y <typeId> <玩家>` 精确按类型定位
- 审核人身份记为「群管理员」（群内 isAdmin ≠ 游戏 LP 组，见 orzmc-bot-command-testing.md）

## 游戏内命令（FeatureModule registerRank，Brigadier）

- `/apply`（列可申请类型）/ `/apply <type> [理由]` / `/apply status` / `/apply cancel <type>`
- `/review approve|reject <name>`（替代一期 `/rank approve|reject`）
- `/rank`（当前组+时长/进度+下一步可申请——「下一步」由 ReviewType 注册表反向生成，资格预检通过的项）
- 玩家侧三件套：`/rank`（我是谁）· `/apply status`（我申请了什么）· `/apply cancel`（我能撤回）

## 通知矩阵（4 环节全覆盖，模板键 + 默认文案）

| 环节 | 触发方 | 模板键 |
|:--|:--|:--|
| 提交 | 玩家 /apply | `review_submitted` = 📋 [新申请] {player}：{summary}（$v l 查看） |
| 撤回 | 玩家 /apply cancel | `review_cancelled` = ↩️ {player} 撤回了申请：{summary} |
| 通过 | 管理员 | `review_approved` = ✅ {player} 的申请已通过（审核人：{reviewer}）：{summary} |
| 拒绝 | 管理员 | `review_rejected` = ❌ {player} 的申请被拒（审核人：{reviewer}）：{summary} |

玩家结果三层兜底：游戏内消息（在线即发）→ 群通知（离线可见）→ `/apply status` 随时自查。

## 测试

- `ReviewServiceTest`（纯 JUnit + Mockito）：提交/预检/防重复/撤回归属/审核 handler 副作用（int[] calls 计数）/多待审按类型提示
- `PermissionStoreTest`：stats 解析 + 三段读写 round-trip
- 注意：`reviewByApplicantName` 测试里 `store.findById` 也要 mock（`listPending` 之外 service 内部还会查 findById）
