# AI 编码智能体协作（Claude Code）

> **工作流决策（2026-08-29 老板定）**：编程/改代码/改配置**直接交给本地 Claude Code**（专用编码智能体，DeepSeek anthropic 端点），Hermes 只做**编排**（任务拆分/规划/验收/测试/部署/git 推送/跨工具调度）。Hermes 不直接写业务代码。
> **Review 时机**：PR 仅在**最终决定合并前**做一次 code review（`git diff main...HEAD | claude -p '...'`），开发过程中不做（避免过多 review 消耗 token）。

## PR 合并流程（老板定，2026-08-29）

开发阶段只 commit 本地分支（不 push、不 review）→ 老板决定合并后：
1. **code review**（claude -p 一次）
2. **检查 PR 实际改动**（`git diff main...HEAD --stat` 核对，确认与 review 结论一致）
3. **更新 PR 标题/描述与改动匹配**（`gh pr edit`，覆盖全部 commit 内容）
4. **force push** 同步分支内容
5. **合并**（squash）

标题/描述更新必须在代码审查完成、确认实际改动之后做，避免描述与实际 diff 不符。

## 三种协作模式

| 模式 | 命令 | 适用 |
|:--|:--|:--|
| 一次性委派 | `claude -p '任务' --max-turns N --permission-mode acceptEdits` | 有界单次任务（改配置/改代码）|
| 交互式会话 | terminal background + pty=true，process submit/poll | 多轮迭代 |
| 代码审查 | `git diff main...HEAD | claude -p 'review...'` | 合并前审查 |

## 编排要点

1. **任务描述必须自包含**：文件路径、条目名、目标值、约束（只改 sell 不动 buy 等）、验证方式——子代理不知道对话上下文
2. **`--max-turns N` 限制**：防失控循环（改配置类 10 足够）
3. **`--permission-mode acceptEdits` 必带**（非交互模式默认不能写文件，否则产出零改动停在权限审批）；shell 验证命令也常被拦 → 验证/验收由 Hermes 编排层做
4. **子代理自报不可信**：委派后必须自己验收——`git diff` 核对 + YAML/语法验证 + 实际部署测试
5. **git 仓库上下文**：在对应 repo 目录运行，prompt 里给准相对路径
6. review prompt 要引导检查：漏洞路径/配置语义/漏网项，按严重级输出

## 坑

- 非交互 `claude -p` 无文件写权限 → 加 `--permission-mode acceptEdits`
- shell 命令（python3 验证等）会被会话权限拦 → 验收交给 Hermes
- 模型提示 `deepseek-v4-flash is not a model this version recognizes` 为已知提示，可忽略（auto-compact 按 200k 处理）；设 `CLAUDE_CODE_MAX_CONTEXT_TOKENS` 为真实窗口可消除
- Codex 已卸载；OpenCode 可随时装（provider-agnostic 备选）

## max-turns 耗尽续跑（2026-08-29 实测验证）

`--max-turns` 耗尽报错退出，但**会话完整保存**（~/.claude/projects/）→ 可恢复：

```bash
# 委派：固定 UUID（关键！否则耗尽即弃无法续跑）
UUID=$(uuidgen)
claude -p --session-id $UUID --max-turns 20 "任务..."
# 超时/耗尽后：--resume 同 ID 续跑（上下文完整保留，实测 DeepSeek 端点可用）
claude -p --resume $UUID --max-turns 20 "继续完成剩余部分"
# 循环：耗尽→resume→再耗尽→再 resume 直到完成
```

其他恢复方式：`claude -c -p "继续"`（最近 -p 会话）；`claude -p --bg` + `claude respawn <id>`（后台会话重启）；`--name <名>` 按名 resume；`--fork-session` 分支探索。

**规避优先**：任务拆小（每个 <10 轮）；prompt 直接给执行路径（「读文件→改→构建」，减少确认磨轮次）；max-turns 按复杂度给足（配置 15-20 / 代码调试 25-30）。
