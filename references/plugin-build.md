# 插件源码构建与开发（plugin-build）

> 合并自：minecraft-plugin-source-build + paper-plugin-development（2026-08-10 阶段一整合）
> 触发：需要从源码构建/修改插件 jar 并部署（自维护仓库、上游 bug 修复、PR 产物测试）。

## 构建工具选择（关键）

1. **确认构建工具**：`gradlew`（Gradle）/ `pom.xml`（Maven）
2. ⚠️ **两者并存时先看 git 近期提交**：项目可能从 Maven 迁移到 Gradle（如 LoginSecurity `migrate to papermc 26.2 and java 25` 只改 build.gradle.kts，pom.xml 是陈旧残留）。**陈旧 pom 编译必然失败**（`程序包 io.papermc.paper.event.player 不存在` 等 API 缺失 = 构建工具选错的信号，不是源码坏了）→ 改用 `./gradlew shadowJar`
3. **Maven 缺失**：清华镜像 `https://mirrors.tuna.tsinghua.edu.cn/apache/maven/maven-3/`（先查目录版本列表选存在的 3.9.x，如 3.9.16）

## 构建命令

- Gradle：`./gradlew shadowJar`（产物 `build/libs/`）
- Maven：`mvn clean package -Dmaven.test.skip=true`（**测试编译与 API 版本冲突时用 `-Dmaven.test.skip=true` 而非 `-DskipTests`**——后者仍编译测试代码）
- ⚠️ **产物名带版本号**（OrzMC-1.0.15-dev.jar → bump 后变 1.0.16-dev.jar）——部署前 `ls -la build/libs/*.jar` 确认**实际产物名+时间戳**再拷贝（一直拷贝旧文件名 = 部署旧 jar，无报错但改动无效，实测踩坑）
- Gradle toolchain 不匹配：build.gradle.kts 钉死版本（如 21）本机只有 JDK 25 → 改 toolchain 为 25（`options.release.set(17)` 保证字节码兼容）
- 部署确认 shaded 版（含依赖），否则运行时报 NoClassDefFoundError

## 部署（源码构建产物）

- **新装**：停服 → 删旧插件目录+旧 jar（不删目录则插件输出 "Skipping bundled default category files"，旧配置/语言不刷新）→ 放新 jar → 启动生成新配置 → 改配置 → 重启
- **升级（PaperMC update/ 机制）**：新 jar 放 `plugins/update/` → 重启自动替换（按插件名匹配）；**带版本号 jar 例外**：文件名不同 update/ 不生效 → 备份→删旧→新 jar 直放 plugins/

## 源码级修复工作流（paper-plugin-development 核心）

1. 查仓库：plugin.yml main 包名 → GitHub 搜；确认 MIT 协议 + 活跃
2. clone → 读源码定位（控制流图 `*.mmd`/`docs/` 往往直接暴露根因）
3. **先复现再修**：改代码前记录修复前基线，修复后同一条件验证消失
4. 编译 → 部署 → 回归验证（≥8 轮自动化，轮间 sleep 30 防登录冷却）
5. **提 PR 上游**：fork → fix 分支 → PR（描述含回归数据）→ 稳定后切 fork main 重提 → 关旧 PR 注明被取代
6. **发布流程（自家插件）**：feature/bugfix 走分支→PR→合入 main→**询问用户确认**→打 SemVer tag（不加 v）触发 Publish；误发版撤销 = `gh run cancel` + `git tag -d` + `git push origin :refs/tags/<ver>`

## 高频坑速查（详见各 references）

- **Paper 26.2 与 EssentialsX 2.22 不兼容**：unsupported server version + /spawn 未注册 + op 权限全拒；排查铁律：LP 权限即时生效 / Unknown=命令未注册≠权限问题 / 本地复现须同核心构建 / 优先回退核心到插件支持版
- **dispatchCommand 必须主线程**：异步线程调抛 `IllegalStateException: Asynchronous Command Dispatched Async`——runSync 回主线程
- **LP API 集成三连坑**（implementation→Provider 副本 NotLoadedException / compileOnly+旧 softdepend→ClassNotFoundException / `track.promote()` 必须 `saveUser().get()` 落库）→ references/luckperms-api-integration.md
- **LoginSecurity 拦截未登录玩家命令**（op 也不能免）：mineflayer 测试 spawn 后必须先 `/login <密码>`
- **mockStatic 泄漏**：每个测试 try-with-resources 包住
- **markAlwaysSave 配置停服后改**：运行中改会被关服保存的内存态覆盖
- **read_file 误判中文注释 .java 为 binary**：用 sed/grep 看
- 新增模板键 = 4 处注册清单 / 删除 = 8 处联动（见 paper-plugin-development 原 SKILL 或 references/orzmc-review-framework.md）

## 支持文件（references/）

- `ezshops-maven-build.md`：EzShops 构建（jaker macOS 大小写坑）
- `loginsecurity-build.md`：LoginSecurity 构建（Gradle 非 Maven、26.2 迁移）+ AuthModeChangedEvent name-null 报错与 null 防御修复
- `deathchest-fix.md`：DeathChest 修复案例
- `luckperms-api-integration.md`：LP API 直调（类加载三连坑/saveUser/AMBIGUOUS_CALL）
- `rank-lp-integration.md`：LP 晋升幂等（promoted 标记）
- `rank-status-display.md`：权限状态动态化
- `orzmc-review-framework.md`：通用审核框架 + 模板键注册
- `orzmc-review-acceptance.md`：审核框架验收
- `orzmc-e2e-robot-testing.md`：RCON+orzdebug+Mineflayer 自动化测试
- `orzmc-bot-command-testing.md`：Bot 命令测试
- `orzmc-entity-teleport-tnt.md`：实体传送/TNT
- `rank-playtime-data-source.md`：在线时长数据源（stats 文件）

## 脚本（scripts/）

- `rcon.py` / `rcon.js`：RCON 客户端（`$` 安全，node 原生实现）
- `check-death-chest.js`：死亡点箱子回归验证
- `regression-loop.sh`：多轮回归循环
- `stress-concurrent.js`：并发压测
- `fix_exaroton_cfg.py`：Exaroton 配置文件修复（JSON 包装）
- `templates/migrate_keys.py`：配置键迁移模板
