#!/bin/bash
# OrzMC: 让本机对外服务的应答包绕开 Clash TUN（通用版，与端口无关）
#
# 背景（2026-09-11 实测）:
#   Clash TUN 网卡(198.18.0.1) 默认路由 metric=1 优先于 Wi-Fi 的 metric=45，
#   本机发出的包（含"入站连接的应答"）会走 TUN：出口错网卡、源地址还被定成 198.18.0.1
#     - Java(TCP)   ：SYN-ACK 钻进隧道 → 外网玩家超时
#     - Bedrock(UDP)：pong 从 198.18.0.1 发出 → 客户端丢弃
#   局域网内直连不受影响 → 表现为"内网通、外网不通"。
#
# 核心修复（通用、零维护）:
#   ip rule: from <LAN IP> lookup 100
#   语义 = 凡是"源地址是本机 LAN IP"的包（即所有监听在 LAN IP 上的服务，无论端口），
#          一律用 Wi-Fi 出口 + Wi-Fi 源地址。代理流量源地址是 TUN(198.18.x) → 不受影响。
#   → 以后新增/自定义任何端口都无需改这里。
#
# 兜底（可选）: 对已知游戏端口再加按源端口的规则，防极端情况下源地址未被选中的场景。
#
# 幂等；供开机自愈（Windows 计划任务 OrzMC-MC-Reply-Route 每 10min 调一次）。
# 用法: orzmc-mc-reply-route.sh [--check|--force]
# 环境变量: ORZMC_IFACE / ORZMC_GW / ORZMC_SIP / ORZMC_TCP_PORTS / ORZMC_UDP_PORTS

set -u

IFACE="${ORZMC_IFACE:-eth4}"
GW="${ORZMC_GW:-192.168.0.1}"
SIP="${ORZMC_SIP:-192.168.0.33}"
LAN="$(echo "$SIP" | cut -d. -f1-3).0/24"
TABLE=100
TCP_PORTS="${ORZMC_TCP_PORTS:-25565 25566 25567}"
UDP_PORTS="${ORZMC_UDP_PORTS:-19132 19133 19134}"
FROM_PREF=85
SPORT_PREF=90

MODE="${1:-apply}"

need_apply() {
  ip route show table $TABLE 2>/dev/null | grep -q "dev $IFACE" || return 0
  ip rule show | grep -q "from $SIP lookup $TABLE" || return 0
  for p in $TCP_PORTS; do ip rule show | grep -q "ipproto tcp sport $p lookup $TABLE" || return 0; done
  for p in $UDP_PORTS; do ip rule show | grep -q "ipproto udp sport $p lookup $TABLE" || return 0; done
  return 1
}

if [ "$MODE" = "--check" ]; then
  if need_apply; then echo "MISSING"; exit 1; else echo "OK"; exit 0; fi
fi

if [ "$MODE" != "--force" ] && ! need_apply; then
  echo "OK (rules already in place)"; exit 0
fi

# 等网卡就绪（开机自愈场景）
for _ in $(seq 1 30); do
  ip link show "$IFACE" >/dev/null 2>&1 && ip -4 addr show "$IFACE" | grep -q "$SIP" && break
  sleep 2
done

ip route replace default via "$GW" dev "$IFACE" src "$SIP" table $TABLE
ip route replace "$LAN" dev "$IFACE" src "$SIP" table $TABLE

# ① 通用规则：源 = LAN IP 的所有包（覆盖任意端口）
ip rule del from "$SIP" table $TABLE 2>/dev/null
ip rule add from "$SIP" table $TABLE pref $FROM_PREF

# ② 兜底：已知游戏端口按源端口
for p in $UDP_PORTS; do
  ip rule del ipproto udp sport "$p" table $TABLE 2>/dev/null
  ip rule add ipproto udp sport "$p" table $TABLE pref $SPORT_PREF
done
for p in $TCP_PORTS; do
  ip rule del ipproto tcp sport "$p" table $TABLE 2>/dev/null
  ip rule add ipproto tcp sport "$p" table $TABLE pref $SPORT_PREF
done

echo "APPLIED table=$TABLE iface=$IFACE src=$SIP rule='from $SIP' + sport=[tcp:$TCP_PORTS udp:$UDP_PORTS]"
