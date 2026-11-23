# EzShops（tools/EzShops 子模块）构建与测试

## 环境

本机无 `mvn`，已放 Maven 3.9.16：`E:\deploy\tools\apache-maven-3.9.16`，
包装脚本 `E:/deploy/tools/mvnw-here.sh`（git-bash 下 `bin/mvn` 算不出 MAVEN_HOME，
直接 `java -classpath boot/plexus-classworlds-2.11.0.jar -Dclassworlds.conf=bin/m2.conf`）。

## 唯一能跑通的命令

```bash
cd /e/dev/OrzMC/tools/EzShops
bash /e/deploy/tools/mvnw-here.sh -B -ntp -Dpaper.version=1.21.11-R0.1-SNAPSHOT clean test
# → 368 tests, 0 failures, 0 errors, 2 skipped, BUILD SUCCESS
```

## 三个坑（顺序踩过）

1. **必须指定 `-Dpaper.version=1.21.11-R0.1-SNAPSHOT`**：pom 默认 `1.20.4-R0.1-SNAPSHOT`，
   与 `mockbukkit-v1.21` 4.101.0 不兼容 → 测试编译报 `找不到 io.papermc.paper.datacomponent.DataComponentType 的类文件`。
2. **必须带 `clean`**：换 paper 版本后增量编译会留下旧类，实测出现 8 个 GUI 测试
   `IncompatibleClassChangeError: Found interface org.bukkit.inventory.InventoryView, but class was expected`
   —— 是上次按 1.20.4 编出的 `target/` 残留，不是代码 bug。
3. **JitPack 依赖 POM 坏**：`com.github.EzFramework.Jaker:1.0.7` 及其子模块 POM 有 parent 循环，
   Maven 打一堆 `[ERROR] Invalid packaging` / `[FATAL] parents form a cycle`，属**可忽略警告**，构建仍继续。

## 已知与本仓库无关的失败

`JaloquentTransactionRepositoryIT` 3 errors（`StorageException: Failed to find model` /
`DataSourceJdbcStore does not support flat-map operations`）= 上游 issue #84，默认 `test` 阶段不跑 IT。

## 输出编码

Maven 输出是 GBK，git-bash 里直接 grep 会「Binary file matches」或乱码，
落盘后用 python `raw.decode('gbk')` 再过滤。

## 打包给测试服

```bash
bash /e/deploy/tools/mvnw-here.sh -B -ntp \
  -Dpaper.version=1.21.11-R0.1-SNAPSHOT -DskipTests clean package
# → target/EzShops-2.5.9.jar（target/original-*.jar 是没 shade 的中间产物，别部署）
```

打包后先自查 jar 内资源（zipfile 直接读，不用解压）：`shop/smp/categories/daily_specials.yml`
里 `premium_pick:` 后必须紧跟 `slot: 24`，`messages/*_zh.yml` 行数应 >400 且抽样是中文 ——
资源文件没进 jar 是只改 `src/main/resources` 时最常见的漏。(部署与重启见
`references/mcsm-instance-jar-restart.md`)

## 提上游 PR：先拆干净再开分支

fork 里混着**自用改动**（smp 经济压价、storage/game-mode、样例调价），它们绝不能进上游 PR。
可靠做法是**按文件边界**从 `upstream/main` 拉分支，再从 fork 上整文件检出：

```bash
git checkout -b fix/<topic> upstream/main
git checkout <fork-main> -- <与该修复有关的 1~3 个文件>   # 整文件覆盖，只含该修复
git -c user.name=<user> commit -m "..."
```

前提是先用 `git diff --stat upstream/main <fork-main> -- <目标文件>` 确认这些文件里**只有**
我们的新增（纯增量才好整文件搬）；若某文件同时含自用改动，改用 `git cherry-pick -x <commit>`
并检查是否夹带。`git merge-tree --write-tree upstream/main <commit>` 可先判能否干净合并。

两个分支各带自己的测试类（新测试通常和修复同一个提交，无需单独挑）。每个分支单独跑
`-Dtest='<相关测试>' clean test`，别拿全量结果顶替。

## 部署到测试实例

停/启实例的纪律见技能 `mcsm-instance-ops` §4 —— 核心一条：**`docker restart MCSM-<前6位>` 不是重启，
是停服**（容器随即被回收），重启只走 `protected_instance/restart`；容器真的没了就 `docker restart
<daemon容器>` 让 daemon 按运行态重建。

本插件部署后必查三项：

1. **容器内哈希 = 本机产物**：`docker exec MCSM-<前6位> md5sum /server/plugins/EzShops-<ver>.jar`
   与本机 `md5sum target/EzShops-<ver>.jar` 一致；多实例逐个比（漏拷一个只会在玩家反馈里暴露）。
2. **新 jar 不覆盖现场配置**：启动日志应有 `Skipping bundled default category files for existing mode
   directories:`，且运行时 `shop/` 下文件 mtime 保持旧值 —— 有它说明没被 jar 内样例顶掉；真被覆盖就
   用部署前打的 shop tgz 还原。
3. **加载行**：`EzShops (smp mode: shop/smp/, shop/, shop.yml): Shop configuration loaded: N item(s)`，
   且**没有** `Ignoring item 'rotations.…' because slot -1 is outside the menu bounds`。

部署前备份两样：旧 jar（`.bak-<YYYYMMDD>`）+ 整个 `plugins/EzShops/shop/` 打包；回滚 = 换回两者再重启。
插件会自动释放样例配置，但**只在首次**——运行时目录可能是很久以前的拷贝，判「配置是被谁改坏的」
必须把「jar 内资源」和「运行目录」分开看。

## 上游位置

上游 `ez-plugins/EzShops` 长期无新提交，我们对它只有 read 权限、维护者响应很慢 ——
这是常态而非意外：**修复先落在 fork，上游 PR 当成“顺手提交、可能长躺”**，不要为了等合并
而推迟自己的发版。提 PR 时顺手把正文补上 `Fixes #<issue>`（issue 先建，标题用 `[Bug] …`，
正文给代码定位 + 复现步骤 + 影响面），合并时会自动关。
