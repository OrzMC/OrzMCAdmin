# 技能自检（每日 08:30 `orzmc-selfcheck`）怎么判绿，以及写文档的硬约束

`orzmc_selfcheck.py` 第 1 段会子进程跑 `scripts/skill_self_check.py`，判据：

- **死链**：SKILL.md 里 `references/x.md` 指向不存在的文件 → FAIL。
- **孤儿**：`references/` 下有文件没被 SKILL.md 引用 → FAIL。这是最容易自己造出来的红灯：新建
  `references/<topic>.md` 却忘了在同批给 SKILL.md 加一行索引。**新建参考文档与加索引必须同一次操作完成**。
- **超长行**（>1200 字符）：仅提示，不 FAIL，但会一直出现在每日报告里；写 CHANGELOG 行时别把整段设计
  说明塞进一行表格，细节放 references（本文件就是这类细节的落脚处）。
- **版本**：读技能目录里 `SKILL.md` 的 `version:`；改了内容不同步 bump，会看到「报告里的版本 ≠ 实际内容」
  这种错位（曾出现自检读到 `2.6.19` 而实际已 2.7.x —— 那是当天 SKILL.md 真的还没升，不是脚本 bug）。

## 改完技能文档后的自验顺序

1. 在技能根目录跑 `python scripts/skill_self_check.py`，要看到 `结果: PASS`、`死链: 无 孤儿: 无`。
2. 再跑整条 `python %LOCALAPPDATA%/hermes/scripts/orzmc_selfcheck.py`，确认第 1 段是 ✅ 而不是靠猜。
3. 之前那次的 `last_status=1` 不会自己消失 —— 它是 cron 记录的历史结果，要么等下一次 08:30 正常跑，
   要么 `cronjob_manage(action='run', job_id=<selfcheck>)` 立刻重跑一次把状态刷绿。

## 不要把「自检 FAIL」当环境问题

每日自检红的时候先看它引用的那个子进程输出：报「孤儿 / 死链」是文档问题（改文档），报「脚本不存在」
是脚本位置约定问题（`hermes/scripts/` 放 stub，真源在技能 `scripts/`），只有报容器/端口/磁盘才是环境。
同类内容出现在两个地方时（例如面板 API key 有两套读取口径），先记进报告再动，别在同一轮里既改脚本又改文档。
