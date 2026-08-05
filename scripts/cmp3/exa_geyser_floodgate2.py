#!/usr/bin/env python3
"""Exaroton：上传覆盖 Geyser config.yml（与 MCSM 成功方式一致）
流程: GET 当前 config → 改 auth-type floodgate → PUT 到临时路径 → 验证
Exaroton 无 multipart upload 端点（files/data PUT 即上传），直接 PUT 覆盖
"""
import urllib.request, json, os, re, time

key = os.environ.get("EXAROTON_API_KEY", "")
sid = os.environ.get("EXAROTON_SERVER_ID", "")
BASE = f"https://api.exaroton.com/v1/servers/{sid}/files/data/plugins/Geyser-Spigot/config.yml/"

def api(path, method="GET", data=None, ctype=None):
    req = urllib.request.Request(path, headers={"Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0"}, method=method)
    if data is not None:
        if ctype:
            req.add_header("Content-Type", ctype)
        req.data = data
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

# 1. GET 当前
raw = api(BASE).decode("utf-8", errors="replace")
try:
    text = json.loads(raw).get("text", raw)
except Exception:
    text = raw

# 2. 改 auth-type
new_text, n = re.subn(r"^(\s*)auth-type: (offline|online)", r"\1auth-type: floodgate", text, flags=re.M)
print(f"替换 {n} 处 -> floodgate")

# 3. PUT 覆盖（JSON text 包装）
resp = api(BASE, "PUT", json.dumps({"text": new_text}).encode(), "application/json")
print("PUT:", resp.decode()[:80])
time.sleep(3)

# 4. 验证
raw2 = api(BASE).decode("utf-8", errors="replace")
try:
    text2 = json.loads(raw2).get("text", raw2)
except Exception:
    text2 = raw2
for line in text2.splitlines():
    if "auth-type" in line:
        print("验证:", line.strip())
