#!/usr/bin/env python3
"""MCSM：上传覆盖 Geyser config.yml
⚠️ 历史方案（PUT 404 时期）；2026-08-06 已确认 PUT /api/files/ 可用——新代码优先用 PUT 改配置
保留作参考：上传覆盖仍是有效方式（download 改 → upload 同名覆盖）
读 /tmp/geyser_mcsm.yml（已改 auth-type）→ 上传覆盖
"""
import sys, os, time, hashlib, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcsm_env import get_mcsm_config, mcsm_api_post

cfg = get_mcsm_config()
HOST = cfg["url"].split("//")[1].split(":")[0]

content = open("/tmp/geyser_mcsm.yml", "rb").read()
print(f"上传覆盖 config.yml ({len(content)}B, sha256={hashlib.sha256(content).hexdigest()[:12]}) -> plugins/Geyser-Spigot/")

d = mcsm_api_post(cfg, "api/files/upload",
                  {"upload_dir": "/plugins/Geyser-Spigot", "daemonId": cfg["daemon_id"], "uuid": cfg["instance_id"]})
if not d or d.get("status") != 200:
    print(f"❌ 凭证失败: {str(d)[:100]}")
    sys.exit(1)
addr = d["data"]["addr"].replace("localhost", HOST)
url = f"http://{addr}/upload/{d['data']['password']}"

boundary = "----hb-" + str(int(time.time()))
body = b""
body += f"--{boundary}\r\n".encode()
body += f'Content-Disposition: form-data; name="file"; filename="config.yml"\r\n'.encode()
body += b"Content-Type: application/octet-stream\r\n\r\n"
body += content
body += f"\r\n--{boundary}--\r\n".encode()

try:
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"✅ 上传响应: {r.read().decode()[:80]}")
except Exception as e:
    print(f"❌ 上传失败: {e}")
