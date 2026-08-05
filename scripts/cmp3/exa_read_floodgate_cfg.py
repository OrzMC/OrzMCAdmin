#!/usr/bin/env python3
"""Exaroton：读 floodgate config.yml 全文"""
import urllib.request, json, os

key = os.environ.get("EXAROTON_API_KEY", "")
sid = os.environ.get("EXAROTON_SERVER_ID", "")
url = f"https://api.exaroton.com/v1/servers/{sid}/files/data/plugins/floodgate/config.yml/"
req = urllib.request.Request(url)
req.add_header("Authorization", "Bearer " + key)
req.add_header("User-Agent", "Mozilla/5.0")
raw = urllib.request.urlopen(req, timeout=30).read().decode()
try:
    d = json.loads(raw)
    text = d.get("text", raw)
except Exception:
    text = raw
print(text)
