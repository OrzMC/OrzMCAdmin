#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""orzmc_upgrade_sync.py — 周一升级流水线（版本检测 → 出包 → 测试服三实例部署 → 验收 → S: 盘交接件 → Exaroton 同步 → 清理旧包）

铁律（ADR-040 / ADR-041 / ADR-042）：
  * 面板 API 是唯一重启手段；禁止 docker restart / docker compose restart
  * 核心与插件由面板实例持有；换版本 = 传 jar + 重启实例，不改启动命令
  * 已有 jar 一律不覆盖（除本脚本认定的目标版本，且先备份）
  * Geyser 两份都留：proxy（Geyser-Velocity）+ 后端（Geyser-Spigot）
  * Exaroton 只在 OFFLINE(status=0) 写文件；不擅自开服

用法：
  python orzmc_upgrade_sync.py                # 全流程（无新版本则只报告）
  python orzmc_upgrade_sync.py --dry-run      # 只检测+报告，不动文件不动实例
  python orzmc_upgrade_sync.py --skip-exaroton
  python orzmc_upgrade_sync.py --exaroton-only
  python orzmc_upgrade_sync.py --paper-only   # 只升 paper 线（调试用）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(_k, None)

import orzmc_paths as P  # noqa: E402

DATA_ROOT = P.data_env("DATA_ROOT") or "E:/orzmc"
INSTANCE_ROOT = os.path.join(DATA_ROOT, "mcsmanager", "daemon", "data", "InstanceData")
PACKAGES = os.path.join(DATA_ROOT, "packages")
BACKUPS = "E:/orzmc-backups"
S_ROOT = "S:/orzmc-upgrade"
UA = {"User-Agent": "orzmc-ops/1.0"}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

PAPER_UUID = "716c2fb712154c36ba5ab0f1480d3f87"
FOLIA_UUID = "8A932DD47F4D42AAAD6A6A9A5FAD2A91"

EV = []          # 证据行
ACTIONS = []     # 动作行
WARN = []


def say(icon, text):
    EV.append("%s %s" % (icon, text))


def act(text):
    ACTIONS.append(text)


# ------------------------------------------------------------------ 基础工具
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_json(url, timeout=60):
    with OPENER.open(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url, dest, want_sha256=None, want_sha1=None):
    """流式下载 + 哈希复核；已存在且哈希匹配则跳过。返回 (ok, msg)。"""
    if os.path.isfile(dest):
        if want_sha256 and sha256(dest) == want_sha256:
            return True, "已存在且 sha256 匹配，跳过"
        if want_sha1 and sha1(dest) == want_sha1:
            return True, "已存在且 sha1 匹配，跳过"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with OPENER.open(urllib.request.Request(url, headers=UA), timeout=300) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    got256, got1 = sha256(tmp), sha1(tmp)
    if want_sha256 and got256 != want_sha256:
        os.remove(tmp)
        return False, "sha256 不匹配 %s ≠ %s" % (got256[:16], want_sha256[:16])
    if want_sha1 and got1 != want_sha1:
        os.remove(tmp)
        return False, "sha1 不匹配 %s ≠ %s" % (got1[:16], want_sha1[:16])
    os.replace(tmp, dest)
    return True, "下载完成 %.1fMB sha256 %s" % (os.path.getsize(dest) / 1e6, got256[:16])


def vkey(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))) or (0,)


def jars_in(path):
    if not os.path.isdir(path):
        return []
    return sorted(x for x in os.listdir(path) if x.endswith(".jar"))


def versioned(path, pattern):
    """目录内匹配 pattern 的最高版本 jar：(文件名, 版本串) 或 (None, None)"""
    out = []
    for n in jars_in(path):
        m = re.match(pattern, n)
        if m:
            out.append((n, m.group(1)))
    if not out:
        return None, None
    out.sort(key=lambda x: vkey(x[1]))
    return out[-1]


# ------------------------------------------------------------------ 面板实例
def panel():
    dm = P.mcsm_daemon_id()
    return dm, [i for i in P.mcsm_instances()]


def inst_status(dm, uuid):
    r = P.mcsm_get("instance", daemonId=dm, uuid=uuid) or {}
    return (r.get("data") or {}).get("status")


def restart_instance(dm, uuid, name, dry=False, inst_dir=None):
    """面板 stop → 等 status=0 → open → 等 status=3。返回 True/False。"""
    if dry:
        act("[dry] 面板重启 `%s`（stop → open，不执行）" % name)
        return True
    P.mcsm_get("protected_instance/stop", uuid=uuid, remote_uuid=dm)
    st = None
    for _ in range(45):
        st = inst_status(dm, uuid)
        if st == 0:
            break
        time.sleep(1)
    if st != 0:
        # 实测 velocity 停服后 status 常在 1/2 徘徊，面板 open 幂等 —— 记信息不记异常
        say("ℹ️", "%s 停止后 status=%s（未归零），直接 open" % (name, st))
    time.sleep(2)
    P.mcsm_get("protected_instance/open", uuid=uuid, remote_uuid=dm)
    for _ in range(150):
        if inst_status(dm, uuid) == 3:
            act("面板重启 `%s` 完成（status=3）" % name)
            return True
        time.sleep(1)
    # status 不可读时以日志为凭据（避免误报失败）
    if inst_dir:
        ok, _ = wait_log(inst_dir, ["Done ("], timeout=5)
        if ok:
            act("面板重启 `%s` 完成（status 不可读，日志已 Done）" % name)
            return True
    WARN.append("%s 启动超时" % name)
    return False


def wait_log(inst_dir, needles, timeout=200):
    """等待 logs/latest.log 出现全部 needles（子串）。返回 (ok, tail 文本)。"""
    log = os.path.join(inst_dir, "logs", "latest.log")
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            txt = open(log, encoding="utf-8", errors="replace").read()
        except OSError:
            txt = ""
        if all(n in txt for n in needles):
            return True, txt
        time.sleep(5)
    try:
        txt = open(log, encoding="utf-8", errors="replace").read()
    except OSError:
        txt = ""
    return False, txt


def players_online():
    """经代理 ping 当前在线人数；探测失败返回 None（视为未知，不阻断）"""
    try:
        import mc_ping_probe as M
        st = M.mc_status("127.0.0.1", 25565, timeout=6)
        d = st.get("players") or {}
        return int(d.get("online", 0))
    except Exception:                                          # noqa: BLE001
        return None


# ------------------------------------------------------------------ 上游版本
def paper_latest(project, current_line):
    """返回 {build, version, url, sha256, channel, newer_line}；只取当前版本线（current_line）的 STABLE。"""
    try:
        info = fetch_json("https://fill.papermc.io/v3/projects/" + project)
        versions = info.get("versions") or {}
        lines = list(versions.keys()) if isinstance(versions, dict) else list(versions)
    except Exception as e:                                     # noqa: BLE001
        return {"error": "取版本列表失败 %s" % e}
    latest_line = lines[0] if lines else None
    line = current_line if (current_line and current_line in lines) else latest_line
    builds = fetch_json("https://fill.papermc.io/v3/projects/%s/versions/%s/builds" % (project, line))
    stables = [b for b in builds if str(b.get("channel", "")).upper() == "STABLE"]
    if not stables:
        return {"error": "%s %s 无 STABLE build" % (project, line)}
    b = sorted(stables, key=lambda x: x["id"])[-1]
    dl = (b.get("downloads") or {}).get("server:default") or {}
    return {
        "build": b["id"], "version": line, "channel": b.get("channel"),
        "filename": dl.get("name"),
        "url": dl.get("url"), "sha256": dl.get("checksums", {}).get("sha256"),
        "newer_line": (latest_line if latest_line and latest_line != line else None),
    }


def geyser_latest():
    vs = fetch_json("https://api.modrinth.com/v2/project/geyser/version")
    if not vs:
        return {"error": "Modrinth 无 version"}
    v = vs[0]
    out = {"version": v["version_number"], "urls": {}}
    for f in v.get("files", []):
        if f["filename"] in ("Geyser-Spigot.jar", "Geyser-Velocity.jar"):
            out["urls"][f["filename"]] = {"url": f["url"], "sha1": (f.get("hashes") or {}).get("sha1"),
                                          "size": f.get("size")}
    return out


# ------------------------------------------------------------------ 出包
def build_package(date_str, paper_t, folia_t, geyser_t, paper_cur, folia_cur, vel_ver, dry=False, flags=None):
    base = os.path.join(PACKAGES, "upgrade-" + date_str)
    for sub in ("core/paper", "core/folia", "core/velocity", "plugins/proxy", "plugins/paper",
                "plugins/folia", "production"):
        if not dry:
            os.makedirs(os.path.join(base, sub), exist_ok=True)
    got = {}
    if dry:
        parts = []
        if paper_t.get("build"):
            parts.append("paper %s-%s" % (paper_t.get("version"), paper_t.get("build")))
        if folia_t.get("build"):
            parts.append("folia %s-%s" % (folia_t.get("version"), folia_t.get("build")))
        if (flags or {}).get("geyser") and geyser_t.get("urls"):
            parts.append("geyser %s" % geyser_t.get("version"))
        act("[dry] 应出包 %s：%s" % (base, " / ".join(parts) or "（无变更）"))
        return base, got
    if paper_t.get("url"):
        dest = os.path.join(base, "core/paper", "paper-%s-%s.jar" % (paper_t["version"], paper_t["build"]))
        ok, msg = download(paper_t["url"], dest, want_sha256=paper_t.get("sha256"))
        say("✅" if ok else "❌", "paper %s-%s：%s" % (paper_t["version"], paper_t["build"], msg))
        if ok:
            got["paper"] = dest
    if folia_t.get("url"):
        dest = os.path.join(base, "core/folia", "folia-%s-%s.jar" % (folia_t["version"], folia_t["build"]))
        ok, msg = download(folia_t["url"], dest, want_sha256=folia_t.get("sha256"))
        say("✅" if ok else "❌", "folia %s-%s：%s" % (folia_t["version"], folia_t["build"], msg))
        if ok:
            got["folia"] = dest
    urls = geyser_t.get("urls") or {}
    if "Geyser-Velocity.jar" in urls:
        u = urls["Geyser-Velocity.jar"]
        dest = os.path.join(base, "plugins/proxy/Geyser-Velocity.jar")
        ok, msg = download(u["url"], dest, want_sha1=u.get("sha1"))
        say("✅" if ok else "❌", "Geyser-Velocity %s：%s" % (geyser_t.get("version"), msg))
        if ok:
            got["geyser_velocity"] = dest
    if "Geyser-Spigot.jar" in urls:
        u = urls["Geyser-Spigot.jar"]
        ver = re.sub(r"\D", "", geyser_t.get("version", "").split("b")[-1]) or "new"
        dest = os.path.join(base, "plugins/paper", "Geyser-Spigot-%s.jar" % ver)
        ok, msg = download(u["url"], dest, want_sha1=u.get("sha1"))
        say("✅" if ok else "❌", "Geyser-Spigot %s：%s" % (geyser_t.get("version"), msg))
        if ok:
            got["geyser_spigot"] = dest
            shutil.copy2(dest, os.path.join(base, "plugins/folia", os.path.basename(dest)))
            shutil.copy2(dest, os.path.join(base, "production", os.path.basename(dest)))
    if got.get("paper"):
        shutil.copy2(got["paper"], os.path.join(base, "production", os.path.basename(got["paper"])))
    # 包内已有同件（上次跑过）时也回填 got，供后续 S: 导出与 Exaroton 上传使用
    def pick(sub, prefix, key):
        if key in got:
            return
        cand = [x for x in jars_in(os.path.join(base, sub)) if x.startswith(prefix)]
        if cand:
            got[key] = os.path.join(base, sub, sorted(cand, key=vkey)[-1])
    pick("core/paper", "paper-", "paper")
    pick("core/folia", "folia-", "folia")
    pick("plugins/proxy", "Geyser-Velocity", "geyser_velocity")
    pick("plugins/paper", "Geyser-Spigot-", "geyser_spigot")
    write_docs(base, paper_t, folia_t, geyser_t, paper_cur, folia_cur, vel_ver, got)
    return base, got


def write_docs(base, paper_t, folia_t, geyser_t, paper_cur, folia_cur, vel_ver, got):
    rows = []
    for key, label, target in (("paper", "core/paper", "paper"), ("folia", "core/folia", "folia"),
                               ("geyser_velocity", "plugins/proxy", "Geyser-Velocity"),
                               ("geyser_spigot", "plugins/paper|folia", "Geyser-Spigot")):
        if key in got:
            p = got[key]
            rows.append("| %s | %s | %s | `%s` |" % (label, os.path.basename(p),
                                                     geyser_t.get("version") if "geyser" in key else
                                                     (paper_t.get("build") if key == "paper" else folia_t.get("build")),
                                                     sha256(p)))
    man = """# MANIFEST · %s

| 档位 | 文件 | 目标版本 | sha256 |
|:--|:--|:--|:--|
%s

现装：paper `%s` / folia `%s` / velocity `%s`
上游：PaperMC Fill API（sha256 校验）、Modrinth `geyser`（sha1 校验）。

## 本批不动
%s

## 回滚
`start.sh` 用 `ls -1 <前缀>-*.jar | sort -V | tail -1` 取最高版本 → 把新 jar 移出实例目录（改名 `.bak`）即回滚，
旧 jar 保留在实例目录内（selfcheck 视为「旧版保留」，不告警）。插件回滚 = 传回旧件并删新件 + 面板重启实例。
""" % (os.path.basename(base), "\n".join(rows), paper_cur, folia_cur, vel_ver,
       "\n".join("- " + w for w in (WARN or ["（无）"])))
    open(os.path.join(base, "MANIFEST.md"), "w", encoding="utf-8", newline="\n").write(man)
    readme = """# %s · 部署顺序

> 面板上传/覆盖 + **面板重启实例**；禁 `docker restart`、禁改启动命令。

1. Paper：根目录放 `core/paper/*.jar`（旧 jar 留着回滚）→ `plugins/` 放 `plugins/paper/Geyser-Spigot-*.jar`，
   **删掉旧的 Geyser-Spigot-*.jar**（同插件留两版会冲突）→ 面板重启 Paper
2. Folia：同上，用 `core/folia/` 与 `plugins/folia/`
3. Velocity：`plugins/proxy/Geyser-Velocity.jar` 覆盖 → 面板重启 Velocity
4. 验收：三实例 status=3、日志 `Done (`、`Geyser 2.12.1-bXXXX`、`0.0.0.0:19132`
5. 线上服：`production/`（只带 paper 一系；velocity/proxy 为 n/a）；Exaroton 核心由软件版本通道管理
""" % os.path.basename(base)
    open(os.path.join(base, "README.md"), "w", encoding="utf-8", newline="\n").write(readme)


# ------------------------------------------------------------------ 部署到测试服
def deploy(inst_dir, new_core, new_geyser_spigot, name, dm, uuid, dry=False):
    """把 jar 放进实例目录；删同插件旧版（先备份）。返回验收用 (needles, ok)"""
    plan = []
    if new_core:
        plan.append(("core", new_core, os.path.join(inst_dir, os.path.basename(new_core))))
    if new_geyser_spigot:
        plan.append(("geyser", new_geyser_spigot, os.path.join(inst_dir, "plugins", os.path.basename(new_geyser_spigot))))
    if dry:
        for kind, src, dst in plan:
            act("[dry] %s ← %s" % (name, os.path.basename(dst)))
        return True
    os.makedirs(os.path.join(BACKUPS, "pre-upgrade-" + time.strftime("%Y%m%d")), exist_ok=True)
    bdir = os.path.join(BACKUPS, "pre-upgrade-" + time.strftime("%Y%m%d"), name)
    os.makedirs(bdir, exist_ok=True)
    for kind, src, dst in plan:
        if kind == "geyser":
            pdir = os.path.join(inst_dir, "plugins")
            for old in jars_in(pdir):
                if old.startswith("Geyser-Spigot-") and old != os.path.basename(dst):
                    shutil.copy2(os.path.join(pdir, old), os.path.join(bdir, old))
                    os.remove(os.path.join(pdir, old))
                    act("%s 删除旧插件 %s（已备份）" % (name, old))
        shutil.copy2(src, dst)
        act("%s 放置 %s（sha256 %s）" % (name, os.path.basename(dst), sha256(dst)[:12]))
    return True


def verify_instance(name, inst_dir, needles, timeout):
    ok, txt = wait_log(inst_dir, needles, timeout)
    for n in needles:
        say("✅" if n in txt else "❌", "%s 日志含 `%s`" % (name, n))
    errs = [l for l in txt.splitlines() if "] ERROR]" in l][-3:]
    for e in errs:
        say("⚠️", "%s 日志 ERROR：%s" % (name, e[:120]))
    return ok


# ------------------------------------------------------------------ Exaroton
def exaroton_sync(paper_geyser, dry=False):
    try:
        sys.path.insert(0, HERE)
        import exa_file
        import exa_sync_plugins as E
    except Exception as e:                                     # noqa: BLE001
        return "skip", "Exaroton 模块不可用：%s" % e
    st, soft = E.server_status()
    if st != 0:
        return "skip", "服务器非 OFFLINE（status=%s），本批不改线上文件" % st
    s, b = E.req("GET", "/servers/%s/files/info/plugins/." % E.SID)
    names = [c["name"] for c in json.loads(b)["data"]["children"]]
    cur = sorted([n for n in names if n.startswith("Geyser-Spigot") and n.endswith(".jar")])
    target = os.path.basename(paper_geyser)
    if cur and cur == [target]:
        return "ok", "线上已是 %s（%s），无需变动" % (target, soft.get("version"))
    if dry:
        return "dry", "[dry] 上传 %s 并删 %s" % (target, ", ".join(cur) or "无")
    lsha = sha256(paper_geyser)
    with open(paper_geyser, "rb") as f:
        s, _ = E.req("PUT", "/servers/%s/files/data/plugins/%s/" % (E.SID, target), data=f.read(),
                     ctype="application/octet-stream")
    if s != 200:
        return "fail", "上传失败 HTTP %s" % s
    _, blob = E.req("GET", "/servers/%s/files/data/plugins/%s/" % (E.SID, target))
    if hashlib.sha256(blob).hexdigest() != lsha:
        return "fail", "回读 sha256 不一致"
    for old in cur:
        if old != target:
            E.req("DELETE", "/servers/%s/files/data/plugins/%s/" % (E.SID, old))
    return "ok", "已上传 %s（sha256 回读一致），删除旧件 %s；软件版本 %s 由 Exaroton 管理" % (
        target, ", ".join(x for x in cur if x != target) or "无", soft.get("version"))


# ------------------------------------------------------------------ S: 交接件
def export_s(base, got, paper_t, folia_t, geyser_t, exa_msg, dry=False):
    dst = os.path.join(S_ROOT.replace("/", os.sep), os.path.basename(base))
    if dry:
        act("[dry] 导出 S: → %s" % dst)
        return dst
    for sub in ("core/paper", "core/velocity", "plugins/paper", "plugins/proxy"):
        os.makedirs(os.path.join(dst, sub), exist_ok=True)
    if "paper" in got:
        shutil.copy2(got["paper"], os.path.join(dst, "core/paper", os.path.basename(got["paper"])))
    if "geyser_spigot" in got:
        shutil.copy2(got["geyser_spigot"], os.path.join(dst, "plugins/paper", os.path.basename(got["geyser_spigot"])))
    open(os.path.join(dst, "core/velocity", "README-n_a.txt"), "w", encoding="utf-8", newline="\n").write(
        "生产服（Exaroton）不使用 Velocity 代理：本档 n/a。\n")
    open(os.path.join(dst, "plugins/proxy", "README-n_a.txt"), "w", encoding="utf-8", newline="\n").write(
        "生产服无 Velocity 代理（25565 明文 ws + EaglerXPaper 直连），代理插件档 n/a。\n")
    lines = ["# MANIFEST · 生产服交接件 %s" % os.path.basename(base), "",
             "| 档位 | 文件 | sha256 |", "|:--|:--|:--|"]
    for k, sub in (("paper", "core/paper"), ("geyser_spigot", "plugins/paper")):
        if k in got:
            lines.append("| %s | %s | `%s` |" % (sub, os.path.basename(got[k]), sha256(got[k])))
    lines += ["", "## Exaroton 同步结果", "", exa_msg, "",
              "## 说明", "- 核心：Exaroton 软件版本通道管理（%s）；`core/paper/` 仅留档/手动兜底" % paper_t.get("version"),
              "- velocity/proxy 档 n/a（生产无代理）", "- 回滚：旧件见 `E:/orzmc-backups/pre-upgrade-*`"]
    open(os.path.join(dst, "MANIFEST.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    open(os.path.join(dst, "README.md"), "w", encoding="utf-8", newline="\n").write(
        "# 生产服手动升级（兜底流程）\n\n"
        "1. Exaroton 面板确认软件版本 PaperMC %s\n"
        "2. `plugins/` 上传 `plugins/paper/%s`，删除旧 Geyser-Spigot\n"
        "3. 开服后看 `Loading Paper` 与 `Geyser ... %s`\n"
        "4. 回滚：旧件传回并删新件\n" % (paper_t.get("version"),
                                          os.path.basename(got.get("geyser_spigot", "")), geyser_t.get("version")))
    act("S: 交接件已落盘 %s" % dst)
    return dst


# ------------------------------------------------------------------ 清理（只留最近一次）
def cleanup(keep_base, dry=False):
    keep = os.path.basename(keep_base)
    removed = []
    for root in (PACKAGES, S_ROOT.replace("/", os.sep)):
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            full = os.path.join(root, name)
            if not os.path.isdir(full) or not name.startswith("upgrade-"):
                continue
            if name == keep:
                continue
            if dry:
                act("[dry] 清理旧包 %s" % full)
                continue
            shutil.rmtree(full, ignore_errors=True)
            removed.append(full)
    if removed:
        act("清理旧升级包 %d 个（只留 %s）：%s" % (len(removed), keep, ", ".join(os.path.basename(x) for x in removed)))
    return removed


# ------------------------------------------------------------------ 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-exaroton", action="store_true")
    ap.add_argument("--exaroton-only", action="store_true")
    ap.add_argument("--no-clean", action="store_true")
    ap.add_argument("--paper-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="即使已是目标版本也重跑一遍（演练/自测）")
    ap.add_argument("--require-idle", action="store_true", help="有玩家在线时不动实例（cron 用）")
    args = ap.parse_args()
    date_str = time.strftime("%Y%m%d")

    vel_dir = P.velocity_dir()
    paper_dir = os.path.join(INSTANCE_ROOT, PAPER_UUID)
    folia_dir = os.path.join(INSTANCE_ROOT, FOLIA_UUID)

    paper_jar, paper_cur = versioned(paper_dir, r"^paper-(.+)\.jar$")
    folia_jar, folia_cur = versioned(folia_dir, r"^folia-(.+)\.jar$")
    vel_jar, vel_ver = versioned(vel_dir, r"^velocity-(.+)\.jar$")
    gs_jar, gs_cur = versioned(os.path.join(paper_dir, "plugins"), r"^Geyser-Spigot-(.+)\.jar$")
    gv_jar, gv_cur = versioned(os.path.join(vel_dir, "plugins"), r"^Geyser-Velocity(.*)\.jar$")

    say("ℹ️", "现装：paper `%s` / folia `%s` / velocity `%s` / Geyser-Spigot `%s` / Geyser-Velocity `%s`"
        % (paper_jar, folia_jar, vel_jar, gs_jar, gv_jar))

    paper_line = (paper_cur or "").split("-")[0] if paper_cur else None
    folia_line = (folia_cur or "").split("-")[0] if folia_cur else None
    try:
        paper_t = paper_latest("paper", paper_line)
        folia_t = {} if args.paper_only else paper_latest("folia", folia_line)
        geyser_t = geyser_latest()
    except Exception as e:                                     # noqa: BLE001
        print("## ❌ 上游查询失败：%s" % e)
        return 2

    def newer(cur, target):
        return bool(target and target.get("build") and vkey(str(target.get("build"))) > vkey(str(cur or "0").split("-")[-1]))

    do_paper = bool(paper_t.get("build")) and (args.force or newer(paper_cur, paper_t))
    do_folia = bool(folia_t.get("build")) and (args.force or newer(folia_cur, folia_t))
    gv_str = str(geyser_t.get("version", ""))
    gnum = re.sub(r"\D", "", gv_str.split("b")[-1]) if "b" in gv_str else re.sub(r"\D", "", gv_str)
    do_geyser = bool(gnum) and (args.force or not gs_jar or not gv_jar or vkey(gnum) > vkey(gs_cur))

    say("ℹ️", "上游：paper %s build %s（%s）/ folia %s build %s / Geyser %s"
        % (paper_t.get("version"), paper_t.get("build"), paper_t.get("channel"),
           folia_t.get("version"), folia_t.get("build"), geyser_t.get("version")))
    if paper_t.get("newer_line"):
        say("ℹ️", "paper 有更新的版本线 %s（本批不自动跳线，只升 %s）" % (paper_t["newer_line"], paper_t.get("version")))

    if args.exaroton_only:
        cand = os.path.join(PACKAGES, os.path.basename(sorted(
            [d for d in os.listdir(PACKAGES) if d.startswith("upgrade-")])[-1]), "plugins/paper")
        jars = jars_in(cand)
        if not jars:
            print("## ❌ 找不到可同步到线上的 Geyser jar（%s 为空）" % cand)
            return 2
        state, msg = exaroton_sync(os.path.join(cand, jars[-1]), dry=args.dry_run)
        print("## Exaroton 同步 %s：%s" % (state, msg))
        return 0

    if not (do_paper or do_folia or do_geyser) and not args.force:
        say("✅", "三端核心与 Geyser 均已是上游最新，本批无需升级")
        state, msg = exaroton_sync(os.path.join(paper_dir, "plugins", gs_jar or ""), dry=args.dry_run) \
            if (gs_jar and not args.skip_exaroton) else ("skip", "跳过")
        say("ℹ️", "线上服：%s" % msg)
        print("\n".join(EV))
        return 0

    if args.require_idle and not args.dry_run:
        n = players_online()
        if n:
            say("⚠️", "当前在线 %s 人 → 只出包+报告，不重启实例（人工择时部署）" % n)
            base, got = build_package(date_str, paper_t if do_paper else {}, folia_t if do_folia else {},
                                      geyser_t if do_geyser else {}, paper_cur, folia_cur, vel_ver,
                                      flags={"paper": do_paper, "folia": do_folia, "geyser": do_geyser})
            export_s(base, got, paper_t, folia_t, geyser_t, "未执行（有玩家在线）")
            cleanup(base) if not args.no_clean else None
            print("\n## 升级流水线 %s（有玩家在线，已跳过部署）" % time.strftime("%Y-%m-%d %H:%M"))
            print("\n".join("- " + e for e in EV))
            print("\n### 动作\n" + ("\n".join("- " + a for a in ACTIONS) or "- 无"))
            print("\nSTATUS_LINE: ⚠️ 有玩家在线，未部署（包已出，待人工择时）")
            return 0

    base, got = build_package(date_str, paper_t if do_paper else {}, folia_t if do_folia else {},
                              geyser_t if do_geyser else {}, paper_cur, folia_cur, vel_ver,
                              dry=args.dry_run,
                              flags={"paper": do_paper, "folia": do_folia, "geyser": do_geyser})

    dm, _ = panel()
    ok_all = True
    if do_paper or (do_geyser and not args.dry_run):
        deploy(paper_dir, got.get("paper"), got.get("geyser_spigot"), "paper", dm, PAPER_UUID, dry=args.dry_run)
        if not args.dry_run:
            restart_instance(dm, PAPER_UUID, "paper", dry=False, inst_dir=paper_dir)
            needles = ["Done ("]
            if do_paper:
                needles.append("Paper version %s-%s" % (paper_t["version"], paper_t["build"]))
            if do_geyser:
                needles.append("Geyser-Spigot v%s" % str(geyser_t.get("version", "")).split("-")[0])
            ok_all &= verify_instance("paper", paper_dir, needles, 200)
    if do_folia:
        deploy(folia_dir, got.get("folia"), got.get("geyser_spigot"), "folia", dm, FOLIA_UUID, dry=args.dry_run)
        if not args.dry_run:
            restart_instance(dm, FOLIA_UUID, "folia", dry=False, inst_dir=folia_dir)
            folia_needles = ["Done ("]
            if do_folia:
                folia_needles.append("Folia version %s-%s" % (folia_t["version"], folia_t["build"]))
            if do_geyser:
                folia_needles.append("Geyser-Spigot v%s" % str(geyser_t.get("version", "")).split("-")[0])
            ok_all &= verify_instance("folia", folia_dir, folia_needles, 200)
    if do_geyser and got.get("geyser_velocity"):
        vel_uuid = os.path.basename(str(vel_dir))  # 小写，与面板 uuid 一致；upper() 会让 API 返回空
        if args.dry_run:
            act("[dry] velocity ← Geyser-Velocity.jar + 面板重启")
        else:
            bk = os.path.join(BACKUPS, "pre-upgrade-" + time.strftime("%Y%m%d"), "velocity")
            os.makedirs(bk, exist_ok=True)
            for old in jars_in(os.path.join(vel_dir, "plugins")):
                if old.startswith("Geyser-Velocity"):
                    shutil.copy2(os.path.join(vel_dir, "plugins", old), os.path.join(bk, old))
            dst = os.path.join(vel_dir, "plugins", "Geyser-Velocity.jar")
            shutil.copy2(got["geyser_velocity"], dst)
            act("velocity 放置 Geyser-Velocity.jar（sha256 %s）" % sha256(dst)[:12])
            restart_instance(dm, vel_uuid, "velocity", dry=False, inst_dir=vel_dir)
            vneedles = ["Done ("]
            if do_geyser:
                # velocity 侧日志带完整 build：Loaded plugin geyser 2.12.1-b1306
                vneedles.append("geyser %s" % geyser_t.get("version"))
            ok_all &= verify_instance("velocity", vel_dir, vneedles, 120)

    exa_state, exa_msg = ("skip", "未执行")
    if ok_all and not args.skip_exaroton and got.get("geyser_spigot"):
        exa_state, exa_msg = exaroton_sync(got["geyser_spigot"], dry=args.dry_run)
        say("✅" if exa_state in ("ok", "dry") else "⚠️", "线上服（Exaroton）：%s" % exa_msg)

    if not args.dry_run:
        export_s(base, got, paper_t, folia_t, geyser_t, exa_msg)
        if not args.no_clean:
            cleanup(base)

    print("\n## 升级流水线 %s" % time.strftime("%Y-%m-%d %H:%M"))
    print("\n### 版本与取证\n" + "\n".join("- " + e for e in EV))
    print("\n### 动作\n" + ("\n".join("- " + a for a in ACTIONS) or "- 无"))
    if WARN:
        print("\n### ⚠️ 异常\n" + "\n".join("- " + w for w in WARN))
    print("\nSTATUS_LINE: %s" % ("✅ 全绿" if ok_all and not WARN else "⚠️ 有异常"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
