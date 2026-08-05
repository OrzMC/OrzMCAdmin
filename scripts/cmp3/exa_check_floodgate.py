#!/usr/bin/env python3
"""Exaroton：查询服务器状态 + floodgate key.pem 是否生成"""
import urllib.request, json, os

key = os.environ.get("EXAROTON_API_KEY", "")
sid = os.environ.get("EXAROTON_SERVER_ID", "")

def api(path):
    req = urllib.request.Request(f"https://api.exaroton.com/v1/servers/{sid}{path}")
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("User-Agent", "Mozilla/5.0")
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

d = api("/")["data"]
status_map = {0: "OFFLINE", 1: "LOADING", 2: "STARTING", 3: "ONLINE", 4: "SAVING", 5: "STOPPING", 6: "RESTARTING", 7: "CRASHED"}
print("Exaroton status:", status_map.get(d["status"], d["status"]))

# 查 floodgate key.pem
try:
    url = f"https://api.exaroton.com/v1/servers/{sid}/files/info/plugins/floodgate/key.pem/"
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("User-Agent", "Mozilla/5.0")
    raw = urllib.request.urlopen(req, timeout=30).read().decode()
    info = json.loads(raw)["data"]
    print("floodgate key.pem:", "✅ 存在" if info.get("isReadable") else "❌ 不可读", "| size:", info.get("size"))
except Exception as e:
    print("key.pem 检查:", str(e)[:80])
