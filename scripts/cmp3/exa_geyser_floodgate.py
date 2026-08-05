#!/usr/bin/env python3
"""Exaroton：改 Geyser config.yml auth-type → floodgate（GET → 替换 → PUT）
策略：GET 全文 → 精确替换 auth-type 行 → PUT 覆盖
"""
import urllib.request, json, os, time

key = os.environ.get("EXAROTON_API_KEY", "")
sid = os.environ.get("EXAROTON_SERVER_ID", "")
BASE = f"https://api.exaroton.com/v1/servers/{sid}/files/data/plugins/Geyser-Spigot/config.yml/"

def api(path, method="GET", body=None):
    req = urllib.request.Request(path, headers={"Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0"}, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")

# 1. GET 全文
raw = api(BASE)
try:
    d = json.loads(raw)
    text = d.get("text", raw)
except Exception:
    text = raw

# 2. 检查当前值
if "auth-type: floodgate" in text:
    print("已是 floodgate，无需修改")
else:
    # 精确替换（保留缩进）
    import re
    new_text, n = re.subn(r"^(\s*)auth-type: (offline|online)", r"\1auth-type: floodgate", text, flags=re.M)
    if n == 0:
        print("❌ 未找到 auth-type: offline/online（当前值:", [l.strip() for l in text.splitlines() if "auth-type" in l], "）")
    else:
        print(f"替换 {n} 处 auth-type: offline → floodgate")
        # 3. PUT 覆盖
        resp = api(BASE, "PUT", {"text": new_text})
        print("PUT 响应:", resp[:100])
        time.sleep(3)
