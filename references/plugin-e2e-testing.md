# PaperMC 插件端到端测试方案调研

> **日期**：2026-08-06
> **来源**：web 调研（MockBukkit / WatchWolf / GameTest / Testcontainers）+ OrzMC 实战经验
> **结论**：PaperMC 插件 E2E 无"一键式"成熟方案；**MockBukkit 做底层逻辑 + 真实环境 E2E 做最终验收**是最实用组合。

## 方案总览（按层级）

| 层级 | 方案 | 核心思路 | 适合场景 |
|:--|:--|:--|:--|
| 单元测试 | MockBukkit | 内存 mock 整个 Bukkit API，无真实服务器 | 事件逻辑、命令解析、纯业务 |
| 服务器内集成 | WatchWolf | 启动真实服务器 + 连接真实客户端，编排测试 | 多服交互、协议级行为 |
| 原版测试框架 | GameTest Framework | Mojang 官方 `@GameTest`，结构内断言 | 方块/实体/世界交互 |
| 真实环境 E2E | 测试服 + 机器人/RCON | 生产同构环境，bot/RCON/真实玩家驱动 | 验收、插件互操作、跨服（OrzMC 采用） |
| 容器化 | Docker 测试服 | 一次性容器起服跑测试，CI 集成 | 持续集成、可重复回归 |

## 各方案详解

### 1. MockBukkit（最主流）
- **定位**：mocking 框架，JUnit + Hamcrest，**秒级跑完测试套件**
- **能力**：mock 服务器/玩家/世界，测事件、命令、玩家交互
- **资源**：github.com/MockBukkit/MockBukkit、docs.mockbukkit.org、mockbukkit.org
- **局限**：非真实服务器——调度器、网络、真实方块引擎是 mock 的；**协议层/跨服/性能相关测不了**
- **实战**：OrzMC 已有 `integrationTest`（MockBukkit，`./gradlew integrationTest` 需要 Java 25），但 transfer/传送门等真实服务器行为必须真机测

### 2. WatchWolf（集成测试框架）
- **定位**：Spigot 插件**集成测试**，一键拉起多服务器 + 自动连接客户端
- **能力**：编排 client + server 双向控制，测跨服/多玩家场景
- **资源**：github.com/watch-wolf/WatchWolf、spigotmc.org/resources/watchwolf.107051、watchwolf.dev/docs/testing
- **局限**：文档少、社区小（2023 年后活跃度低）、学习曲线陡
- **适配度**：概念上正是"双服 transfer 自动化测试"，但生态不活跃，OrzMC 用手动 E2E 达成同等目标

### 3. GameTest Framework（原版）
- **定位**：Mojang 官方，`@GameTest` 注解 + `GameTestHelper` 断言，**结构内**测试（方块/实体/世界）
- **局限**：**Paper 上不完整支持**（Paper 移除了部分 vanilla 测试钩子，主要面向 mod 平台 Forge/Fabric）；插件 API 交互（玩家、GUI、命令）覆盖弱
- **适合**：纯世界交互类插件（如 TNT 结构、传送门方块）

### 4. 真实环境 E2E（✅ OrzMC 采用，已实战）
- **架构**：测试服（production 同构）→ 驱动层（mineflayer bot + RCON + screen 注入 + 真实玩家）
- **实战成果**：28 项用例全过 + 双服 transfer 闭环 + 发现并修复 1 个 bug（详见 orzmc-acceptance-20260806.md）
- **优势**：**最真实**——插件互操作（LoginSecurity/Essentials/Geyser）、协议层行为（transfer）、性能影响全部覆盖
- **代价**：手动/半自动，需要运维脚本沉淀（已做：rcon.py / portal-cmd.js / portal-probe.js / portal-transfer-test.js）
- **关键脚本**：
  - `scripts/rcon.py` — RCON 控制台命令
  - `scripts/bot/portal-cmd.js` — bot 玩家身份执行 `/portal` 系列命令
  - `scripts/bot/portal-probe.js` — blockAt 扫描传送门方块
  - `scripts/bot/portal-transfer-test.js` — transfer 触发测试（mineflayer 位置同步限制已知）
- **验证通道**：主服日志可能停更（Paper 缓冲）→ 用 RCON 确认状态 + 第二服日志实时写入可查 transfer 痕迹

### 5. Docker 容器化（CI 友好）
- **定位**：Testcontainers 风格，CI 里起一次性 Paper 容器跑测试
- **局限**：Minecraft 插件生态**无成熟封装**（无官方 Testcontainers 模块），需自建 Dockerfile + 端口映射 + 等待就绪；资源占用高
- **适合**：有 CI 的团队项目做回归基线

## 推荐组合（OrzMC 现状）

| 层 | 工具 | 作用 | 状态 |
|:--|:--|:--|:--|
| 单元/集成 | MockBukkit（integrationTest） | 业务逻辑快测 | ✅ 已有，Java 25 |
| 验收 | 真实环境 E2E（bot+RCON+真实玩家） | 上线前最终把关 | ✅ 28 项 + 文档化 |
| 自动化双服 | WatchWolf（可选项） | 跨服场景自动化 | ⚠️ 生态不活跃，暂不引入 |

## 测试文档索引

- 功能测试用例（28 项）：插件仓库 `plugin/docs/test-cases.md`
- 端到端测试报告：插件仓库 `plugin/docs/e2e-test-report-20260806.md`
- 验收报告（技能内）：`references/orzmc-acceptance-20260806.md`
