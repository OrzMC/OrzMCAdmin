#!/usr/bin/env python3
"""MCSM：把旧版插件 jar 置空（PUT /api/files/ 写空内容——已验证端点）
用途：升级带版本号插件（OrzMC 1.0.13→1.0.14）时，旧 jar 无法删除（delete 端点 404），
      置空后 Paper 重启不加载空文件，避免新旧并存冲突。
用法: python3 mcsm_null_file.py /plugins/OrzMC-1.0.13-pr.153.394.jar
"""
import sys, os, json, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcsm_env import get_mcsm_config

cfg = get_mcsm_config()
path = sys.argv[1] if len(sys.argv) > 1 else "/plugins/OrzMC-1.0.13-pr.153.394.jar"
print(f"置空 {path} ...")
url = cfg["url"] + "/api/files/?" + urllib.parse.urlencode(
    {"apikey": cfg["apikey"], "daemonId": cfg["daemon_id"], "uuid": cfg["instance_id"]})
req = urllib.request.Request(url, data=json.dumps({"target": path, "text": ""}).encode(), method="PUT")
req.add_header("Content-Type", "application/json; charset=utf-8")
req.add_header("X-Requested-With", "XMLHttpRequest")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("响应:", r.read().decode()[:200])
except Exception as e:
    print("❌ 请求失败:", e)
