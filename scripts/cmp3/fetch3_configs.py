#!/usr/bin/env python3
"""三端配置全量拉取 v2：以本地清单为基准，从 Exaroton + MCSM 拉同名配置
结构: <dir>/server.properties, <dir>/bukkit.yml, ..., <dir>/config_paper-global.yml (核心平铺)
      <dir>/plugins/<插件目录>/<相对路径> (插件配置保留目录结构)
"""
import sys, os, json, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mcsm_env import get_mcsm_config, get_mcsm_local_config, get_exaroton_config, mcsm_download
from exa_file import get_file as exa_get  # GET 自动解包 JSON/裸文本

# 本地基准清单源 = 本机 MCSM Paper 实例目录（宿主可见；只作「要拉哪些配置文件」的清单，非对比数据源）
LOCAL = os.path.expanduser("/Users/Shared/orzmc/mcsmanager/daemon/data/InstanceData/716c2fb712154c36ba5ab0f1480d3f87")
EXA_OUT = "/tmp/exa_configs2"
MCSM_OUT = "/tmp/mcsm_configs2"          # 远程 Win11 MCSM（对比端 B）
MCSM_LOCAL_OUT = "/tmp/mcsm_local_configs2"  # 本机 MCSM 栈（对比端 A = 本地端，2026-09-03 起）
CORE = ["server.properties", "bukkit.yml", "spigot.yml", "commands.yml", "wepif.yml"]
CORE_MAP = {  # 云上路径 → 本地平铺名
    "config/paper-global.yml": "config_paper-global.yml",
    "config/paper-world-defaults.yml": "config_paper-world-defaults.yml",
}
SKIP_DIRS = {"userdata", "homes", "data", "players", "backups", "logs", "cache", "worlds", "messages"}
SKIP_FILES = {"ops.json", "whitelist.json", "banned-players.json", "banned-ips.json",
              "usercache.json", "permissions.yml", "help.yml"}

def local_plugin_configs():
    """遍历本地 plugins 目录，返回所有配置文件相对路径（相对 plugins/）"""
    out = []
    for pdir in sorted(os.listdir(f"{LOCAL}/plugins")):
        pdir_path = f"{LOCAL}/plugins/{pdir}"
        if not os.path.isdir(pdir_path):
            continue
        for root, dirs, files in os.walk(pdir_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in sorted(files):
                if fn.endswith((".yml", ".yaml")) and fn not in SKIP_FILES:
                    rel = os.path.relpath(os.path.join(root, fn), pdir_path)
                    out.append(f"{pdir}/{rel}")
    return out

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

# ---------- MCSM ----------
def fetch_mcsm(files, cfg=None, out_dir=None, label="MCSM"):
    """MCSM 配置拉取（参数化：远程 Win11 或本机栈共用；内部串行+退避规避面板限流）"""
    if cfg is None:
        cfg = get_mcsm_config()
    if out_dir is None:
        out_dir = MCSM_OUT
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
        time.sleep(2)
    for f in CORE:
        data = mcsm_download(cfg, f"/{f}")
        if data is not None and data[:2] != b"PK":
            open(f"{out_dir}/{f}", "wb").write(data)
            print(f"  ✅ {f} ({len(data)}B)"); ok += 1
        else:
            print(f"  ⚠️ {f}: 失败"); fail += 1
        time.sleep(2)
    # 串行拉取 + 失败自动重试（MCSM 面板全局限流，并发必 500；串行+退避最稳）
    failed = []
    for rel in files:
        data = None
        for attempt in range(3):
            data = mcsm_download(cfg, f"/plugins/{rel}")
            if data is not None and data[:2] != b"PK":
                break
            time.sleep(3)  # 限流退避
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

# ---------- 本地端（本机 MCSM Paper 实例，2026-09-03 起） ----------
# ⚠️ 不走 MCSM API 下载：v10 面板文件下载是 wss 私有协议（mcsm_env v9 http 两步法不兼容），
#    且本地端配置本来就在宿主（InstanceData/<uuid>）——目录直读复制，产物与 API 拉取目录同构，
#    cmp3/report/audit 下游全复用（这就是"本地端与 MCSM 端同构"的实质）。
def fetch_local_dir(out_dir=None):
    """本地端配置 → 拉取目录（与 fetch_exa/fetch_mcsm 输出同构）"""
    import shutil
    if out_dir is None:
        out_dir = MCSM_LOCAL_OUT
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    ok = fail = 0
    print("=== 本地端(目录直读) 配置复制 ===")
    for f in CORE:  # server.properties/bukkit/spigot/commands/wepif 平铺
        src = f"{LOCAL}/{f}"
        if os.path.exists(src):
            shutil.copy2(src, f"{out_dir}/{f}"); ok += 1
        else:
            print(f"  ⚠️ {f}: 缺失"); fail += 1
    for path, local in CORE_MAP.items():  # config/paper-*.yml → 平铺 config_paper-*.yml
        src = f"{LOCAL}/{path}"
        if os.path.exists(src):
            shutil.copy2(src, f"{out_dir}/{local}"); ok += 1
        else:
            print(f"  ⚠️ {path}: 缺失"); fail += 1
    for rel in local_plugin_configs():  # plugins/<目录>/<相对路径> 保留结构（同拉取目录）
        src = f"{LOCAL}/plugins/{rel}"
        if os.path.exists(src):
            dst = f"{out_dir}/plugins/{rel}"
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst); ok += 1
        else:
            fail += 1
            print(f"  ⚠️ plugins/{rel}: 缺失")
    print(f"本地端 完成: ok={ok} fail={fail} → {out_dir}\n")
    return ok, fail

def fetch_all(files):
    """三路并发：Exaroton(API) + 远程 MCSM(API v9 协议) + 本地端(目录直读)"""
    print(f"并发: Exaroton + MCSM(远程) + 本地端（基准 {len(files)} 个插件配置）\n")
    with ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(fetch_exa, files)
        f2 = ex.submit(fetch_mcsm, files, get_mcsm_config(), MCSM_OUT, "MCSM(远程Win11)")
        f3 = ex.submit(fetch_local_dir)
        f1.result()
        f2.result()
        f3.result()
    print("=== 三路全部完成 ===\n")

if __name__ == "__main__":
    files = local_plugin_configs()
    print(f"本地基准配置清单: {len(files)} 个插件配置文件\n")
    fetch_all(files)
