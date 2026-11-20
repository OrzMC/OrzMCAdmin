# 技能发布流（B → 独立技能仓 → monorepo 子模块）

**当前形态**：技能有**自己的仓库** `OrzMC/OrzMCAdmin`（可独立迭代、独立打 tag），
monorepo `OrzMC/OrzMC` 以 **git submodule** 把它挂在 `.agents/skills/orzmc`。
**取代**：把技能当 monorepo 里的普通目录（历史混在 monorepo commit 里、无法独立发版）。

## 模型（三级）

```
B  本机技能目录（真实值，唯一真源）
   C:/Users/<u>/AppData/Local/hermes/skills/gaming/orzmc
        │  orzmc_publish.sh（镜像 + enc + leak gate + PR）
        ▼
SK 技能仓 OrzMC/OrzMCAdmin（占位符版，公开）   ← 独立版本线，打 tag vX.Y.Z
        │  gitlink 指针（.gitmodules）
        ▼
R  monorepo OrzMC/OrzMC 的 .agents/skills/orzmc（gitlink，不再跟踪文件内容）
```

- **单向**：只 B → SK，再 bump R 的指针。**绝不反向拉取**（SK 里是脱敏版，拉回会污染真实值）。
- B 是唯一真源；SK 是可公开发布的版本线；R 只是指向某个 SK commit。
- **代价要提前说清**：改一次技能 = 两步提交（技能仓 PR + 主仓 gitlink bump PR）。

## 发布

```bash
bash ~/AppData/Local/hermes/scripts/orzmc_publish.sh            # 建分支 + 开 PR（默认）
bash ~/AppData/Local/hermes/scripts/orzmc_publish.sh --merge    # 等 CI 绿后 squash 合并 + bump 主仓指针
bash ~/AppData/Local/hermes/scripts/orzmc_publish.sh --status   # 只看差异，不提交
```

**`--merge` 的前置条件：monorepo 必须在 `main` 上。** 脚本先合并技能仓 PR、打 tag，最后才 bump 主仓指针；
若主仓停在别的分支（例如刚开完一个 deploy bump PR），第三步会被跳过，回显只有一句
「⚠️ 主仓在分支 X，先切回 main」——**这不是失败**，技能仓 PR 与 tag 都已成功，别重跑整轮。收尾三步：

```bash
cd E:/dev/OrzMC && git checkout main && git pull --ff-only
git submodule update --init -- .agents/skills/orzmc
cd .agents/skills/orzmc && git fetch -q --tags origin && git checkout -q vX.Y.Z && grep -m1 '^version:' SKILL.md
```

再 `git add .agents/skills/orzmc` → 单独一条 bump PR。回读用 `git ls-remote --tags origin vX.Y.Z`
确认远端 tag 指向的技能仓 commit 与 `git ls-tree` 的 gitlink 一致，别只信脚本末尾的 ✅。

脚本变量：`ORZMC_SKILL_REPO`（技能仓克隆）默认 `E:/dev/OrzMCAdmin`，
`ORZMC_PROJECT_DIR`（monorepo）默认 `E:/dev/OrzMC`，子模块路径 `SUB=.agents/skills/orzmc`。

**bump 指针前必须确认 `SUB` 真是 gitlink**：`git ls-tree HEAD -- .agents/skills/orzmc` 的模式应是 `160000`。
若它还是普通目录，`git submodule update --remote` 静默 no-op，而 `git add -- <SUB>` 会把工作区里残留的镜像差异
当「指针变化」提交出去，产出一个只改了 1–2 个文件、看起来像 bump 实则没动子模块的 PR。
守卫写法：模式不是 `160000` 就 `return` 并提示先做 submodule 化。

## 镜像白名单必须覆盖「所有现存扩展名」

拷贝是按扩展名白名单来的（`references/*.md`、`templates/*`、`scripts/*.sh|*.py|*.js`、
子目录各自的规则）。**白名单漏一种扩展名 = 那类文件永远进不了仓，且没有任何报错**——
真实踩过：`scripts/*.ps1` 从未被同步，本机 4 个 PowerShell 脚本长期只在 B 存在。

纪律：新增或发现新扩展名时，先 `find <B> -type f | sed 's/.*\.//' | sort | uniq -c` 列出 B 的全部扩展名分布，
逐项对照白名单补齐；**不用「文件数变多了」当判据**，因为镜像前后数量差永远对不上白名单盲区。

## 脱敏规则（enc）

真实值 → 占位符，规则在脚本 `ENC_RULES`：域名 `{SERVER_HOST}`、仓库名 `{SERVER_NAME}`、
内网 `{LAN_IP}`（含 `192.168.0.<x>`）、机器人密码 `{BOT_PASSWORD}`、API `{API_TOKEN}`、邮箱 `{EMAIL}`。
公网 IP：家宽 WAN → `{HOME_IP}`、云主机 → `{CVM_IP}`，**按 IP 段前缀写成正则规则，不靠发布前手改文档**。
只对**完整公网 IP 形态**写规则：四段数字通配会命中插件版本号（`3.26.11.2`）造成日常误杀。

判据：**enc 是黑名单，leak 门禁只能证明「黑名单里的没漏」**。新增一类敏感值时先补 `ENC_RULES` 再发布。

### 门禁中止了怎么办

leak 门禁中止发布是**设计行为，不是故障**。处理顺序固定：

1. **不要**改本机真源里的值（B 必须保留真实域名/IP 才能操作服务器）。
2. 从门禁输出认出被拦的值，判断类别（域名 / 内网 / 家宽 WAN / 云主机 / 密钥）。
3. 在 `ENC_RULES` 补一条**按网段前缀**的规则，重跑 `--status` 确认差异里只剩占位符。
4. 发布后回仓库 `grep -rn "<该值>" <SUB>` 必须为空，`grep -rl "{HOME_IP}\|{CVM_IP}"` 有命中才算真落地。

**已进 git 历史的真实值不会因新规则消失**：规则只作用于本次产物的文件内容。清历史要改写 commit + `force push`，
成本大于收益（家宽 IP 本身会变）→ **明确告诉老板「历史里那条还在，要不要清」**，由他拍板；
不要默默 force push，也不要假装已清干净。

## 改技能目录成子模块（一次性迁移）

```bash
cd E:/dev/OrzMC
git switch -c chore/skills-submodule
git rm -r -q .agents/skills/orzmc                 # ① 从索引移除 276 个跟踪文件（内容已在技能仓）
git submodule add https://github.com/OrzMC/OrzMCAdmin.git .agents/skills/orzmc   # ② 变成 gitlink
git commit -m "chore: 技能目录改子模块" && git push -u origin HEAD
```

- ① 属**破坏性审批门**（`git rm -r`），老板常不在跟前：**先说明这条会删什么、内容已在技能仓哪条 tag，再请他审批**；被拦就停下等，
  **不要用 `mv`＋删除等变相写法绕过去**——那等于绕过用户对「删 276 个受跟踪文件」的知情同意。
- 迁移前必须确认技能仓 `main` 的最新 commit 就是 B 的当前内容（版本号 + 文件数对得上），否则 gitlink 指向的是旧技能。
- 迁移后同步改三处文字：`.gitmodules`、`AGENTS.md` 的技能小节（路径与「改技能走 PR」规则）、`.agents/skills/README.md`（原写「OrzMCAdmin 已退役」必须改掉），
  以及本技能里所有写「技能是普通目录」的句子。
- **`AGENTS.md` 第 4 章登记表必须同步加一行**（路径 / 仓库 / 分支 / 性质 / 职责 / 子模块 AGENTS）。
  `scripts/verify/check.py` 会硬校验「`.gitmodules` 里每个子模块都在登记表里」，漏了 CI 直接红：
  `##[error]AGENTS.md 登记表缺少子模块：['<path>']`。所以 submodule add 之后第一件事就是补表，否则白等一轮 CI。
  登记表在 §4，表格末行追加即可；`AGENTS.md` 是**受保护文件**，改它要审批（弹窗超时就停下请老板重批，别绕路）。
- gitlink 只有一步能不能成，取决于技能仓 `main` 上是否已有内容：`.gitmodules` 先有、登记表后补，是**同一次 PR** 内完成的两件事。
- 迁移 PR 合并后**回 main 常被旧目录挡住**：`git rm`+`submodule add` 之后，父仓库把子模块工作树里的内容看成 untracked，`git switch main` 报「untracked files 会被覆盖」。正解 `mv .agents/skills/orzmc <scratch>` → `git switch main` → `git pull --ff-only` → `git submodule update --init -- .agents/skills/orzmc`，最后清掉那份临时目录。
- 之后 clone 主仓要 `git submodule update --init`，否则 `.agents/skills/orzmc` 是空目录。

## 发布后回读（不看回显）

1. `gh pr view <n> --json state,merged,mergeCommit` —— **`state: CLOSED` + `merged: true` 是成功的 squash 合并**，
   不是被否决；只看 `state` 会把已合并的 PR 误读成「关掉了」。`gh pr list --repo` 在某些仓返回空属 CLI 行为差异，
   查 PR 一律用 `gh api repos/<owner>/<repo>/pulls?state=all`。
2. 合并后打 tag（技能仓这条版本线才是真正的版本锚点）+ 本地 `git switch main && git pull --ff-only`
   （squash 合并后本地 main 会 diverged，属正常）。
3. 清 `chore/skill-sync-*` 本地分支：`git branch -D` 属审批门 → **回读确认主分支与工作树干净即可**，
   别为删分支把整轮验证卡死。

## 仓库侧约定

- `.agents/skills/README.md`：目录约定与 `hermes skills trust` 用法。
- `AGENTS.md` 技能小节：真实值禁止入库、改技能走 PR、技能的真源与子模块关系。

## Hermes 侧

- 首次需信任仓库：`cd E:/dev/OrzMC && hermes skills trust`（写进 `config.yaml` 的 `skills.trusted_project_dirs`）。
- 载入优先级：**项目技能 > 个人 `~/.hermes/skills/` > external_dirs**；同名时仓库版覆盖本机版。
  `hermes skills list` 只列已安装技能，**不显示**项目技能，别用它判断是否生效。

## 已退役

- `orzmc_bisync.sh`（双向镜像）：方向已改为单向发布，勿再用。
- ~~`OrzMC/OrzMCAdmin` 已退役~~ **该结论作废**：技能仓已复活为主线仓库（见上），文档里凡写「只作历史存档」的地方都要改。
