#!/usr/bin/env python3
"""Exaroton：列出 floodgate 目录内容（找 key.pem）"""
import urllib.request, json, os

key = os.environ.get("EXAROTON_API_KEY", "")
sid = os.environ.get("EXAROTON_SERVER_ID", "")

def ls(path):
    url = f"https://api.exaroton.com/v1/servers/{sid}/files/info/{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + key)
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())["data"]
        return [(it["name"], it.get("size", "?")) for it in (d.get("children") or [])]
    except Exception as e:
        return [("ERR", str(e)[:60])]

print("plugins/floodgate/:", ls("plugins/floodgate/"))
print("plugins/Geyser-Spigot/:", ls("plugins/Geyser-Spigot/"))
