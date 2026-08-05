#!/usr/bin/env python3
"""Exaroton：日志中查 floodgate 加载 + key.pem 大小"""
import urllib.request, json, os

key = os.environ.get("EXAROTON_API_KEY", "")
sid = os.environ.get("EXAROTON_SERVER_ID", "")
url = f"https://api.exaroton.com/v1/servers/{sid}/logs/"
req = urllib.request.Request(url)
req.add_header("Authorization", "Bearer " + key)
req.add_header("User-Agent", "Mozilla/5.0")
raw = urllib.request.urlopen(req, timeout=30).read().decode()
d = json.loads(raw)
data = d.get("data")
if isinstance(data, dict):
    data = json.dumps(data, ensure_ascii=False)
text = data.replace("\\n", "\n")
found = False
for line in text.splitlines():
    if "floodgate" in line.lower():
        print("  ", line.strip()[:120])
        found = True
if not found:
    print("  (日志中未找到 floodgate 行)")

# key.pem 大小
try:
    url2 = f"https://api.exaroton.com/v1/servers/{sid}/files/info/plugins/floodgate/key.pem/"
    req2 = urllib.request.Request(url2)
    req2.add_header("Authorization", "Bearer " + key)
    req2.add_header("User-Agent", "Mozilla/5.0")
    info = json.loads(urllib.request.urlopen(req2, timeout=30).read().decode())["data"]
    print("key.pem size:", info.get("size"))
except Exception as e:
    print("key.pem:", str(e)[:80])
