# 入口探针 / 周巡检 运维手册（分层判定 + 退出码 + 三态自测）

> 适用：本机 Windows Hermes 上的 `orzmc_entry_probe.py`（cron `orzmc-entry-probe`，30m）与
> `orzmc_weekly_patrol.py`（cron `orzmc-weekly-patrol`，周一 09:15）。两脚本都在
> `%LOCALAPPDATA%\hermes\scripts\`，状态/日志在 `%LOCALAPPDATA%\hermes\{state,logs}\`。

## 1. 探针检查项与「三层」语义

入口链路有层级，告警措辞必须落在正确的那一层，否则老板会去查错东西：

| 层 | 检查 | 红了的含义 | 正确措辞 |
|:--|:--|:--|:--|
| **引擎层** | `docker inspect` 两个入口容器 | Docker Desktop / WSL2 挂了 | 「Docker 引擎不可用 —— 容器与端口全部无法核实」**只报这一条**，跳过其余检查 |
| **入口层** | `orzmc-velocity` / `orzmc-caddy` 状态、Java 25565 状态包、NetherNet `GET /v1/join`、网页 18443（TLS+SNI，期望 404 且 `Server: EaglercraftXServer`） | 玩家真的进不来 | 「入口/通道不可用」 |
| **后端层** | `docker ps -a` 查 `MCSM-716c2f` / `MCSM-8A932D` 容器状态；running 才打 RCON 25575/25576 | 实例没起（`autoStart=false`，老板要人工启动） | 「后端 xxx 实例 容器状态 stopped/missing（面板手动启动）」——**不要**把 RCON 的 ConnectionRefused 说成入口故障 |

要点：
- 引擎层不可用时若继续往下探，会得到 6–7 项全红（同一根因），一屏噪音掩盖真信息 → **先判引擎、后判端口**。
- 实例容器 `missing` 是**正常形状**：MCSManager 以 `--rm` 跑实例，停服即删容器（见 `docker-service-lifecycle.md` §3）。所以「`docker ps -a` 里连容器都没有」≠ 被误删，只说明实例未运行。
- `docker inspect` 超时要短（12s 一档）；两处都超时就按引擎层处理，别把 cron 一次跑成 30s+ 的挂起。

## 2. 退出码纪律（no_agent 脚本通用）

| 情形 | 退出码 | 后果 |
|:--|:--|:--|
| 全绿 / 检出业务故障（已投递告警） | **0** | cron 保持绿色，`failure_streak` 不累积 |
| 脚本自身异常 | **2**（`guarded_main()` 打 traceback 前 800 字） | cron 记 error —— 这才是「任务坏了」 |

反例：发现故障就 `return 1` → cron 记 `last_status=error / Script exited with code 1`、`failure_streak` 累加，真故障时反而看不出任务本身是否健康。

状态文件约定（`state/orzmc_entry_probe.json`）：`{fails: [...], last_alert: ts}`；只在「故障集合变化」或「距上次告警 > `REALERT_SECONDS`（6h）」时说话，恢复时发一条 ✅ 并清空。

## 3. 三态自测（改完探针必跑，不碰真实状态）

monkeypatch + 临时 `STATE`/`LOG`，四条路径一次覆盖：

```python
import os, tempfile, io, contextlib
import orzmc_entry_probe as p
d = tempfile.mkdtemp(); p.STATE = os.path.join(d,'s.json'); p.LOG = os.path.join(d,'l.log')

# ① 引擎层：容器探测返回 docker 超时 → 应只有一条「Docker 引擎」
p.container_running = lambda n: (False, "docker 调用失败: TimeoutExpired")

# ② 后端层：容器 stated 非 running → 应报「后端 xxx 实例 容器状态 stopped」
p.container_running = lambda n: (True, "running"); p.instance_containers = lambda: {"paper":"stopped","folia":"stopped"}

# ③ 恢复：全部 mock 成通 → 应输出 ✅ 并清空状态
p.instance_containers = lambda: {"paper":"running","folia":"running"}; p.rcon = lambda *a, **k: (True, "ok")

# ④ 崩溃：让某个检查抛异常 → guarded_main() 返回 2
```

同一脚本连跑两遍必须「第二遍静默」（去重生效）。验证完删掉临时目录即可，真实 `state/` 不受影响。

## 4. cron 结果核对（别只看上次输出）

```bash
cd "$LOCALAPPDATA/hermes" && PYTHONPATH="" python -c "
import json; d=json.load(open('cron/jobs.json',encoding='utf-8'))
j=[x for x in (d['jobs'] if isinstance(d,dict) else d) if x['id']=='f198dd2a7e95'][0]
for k in ('last_status','failure_streak','last_run_at','next_run_at','last_error','last_delivery_error'): print(k,'=',j.get(k))"
```

- 关注 `last_status` / `failure_streak` / `last_delivery_error`（投递失败也会留在这里），`next_run_at` 空才是调度停了。
- 让调度器立刻跑一轮并刷新状态：`cronjob_manage(action='run', job_id=...)`，跑完 `last_status=ok / failure_streak=0` 即修复确认。

## 5. 停机事故的取证顺序（Docker Desktop 掉线这类）

1. `docker ps -a --format '{{.Names}}|{{.Status}}|{{.RunningFor}}'` —— 谁回来了、谁没回来。
2. 实例日志判「正常停机 vs 崩溃」：`logs/latest.log` 尾部出现 `Saving all player data` + `All RegionFile I/O tasks to complete` + `Awaiting termination of worker pool` = **优雅停机，数据安全**；出现栈/`OutOfMemory` 才是崩溃。
3. Docker 侧时间线：`%LOCALAPPDATA%/Docker/log/vm/init.log*` 的轮转时间戳 ≈ VM 重启时刻；`powershell -c "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"` 与 `Get-Process 'Docker Desktop' | select StartTime` 用来排除「整机重启」这个错误假设。
4. 结论要分层写清：入口是否全绿 / 后端是否在跑 / 数据是否安全，然后**问老板要不要手动拉起实例**（不自动拉起是老板的明确要求）。
