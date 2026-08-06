#!/usr/bin/env python3
"""MCSM：读 floodgate.jar 大小（确认置空状态）"""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcsm_env import get_mcsm_config, mcsm_download

cfg = get_mcsm_config()
for path in ["/plugins/floodgate.jar", "/plugins/floodgate/config.yml", "/plugins/update"]:
    data = mcsm_download(cfg, path)
    if data:
        print(f"{path}: {len(data)}B (sha256={hashlib.sha256(data).hexdigest()[:10]})")
    else:
        print(f"{path}: 读取失败/不存在")
