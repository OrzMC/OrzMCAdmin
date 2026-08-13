# Git 子模块全量同步（Monorepo Submodule Sync，2026-08-11 从 git-submodule-sync 技能合并）

> 场景：同步 OrzMC monorepo（~/OrzMC，**15 个子模块**，2026-08-13 deploy 目录拆分新增 OrzMCDeploy）父仓库及全部子模块到最新并切换 main/master 分支。

## 触发场景
- 用户要求同步父仓库 + 所有子模块到各自默认分支（main/master）并拉最新
- 发布正式版/合并 PR 后，子模块指针需要跟进

## 标准流程

```bash
# 1. 父仓库
cd ~/OrzMC && git pull --ff-only
# 2. 新挂载的子模块（父仓库 pull 出现 create mode 160000）需先克隆：
git submodule update --init --recursive
# 3. 全部子模块：探测默认分支 → 切换 → pull
git submodule foreach 'bash /tmp/sync_one_sub.sh'
```

`sync_one_sub.sh`（foreach 注入 `$name`/`$sm_path`，在子模块目录内执行）：
```bash
DEF=$(git ls-remote --symref origin HEAD | head -1 | awk '{print $2}' | sed 's|refs/heads/||')
[ -z "$DEF" ] && DEF=main
CUR=$(git branch --show-current)
[ "$CUR" != "$DEF" ] && git checkout "$DEF" -q
git pull --ff-only -q
echo "  $name → $DEF @ $(git rev-parse --short HEAD)"
```

## 要点与坑

- **子模块数会变**：2026-08-13 父仓 pull 出现大量 `delete mode ... deploy/docker/*` + `Submodule 'deploy' registered` = **deploy 目录拆成独立子模块**（OrzMCDeploy），14→15；以后父仓结构变动以 `git submodule update --init --recursive` 输出为准
- **同步前先检查子模块未提交改动**：父仓 `git status -s` 出现 `m <子模块>` = 该子模块有未提交改动 → 先 `git -C <子模块> stash push -m "..."` 再同步（2026-08-10 实测：LoginSecurity 的 WIP patch 不 stash 会与后续 checkout/pull 冲突）；同步完成后再 `git stash pop` 恢复
- **子模块代码改动必须「先合并子模块 main，再 bump 父仓指针」（2026-08-13 实测翻车教训）**：子模块（如 plugin）有**独立 origin 仓库**（OrzMCPlugin.git）与自己的 CI/Hangar 发布基线。正确流程：① 子模块仓库合并/发 PR → ② 根仓库 bump 指针 → ③ 根仓库 PR。**漏掉第①步**（只做根仓库指针 PR）会让子模块 main 落后：改版不在发布基线，后续开发分支冲突。修复：`git -C <sub> merge --ff-only <sha>`（先 `merge-base main <sha>` 确认 main 是祖先）+ `git push origin main` + 删远程 feat 分支 + 验证 `git rev-parse HEAD` == `git rev-parse HEAD:<sub>`（父仓 gitlink 与子模块 HEAD 一致，`git submodule status` 无 `+` 前缀）。（反向场景：子模块 PR 被 merge 后 main 前进，GitHub 不自动更新父仓指针 → `git add <sub> && git commit "chore: bump..." && git push`，先 `git pull --ff-only` 防重复 commit）
- **GitHub merge 自动删远端源分支**：PR 合并后远端 fix 分支已被自动删除 → `git push origin --delete <branch>` 报 `remote ref does not exist` 是**无害确认**（远端已无），本地 `git branch -D` 清理即可
- **submodule status 无 +/- 前缀 = 与 gitlink 一致（正常）**：`(1.0.16-6-g2188e37)`/`(v0.1.6)` 是 describe 格式描述（tag 之后的提交），**不是 detached 问题**——只有 `+`（漂移）/`-`（未初始化）才需要处理
- **默认分支不统一**：OrzMC 14 个子模块实测 12 个 main + **2 个 master**（tools/LoginSecurity、tools/thanos）——用 `ls-remote --symref origin HEAD` 探测，**别假设全是 main**
- **子模块指针可能停在 tag**（如 OrzMCBackup 在 `v0.1.6`）——同步时切回默认分支（main）
- **父仓库 status 出现 `? <子模块名>` 类未跟踪**：通常是已删 gitlink 的子模块工作区残留目录（实测 app/OrzMCKit）——`git -C <子模块> status` 确认 `??` 后清理，无需动父仓库
- 子模块内 git 操作（checkout/pull）在父仓库视角可能显示 `M <子模块>`（指针漂移）——同步脚本已切回默认分支即一致

## 发布后指针同步（防重复 commit，2026-08-09 实测）

- 用户发布正式版（打 tag + CHANGELOG + `chore: bump version`）时，**发布者会自行提交父仓库的 plugin 子模块指针**
- 本地再手动 `git add plugin && git commit` 会产生重复 commit，直接 `git push` 被 non-fast-forward 拒绝
- **正解**：`git pull --rebase` → 重复 commit 自动 drop（日志 `dropping <sha> ... -- patch contents already upstream`）→ `git push` 显示 `Everything up-to-date`
- 即：**子模块指针同步不要抢先 commit，先 pull --rebase 看是否已被上游包含**

## 验证
- `git submodule status`：全部 `(heads/main)` 或 `(heads/master)`，无 tag/detached
- 父仓库 `git status` 干净（或只剩已知残留）
- `git -C <子模块> log --oneline -1` 与远端一致

## 列出非 main/master 本地分支（用户常要求）
```bash
# 父仓库
git branch --format='%(refname:short)' | grep -vE '^(main|master)$'
# 全部子模块（foreach 注入 $name；空=无额外分支）
git submodule foreach 'echo "  $name: $(git branch --format="%(refname:short)" | grep -vE "^(main|master)$" | tr "\n" " ")"' 2>/dev/null | grep -vE '^  .*: $'
```

## 分支清理：squash 合并后的内容归属判断（2026-08-10 实测）
feature 分支 squash 合并进 main 后，`git log main..<branch>` 仍把分支提交显示为「未合并」（**hash 不同是假象**）——判断内容是否真在 main，**别用 git log**：
```bash
# 分支有而 main 没有的文件（空 = 内容已全部合入，可安全删分支）
git diff main <branch> --name-status | grep '^A'
# 抽查关键文件是否在 main（如 src/main/java/.../features/rank/ 存在 = 功能已合）
ls <关键目录>
```
- 删除前先确认远端无同名分支：`git branch -r | grep <name>`；删除用 `git branch -D`（强删需用户确认）
- 分支删除后提交对象仍在 git 对象库（`git cat-file -t <sha>` 仍返回 commit）——找回可用 reflog/对象库，无需恐慌

## 关联
- OrzMC monorepo 资产地图（各子模块用途）→ `references/orzmc-repo.md`
