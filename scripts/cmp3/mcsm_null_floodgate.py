#!/usr/bin/env python3
"""MCSM：floodgate.jar 置空（0 字节同名覆盖，Paper 忽略空 jar）
⚠️ 已废弃（2026-08-06）：MCSM 实际支持 DELETE /api/files/，用 mcsm_delete.py 直接删
保留仅作历史参考
"""
import sys, os, time, hashlib, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcsm_env import get_mcsm_config, mcsm_api_post

cfg = get_mcsm_config()
HOST = cfg["url"].split("//")[1].split(":")[0]

# 空文件内容（放一个无效标记，避免 0 字节可能被跳过导致旧内容残留）
content = b"DISABLED-BY-ORZMC-ADMIN"

print(f"置空 floodgate.jar ({len(content)}B) -> plugins/")
d = mcsm_api_post(cfg, "api/files/upload",
                  {"upload_dir": "/plugins", "daemonId": cfg["daemon_id"], "uuid": cfg["instance_id"]})
if not d or d.get("status") != 200:
    print(f"❌ 凭证失败: {str(d)[:100]}")
    sys.exit(1)
addr = d["data"]["addr"].replace("localhost", HOST)
url = f"http://{addr}/upload/{d['data']['password']}"
boundary = "----hb-" + str(int(time.time()))
body = b""
body += f"--{boundary}\r\n".encode()
body += f'Content-Disposition: form-data; name="file"; filename="floodgate.jar"\r\n'.encode()
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
