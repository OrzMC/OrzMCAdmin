#!/usr/bin/env python3
"""Exaroton：删除 floodgate.jar + floodgate 配置目录"""
import urllib.request, json, os

key = os.environ.get("EXAROTON_API_KEY", "")
sid = os.environ.get("EXAROTON_SERVER_ID", "")

def api(path, method="GET"):
    url = f"https://api.exaroton.com/v1/servers/{sid}/files/data/{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()[:80]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:100]

# 1. 备份 key.pem
try:
    st, raw = api("plugins/floodgate/key.pem/")
    if st == 200:
        d = json.loads(raw)
        key_data = d.get("text", "")
        with open("/tmp/exa_floodgate_key_backup.pem", "w") as f:
            f.write(key_data)
        print(f"key.pem 已备份 ({len(key_data)} 字符)")
    else:
        print(f"key.pem 备份跳过 ({st})")
except Exception as e:
    print("key.pem 备份失败:", e)

# 2. 删 floodgate.jar
st, resp = api("plugins/floodgate.jar/", "DELETE")
print(f"删除 floodgate.jar: {st} {resp}")

# 3. 删 floodgate 配置目录（尝试，可能失败但无害）
st2, resp2 = api("plugins/floodgate/", "DELETE")
print(f"删除 floodgate/ 目录: {st2} {resp2[:60] if isinstance(resp2, str) else resp2}")
