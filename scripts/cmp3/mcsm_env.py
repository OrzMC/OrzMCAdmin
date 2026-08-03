#!/usr/bin/env python3
"""MCSM 凭据加载（统一入口，从 ~/.hermes/.env 读取，禁止硬编码）
用法: from mcsm_env import get_mcsm_config, get_exaroton_config
"""
import os

ENV_FILE = os.path.expanduser("~/.hermes/.env")

def _load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        for line in open(ENV_FILE):
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def get_mcsm_config():
    """返回 MCSM 连接配置字典"""
    env = _load_env()
    return {
        "url": env.get("MCSM_URL", ""),
        "apikey": env.get("MCSM_API_KEY", ""),
        "daemon_id": env.get("MCSM_DAEMON_ID", ""),
        "instance_id": env.get("MCSM_INSTANCE_ID", ""),
    }

def get_exaroton_config():
    """返回 Exaroton 连接配置字典"""
    env = _load_env()
    return {
        "api_key": env.get("EXAROTON_API_KEY", ""),
        "server_id": env.get("EXAROTON_SERVER_ID", ""),
    }

def mcsm_api_post(cfg, path, params, retries=3, timeout=20):
    """MCSM API POST 请求（带重试）"""
    import urllib.request, urllib.parse, json, time
    url = cfg["url"] + path + "?" + urllib.parse.urlencode({**params, "apikey": cfg["apikey"]})
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=b"{}", method="POST")
            req.add_header("Content-Type", "application/json; charset=utf-8")
            req.add_header("X-Requested-With", "XMLHttpRequest")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception:
            if i < retries - 1:
                time.sleep(3)
    return None

def mcsm_download(cfg, path, retries=3):
    """MCSM 文件下载（两步法：凭证 + 真实 GET），返回 bytes 或 None"""
    import urllib.request, urllib.parse, time
    d = mcsm_api_post(cfg, "api/files/download",
                      {"file_name": path, "daemonId": cfg["daemon_id"], "uuid": cfg["instance_id"]})
    if not d or d.get("status") != 200:
        return None
    addr = d["data"]["addr"].replace("localhost", cfg["url"].split("//")[1].split(":")[0])
    fn = urllib.parse.quote(path.split("/")[-1])
    url = f"http://{addr}/download/{d['data']['password']}/{fn}"
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if i < retries - 1:
                time.sleep(4)
    return None

if __name__ == "__main__":
    c = get_mcsm_config()
    print(f"MCSM_URL={c['url']} API_KEY={'已设置' if c['apikey'] else '缺失!'} "
          f"DAEMON={c['daemon_id'][:8]}... INSTANCE={c['instance_id'][:8]}...")
    e = get_exaroton_config()
    print(f"EXAROTON_KEY={'已设置' if e['api_key'] else '缺失!'} SID={e['server_id']}")
