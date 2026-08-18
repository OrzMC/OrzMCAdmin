# OrzMC 插件 PR 代码审查清单（2026-08-07 PR #160 review 沉淀）

审查本地 PR 分支时的检查流程 + 实际发现的高发问题。适用于任何 OrzMC 插件 PR 合并前。

## 一、文档脱节检查（PR #160 一次性发现 8 处——最高发问题）

**PR body/文档声称的功能与代码实际不符**是本项目常见病。逐项对照：

| 检查点 | 手法 | PR #160 实例 |
|:--|:--|:--|
| PR body 声称的功能 | grep 代码确认存在 | body 声称「旧 ranks.yml 自动迁移」但 `migrateLegacyRanks` 已随配置最小化重构删除 |
| 功能生命周期 | `git log --oneline -- <file>` + `git show <commit>:<file>` 对比历史实现 vs HEAD | 迁移逻辑 16dfa4c 有、b278fb3 删——确认「曾实现后删除」而非「从没实现」 |
| javadoc vs 实现 | 读接口/类 javadoc 对照代码 | RankPromoter javadoc 写「反射访问 LP API」，实际早已改无反射条件实例化 |
| 资源文件 vs 消费方 | `grep -rn "ranks.yml" src/main/java/` | ranks.yml 无任何 loadFile 引用 → 无消费方残留，删除 |
| 配置注释 vs 配置结构 | 读 permission.yml 注释对照代码读写节 | 注释写「三段式 ranks 晋升状态节」，实际 ranks 节已删（两段式） |
| build 注释 vs 实际配置 | 读 build.gradle.kts 注释 | 注释写「softdepend 保证加载顺序」，实际用 paper-plugin.yml `dependencies:` 新格式 |
| 常量表 vs 字符串字面量 | 搜新事件键是否进 TemplateKeys | rank_promoted/rank_demoted 只有字面量，TemplateKeys 缺 → ConfigHealthCheck 模板校验覆盖不到（与 {message} 事故同源） |
| docs/ 设计文档 vs 最终实现 | grep docs 中的「迁移/三段式/ranks」等关键词 | 3.6 数据迁移章节、检查表、开发清单全说过时描述 |
| **接口签名 vs 文档代码块** | 读接口源码对照 docs 里的签名片段 | ReviewHandler 文档写 `void onApproved`，实际 `boolean onApproved`（S1 修复后文档没跟）——单行签名最容易漏 |
| **常量/模板键计数** | 数 TemplateKeys 常量 + templates.yml 内容段/format 段 vs docs 写的键数 | docs 写「5 键」，实际 11 键（rank_promoted/demoted + command_review_* 漏数） |
| **监听器集合 vs 文档描述** | grep @EventHandler 对照文档「双监听/单监听」描述 | 8.4 写「双事件监听」，M3 已改单通道 RCON |
| **验收文档（acceptance）滞后** | 检查 commit hash、测试键数、行为描述（审核人显示等） | acceptance 写 commit 3358e5a（实际 e1c18c1）、「补 5 键」、「审核人=群管理员」（S2 后=发送者昵称透传） |

**教训**：设计文档（docs/）+ javadoc + 配置注释 + PR body 四处极易滞后于代码。大重构（如「配置最小化删 ranks 段」）后必须全链路同步。

## 二、PaperMC/Java 插件审查 check 项（PR #160 实际发现）

1. **void 回调吞掉失败 → 状态假成功**：副作用回调返回 void + 被调方法失败时返回 **null 而非抛异常** → 调用方无法感知。实例：`ReviewHandler.onApproved`（void）→ handler 是 `rankService::promote`（失败返回 null）→ 审核仍落 APPROVED 但玩家组没变。修法：回调返回 boolean，调用方检查。**测试也要覆盖「返回 null」而非只覆盖「抛异常」**（现有测试只有 handlerThrows 异常路径）。
2. **N+1 LP 查询**：`currentTrackGroup` 循环 `trk.getGroups()` 内每次调 `isInGroup` → 每次 `loadUser`（离线玩家最多 3s×4）。修法：loadUser 一次，遍历 `user.getInheritedGroups()` 匹配 track 组。$l 列表对每个玩家调 currentGroup → N 玩家 × 4 次查询。
3. **审核人身份硬编码**：群指令审核 `reviewerName = "群管理员"` 丢真实操作人 → 审计/追溯失效（`/apply status` 无法显示谁审核的）。isAdmin 参数传进来了但没用。
4. **主线程阻塞风险**：`PlayerJoinEvent`（主线程）→ `checkPromotion` → `loadUser().get(3s)` + `saveUser().get(3s)`。在线玩家缓存通常命中（LP 也在 join 加载），但需评估异步化兜底。
5. **双通道事件并存**：Brigadier `executes()` 直调 + `ServerCommandEvent`/`RemoteServerCommandEvent` 事件监听并存——当前 Paper 26 事件不触发无问题，但 Paper 行为变化时同命令处理两次 → 群消息重复。留一个通道，另一个注释说明。

## 三、Review 流程技巧

```bash
git diff main...<branch> --stat                    # 全貌（文件数/增删量）
git diff main...<branch> -- <file>                # 逐个文件
git log --oneline -- <file>                       # 文件生命周期（找「曾实现后删除」）
grep -c "@Test" src/test/java/.../*Test.java      # 快速评估测试量
gh pr checks <n>                                  # CI 状态
```

- **测试覆盖评估**：搜测试名覆盖的「失败路径形态」——异常 vs null 返回是两种不同路径，只测异常会漏 null 静默失败
- **权限校验**：每个命令入口查拦截器（guardAdminCommand / adminInterceptors / requires）
- **异步链路**：runSync + CompletableFuture.join 模式检查异常传播（Bukkit 调度器吞异常只打日志）
- **状态一致性**：副作用（LP 授权）与持久化（状态落盘）的顺序——「先 handler 后落状态」正确，但 handler 失败信号必须能传播

## 四、Folia 异步/并发审查检查点（2026-08-19 PR #196 实战新增）

1. **服务器调度线程等 LP future = 自锁**：全局搜 `loadUser|saveUser|\.get\(|\.join\(`，确认没有任何 global/region 线程同步等待 LP 异步 future（回调排自己后面必自锁/超时）。授权类操作必须 `CompletableFuture` 异步化（LP 在自己管理的异步线程执行）。
2. **状态漂移**：授权结果与业务状态必须原子一致——「LP 已晋升 + 状态 PENDING」= 漂移，重复操作会越级。检查异步回调落状态前是否重读校验。
3. **并发竞态（异步化新引入）**：异步授权后同一实体可被并发操作——in-flight 去重（CHM keySet 占位）或 PROCESSING 占位 CAS；授权在途时撤回/拒绝互斥。
4. **region 线程判定**：`Bukkit.isGlobalTickThread()` 不覆盖 region 线程（Folia 需 `isRegionOwnedByCurrentThread()`，paper-api 编译期无此方法须反射）；任何服务器调度线程上都不应做可能阻塞的离线读。
5. **写盘并发**：异步化把写挪到不同线程后，共享配置对象（FileConfiguration）读写必须加锁，防丢更新/YAML 损坏。
6. **join 超时**：所有 `done.join()` 必须有超时（调度器停摆时防永久挂起）。
