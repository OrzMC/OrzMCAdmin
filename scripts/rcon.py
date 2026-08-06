#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RCON 客户端（通用版）：python3 rcon.py <命令> [端口] [密码]
- 端口默认 25575；密码默认从环境变量 RCON_PASSWORD 读取（未设置则必须显式传第 3 参）
- 多包响应循环读取；AUTH FAIL 退出码 1
用法示例:
  python3 rcon.py "list" 25575
  python3 rcon.py "stop" 25576
  python3 rcon.py "transfer 192.168.0.35 25566 HermesBot" 25575
"""
import socket
import struct
import sys
import os

HOST = "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 25575
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("RCON_PASSWORD", "")
CMD = sys.argv[1] if len(sys.argv) > 1 else "list"

if not PASSWORD:
    print("ERROR: 未提供 RCON 密码（第 3 参数或环境变量 RCON_PASSWORD）")
    sys.exit(1)


def send_packet(sock, pkt_id, pkt_type, payload):
    body = struct.pack("<ii", pkt_id, pkt_type) + payload.encode("utf-8") + b"\x00\x00"
    sock.sendall(struct.pack("<i", len(body)) + body)


def read_packet(sock):
    length = struct.unpack("<i", sock.recv(4))[0]
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            break
        data += chunk
    pkt_id, pkt_type = struct.unpack("<ii", data[:8])
    payload = data[8:-2].decode("utf-8", errors="replace")
    return pkt_id, pkt_type, payload


sock = socket.create_connection((HOST, PORT), timeout=5)
send_packet(sock, 1, 3, PASSWORD)
pid, ptype, payload = read_packet(sock)
if pid == -1:
    print("AUTH FAIL")
    sys.exit(1)

send_packet(sock, 2, 2, CMD)
while True:
    try:
        pid, ptype, payload = read_packet(sock)
        print(payload)
        if ptype == 0:
            break
    except Exception:
        break
