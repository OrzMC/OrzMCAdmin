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
    """返回 MCSM 连接配置字典（远程 Win11 面板）"""
    env = _load_env()
    return {
        "url": env.get("MCSM_URL", "http://{SERVER_HOST}:23333/"),
        "apikey": env.get("MCSM_API_KEY", ""),
        "daemon_id": env.get("MCSM_DAEMON_ID", ""),
        "instance_id": env.get("MCSM_INSTANCE_ID", ""),
    }

def get_mcsm_local_config():
    """本机 MCSM 栈（mcs.{SERVER_NAME}.cn，本地测试服双实例；2026-09-03 迁移后成为三端审查「本地端」）"""
    env = _load_env()
    return {
        "url": env.get("MCSM_LOCAL_URL", "https://mcs.{SERVER_NAME}.cn/"),
        "apikey": env.get("MCSM_LOCAL_API_KEY", ""),
        "daemon_id": env.get("MCSM_LOCAL_DAEMON_ID", ""),
        "instance_id": env.get("MCSM_LOCAL_INSTANCE_ID", ""),
    }

def get_exaroton_config():
    """返回 Exaroton 连接配置字典"""
    env = _load_env()
    return {
        "api_key": env.get("EXAROTON_API_KEY", ""),
        "server_id": env.get("EXAROTON_SERVER_ID", "{API_TOKEN}"),
    }

def mcsm_api_post(cfg, path, params, retries=3, timeout=20):
    """MCSM API POST 请求（带重试，含限流 status 感知）"""
    import urllib.request, urllib.parse, json, time
    url = cfg["url"] + path + "?" + urllib.parse.urlencode({**params, "apikey": cfg["apikey"]})
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=b"{}", method="POST")
            req.add_header("Content-Type", "application/json; charset=utf-8")
            req.add_header("X-Requested-With", "XMLHttpRequest")
            req.add_header("User-Agent", "Mozilla/5.0")  # {SERVER_NAME} 面板中间件拦 Python UA（2026-09-09 实测）
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode())
                # 面板限流/错误也重试（500/429）
                if isinstance(d, dict) and d.get("status") in (200, None):
                    return d
        except Exception:
            pass
        if i < retries - 1:
            time.sleep(3)
    return None

def mcsm_download(cfg, path, retries=4):
    """MCSM 文件下载（两步法：凭证 + 真实 GET），返回 bytes 或 None
    两步均带重试：MCSM 并发会触发面板 500 限流（status!=200），需退避重试
    addr 兼容：老面板返回 http 地址（localhost:24444）；新面板（2026-09 迁移栈实测）
    返回 wss://host:443 —— 两种都走 HTTPS GET https://host/download/{pwd}/{fn}
    """
    import urllib.request, urllib.parse, time, re
    d = None
    for i in range(retries):
        d = mcsm_api_post(cfg, "api/files/download",
                          {"file_name": path, "daemonId": cfg["daemon_id"], "uuid": cfg["instance_id"]})
        if d and d.get("status") == 200 and d.get("data", {}).get("addr"):
            break
        # 限流/失败：指数退避（4s, 8s, 16s...）
        wait = 4 * (2 ** i)
        time.sleep(wait)
        d = None
    if not d or d.get("status") != 200:
        return None
    addr = d["data"]["addr"]
    pw = d["data"]["password"]
    fn = urllib.parse.quote(path.split("/")[-1])
    # addr 解析：'localhost:24444' | 'wss://mcs-node.{SERVER_NAME}.cn:443' | 'http(s)://host:port'
    m = re.match(r"^(?:wss?://)?([^/:]+)(?::\d+)?$", addr)
    host = m.group(1) if m else addr
    if host == "localhost":
        host = cfg["url"].split("//")[1].split(":")[0]  # 老面板：换面板主机名
    url = f"https://{host}/download/{pw}/{fn}"
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception:
            if i < retries - 1:
                time.sleep(4)
    return None

def mcsm_list(cfg, target, file_name="", page=0, page_size=100):
    """MCSM 列目录（REST GET /api/files/list），返回 [(name, type), ...]
    type: 0=目录 1=文件；file_name 是过滤词（空=列全部，新面板已无需过滤词）
    """
    import urllib.request, urllib.parse, json
    params = {"file_name": file_name, "daemonId": cfg["daemon_id"],
              "uuid": cfg["instance_id"], "target": target,
              "page": page, "page_size": page_size, "apikey": cfg["apikey"]}
    url = cfg["url"] + "api/files/list?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Content-Type": "application/json; charset=utf-8",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0"})  # 面板中间件拦 Python UA
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    if d.get("status") != 200:
        return []
    data = d.get("data") or {}
    items = data.get("items") or data.get("data") or []
    # 兼容两种字段形态（list: {items:[...]} 实测；个别版本 {data:[...]})
    if isinstance(items, dict):
        items = items.get("items") or items.get("data") or []
    out = []
    for it in items:
        if isinstance(it, dict):
            out.append((it.get("name") or it.get("fileName") or "", int(it.get("type", 1))))
    return out

def mcsm_scan_plugin_configs(cfg, skip_dirs=None, skip_files=None, max_depth=4):
    """递归扫描 MCSM 实例 plugins/ 下全部配置文件相对路径（相对 plugins/）
    替代迁移前「本地目录直读扫描」——数据源 = 巡检目标端本身（2026-09-09 两端模型）
    """
    SKIP_DIRS = skip_dirs or {"userdata", "homes", "data", "players", "backups",
                              "logs", "cache", "worlds", "messages"}
    SKIP_FILES = skip_files or {"ops.json", "whitelist.json", "banned-players.json",
                                "banned-ips.json", "usercache.json", "permissions.yml", "help.yml"}
    out = []

    def walk(rel_dir, depth):
        if depth > max_depth:
            return
        items = mcsm_list(cfg, f"/plugins/{rel_dir}".rstrip("/") or "/plugins")
        for name, typ in items:
            if typ == 0:  # 目录
                if name in SKIP_DIRS:
                    continue
                walk(f"{rel_dir}/{name}" if rel_dir else name, depth + 1)
            else:  # 文件
                if name.endswith((".yml", ".yaml")) and name not in SKIP_FILES:
                    out.append(f"{rel_dir}/{name}" if rel_dir else name)
    walk("", 1)
    return sorted(out)

if __name__ == "__main__":
    c = get_mcsm_config()
    print(f"MCSM_URL={c['url']} API_KEY={'已设置' if c['apikey'] else '缺失!'} "
          f"DAEMON={c['daemon_id'][:8]}... INSTANCE={c['instance_id'][:8]}...")
    e = get_exaroton_config()
    print(f"EXAROTON_KEY={'已设置' if e['api_key'] else '缺失!'} SID={e['server_id']}")
