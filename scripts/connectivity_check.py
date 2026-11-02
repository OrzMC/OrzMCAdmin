#!/usr/bin/env python3
"""OrzMC 统一连通性检查 v1（2026-11-02）

一次说清「玩家到底连不连得上」——四个层次全部覆盖：

  ① 网络层    DNS 解析 / TCP 握手
  ② Java 层   Minecraft 协议握手 + Status Ping（版本、协议号、在线人数、MOTD）
  ③ 基岩旧协议 RakNet UDP Unconnected Ping → Pong（transport: raknet / both 才有）
  ④ 基岩新协议 NetherNet 信令 GET /v1/join（transport: nethernet / both 才有）
              返回服务端支持的 Bedrock 协议号/版本 + 实时人数
  ⑤ TLS 信令   域名入口必需的 HTTPS（无 TLS 时域名玩家卡「加载延迟」）
  ⑥ 公网可达  check-host.net 外部节点 TCP 探测（--external，需公网 IP:端口）

用法:
  python3 connectivity_check.py                      # 默认：测试服双实例（LAN）+ 生产两端
  python3 connectivity_check.py --only paper          # 只测 paper
  python3 connectivity_check.py --external           # 追加外部节点 TCP 探测
  python3 connectivity_check.py --json               # 机器可读（周巡检用）
  python3 connectivity_check.py --host example.com --java 25565 --bedrock 19132   # 自定义单目标
  python3 connectivity_check.py -h

退出码: 0=全部通过 / 1=有 FAIL / 3=仅 WARN（降级/不可判定）

⚠️ 本机若开 Clash/Surge 等 TUN 代理，**域名**的 TCP 探测可能被伪造（fake-IP）；
   判定公网可达性请用真实公网 IP + --external（外部节点结论为准）。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import time
import urllib.error
import urllib.request

# ---------------- 默认目标 ----------------
LAN_HOST = os.environ.get("ORZMC_LAN_HOST", "192.168.0.33")
PUBLIC_HOST = os.environ.get("ORZMC_PUBLIC_HOST", "")  # 留空则用域名 + DoH 取真值
PUBLIC_DOMAIN = os.environ.get("ORZMC_PUBLIC_DOMAIN", "dev.{SERVER_NAME}.cn")

TARGETS = {
    # name: host, java_port, bedrock_port, webrtc_port, note
    "paper": dict(host=LAN_HOST, java=25565, bedrock=19132, webrtc=19134, note="测试服 Paper（LAN）"),
    "folia": dict(host=LAN_HOST, java=25566, bedrock=19133, webrtc=19135, note="测试服 Folia（LAN）"),
    "paper-pub": dict(host=PUBLIC_HOST or PUBLIC_DOMAIN, java=25565, bedrock=19132, webrtc=19134,
                      note="测试服 Paper（公网，域名经 DoH 解真 IP）"),
    "prod-mcsm": dict(host="{SERVER_HOST}", java=25565, bedrock=19132, webrtc=None, note="国内服生产 MCSM"),
}

RAKNET_MAGIC = bytes([0x00, 0xFF, 0xFF, 0x00, 0xFE, 0xFE, 0xFE, 0xFE,
                      0xFD, 0xFD, 0xFD, 0xFD, 0x12, 0x34, 0x56, 0x78])


# ---------------- 工具 ----------------
def resolve(host):
    try:
        infos = socket.getaddrinfo(host, None)
        return sorted({i[4][0] for i in infos if i[0] == socket.AF_INET}) or \
               sorted({i[4][0] for i in infos})
    except Exception as e:
        return f"DNS 失败: {type(e).__name__}"


def _is_ip_literal(h):
    try:
        socket.inet_aton(h)
        return True
    except Exception:
        return False


def is_fake_ip(ip):
    """Clash/Surge TUN 常见的 fake-IP 段（198.18.0.0/15）"""
    try:
        a, b, c, d = [int(x) for x in ip.split(".")]
    except Exception:
        return False
    return a == 198 and b in (18, 19)


def doh_resolve(host, timeout=8):
    """通过 Cloudflare DoH 拿真实 A 记录（绕开本机 TUN fake-IP）"""
    try:
        url = "https://1.1.1.1/dns-query?name=%s&type=A" % host
        req = urllib.request.Request(url, headers={"accept": "application/dns-json",
                                                  "User-Agent": "OrzMC-ConnectivityCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode())
        ips = [a.get("data") for a in d.get("Answer", []) if a.get("type") == 1]
        return ips or None
    except Exception:
        return None


def varint(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | 0x80]) if n else bytes([b])
        if not n:
            return out


def read_varint(sock):
    val = 0
    for i in range(5):
        b = sock.recv(1)
        if not b:
            raise IOError("连接被关闭")
        val |= (b[0] & 0x7F) << (7 * i)
        if not b[0] & 0x80:
            return val
    raise IOError("VarInt 过长")


def java_status(host, port, timeout=6, proto=767):
    """MC 协议：Handshake(next=1) + Status Request → Status Response JSON"""
    t0 = time.time()
    s = socket.create_connection((host, port), timeout=timeout)
    try:
        host_b = host.encode()
        hs = varint(0x00) + varint(proto) + varint(len(host_b)) + host_b + struct.pack(">H", port) + varint(1)
        s.sendall(varint(len(hs)) + hs)
        s.sendall(varint(1) + varint(0x00))  # status request
        ln = read_varint(s)
        buf = b""
        while len(buf) < ln:
            chunk = s.recv(ln - len(buf))
            if not chunk:
                break
            buf += chunk
        ms = (time.time() - t0) * 1000
        # 跳过 packet id
        idx = 0
        while True:
            b = buf[idx]
            idx += 1
            if not b & 0x80:
                break
        slen = 0
        shift = 0
        while True:
            b = buf[idx]
            idx += 1
            slen |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                break
        d = json.loads(buf[idx:idx + slen].decode("utf-8", "replace"))
        return dict(ok=True, ms=ms, version=d.get("version", {}).get("name"),
                    protocol=d.get("version", {}).get("protocol"),
                    players=d.get("players", {}).get("online"),
                    max=d.get("players", {}).get("max"),
                    motd=_flatten(d.get("description")))
    finally:
        s.close()


def _flatten(desc):
    if isinstance(desc, str):
        return desc
    if isinstance(desc, dict):
        return (desc.get("text") or "") + "".join(_flatten(e) for e in desc.get("extra", []))
    if isinstance(desc, list):
        return "".join(_flatten(e) for e in desc)
    return ""


def raknet_ping(host, port, timeout=5):
    """基岩旧协议：RakNet Unconnected Ping → Pong"""
    txn = os.urandom(8)
    pkt = b"\x01" + struct.pack(">q", int(time.time() * 1000)) + RAKNET_MAGIC + txn
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    t0 = time.time()
    try:
        s.sendto(pkt, (host, port))
        data, _ = s.recvfrom(4096)
        ms = (time.time() - t0) * 1000
        if not data or data[0] != 0x1C:
            return dict(ok=False, err=f"非 Pong 应答 ({data[:8].hex()})")
        off = 35  # 0x1C + time(8) + serverGUID(8) + magic(16) + strlen(2)
        slen = struct.unpack(">H", data[33:35])[0]
        motd = data[off:off + slen].decode("utf-8", "replace")
        parts = motd.split(";")
        return dict(ok=True, ms=ms, motd=motd,
                    bedrock_version=parts[3] if len(parts) > 3 else None,
                    protocol=parts[2] if len(parts) > 2 else None,
                    players=parts[4] if len(parts) > 4 else None,
                    max=parts[5] if len(parts) > 5 else None)
    except socket.timeout:
        return dict(ok=False, err="UDP 无应答（超时：未启用 RakNet / 端口未转发）")
    except Exception as e:
        return dict(ok=False, err=f"{type(e).__name__}: {e}")
    finally:
        s.close()


def nethernet_join(host, port, timeout=6, scheme="http"):
    """基岩新协议：NetherNet 信令 GET /v1/join"""
    url = f"{scheme}://{host}:{port}/v1/join"
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": "OrzMC-ConnectivityCheck/1.0"}), timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            ms = (time.time() - t0) * 1000
        d = json.loads(raw)
        return dict(ok=True, ms=ms, name=d.get("name"), version=d.get("version"),
                    protocol=d.get("protocol"), players=d.get("players"),
                    max=d.get("maxPlayers"), level=d.get("level"),
                    transport_layer=d.get("transportLayer"))
    except urllib.error.HTTPError as e:
        return dict(ok=False, err=f"HTTP {e.code}（信令在线但路径不符）", code=e.code)
    except Exception as e:
        return dict(ok=False, err=f"{type(e).__name__}: {str(e)[:60]}")


def https_signal(host, port, timeout=6):
    """域名入口的硬要求：客户端对域名强制 TLS。
    返回 ok=True 表示基岩端口提供 HTTPS 信令（域名玩家可直连，无 TOFU 弹窗）"""
    import ssl as _ssl
    ctx = _ssl._create_unverified_context()
    try:
        with urllib.request.urlopen("https://%s:%s/v1/join" % (host, port),
                                    timeout=timeout, context=ctx) as r:
            return dict(ok=True, ms=None, code=r.status)
    except Exception as e:
        msg = str(e)[:70]
        hint = ""
        if "EOF occurred" in msg or "SSL" in type(e).__name__:
            hint = "端口只讲明文 HTTP（未配 TLS 证书）"
        return dict(ok=False, err=f"{type(e).__name__}: {msg}", hint=hint)


def external_tcp(host, port, nodes=3, wait=14):
    """check-host.net 外部节点 TCP 探测（真实公网可达性）"""
    try:
        req = urllib.request.Request(
            f"https://check-host.net/check-tcp?host={host}:{port}&max_nodes={nodes}",
            headers={"Accept": "application/json", "User-Agent": "OrzMC-ConnectivityCheck/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            rid = json.loads(r.read().decode()).get("request_id")
        if not rid:
            return dict(ok=False, err="未拿到 request_id")
        time.sleep(wait)
        req2 = urllib.request.Request(f"https://check-host.net/check-result/{rid}",
                                      headers={"Accept": "application/json",
                                               "User-Agent": "OrzMC-ConnectivityCheck/1.0"})
        with urllib.request.urlopen(req2, timeout=20) as r2:
            res = json.loads(r2.read().decode())
        ok_nodes, bad = [], []
        for node, val in res.items():
            if isinstance(val, list) and val and isinstance(val[0], dict) and "time" in val[0]:
                ok_nodes.append(node)
            else:
                bad.append(node)
        return dict(ok=bool(ok_nodes), ok_nodes=len(ok_nodes), bad_nodes=len(bad),
                    total=len(res), err=None if ok_nodes else "全部节点不可达")
    except Exception as e:
        return dict(ok=False, err=f"{type(e).__name__}: {str(e)[:60]}")


# ---------------- 单目标检查 ----------------
def check_target(name, cfg, do_external=False, timeout=6):
    host, jport, bport = cfg["host"], cfg["java"], cfg["bedrock"]
    out = dict(name=name, note=cfg.get("note", ""), host=host,
               java_port=jport, bedrock_port=bport, checks={}, fail=[], warn=[])

    ips = resolve(host)
    out["checks"]["dns"] = ips
    if isinstance(ips, str):
        out["fail"].append(ips)
        return out
    ip = ips[0]
    # 本机 TUN 代理会把域名解析成 198.18.x.x（fake-IP）→ 必须用 DoH 真值
    if is_fake_ip(ip) and not _is_ip_literal(host):
        real = doh_resolve(host)
        if real:
            out["checks"]["dns_tun_bypass"] = f"本机 TUN fake-IP {ip} → DoH 真值 {real[0]}"
            ip = real[0]
        else:
            out["fail"].append(f"DNS 被 TUN 劫持为 {ip} 且 DoH 解析失败，本次结果不可信")
            out["checks"]["dns_invalid"] = True
            return out

    # Java
    try:
        js = java_status(ip, jport, timeout)
        out["checks"]["java"] = js
    except Exception as e:
        out["checks"]["java"] = dict(ok=False, err=f"{type(e).__name__}: {str(e)[:60]}")
        out["fail"].append(f"Java {jport} 状态握手失败")

    # Bedrock 旧协议
    rk = raknet_ping(ip, bport, timeout)
    out["checks"]["raknet"] = rk

    # Bedrock 新协议（信令）
    tls = https_signal(ip, bport, timeout)
    out["checks"]["tls_signal"] = tls
    if not tls.get("ok"):
        # 2026-11-02 更正：Geyser 2.12.1 + Bedrock 26.60 实测「域名 + 无证书」可正常连（测试服 dev.{SERVER_NAME}.cn 即为证）
        # → 无 TLS 只影响体验（会弹一次 TOFU 信任框），不是可用性前提，故记 INFO 不记 WARN
        out.setdefault("info", []).append(
            "基岩端口无 HTTPS 信令（%s）→ 玩家域名连接仍可用，但会弹一次「信任此服务器」；配证书可免弹窗"
            % (tls.get("hint") or "TLS 不可用"))

    nn = nethernet_join(ip, bport, timeout)
    out["checks"]["nethernet"] = nn
    if not nn.get("ok"):
        out["warn"].append(f"NetherNet 信令(TCP {bport}) 不可用：{nn.get('err')}")
    # 判读纪律（2026-11-02）：`transport: nethernet` 单端口模式下 RakNet 本就无应答，
    # 只要 NetherNet 通就属正常，记 INFO 不记 WARN —— 否则周巡检每周都误报。
    if not rk.get("ok") and nn.get("ok"):
        out.setdefault("info", []).append(
            f"RakNet(UDP {bport}) 无应答，但 NetherNet 信令正常 → 与 nethernet 单端口模式一致（正常）；"
            "若要兼容 26.40 之前的老客户端，需 transport=both + 另开 UDP webrtc-port")

    if rk.get("ok") and nn.get("ok"):
        out["checks"]["bedrock_mode"] = "both ✅（新旧客户端都能进）"
    elif nn.get("ok"):
        out["checks"]["bedrock_mode"] = "NetherNet ✅ / RakNet 无应答（nethernet 单端口或 raknet 关闭；26.40+ 新客户端可进，老客户端需 transport=both + UDP webrtc-port）"
    elif rk.get("ok"):
        out["checks"]["bedrock_mode"] = "RakNet ✅ / NetherNet 不可用 ⚠️（26.40+ 新客户端进不来）"
    else:
        out["checks"]["bedrock_mode"] = "不可用 ❌"
        out["fail"].append("基岩两条通道都不通")

    # 外部节点
    if do_external:
        out["checks"]["external_tcp"] = external_tcp(ip, jport)
        if not out["checks"]["external_tcp"].get("ok"):
            out["warn"].append(f"公网 TCP {jport} 外部节点不可达")
    return out


def render(results, as_json=False):
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
        return
    for r in results:
        c = r["checks"]
        print("=" * 74)
        print(f"【{r['name']}】{r['note']}  {r['host']}  (Java {r['java_port']} / 基岩 {r['bedrock_port']})")
        print(f"  DNS      {c.get('dns')}")
        js = c.get("java", {})
        if js.get("ok"):
            print(f"  Java ✅  {js['ms']:.0f}ms | 版本 {js['version']} | 协议 {js['protocol']} | "
                  f"玩家 {js['players']}/{js['max']}")
        else:
            print(f"  Java ❌  {js.get('err')}")
        rk = c.get("raknet", {})
        if rk.get("ok"):
            print(f"  RakNet(旧)   ✅ {rk['ms']:.0f}ms | 基岩版本 {rk.get('bedrock_version')} "
                  f"| 协议 {rk.get('protocol')} | {rk.get('players')}/{rk.get('max')}")
        else:
            nn_ok = c.get("nethernet", {}).get("ok")
            print(f"  RakNet(旧)   {'ℹ️ 无应答（nethernet 单端口模式属正常）' if nn_ok else '⚠️ ' + str(rk.get('err'))}")
        nn = c.get("nethernet", {})
        if nn.get("ok"):
            print(f"  NetherNet(新)✅ {nn['ms']:.0f}ms | 版本 {nn.get('version')} | 协议 {nn.get('protocol')} "
                  f"| 玩家 {nn.get('players')}/{nn.get('max')}")
        else:
            print(f"  NetherNet(新)⚠️ {nn.get('err')}")
        tls = c.get("tls_signal", {})
        print(f"  HTTPS 信令  {'✅ 可用（域名连接无信任弹窗）' if tls.get('ok') else 'ℹ️ 无（域名仍可连，会弹一次 TOFU 信任）'}")
        if c.get("dns_tun_bypass"):
            print(f"  DNS 修正    {c['dns_tun_bypass']}")
        print(f"  基岩模式  {c.get('bedrock_mode')}")
        ex = c.get("external_tcp")
        if ex:
            print(f"  公网 TCP  {'✅ ' + str(ex.get('ok_nodes')) + '/' + str(ex.get('total')) + ' 节点可达' if ex.get('ok') else '❌ ' + str(ex.get('err'))}")
    print("=" * 74)
    fails = [(r["name"], f) for r in results for f in r["fail"]]
    warns = [(r["name"], w) for r in results for w in r["warn"]]
    infos = [(r["name"], i) for r in results for i in r.get("info", [])]
    print(f"汇总: 目标 {len(results)} 个 | FAIL {len(fails)} | WARN {len(warns)}")
    for n, f in fails:
        print(f"  ❌ [{n}] {f}")
    for n, w in warns:
        print(f"  ⚠️ [{n}] {w}")
    for n, i in infos:
        print(f"  ℹ️ [{n}] {i}")


def main():
    ap = argparse.ArgumentParser(description="OrzMC 统一连通性检查（Java + 基岩旧/新协议）")
    ap.add_argument("--only", help="只测指定目标（逗号分隔，见 --list）")
    ap.add_argument("--list", action="store_true", help="列出内置目标")
    ap.add_argument("--host", help="自定义目标 host（配合 --java/--bedrock）")
    ap.add_argument("--java", type=int, default=25565)
    ap.add_argument("--bedrock", type=int, default=19132)
    ap.add_argument("--external", action="store_true", help="追加 check-host 外部节点 TCP 探测")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--timeout", type=float, default=6.0)
    a = ap.parse_args()

    if a.list:
        for k, v in TARGETS.items():
            print(f"{k:<12} {v['note']:<24} {v['host']}:{v['java']} / 基岩 {v['bedrock']}")
        return 0

    if a.host:
        targets = {"custom": dict(host=a.host, java=a.java, bedrock=a.bedrock, note="自定义")}
    elif a.only:
        keys = [k.strip() for k in a.only.split(",") if k.strip()]
        targets = {k: TARGETS[k] for k in keys if k in TARGETS}
        missing = [k for k in keys if k not in TARGETS]
        if missing:
            print(f"未知目标: {missing}（用 --list 查看）")
            return 2
    else:
        targets = TARGETS

    results = [check_target(n, c, a.external, a.timeout) for n, c in targets.items()]
    render(results, a.json)
    if any(r["fail"] for r in results):
        return 1
    if any(r["warn"] for r in results):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
