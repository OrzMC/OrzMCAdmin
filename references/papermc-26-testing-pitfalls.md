# Paper 26 测试踩坑明细（2026-08-07 权限系统二期 E2E 实测）

本文件记录在本地测试服（Paper 26.2-92, papermc-test）做插件 E2E 时遇到的全部非平凡问题与证据链。

## 1. Brigadier 命令不触发 ServerCommandEvent（OrzDebugEvent 彻底失效）

**现象**：`orzdebug $v l` 执行只输出 Brigadier 分支的「debug 已受理」，Bot 模拟分支（`cmd debug:` 日志）永远不触发。

**根因（2026-08-07 二次实测修正）**：`OrzDebugEvent.cmdDebugHandler` 监听 `ServerCommandEvent`/`RemoteServerCommandEvent`，但 **Paper 26 中 Brigadier 注册的命令（`literal("orzdebug")`）根本不派发这两个事件**——Brigadier 命令有自己的分发路径。「X issued server command」日志是 Bukkit 通用命令日志，**不代表**事件触发。用分层日志实测确认：事件监听器入口日志（`ServerCommandEvent 触发`）从未出现，而 `.executes()` 内「已受理」正常输出。

**早期错误修复（已废弃）**：双事件注册 + 剥斜杠（`cmdDebugHandler(ServerCommandEvent)` + `rconDebugHandler(RemoteServerCommandEvent)`）。无效——事件根本没触发。

**正确修复**：直接在 Brigadier `.executes()` 里调用 BotInboundHandler：
```java
literal("orzdebug")
    .then(argument("cmd", StringArgumentType.greedyString())
        .executes(ctx -> {
            String cmd = ctx.getArgument("cmd", String.class);
            ctx.getSource().getSender().sendMessage("debug 已受理（模拟 Bot 入站命令）");
            var inbound = botModule.botInboundHandler();   // FeatureModule 字段
            plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> {
                try {
                    inbound.handleMessage(cmd, true,
                        env -> { if (env != null) plugin.getLogger().info("cmd debug: \n" + env.message()); });
                } catch (Exception e) {
                    plugin.getLogger().log(Level.SEVERE, "debug 命令异步执行异常", e);
                }
            });
            return 1;
        }))
```
**验证**：日志出现完整链路 `parse 匹配: cmd=v ... → handleReview 进入 → emit → cmd debug:`。

**通用教训**：事件监听器依赖 `ServerCommandEvent` 捕获命令的调试桥在 Paper 26 不可靠；需要「命令 → 代码」直连时在 Brigadier 注册点直接接线，别绕事件。

## 1b. 断链分层调试法（定位"受理了但无效果"）

群指令/异步链路出现「入口有反应、业务无效果」时，**从入口到出口每层加一行日志，一次部署一次实测**：
```
事件监听器/executes 入口 → parse 匹配（cmd=xxx rawArgs=yyy）→ handler 进入 → emit（templateKey/fallback/env）
```
本例正是靠 `[OrzMC-debug]` 分层日志发现断点在第 0 层（事件监听器），从而避免继续误修 review 业务逻辑。**纯单测禁用 `Bukkit.getLogger()`**（无 MockBukkit 时 `Bukkit.server` 为 null → NPE），调试日志用 `java.util.logging.Logger.getLogger("OrzMC.Xxx")`。

## 1c. `$v y <玩家>` 离线玩家名解析

**现象**：群指令 `$v y TestNewbie` 受理但「找不到待审申请」，而游戏内 `/review approve TestNewbie` 成功——两者定位代码不同：
- 游戏内 `reviewByApplicantName` 用 `lookup.resolve(name)`（usercache，离线可解析）✅
- 群指令旧实现用 `Bukkit.getOfflinePlayer(uuid).getName()` → 离线玩家返回 null → 匹配失败 ❌

**修复**：群指令决策统一走 `reviewByApplicantName`（或 PlayerLookup 端口），不要用 `getOfflinePlayer().getName()`。

## 1d. 部署 jar 版本名变更 → 静默拷旧 jar

构建产物名带版本（`OrzMC-1.0.15-dev.jar` → bump 后 `OrzMC-1.0.16-dev.jar`）。部署命令若写死旧名：`cp build/libs/OrzMC-1.0.15-dev.jar plugins/` → 源不存在，**旧 jar 残留，改动完全不生效**，表现为「改了代码重测还是老行为」。**部署后必验**：
- `ls -la build/libs/*.jar plugins/OrzMC*.jar` 时间戳一致
- `grep "Enabling OrzMC" logs/latest.log` 确认版本号
- `ls plugins/OrzMC*.jar` 确认无残留旧名 jar（同名覆盖原则）

## 2. LP 命令异步 dispatch 崩溃

**现象**：`$v y TestNewbie`（经 orzdebug，异步线程）→ 日志：
```
java.lang.IllegalStateException: Asynchronous Command Dispatched Async: lp user TestNewbie parent add builder!
	at LuckPermsPromoter.dispatch(LuckPermsPromoter.java:76)
```
审核状态流转其实已成功（记录 APPROVED），但 LP 授权命令没执行。

**根因**：Paper 禁止在异步线程 dispatch 命令。群指令/orzdebug 链路走 `runTaskAsynchronously`。

**修复**：Promoter 注入 `ServerScheduler` 端口，非主线程回主线程：
```java
if (Bukkit.isPrimaryThread() || scheduler == null) {
    server.dispatchCommand(Bukkit.getConsoleSender(), command);
} else {
    scheduler.runSync(() -> server.dispatchCommand(Bukkit.getConsoleSender(), command));
}
```
构造重载（`(ServerAccess, PlayerNameResolver)` 不带 scheduler）保持单测兼容（mock 环境 isPrimaryThread=false → 走同步直发分支）。

**⚠️ 进阶坑：runSync 异常被吞**。`runSync` 内部是 `Bukkit.getScheduler().runTask(...)`，任务抛出的异常**只打印日志、不传播回调用方**。若业务需要感知授权成败（如「审核通过但 LP 授权失败 → 状态回滚」），必须显式等待并传播：
```java
CompletableFuture<Void> done = new CompletableFuture<>();
scheduler.runSync(() -> {
    try {
        server.dispatchCommand(Bukkit.getConsoleSender(), command);
        done.complete(null);
    } catch (Throwable t) {
        done.completeExceptionally(t);
    }
});
done.join(); // 阻塞异步线程直到主线程派发完成，异常以 CompletionException 抛出
```
**审核状态一致性顺序**：`review()` 必须**先执行 handler（LP 授权）再落状态**（save APPROVED），授权失败时申请保持 PENDING 并返回失败——否则出现「玩家看到已通过、实际无权限」的永久不一致。对应测试断言：`verify(store, never()).save(argThat(APPROVED))`。

**验证**：修复后日志出现 `[LP] testnewbie 已經從環境 global 中繼承了 builder.`（玩家离线也成功 → OfflinePlayer 解析生效）。

## 3. RCON 包 length 字段语义

**错误写法**（服务器立即断连，python 报 `struct.error: unpack requires a buffer of 4 bytes`）：
```js
pkt.writeInt32LE(body.length, 0);  // 漏算 id+type 8 字节
```
**正确**：`length = id(4) + type(4) + payload + 2 null` 总长 = `body.length + 8`（其中 body = payload + 2 null）。
认证响应 `id=1 type=2`，命令响应 `type=0`，失败 `id=-1`。

## 4. `$` 命令被 shell 展开

`execSync('python3 rcon.py "orzdebug $v l" ...')` → bash 把 `$v` 展开为空 → 命令变成 `orzdebug  l`。
- bash 里：用单引号包裹 `'orzdebug $v l'`
- node 里：spawnSync 数组参数（不经 shell）或原生 net 实现
- **注意**：`node -e "..."` 嵌套时 bash 先展开外层 `$`，调试要看实际执行的 argv

## 5. node 子进程 python 环境差异

`spawnSync('python3', ...)` 在 node 里失败、terminal 里成功，且服务器日志无连接记录。
原因复杂（PATH/python 版本/shell 差异），**结论：node 脚本内做 RCON 直接用原生 net 实现**（`scripts/rcon-node.js`），不要调 python 子进程。

## 6. markAlwaysSave 配置覆盖陷阱

**现象**：停服前改了 `permission.yml` 清空 reviews，重启后数据还在（/apply status 仍显示已通过）。

**根因**：插件 markAlwaysSave 配置在服务器关闭时用**内存态**覆盖写回文件。运行中改文件无效。

**正确流程**：**停服 → 改文件 → 再启服**。或利用「关闭时写回」——先停服（触发写回）再改。

## 7. 其他

- **bot 快速重连限流**：同一账号退出后立刻重进 → `进服超时`。两次进服间 sleep 8-10s。
- **Minecraft 协议 25565 状态查询**：TCP 可连但响应超时（socket.timeout），不可靠；RCON 才是可靠控制通道。
- **LP 状态查询**：`lp user X info` RCON 无回显、audit 日志存 H2（服务器运行中 DB 被占用不可读）。验证 LP 授权真实性 → 用玩家侧组专属命令实测（builder 组 `//wand` → WE 木斧提示）。
- **测试脚本模板**（沉淀于 `~/minecraft-bot/`）：`review-e2e.js`（提交→列表→通过→status→rank）、`review-e2e-2.js`（预检拒绝→$v n 拒绝→重申请→cancel 撤回）、`review-real.js`（真实玩家场景：提交→下线→离线审核→重连验证）。

## 9. $v 群指令全链路验收证据模板（2026-08-07 实测通过）

修复 orzdebug 链路后，`$v l/y/n` 全链路验收的标准输出对照：

```
# $v l（待审列表，含类型/玩家/当前组/内容摘要/相对时间）
------待审核申请------
第1/1页
[晋升建造者] TestMember（当前组：member）：申请晋升 builder：验收 $v 列表功能（刚刚 提交）

# $v n <玩家>（拒绝）→ 日志 cmd debug + 记录 REJECTED + reviewer=群管理员
已拒绝 TestMember 的「晋升建造者」申请。
      status: REJECTED
      reviewed-at: <epoch-ms>
      reviewer: 群管理员

# $v y <玩家>（通过）→ 日志先出现 LP 授权再落状态
[LP] LOG > (Console) [U] (testmember)
[LP] LOG > parent add builder
      status: APPROVED
      reviewer: 群管理员
# LP 组确认：builder + member（叠加，不替换原组）
```

**关键顺序**：`$v y` 的 LP 授权（`parent add builder`）**先于**状态落盘（APPROVED），若授权失败记录保持 PENDING（review() 先 handler 后 save 的设计）。拒绝/通过后**玩家可立即重新申请**（REJECTED/APPROVED 都不阻塞新申请，只有 PENDING 防重）。

**群指令结果输出**：orzdebug 模拟时结果打到服务器日志（`cmd debug:` 前缀）；真实 EasyBot 群连接时走 sink 发回群聊（本地无真实群则只见日志，且可能报 `EasyBot 批量发送失败 status=409`——**那是通知发送失败，不是审核失败**，别误判）。


**现象**：`ReviewNotifierAdapter.groupEvent()` 传 vars `{player, type, summary, reviewer}`，但仓库默认模板是 `review_submitted: "{message}"`（vars 里**没有 message 键**）→ 渲染结果就是字面 `{message}`。fallback 参数里有正确中文文案，但 `TemplateRenderer.resolveTemplate` **优先命中模板文件**（有 `{message}` 就用它），fallback 只在模板缺失/为空时生效。

**根因**：默认模板占位符与调用方传入的 vars 键集不匹配；测试服因手工改过模板（中文文案）才没暴露，**新部署必现**。

**验证脚本**（模拟 render 行为）：
```python
tpl = "{message}"; vars_ = {"player":"P","type":"T","summary":"S"}
out = tpl
for k, v in vars_.items(): out = out.replace("{"+k+"}", v)
print(out)  # '{message}' ← 字面残留
```

**修复模式**：默认模板必须用与 vars 一致的占位符（`{player}/{summary}/{reviewer}`），或调用方补一个 `message` 键。**review 检查点**：凡 `renderTemplate(key, vars, fallback)` 调用，核对 vars 键 ⊇ 模板占位符键；`command_review_list` 类传了 `message` 键所以没事，`review_*` 四键没传所以坏。

**同类检查点（Paper 插件 review 通用）**：
- `handler.onApproved()` 抛异常时状态已存 APPROVED 但 LP 未授权 → 玩家看到「已通过」实际无权限；应先 handler 后落状态或 try-catch 告警。
- `newRequestId()` 用 `UUID.hashCode()` 可能为负且碰撞概率存在 → 用完整 UUID。
- `cancel()` 的 reviewer 字段存申请人 UUID（语义错误，应存名字或 null）。
- 迁移循环内每次 `save()` 全量落盘 → 批量迁移应攒批一次保存。
- **坏记录容错**：YAML 存储读记录时 `UUID.fromString`/`Status.valueOf` 对损坏配置直接抛异常，单条坏记录会拖垮整个 list 功能 → 读取方法返回 `Optional`，解析失败 catch 后跳过 + warning 日志（不中断全表）。
- **迁移脏 key 容错**：遗留文件循环内 `UUID.fromString(key)` 对非 UUID key 抛异常中断迁移 → try-catch 跳过 + warning。
- **权限命令测试要验证「真实生效」而非仅日志/状态**：LP 命令 RCON 无回显、audit 存 H2 不可读 → 用组专属命令实测（builder 组 `//wand` → WE 木斧提示）。

## 10. LP track API 原生钳位（2026-08-07 反编译证伪「绕圈」假设）

**早期假设（已证伪）**：LP track 是循环的，`promote` 在链尾（admin）会绕回 default、`demote` 在链首（default）会绕回 admin，因此必须用显式 `parent add/remove` + 本地状态推断当前组实现钳位。

**反编译证据（LP API 5.4 jar，`javap -p`）**：
- `PromotionResult$Status`：`SUCCESS` / `ADDED_TO_FIRST_GROUP`（不在 track 上 → 加入首组）/ `MALFORMED_TRACK` / **`END_OF_TRACK`（链顶再 promote = 失败，不绕回）** / `AMBIGUOUS_CALL` / `UNDEFINED_FAILURE`
- `DemotionResult$Status`：`SUCCESS` / **`REMOVED_FROM_FIRST_GROUP`（链底 demote = 移除首组回 default）** / `MALFORMED_TRACK` / **`NOT_ON_TRACK`（不在 track = 已是 default）** / `AMBIGUOUS_CALL` / `UNDEFINED_FAILURE`
- `Track` 接口：`getGroups()`（链定义）、`promote(User, ContextSet)` / `demote(User, ContextSet)`（原生钳位）、`getNext/getPrevious`、`containsGroup`
- `UserManager`：`getUser(uuid)` 同步查缓存（在线）、`loadUser(uuid)` 异步加载（离线）、`getPrimaryGroup()` 查当前主组

**正确设计（最简版）**：track 定义 `default→member→builder→admin`（首组=default，`ADDED_TO_FIRST_GROUP` 语义让 default 玩家 promote 自然进 member）。插件侧：
```java
// 升级（自动钳位，无需自己判断当前组）
PromotionResult r = track.promote(user, ctx);
// r.getStatus() == END_OF_TRACK → 提示「已在最高等级（管理员）」
// 降级（同样钳位）
DemotionResult r = track.demote(user, ctx);
// REMOVED_FROM_FIRST_GROUP / NOT_ON_TRACK → 提示「已在最低等级（访客）」
```
**连带简化**：本地 `promoted`/`demoted`/`admin` 标记全删（LP 为唯一事实源），permission.yml 只留 config + reviews 两段。无 LP 时回退本地推断（reviews 的 APPROVED 记录 → builder，否则 default）。

**验证 Java API 语义的通用方法**（web 搜索被墙/污染时）：`curl -L -o /tmp/lp-api.jar https://repo1.maven.org/maven2/net/luckperms/api/<v>/api-<v>.jar` → `unzip -o -q` → `javap -p`（反编译接口/枚举，`javap -p 'net/luckperms/api/track/PromotionResult$Status.class' | grep "public static final"`）。比查博客/问答可靠，一次 1 分钟。

## 11. demoted 标记：降级后抑制历史 APPROVED 判定

**现象**：currentGroup 判定「有 APPROVED builder 记录 → builder」，但 builder→member 降级后该记录仍在 → 玩家仍被判为 builder，降级"无效"。

**修复**：降级时写 `demoted: true`（permission.yml ranks 节），currentGroup 的 builder 判定加 `&& !hasDemoted`；**重新 approve（重新晋升）时 clearDemoted** 恢复 builder 判定。降级语义：每次降一级（builder→member→default），链底 no-op。

**测试**：`RankServiceTest.demote_builder_removesBuilderAndMarksDemoted` / `demote_default_noOpReturnsNull` / `currentGroup_demotedBuilder_returnsMember`。

## 13. Paper 26 jar 三层结构 + 反编译法（2026-08-13 实测）

- `paper-26.2-111.jar` = **paperclip 启动器壳**（thin，只有 libraries），**不是服务端**
- 真实服务端嵌套：`cache/mojang_26.2.jar` → `META-INF/versions/26.2/server-26.2.jar`（内层 jar）
- **反编译服务端类路径**：
```bash
cd /tmp && mkdir paperx && cd paperx
unzip -o -q ~/minecraft-server/cache/mojang_26.2.jar 'META-INF/versions/26.2/server-26.2.jar'
unzip -o -q META-INF/versions/26.2/server-26.2.jar 'net/minecraft/server/players/PlayerList.class'
javap -c -p net/minecraft/server/players/PlayerList.class   # 字节码
```
- ⚠️ **macOS `strings` 不兼容 class 文件**（报 `fat file: ... truncated or malformed`）→ 用 python 提取：
```python
import re; data = open('X.class','rb').read()
[str(s.decode()) for s in re.findall(rb'[\x20-\x7e]{5,}', data) if b'keyword' in s.lower()]
```
- **per-IP 5 在线限制**：`PlayerList.class` 字符串表**没有** `ip_limit`/`too many` key（被 Paper 重构，语言 key 移到别处），但**行为实测存在**（同 IP 第 6+ 被踢 `Sorry, there are too many players logged in with your IP address`）——验证行为用实测，别依赖反编译字符串

## 14. 审核命令 vs 管理命令职责边界（用户设计评审）

`$v` 本是 review 审核命令（l/y/n 裁决玩家申请），若混入 `$v d`（管理员主动降级，无申请流程）职责模糊。用户明确指出：**审核（对申请的裁决）与管理（管理员主动操作）语义不同**。设计取舍：① `$v` 扩展为完整权限管理（l/y/n + d + u 对称钳位）；② 审核与管理分命令；③ 管理操作只留游戏内命令。**先和用户确认方案再实现**，不要默认混在一起。
