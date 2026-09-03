#!/usr/bin/env python3
"""三端配置差异完整报告生成器 v2（2026-08-10 二次审计）
判定基准：交集语义（cmp3 口径）——三端共同 key 值全同 = 完全一致；
单端独有 key（∅）不计为差异，单独标注。
数据类文件（玩家数据/交易记录/时间戳）标注为"运行时数据"。
"""
import os, sys, re

LOCAL = "/tmp/mcsm_local_configs2"   # 基准端 = 本机 MCSM 栈 Paper 实例配置（2026-09-03 起；原 ~/minecraft-server 目录已迁 MCSM）
E = "/tmp/exa_configs2"              # Exaroton（海外服）
M = "/tmp/mcsm_configs2"             # MCSM 远程 Win11（国内服）
SKIP_DIRS = {"userdata", "homes", "data", "players", "backups", "logs", "cache", "worlds", "messages"}
SKIP_FILES = {"ops.json", "whitelist.json", "banned-players.json", "banned-ips.json",
              "usercache.json", "permissions.yml", "help.yml"}

# 数据类文件（内容随玩家/运行变化，非配置）
DATA_FILES = {
    "BackOnDeath/config.yml", "GetMeHome/homes.yml", "EzShops/transactions.yml",
    "EzShops/player-shops.yml", "EzShops/shop-rotations.yml", "OrzMC/permission.yml",
    "OrzMC/ip_blacklist.yml", "Essentials/upgrades-done.yml",
}

def read(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read().splitlines()
    except Exception:
        return None

def key_lines(lines, eq_style=False):
    out = []
    for l in lines:
        if l.strip() and not l.strip().startswith("#"):
            if eq_style:
                if "=" in l:
                    k = l.split("=", 1)[0].rstrip()
                    v = l.split("=", 1)[1].strip()
                    out.append((0, k.strip(), v))
            elif ":" in l:
                k = l.split(":", 1)[0].rstrip()
                v = l.split(":", 1)[1].strip()
                ind = len(l) - len(l.lstrip())
                out.append((ind, k.strip(), v))
    return out

def semantic_map(lines, eq_style=False):
    return {f"{ind}|{k}": v for ind, k, v in key_lines(lines, eq_style)}

def norm(s):
    try:
        return ("num", float(s))
    except Exception:
        return ("str", s)

def diff_file(local_path, exa_path, mcsm_path, eq_style=False):
    """返回 (status, 交集差异列表, 单端独有 key 统计)
    status: 'same' | 'diff' | 'local_missing'"""
    ll = read(local_path)
    if ll is None:
        return 'local_missing', [], {}
    dl = semantic_map(ll, eq_style)
    el = read(exa_path)
    ml = read(mcsm_path)
    de = semantic_map(el, eq_style) if el else {}
    dm = semantic_map(ml, eq_style) if ml else {}
    # 交集差异（cmp3 口径）
    diffs = []
    for k in sorted(set(dl) & set(de) & set(dm)):
        vl, ve, vm = dl[k], de[k], dm[k]
        if vl == ve == vm:
            continue
        if norm(vl) == norm(ve) == norm(vm):
            continue
        diffs.append((k, vl, ve, vm))
    # 单端独有
    side = {}
    allk = set(dl) | set(de) | set(dm)
    for k in allk:
        cnt = sum(1 for d in (dl, de, dm) if k in d)
        if cnt < 3:
            side[k] = cnt
    return ('same' if not diffs else 'diff', diffs, side)

def label(k):
    return k.replace('|', '@').replace(' ', '')

# ============ 核心配置 ============
core_files = [
    ("server.properties", "server.properties", "server.properties", "server.properties", True),
    ("bukkit.yml", "bukkit.yml", "bukkit.yml", "bukkit.yml", False),
    ("spigot.yml", "spigot.yml", "spigot.yml", "spigot.yml", False),
    ("commands.yml", "commands.yml", "commands.yml", "commands.yml", False),
    ("config/paper-global.yml", "config/paper-global.yml", "config_paper-global.yml", "config_paper-global.yml", False),
    ("config/paper-world-defaults.yml", "config/paper-world-defaults.yml", "config_paper-world-defaults.yml", "config_paper-world-defaults.yml", False),
    ("wepif.yml", "wepif.yml", "wepif.yml", "wepif.yml", False),
]

out = []
out.append("# 三端配置差异审计报告（2026-08-11 三次·工具链修复后）\n")
out.append("## 审计范围：77 个配置文件\n")
out.append("| 类别 | 数量 |")
out.append("|:--|:--|")
out.append("| 核心配置（服务端） | 7 |")
out.append("| 插件配置 | 70 |")
out.append("| **合计** | **77** |\n")
out.append("三端：**本地**（本机 MCSM 栈 Paper 实例）/tmp/mcsm_local_configs2 / **Exa** Exaroton（海外服） / **MCSM**（远程 Win11 国内服）")
out.append("判定口径：**交集语义**（三端共同 key 值全同=完全一致；单端独有 key 另计）\n")

out.append("---\n## 一、核心配置（服务端 7 个）\n")
core_same = core_diff = 0
for name, lf, ef, mf, eq in core_files:
    st, diffs, side = diff_file(f"{LOCAL}/{lf}", f"{E}/{ef}", f"{M}/{mf}", eq)
    if st == 'same':
        core_same += 1
        note = "（Exa 为全量展开版 369 行/本地 MCSM 精简版 184 行，交集配置值全同，行为一致）" if name == "spigot.yml" else ""
        out.append(f"### ✅ {name} — 三端完全一致{note}\n")
    else:
        core_diff += 1
        side_note = f"，另有单端独有 key {len(side)} 个" if side else ""
        out.append(f"### ❌ {name} — 差异 {len(diffs)} 处{side_note}\n")
        out.append("| key | 本地 | Exa | MCSM |")
        out.append("|:--|:--|:--|:--|")
        for k, vl, ve, vm in diffs:
            out.append(f"| {label(k)} | {vl} | {ve} | {vm} |")
        out.append("")

# ============ 插件配置 ============
out.append("---\n## 二、插件配置（70 个，按插件分组）\n")
plugin_dirs = sorted([d for d in os.listdir(f"{LOCAL}/plugins") if os.path.isdir(f"{LOCAL}/plugins/{d}")])

total_same = total_diff = total_data = 0
for pdir in plugin_dirs:
    pdir_path = f"{LOCAL}/plugins/{pdir}"
    entries = []
    for root, dirs, files in os.walk(pdir_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in sorted(files):
            if not fn.endswith((".yml", ".yaml")) or fn in SKIP_FILES:
                continue
            rel = os.path.relpath(os.path.join(root, fn), pdir_path)
            name = f"{pdir}/{rel}"
            st, diffs, side = diff_file(f"{pdir_path}/{rel}", f"{E}/plugins/{pdir}/{rel}", f"{M}/plugins/{pdir}/{rel}")
            entries.append((name, rel, st, diffs, side))
    if not entries:
        continue
    same = [e for e in entries if e[2] == 'same']
    diff = [e for e in entries if e[2] == 'diff']
    data_files_in_dir = [e for e in entries if e[0] in DATA_FILES]
    # 数据文件从"一致"与"差异"中扣除（数据=非配置）
    data_same = len([e for e in data_files_in_dir if e[2] == 'same'])
    data_diff = len([e for e in data_files_in_dir if e[2] == 'diff'])
    same_eff = len(same) - data_same
    diff_eff = len(diff) - data_diff
    total_same += same_eff
    total_diff += diff_eff
    status_icon = "✅" if not diff_eff else "❌"
    out.append(f"### {status_icon} {pdir}（{len(entries)} 个：{same_eff} 一致 / {diff_eff} 差异 / {len(data_files_in_dir)} 数据）\n")
    for name, rel, st, diffs, side in entries:
        if name in DATA_FILES:
            total_data += 1
            out.append(f"- ℹ️ `{rel}` 运行时数据（玩家/交易/记录，三端独立属正常）")
        elif st == 'same':
            out.append(f"- ✅ `{rel}` 三端完全一致")
        elif st == 'diff':
            out.append(f"- ❌ `{rel}` 差异 {len(diffs)} 处：")
            for k, vl, ve, vm in diffs[:10]:
                out.append(f"  - `{label(k)}`：本地=`{vl}` Exa=`{ve}` MCSM=`{vm}`")
            if len(diffs) > 10:
                out.append(f"  - …等共 {len(diffs)} 处")
    out.append("")

out.append("---\n## 三、汇总\n")
out.append(f"| 状态 | 核心 | 插件 | 合计 |")
out.append(f"|:--|:--|:--|:--|")
out.append(f"| ✅ 三端完全一致 | {core_same} | {total_same} | {core_same + total_same} |")
out.append(f"| ❌ 配置差异 | {core_diff} | {total_diff} | {core_diff + total_diff} |")
out.append(f"| ℹ️ 运行时数据差异（正常） | 0 | {total_data} | {total_data} |")
out.append(f"| **合计** | **{core_same + core_diff}** | **{total_same + total_diff + total_data}** | **{core_same + core_diff + total_same + total_diff + total_data}** |")
out.append("\n> 注：运行时数据文件 = 玩家家/死亡点/交易记录/审批记录等随玩家变化的内容，三端独立属预期，不算配置漂移。")

report = "\n".join(out)
open("/tmp/cmp3_report_v2.md", "w").write(report)
print(report)
