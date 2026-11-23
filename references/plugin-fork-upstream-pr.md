# 第三方插件 fork 维护与上游 PR

适用：`tools/<plugin>` 这类自带 fork 的第三方 Bukkit/Paper 插件——修 bug、跑测试、判断 fork 与上游差异、给上游提 PR、bump 子模块指针。

## 1. 先把三方关系钉死

- 链路：`E:\dev\OrzMC`（monorepo，只存子模块指针）→ `OrzMC/<plugin>`（fork）→ 上游作者仓库。
- `git submodule update --init tools/<name>` 后子模块通常处于 **detached HEAD**，别在那个状态下 commit / push main（`push origin main` 会返回 Everything up-to-date 骗人）。先建分支。
- fork 关系不要从 README 推断：`gh api repos/OrzMC/<name> --jq '{fork,parent:.parent.full_name,default_branch}'`。
- 浅克隆下的 `git rev-list --count HEAD..upstream/main` 不可信，先 `git fetch --unshallow upstream main` 再数。
- 判断上游是否真的在动：`gh api repos/<up> --jq .pushed_at`。「同步上游最新」很多时候是 no-op，要明确告诉用户“上游落后 0 提交”，而不是含糊说已同步。

## 2. 构建与测试（Maven / Windows git-bash）

- 机器上不一定有 mvn：下 `apache-maven-*-bin.zip` 解压到 `E:\deploy\tools`，用包装脚本调用：`java -classpath "$M/boot/plexus-classworlds-*.jar" -Dclassworlds.conf="$M/bin/m2.conf" -Dmaven.home="$M" org.codehaus.plexus.classworlds.launcher.Launcher "$@"`。**`m2.conf` 在 `bin/` 不在 `conf/`**；git-bash 下自带 `mvn` 脚本算不出 MAVEN_HOME，直接调 java 最稳。
- **必须带 `clean`**：`target/` 里按旧 `paper.version` 编出的 class，换版本后会以 `IncompatibleClassChangeError: Found interface X, but class was expected` 炸在 GUI/事件测试里——看着像代码 bug，实际是残留类。
- `paper.version` 要显式指定：pom 默认值常落后于 MockBukkit 版本，表现为测试编译报找不到 `io.papermc.paper.datacomponent.DataComponentType` 之类的新 API 类。取值从 `.github/workflows/ci.yml` 的 unit-tests job 抄（例如 `1.21.11-R0.1-SNAPSHOT`）。
- 标准命令：`mvn -B -ntp -Dpaper.version=<ver> clean test`。
- **基线对照**：`git worktree add <tmp> upstream/main` 起一个纯净 worktree 跑同一条命令。测试红了先问“是不是环境/版本”，再问“是不是我们的改动”。
- 控制台编码是 GBK：日志重定向到文件后，用 Python `raw.decode('gbk', errors='replace')` 再筛 `Tests run:` / `BUILD` / `COMPILATION ERROR`；直接 grep 会报 `Binary file matches`。

## 3. 差异盘点与 PR 拆分

- `git log --oneline upstream/main..HEAD` + `git diff --stat upstream/main..HEAD`，把提交分三类：**自用业务改造**（改价、改样例、换 storage/game-mode）、**通用 bug 修复**、**本地化**。
- 只有通用 bug 修复能提上游；业务改造混进 PR 等于让维护者替我们做取舍。
- 拆分：从 `upstream/main` 拉分支再 `git cherry-pick -x <sha>`。修复被夹带在大提交里时，用 `git checkout <fork-main> -- <file>` 取整文件最终态——前提是先 `git diff upstream/main <fork-main> -- <file>` 确认该文件的差异是**纯新增**。
- 每个分支单独跑相关测试（`-Dtest='*Transaction*'`、`-Dtest='MessageFilesDuplicateKeyTest'`）再 push。
- `*IT` 集成测试常年红（要 DB/存储），先查是不是已有 issue 登记的已知问题，别背到自己身上。

## 4. 提 PR / 回帖

- `gh pr create --repo <up> --base main --head OrzMC:<branch>`——跨 fork 的 head 必须带 owner 前缀。
- 正文结构：现象 → 根因 → 改动（按文件）→ 复现与测试结果（贴 `Tests run: N, Failures: 0, Errors: 0`）→ 已知无关失败。
- 用 `Fixes #N` 关联 issue；PR 没有对应 issue 就先建一个，否则合并时不会自动关闭。
- 查状态：`gh pr view <n> --json state,mergeable,mergeStateStatus`。`MERGEABLE` + `BLOCKED` = 只差维护者审查——我们对上游通常只有 `pull` 权限（`gh api repos/<up> --jq .permissions`），永远合不了，别答应“我来合并”。
- **删了头分支的 PR 无法 reopen**，只能推分支开新 PR；先 `gh api repos/<fork>/branches/<branch>` 确认分支还在。
- 关掉的 PR / 悬挂的 issue：用 timeline API 查 `closed` 事件的 actor，先分清是维护者拒的还是自己关的，再决定要不要重提。

## 5. 子模块指针 bump

- monorepo 里只 `git add tools/<name>`，提交 `chore(tools): bump <name> → <sha>`，走 PR（main 受保护）。body 写清这个 SHA 里修了什么。
- 合并后校验：`gh api repos/OrzMC/OrzMC/contents/tools/<name>?ref=main --jq .sha` 应等于目标 SHA。
- 指针 bump 与 fork 侧修复是两个动作：先合 fork（或 PR #4 那种 squash 后的新 main），再 bump，顺序不能反。

## 6. shell 引号坑

- `gh issue comment --body "含 \`反引号\` 的正文"`：bash 会把反引号当命令替换执行，正文被吞词。**带反引号或多行的正文一律写文件用 `--body-file`**，或 Python `subprocess` 传参。发完用 `gh api .../comments --jq` 读回确认没被截断。

## 7. `git status` 里的 `M plugin` 不一定是脏数据（2026-11-23 定论）

`E:/dev/OrzMC` 显示 `M plugin` 时先分辨两种情况，别急着「对齐回记录指针」：

| 现象 | 含义 | 处置 |
|:--|:--|:--|
| 本地 plugin 在 **`develop`** 分支，gitlink 记的是 plugin **`main`** 的 SHA | 正常开发态：开发线比发布线新，主仓指针本就该指向 main | **留着**，等 plugin 自己的 develop→main 里程碑再 bump 指针 |
| 本地 plugin 有 **未推送提交**或工作区脏 | 真正的未同步工作 | 先推 fork / 提 PR，再 bump |

判定命令：`git -C plugin rev-parse --abbrev-ref HEAD` + `git -C plugin branch -r --contains HEAD`（若 HEAD 在 `origin/develop` 上，说明提交已进仓，只是没进 main）。

**老板 2026-11-23 决策**：保持 `develop` 检出，不做 `--detach` 对齐 —— 对齐会让 monorepo 构建悄悄用旧插件版本，反而更难查。

