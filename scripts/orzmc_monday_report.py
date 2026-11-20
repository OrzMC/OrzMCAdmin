#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OrzMC 周一总报告聚合器 v2（no_agent，每周一 09:15）

v1：三段原始输出直接拼接 → 6.1KB，重点埋在表格里。
v2（老板要求「再结构化、条理清晰、尽量简洁」）：
  正文只出浓缩摘要 —— 结论一览 + 待办 + 运行态/版本/配置三张小表；
  三段完整输出另存 monday-full.md。目标：10 秒判断「要不要动手」。

合并来源（定义保留、已 paused，可随时 resume）：
  orzmc-config-audit 836f72d6ad16 / orzmc-version-check e9a7e185fbff / orzmc-weekly-patrol 9d625c27db6d
退出码：业务异常一律 0（报告本身就是产出），聚合器自身崩了才 2。
"""
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPTS = Path(__file__).resolve().parent
REPORT_ROOT = Path("E:/orzmc/reports")
BLOCK_TIMEOUT = 420

BLOCKS = [
    ("配置审查", "orzmc_config_audit.py", ()),
    ("版本巡检", "mc_version_check.py", ()),
    ("运行巡检", "orzmc_weekly_patrol.py", ()),
    # 第四段：升级流水线（检测→出包→测试服三实例→验收→S: 交接件→Exaroton 同步→清理旧包）
    # --require-idle：有玩家在线时只出包不重启实例
    ("升级同步", "orzmc_upgrade_sync.py", ("--require-idle",)),
]


# ------------------------------------------------------------------ 执行
def run_block(script, extra=()):
    path = SCRIPTS / script
    if not path.is_file():
        return {"rc": -1, "out": "", "err": "脚本不存在: %s" % path, "secs": 0.0, "ok": False}
    env = dict(os.environ, PYTHONPATH="", PYTHONIOENCODING="utf-8")
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(path)] + list(extra), cwd=str(SCRIPTS),
                           capture_output=True, timeout=BLOCK_TIMEOUT, env=env)
        out = (p.stdout or b"").decode("utf-8", "replace").strip()
        err = (p.stderr or b"").decode("utf-8", "replace").strip()
        return {"rc": p.returncode, "out": out, "err": err,
                "secs": time.time() - t0, "ok": p.returncode == 0}
    except subprocess.TimeoutExpired:
        return {"rc": -2, "out": "", "err": "超时 > %ds" % BLOCK_TIMEOUT,
                "secs": time.time() - t0, "ok": False}
    except Exception as exc:  # noqa: BLE001
        return {"rc": -3, "out": "", "err": "%s: %s" % (type(exc).__name__, exc),
                "secs": time.time() - t0, "ok": False}


# ------------------------------------------------------------------ 解析
def _f(pat, text, default=None, g=1):
    m = re.search(pat, text, re.M)
    return m.group(g).strip() if m else default


def _c(s):
    return re.sub(r"\*\*|`", "", s or "").strip()


def _cell(s):
    """表格单元格清洗：去掉装饰符，竖线必须替换，否则整张表错行。"""
    return _c(s).replace("|", "，")


def parse_config(txt):
    base = _f(r"^基准端:\s*(.+)$", txt) or ""
    other = _f(r"^对比端:\s*(.+)$", txt) or ""
    base = base.replace("件配置", "件").replace("件（", "件（")
    other = re.sub(r"^Exaroton\s*", "", other)
    d = {
        "base": base,
        "other": other,
        "diff": _f(r"^差异:\s*(.+)$", txt),
    }
    d["ok"] = bool(d["base"] and d["diff"])
    d["clean"] = bool(re.search(r"核心 0 件\s*/\s*插件 0 件", d["diff"] or ""))
    return d


def parse_version(txt):
    d = {"ok": False, "rows": 0, "latest": 0, "local": 0, "unknown": [],
         "paper_up": _c(_f(r"^核心:\s*Paper核心\s*(\S+)", txt)),
         "folia_up": _c(_f(r"^Folia核心:\s*([^\s（(]+)", txt))}
    for line in txt.splitlines():
        if "组件" in line and "部署" in line:
            continue
        m = re.match(r"^\s*(\S+)\s{2,}(.+?)\s{2,}(.+?)\s{2,}(✅|➖.*|❓.*)\s*$", line)
        if not m:
            continue
        d["rows"] += 1
        st = m.group(4)
        if st.startswith("✅"):
            d["latest"] += 1
        elif st.startswith("➖"):
            d["local"] += 1
        else:
            d["unknown"].append("%s %s" % (_c(m.group(1)), _c(m.group(2))))
    d["ok"] = d["rows"] > 0
    return d


def parse_patrol(txt):
    d = {"ok": False, "containers": [], "down": [], "todo": [], "disks": {}}
    for line in txt.splitlines():
        m = re.match(r"^\|\s*`([\w.-]+)`\s*\|\s*(Up[^|]*)\|", line)
        if m:
            d["containers"].append(m.group(1))
        m = re.match(r"^-\s*容器\s*`([\w.-]+)`\s*没在运行", line)
        if m:
            d["down"].append(m.group(1))
        m = re.match(r"^- ([A-Z]): 剩余 \*?\*?([\d.]+)GB / ([\d.]+)GB\*?\*?（(\d+)%）", line)
        if m:
            d["disks"][m.group(1)] = "用 %s%%（余 %sGB）" % (m.group(4), m.group(2))
    d["java"] = _c(_f(r"^- Java 25565[：:]\s*(.+)$", txt))
    d["bedrock"] = _c(_f(r"^- NetherNet 信令[：:]\s*(.+)$", txt))
    web_raw = _c(_f(r"^- 网页入口[^：:]*[：:]\s*(.+)$", txt))
    srv = _f(r"Server:\s*([\w./-]+)", web_raw or "")
    d["web"] = ("✅ %s" % srv) if (web_raw or "").startswith("✅") and srv else web_raw
    d["advertise"] = _c(_f(r"^- 结论[：:]\s*(.+)$", txt))
    d["paper_rcon"] = _c(_f(r"^- paper[：:]\s*(.+)$", txt))
    d["folia_rcon"] = _c(_f(r"^- folia[：:]\s*(.+)$", txt))
    d["paper_cur"] = _f(r"^- Paper \*\*(.+?)\*\* →", txt)
    d["paper_latest"] = _f(r"^- Paper .*?build \*?\*?`?(\d+)`?", txt)
    d["paper_behind"] = _f(r"^- Paper .*?落后 (\d+)", txt)
    d["folia_cur"] = _f(r"^- Folia \*\*(.+?)\*\* →", txt)
    d["folia_latest"] = _f(r"^- Folia .*?build \*?\*?`?(\d+)`?", txt)
    d["errors"] = _f(r"ERROR \*?\*?(\d+)\*?\*?\s*条", txt)
    d["backup"] = _c(_f(r"^- 最近备份[：:]\s*(.+)$", txt))

    in_todo = False
    for line in txt.splitlines():
        if line.startswith("## 需要动手"):
            in_todo = True
            continue
        if in_todo:
            if line.startswith("_耗时") or line.startswith("#"):
                break
            m = re.match(r"^-\s*(.+)$", line)
            if m:
                d["todo"].append(_c(m.group(1)))
    d["ok"] = bool(d["containers"] or d["java"])
    return d


# ------------------------------------------------------------------ 渲染
def build_todo(cfg, ver, pat, failed):
    todo = []
    backend = pat.get("down") or []
    rcon_bad = any("RCON 不通" in (pat.get(k) or "") for k in ("paper_rcon", "folia_rcon"))
    if backend or rcon_bad:
        names = "、".join(backend) if backend else "Paper/Folia"
        todo.append("**后端实例没起**：%s 未运行、RCON 不通 → 玩家登录会卡在切换服" % names)
    if pat.get("paper_behind") not in (None, "0"):
        cur, build = pat.get("paper_cur") or "?", pat.get("paper_latest") or "?"
        tgt = "%s-%s" % (cur.rsplit("-", 1)[0], build) if "-" in cur else build
        todo.append("**Paper 落后 %s 个 build**：%s → %s" % (pat["paper_behind"], cur, tgt))
    if cfg.get("ok") and not cfg.get("clean"):
        todo.append("**配置漂移**：本机 %s vs %s，%s" % (
            _c(cfg.get("base", "?")), _c(cfg.get("other", "?")), cfg.get("diff")))
    if pat.get("errors") not in (None, "0"):
        todo.append("**日志 %s 条 ERROR**：Geyser 与 packetevents/GrimAC 管道冲突（已知，非致命）" % pat["errors"])
    for u in (ver.get("unknown") or []):
        todo.append("**版本待核**：%s（查不到上游渠道）" % u)
    for b in failed:
        n = len(b.get("out") or "")
        why = "rc=%s 但 stdout 为空（脚本被 import 劫持/静默退出最常见）" % b["rc"] if b["ok"] else "rc=%s" % b["rc"]
        todo.append("**%s 段无有效结果**（%s，stdout %d 字节）" % (b["name"], why, n))
    return todo


def parse_upgrade(txt):
    """解析 orzmc_upgrade_sync.py 输出：STATUS_LINE + 「版本与取证」「动作」要点"""
    ok = "STATUS_LINE: ✅" in txt
    status = _f(r"STATUS_LINE:\s*(.+)", txt, "")
    lines_all = txt.splitlines()
    actions_at = next((i for i, l in enumerate(lines_all) if l.strip() == "### 动作"), None)
    head = lines_all[:actions_at] if actions_at is not None else lines_all
    bullets = [l[2:].strip() for l in head if l.startswith("- ")]
    lines = lines_all
    acts = []
    if actions_at is not None:
        for l in lines[actions_at + 1:]:
            if l.startswith("#"):
                break
            if l.startswith("- "):
                acts.append(l[2:].strip())
    return {"ok": ok, "status": status, "ev": bullets[:6], "actions": acts[:8],
            "has_content": bool(bullets or acts)}


def render(now, blocks, outdir, full_path):
    cfg, ver, pat = (b["parsed"] for b in blocks[:3])
    up = blocks[3]["parsed"] if len(blocks) > 3 else {"ok": True, "status": "未运行", "ev": [], "actions": []}
    # 注意：rc=0 但解析不出内容同样算失败（实测 orzmc_weekly_patrol 曾因 import 劫持静默退出、rc=0）
    failed = [b for b in blocks if not (b["ok"] and b["parsed"].get("ok"))]
    secs = sum(b["secs"] for b in blocks)
    todo = build_todo(cfg, ver, pat, failed)
    backend_down = bool(pat.get("down")) or any(
        "RCON 不通" in (pat.get(k) or "") for k in ("paper_rcon", "folia_rcon"))

    L = ["# OrzMC 周一总报告 · %s" % now.strftime("%m-%d"), ""]
    if todo:
        L.append("**🔴 %d 项待处理**　·　%d/%d 段完成　·　%.0fs" % (
            len(todo), len(blocks) - len(failed), len(blocks), secs))
    else:
        L.append("**✅ 无需动手**　·　%d/%d 段完成　·　%.0fs" % (
            len(blocks) - len(failed), len(blocks), secs))
    L.append("")

    if not cfg.get("ok"):
        c = "❌ 失败"
    elif cfg.get("clean"):
        c = "✅ 一致"
    else:
        c = "⚠️ %s" % (cfg.get("diff") or "有差异")
    if not ver.get("ok"):
        v = "❌ 失败"
    elif ver.get("unknown"):
        v = "⚠️ %d 项最新 / %d 项待核" % (ver["latest"], len(ver["unknown"]))
    else:
        v = "✅ %d 项全部最新" % ver["latest"]
    p = "🔴 后端未启动" if backend_down else ("✅ 全部正常" if pat.get("ok") else "❌ 失败")

    u = ("✅ 已最新" if "无需升级" in (up.get("status") or "") else
         ("⚠️ " + up["status"] if up.get("status") else "⚠️ 有异常"))
    L += ["| 段 | 结果 | 用时 |", "|:--|:--|--:|"]
    for b, res in zip(blocks, (c, v, p, u)):
        L.append("| %s | %s | %.0fs |" % (b["name"], _cell(res), b["secs"]))
    L.append("")

    L += ["## 待处理", ""]
    if todo:
        for i, t in enumerate(todo[:8], 1):
            L.append("%d. %s" % (i, t))
    else:
        L.append("无")
    L.append("")

    if pat.get("ok"):
        L += ["## 运行态", "", "| 项 | 状态 |", "|:--|:--|"]
        missing = "，缺 %s" % "、".join(pat["down"]) if pat.get("down") else ""
        L.append("| 容器 | %d 个 Up%s |" % (len(pat["containers"]), missing))
        for key, label in (("java", "Java 25565"), ("bedrock", "基岩 NetherNet"),
                           ("web", "网页 443"), ("advertise", "advertise 一致性")):
            if pat.get(key):
                L.append("| %s | %s |" % (label, _cell(pat[key])))
        if pat.get("paper_rcon") or pat.get("folia_rcon"):
            def _rcon_cell(v):
                v = str(v or "")
                if v.startswith("✅"):
                    return "✅"
                if "已关闭" in v:   # RCON 关闭属既定配置（后端由面板/日志核对），不是故障
                    return "ℹ️ 已关闭"
                return "❌ 不通" if "不通" in v else ("⚠️ 未检" if v else "—")
            L.append("| 后端 RCON | paper %s / folia %s |" % (
                _rcon_cell(pat.get("paper_rcon")), _rcon_cell(pat.get("folia_rcon"))))
        if pat.get("disks"):
            L.append("| 磁盘 | %s |" % _cell("　".join(
                "%s %s" % (k, val) for k, val in sorted(pat["disks"].items()))))
        if pat.get("backup"):
            L.append("| 最近备份 | %s |" % _cell(pat["backup"]))
        L.append("")

    if ver.get("ok"):
        L += ["## 版本", "", "| 组件 | 当前 | 上游最新 | 判定 |", "|:--|:--|:--|:--|"]
        def _full(cur, build, fallback):
            if not build:
                return fallback or "?"
            return "%s-%s" % (cur.rsplit("-", 1)[0], build) if cur and "-" in cur else build
        if pat.get("paper_cur"):
            behind = pat.get("paper_behind")
            L.append("| Paper | %s | %s | %s |" % (
                pat["paper_cur"], _full(pat["paper_cur"], pat.get("paper_latest"), ver.get("paper_up")),
                "✅" if behind in (None, "0") else "⬆ 落后 %s" % behind))
        if pat.get("folia_cur"):
            L.append("| Folia | %s | %s | ✅ |" % (
                pat["folia_cur"], _full(pat["folia_cur"], pat.get("folia_latest"), ver.get("folia_up"))))
        L.append("| 插件 %d 项 | — | — | %s |" % (
            ver["rows"], "✅ 全部最新" if not ver.get("unknown")
            else "⚠️ %d 项待核" % len(ver["unknown"])))
        if ver.get("local"):
            L.append("")
            L.append("插件中 %d 项为本地构建版（无上游渠道，以本地为准）。" % ver["local"])
        L.append("")

    if cfg.get("ok"):
        L += ["## 配置（本机 vs Exaroton）", "",
              "- 本机 %s" % _c(cfg.get("base")),
              "- Exaroton %s" % _c(cfg.get("other")),
              "- 差异 %s" % _c(cfg.get("diff")), ""]

    # 升级流水线（第四段）
    if len(blocks) > 3:
        L += ["## 升级流水线", "", "- 结论 %s" % _c(up.get("status") or "—")]
        for e in (up.get("ev") or [])[:4]:
            L.append("- %s" % _c(e))
        for a in (up.get("actions") or [])[:6]:
            L.append("  - %s" % _c(a))
        L.append("")

    L += ["---", "明细 `%s`" % (full_path or "报告目录")]
    if outdir:
        L.append("原始输出 `%s`" % outdir)
    L.append("")
    L.append("STATUS_LINE: %s · %d/%d 段完成 · 待办 %d 项" % (
        "❌" if failed else ("⚠️" if todo else "✅"),
        len(blocks) - len(failed), len(blocks), len(todo)))
    return "\n".join(L)


def main():
    now = datetime.now()
    outdir = REPORT_ROOT / ("monday-%s" % now.strftime("%Y%m%d"))
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except Exception:
        outdir = None

    blocks = []
    for name, script, extra in BLOCKS:
        r = run_block(script, extra)
        r["name"], r["script"] = name, script
        if script == "orzmc_config_audit.py":
            r["parsed"] = parse_config(r["out"])
        elif script == "mc_version_check.py":
            r["parsed"] = parse_version(r["out"])
        elif script == "orzmc_upgrade_sync.py":
            r["parsed"] = parse_upgrade(r["out"])
        else:
            r["parsed"] = parse_patrol(r["out"])
        if outdir:
            try:
                (outdir / script.replace(".py", ".txt")).write_text(
                    "rc=%s\n\n%s\n\n--- stderr ---\n%s" % (r["rc"], r["out"], r["err"]),
                    encoding="utf-8")
            except Exception:
                pass
        blocks.append(r)

    full_path = None
    if outdir:
        try:
            full_path = outdir / "monday-full.md"
            parts = ["# OrzMC 周一总报告（明细）· %s\n" % now.strftime("%Y-%m-%d %H:%M")]
            for b in blocks:
                parts.append("\n---\n\n## %s（rc=%s，%.0fs）\n\n%s\n"
                             % (b["name"], b["rc"], b["secs"], b["out"] or b["err"]))
            full_path.write_text("".join(parts), encoding="utf-8")
        except Exception:
            full_path = None

    report = render(now, blocks, outdir, full_path)
    if outdir:
        try:
            (outdir / "monday-report.md").write_text(report, encoding="utf-8")
        except Exception:
            pass
    print(report)
    return 0


def guarded_main():
    try:
        return main()
    except Exception:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(guarded_main())
