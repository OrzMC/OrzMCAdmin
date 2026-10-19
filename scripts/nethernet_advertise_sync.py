#!/usr/bin/env python3
"""NetherNet 公网地址自动同步（OrzMC 本地测试服）。

背景：Geyser 的 signaling.builtin.advertise-addresses 只接受 **数字 IP 字面量**
（EndpointAddress 源码明确拒绝域名："Expected a numeric IP address"），而本机公网 IP
来自动态域名 → 必须有人盯着 A 记录变化并改写配置。

本脚本：DoH 解析域名 → 与两个实例的 advertise-addresses 比对 → 不同则改配置并
`geyser reload`（只重载 Geyser，不踢 Java 玩家）。

用法：
  python nethernet_advertise_sync.py          # 检查并自动修正（cron 用）
  python nethernet_advertise_sync.py --dry    # 只报告
  python nethernet_advertise_sync.py -v       # 打印详细过程
退出码：0 正常（含"无变化"）；1 出错。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

DOMAIN = "dev.{SERVER_NAME}.cn"
MCSM_DIR = r"E:/orzmc/mcsmanager"
INSTANCES = [
    # (昵称, 实例 UUID, Geyser advertise 用的宿主端口)
    ("papermc-test", "716c2fb712154c36ba5ab0f1480d3f87", 19134),
    ("folia-test", "8A932DD47F4D42AAAD6A6A9A5FAD2A91", 19135),
]
LOG = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "logs", "nethernet-advertise-sync.log")


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def resolve_a(domain: str, verbose: bool = False) -> str:
    """DoH 查 A 记录。Clash TUN 会把普通 DNS 变成 198.18.x 假 IP，必须走 DoH。"""
    endpoints = [
        ("https://1.1.1.1/dns-query", {"name": domain, "type": "A"}),
        ("https://dns.alidns.com/resolve", {"name": domain, "type": "1"}),
    ]
    last = ""
    for url, params in endpoints:
        try:
            req = urllib.request.Request(
                url + "?" + urllib.parse.urlencode(params),
                headers={"accept": "application/dns-json", "User-Agent": "nethernet-sync/1.0"},
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            ips = [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
            ips = [ip for ip in ips if not ip.startswith("198.18.")]
            if ips:
                if verbose:
                    log(f"DoH {url} -> {ips[0]}")
                return ips[0]
            last = f"{url} 无 A 记录"
        except Exception as exc:  # noqa: BLE001
            last = f"{url}: {exc}"
    raise RuntimeError(f"DNS 解析失败：{last}")


def config_path(uuid: str) -> str:
    return f"{MCSM_DIR}/daemon/data/InstanceData/{uuid}/plugins/Geyser-Spigot/config.yml"


def current_advertised(path: str) -> str | None:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^\s*advertise-addresses:\s*\[(.*?)\]", text, re.MULTILINE)
    if not m:
        return None
    first = m.group(1).split(",")[0].strip().strip('"\'')
    return re.search(r":(\d+)$", first).group(1) if re.search(r":(\d+)$", first) else ""


def set_advertised(path: str, value: str) -> None:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new, n = re.subn(
        r'^(\s*advertise-addresses:\s*).*$',
        lambda m: f'{m.group(1)}["{value}"]',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise RuntimeError(f"未找到 advertise-addresses 行：{path}")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new)


def mcsm_credentials() -> tuple[str, str]:
    """返回 (panel_base, apikey)：apikey 取面板用户文件里第一个非空 apiKey。"""
    key = ""
    for p in glob.glob(f"{MCSM_DIR}/web/data/User/*.json"):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if d.get("apiKey"):
            key = d["apiKey"]
            break
    if not key:
        raise RuntimeError("找不到可用的面板 apikey")
    daemons = glob.glob(f"{MCSM_DIR}/web/data/RemoteServiceConfig/*.json")
    if not daemons:
        raise RuntimeError("找不到 RemoteServiceConfig（daemonId）")
    daemon_id = os.path.splitext(os.path.basename(daemons[0]))[0]
    return key, daemon_id


def send_command(key: str, daemon_id: str, uuid: str, command: str) -> str:
    url = "https://mcs.{SERVER_NAME}.cn/api/protected_instance/command?" + urllib.parse.urlencode(
        {"daemonId": daemon_id, "uuid": uuid, "command": command, "apikey": key}
    )
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return f"HTTP {r.status} {r.read()[:120].decode(errors='replace')}"
    except Exception as exc:  # noqa: BLE001
        return f"失败: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只检查不改写")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    try:
        ip = resolve_a(DOMAIN, args.verbose)
    except Exception as exc:  # noqa: BLE001
        log(f"❌ {exc}")
        return 1

    changed: list[tuple[str, str]] = []
    for name, uuid, port in INSTANCES:
        path = config_path(uuid)
        if not os.path.isfile(path):
            log(f"❌ {name}: 配置不存在 {path}")
            return 1
        want = f"{ip}:{port}"
        cur_port = current_advertised(path)
        if args.verbose:
            log(f"{name}: 当前 advertise 端口={cur_port} 目标={want}")
        with open(path, encoding="utf-8") as f:
            head = f.read()
        m = re.search(r'^\s*advertise-addresses:\s*\["(.*?)"\]', head, re.MULTILINE)
        cur = m.group(1) if m else None
        if cur == want:
            log(f"✅ {name}: {want}（无变化）")
            continue
        changed.append((name, uuid))
        if args.dry:
            log(f"🟡 {name}: {cur} → {want}（dry-run 未改）")
            continue
        set_advertised(path, want)
        log(f"✏️ {name}: {cur} → {want}")

    if not changed or args.dry:
        return 0

    key, daemon_id = mcsm_credentials()
    for name, uuid in changed:
        res = send_command(key, daemon_id, uuid, "geyser reload")
        log(f"🔄 {name}: geyser reload → {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
