#!/usr/bin/env python3
"""Exaroton：用 PUT files/data 覆盖写全部配置（E3-E10 + E1/E2 已成功）
策略：GET 当前文件 → 文本替换 → PUT 覆盖（body {"text": 内容}）"""
import urllib.request, json, os, time

API_KEY = ""
for line in open(os.path.expanduser("~/.hermes/.env")):
    if line.startswith("EXAROTON_API_KEY="):
        API_KEY = line.split("=", 1)[1].strip()
        break
SID = ""
for line in open(os.path.expanduser("~/.hermes/.env")):
    if line.startswith("EXAROTON_SERVER_ID="):
        SID = line.split("=", 1)[1].strip()
        break
UA = {"User-Agent": "Mozilla/5.0", "Authorization": f"Bearer {API_KEY}"}
BASE = "https://api.exaroton.com/v1"

def api(path, method="GET", body=None):
    req = urllib.request.Request(f"{BASE}{path}", headers=UA, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")

def get_file(path):
    raw = api(f"/servers/{SID}/files/data/{path}/")
    # PUT 后响应是 {"text": "..."} 包装；GET 可能是裸文本或 JSON 包装，需兼容
    try:
        d = json.loads(raw)
        if isinstance(d, dict) and "text" in d:
            return d["text"]
    except Exception:
        pass
    return raw

def put_file(path, content):
    resp = api(f"/servers/{SID}/files/data/{path}/", "PUT", {"text": content})
    print(f"  📤 {path}: PUT 响应 {resp[:60]}")
    time.sleep(3)

def apply(path, old, new, desc):
    content = get_file(path)
    if old not in content:
        print(f"  ⚠️ {path}: 未找到 {old!r} (跳过)")
        return False
    new_content = content.replace(old, new, 1)
    put_file(path, new_content)
    print(f"  ✅ {desc}")
    return True

# E3 timeout-time 180 → 60
apply("spigot.yml", "timeout-time: 180", "timeout-time: 60", "E3 timeout-time")
# E4 anti-xray enabled false→true + engine-mode 1→2
apply("config/paper-world-defaults.yml", "enabled: false\n    engine-mode: 1", "enabled: true\n    engine-mode: 2", "E4 anti-xray")
# E5 spawn-limits 128/32 → default
apply("config/paper-world-defaults.yml", "hard: 128\n        soft: 32", "hard: default\n        soft: default", "E5 spawn-limits")
# E6 save-empty-scoreboard-teams false → true
apply("config/paper-global.yml", "save-empty-scoreboard-teams: false", "save-empty-scoreboard-teams: true", "E6 scoreboard-teams")
# E7 Essentials max-nick-length 15 → 16
apply("plugins/Essentials/config.yml", "max-nick-length: 15", "max-nick-length: 16", "E7 max-nick-length")
# E8 ViaVersion fix-1_21 false → true
apply("plugins/ViaVersion/config.yml", "fix-1_21-placement-rotation: false", "fix-1_21-placement-rotation: true", "E8 ViaVersion fix")
# E9 GP Enabled false→true + PistonMovement
apply("plugins/GriefPreventionData/config.yml", "Enabled: false", "Enabled: true", "E9a GP Enabled")
apply("plugins/GriefPreventionData/config.yml", "PistonMovement: EVERYWHERE", "PistonMovement: CLAIMS_ONLY", "E9b GP Piston")
# E10 EzShops min-price 0.0 → 1.0
apply("plugins/EzShops/config.yml", "min-price: 0.0", "min-price: 1.0", "E10 EzShops min-price")

print("\n✅ 全部处理完成")
