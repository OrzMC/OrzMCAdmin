#!/usr/bin/env python3
"""三端配置全量对比（本地 vs Exaroton vs MCSM，语义级）
用法: python3 cmp3_configs.py <exaroton_dir> <mcsm_dir> [local_dir]
  例: python3 cmp3_configs.py /tmp/exa_configs2 /tmp/mcsm_configs2 ~/minecraft-server
对比内容: 核心配置文件（server.properties/bukkit/spigot/commands/paper-*）+ 插件配置
排除: 数据文件（userdata/homes/players 等）
"""
import os, sys

LOCAL = os.path.expanduser(sys.argv[3] if len(sys.argv) > 3 else "~/minecraft-server")
E = sys.argv[1] if len(sys.argv) > 1 else "/tmp/exa_configs2"
M = sys.argv[2] if len(sys.argv) > 2 else "/tmp/mcsm_configs2"
SKIP_DIRS = {"userdata", "homes", "data", "players", "backups", "logs", "cache", "worlds", "messages"}
SKIP_FILES = {"ops.json", "whitelist.json", "banned-players.json", "banned-ips.json",
              "usercache.json", "permissions.yml", "help.yml"}

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
                    key = l.split("=", 1)[0].rstrip()
                    val = l.split("=", 1)[1].strip()
                    out.append((0, key.strip(), val))
            elif ":" in l:
                key = l.split(":", 1)[0].rstrip()
                val = l.split(":", 1)[1].strip()
                indent = len(l) - len(l.lstrip())
                out.append((indent, key.strip(), val))
    return out

def semantic_diff(a_lines, b_lines, eq_style=False):
    ka, kb = key_lines(a_lines, eq_style), key_lines(b_lines, eq_style)
    da = {f"{ind}|{k}": v for ind, k, v in ka}
    db = {f"{ind}|{k}": v for ind, k, v in kb}
    diffs = []
    for key in sorted(set(da) & set(db)):
        va, vb = da[key], db[key]
        if va == vb:
            continue
        def norm(s):
            try:
                return ("num", float(s))
            except:
                return ("str", s)
        if norm(va) == norm(vb):
            continue
        diffs.append((key, va, vb))
    return diffs

def compare_local_file(name, local_path, exa_path, mcsm_path, eq_style=False):
    """返回 (名称, 状态, Exa差异数, MCSM差异数)"""
    ll = read(local_path)
    ee = read(exa_path) if exa_path else None
    mm = read(mcsm_path) if mcsm_path else None
    if ll is None:
        return (name, "本地缺失", 0, 0)
    d_le = semantic_diff(ll, ee, eq_style) if ee else None
    d_lm = semantic_diff(ll, mm, eq_style) if mm else None
    n_le = len(d_le) if d_le else 0
    n_lm = len(d_lm) if d_lm else 0
    if n_le == 0 and n_lm == 0:
        return (name, "一致", 0, 0)
    return (name, "差异", n_le, n_lm)

print("=" * 75)
print(f"三端配置全量对比: {LOCAL} / {E} / {M}")
print("=" * 75)

# 核心配置
print("\n【核心配置】")
core_files = [
    ("server.properties", "server.properties", "server.properties"),
    ("bukkit.yml", "bukkit.yml", "bukkit.yml"),
    ("spigot.yml", "spigot.yml", "spigot.yml"),
    ("commands.yml", "commands.yml", "commands.yml"),
    ("config/paper-global.yml", "config_paper-global.yml", "config_paper-global.yml"),
    ("config/paper-world-defaults.yml", "config_paper-world-defaults.yml", "config_paper-world-defaults.yml"),
    ("wepif.yml", "wepif.yml", "wepif.yml"),
]
for name, ef, mf in core_files:
    eq = (name == "server.properties")
    name2, status, n_le, n_lm = compare_local_file(
        name, f"{LOCAL}/{name}", f"{E}/{ef}", f"{M}/{mf}", eq_style=eq)
    if status == "一致":
        print(f"  ✅ {name}")
    elif status == "本地缺失":
        print(f"  ℹ️  {name}: 本地缺失")
    else:
        print(f"  ❌ {name}: vs Exa {n_le} 处, vs MCSM {n_lm} 处")

# 插件配置
print("\n【插件配置】")
total = 0
diff_files = []
for pdir in sorted(os.listdir(f"{LOCAL}/plugins")):
    pdir_path = f"{LOCAL}/plugins/{pdir}"
    if not os.path.isdir(pdir_path):
        continue
    for root, dirs, files in os.walk(pdir_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in sorted(files):
            if not fn.endswith((".yml", ".yaml")):
                continue
            if fn in SKIP_FILES:
                continue
            rel = os.path.relpath(os.path.join(root, fn), pdir_path)
            total += 1
            local_path = f"{pdir_path}/{rel}"
            exa_path = f"{E}/plugins/{pdir}/{rel}"
            mcsm_path = f"{M}/plugins/{pdir}/{rel}"
            name2, status, n_le, n_lm = compare_local_file(
                f"{pdir}/{rel}", local_path, exa_path, mcsm_path)
            if status == "差异":
                diff_files.append((f"{pdir}/{rel}", n_le, n_lm))

print(f"  共检查 {total} 个插件配置文件，其中差异 {len(diff_files)} 个：")
for name, n_le, n_lm in diff_files:
    print(f"    ❌ {name}: vs Exa {n_le} 处, vs MCSM {n_lm} 处")

print(f"\n总计：核心 7 + 插件 {total} = {7 + total} 个配置文件")
