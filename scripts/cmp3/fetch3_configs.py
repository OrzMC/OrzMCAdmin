#!/usr/bin/env python3
"""两端配置拉取 v4（2026-09-09 迁移后：本地端退役，MCSM = Windows {SERVER_NAME} 栈）
清单 = MCSM 实例 API 递归扫描（真源，非本地目录）；Exaroton + MCSM 拉同名配置。
结构: <dir>/server.properties, <dir>/bukkit.yml, ..., <dir>/config_paper-global.yml (核心平铺)
      <dir>/plugins/<插件目录>/<相对路径> (插件配置保留目录结构)
"""
import sys, os, json, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mcsm_env import get_mcsm_local_config, get_exaroton_config, mcsm_download, mcsm_scan_plugin_configs
from exa_file import get_file as exa_get  # GET 自动解包 JSON/裸文本

EXA_OUT = "/tmp/exa_configs2"
MCSM_OUT = "/tmp/mcsm_configs2"          # MCSM({SERVER_NAME}, Windows 栈) = 基准端（2026-09-09 起）
CORE = ["server.properties", "bukkit.yml", "spigot.yml", "commands.yml", "wepif.yml"]
CORE_MAP = {  # 云上路径 → 本地平铺名
    "config/paper-global.yml": "config_paper-global.yml",
    "config/paper-world-defaults.yml": "config_paper-world-defaults.yml",
}

# ---------- Exaroton ----------
def exa_cfg():
    e = get_exaroton_config()
    return e["api_key"], e["server_id"]

def fetch_exa(files):
    api_key, sid = exa_cfg()
    os.makedirs(f"{EXA_OUT}/plugins", exist_ok=True)
    print("=== Exaroton 配置拉取 ===")
    ok = fail = 0
    for path, local in CORE_MAP.items():
        try:
            content = exa_get(path, api_key, sid)
            open(f"{EXA_OUT}/{local}", "w").write(content)
            print(f"  ✅ {path} ({len(content)}B)"); ok += 1
        except Exception as e:
            print(f"  ⚠️  {path}: {str(e)[:50]}"); fail += 1
        time.sleep(1)
    for f in CORE:
        try:
            content = exa_get(f, api_key, sid)
            open(f"{EXA_OUT}/{f}", "w").write(content)
            print(f"  ✅ {f} ({len(content)}B)"); ok += 1
        except Exception as e:
            print(f"  ⚠️  {f}: {str(e)[:50]}"); fail += 1
        time.sleep(1)
    def dl(rel):
        try:
            content = exa_get(f"plugins/{rel}", api_key, sid)
            dst = f"{EXA_OUT}/plugins/{rel}"
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "w").write(content)
            return (rel, "ok", len(content))
        except Exception as e:
            return (rel, "err", str(e)[:40])
    with ThreadPoolExecutor(max_workers=4) as ex:
        for rel, st, info in ex.map(dl, files):
            if st == "ok":
                ok += 1
            else:
                fail += 1
                print(f"  ⚠️  plugins/{rel}: {info}")
    print(f"Exaroton 完成: ok={ok} fail={fail} → {EXA_OUT}\n")

# ---------- MCSM（{SERVER_NAME} Windows 栈，2026-09-09 起 = 巡检 MCSM 端）----------
def fetch_mcsm(files, cfg=None, out_dir=None, label="MCSM({SERVER_NAME})"):
    """MCSM 配置拉取（串行 + 退避规避面板限流）"""
    if cfg is None:
        cfg = get_mcsm_local_config()
    if out_dir is None:
        out_dir = MCSM_OUT
    if os.path.exists(out_dir):
        import shutil; shutil.rmtree(out_dir)
    os.makedirs(f"{out_dir}/plugins", exist_ok=True)
    print(f"=== {label} 配置拉取 ===")
    ok = fail = 0
    for path, local in CORE_MAP.items():
        data = mcsm_download(cfg, f"/{path}")
        if data is not None and data[:2] != b"PK":
            open(f"{out_dir}/{local}", "wb").write(data)
            print(f"  ✅ {path} ({len(data)}B)"); ok += 1
        else:
            print(f"  ⚠️ {path}: 失败"); fail += 1
        time.sleep(1.5)
    for f in CORE:
        data = mcsm_download(cfg, f"/{f}")
        if data is not None and data[:2] != b"PK":
            open(f"{out_dir}/{f}", "wb").write(data)
            print(f"  ✅ {f} ({len(data)}B)"); ok += 1
        else:
            print(f"  ⚠️ {f}: 失败"); fail += 1
        time.sleep(1.5)
    failed = []
    for rel in files:
        data = None
        for attempt in range(3):
            data = mcsm_download(cfg, f"/plugins/{rel}")
            if data is not None and data[:2] != b"PK":
                break
            time.sleep(2)  # 限流退避
        if data is not None and data[:2] != b"PK":
            dst = f"{out_dir}/plugins/{rel}"
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(data)
            ok += 1
        else:
            fail += 1
            failed.append(rel)
            print(f"  ⚠️  plugins/{rel}: 失败")
    print(f"{label} 完成: ok={ok} fail={fail} → {out_dir}")
    if failed:
        print(f"失败清单({len(failed)}): {', '.join(failed)}")

def fetch_all():
    """两端：Exaroton(API) + MCSM({SERVER_NAME} API)。清单 = MCSM 端 API 递归扫描"""
    files = mcsm_scan_plugin_configs(get_mcsm_local_config())
    print(f"MCSM 端配置清单（API 递归扫描）: {len(files)} 个插件配置文件\n")
    print("并发: Exaroton + MCSM({SERVER_NAME})\n")
    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(fetch_exa, files)
        f2 = ex.submit(fetch_mcsm, files)
        f1.result()
        f2.result()
    print("=== 两端全部完成 ===\n")
    return files

if __name__ == "__main__":
    fetch_all()
