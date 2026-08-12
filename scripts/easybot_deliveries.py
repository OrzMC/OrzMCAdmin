#!/usr/bin/env python3
"""EasyBot 投递诊断（0.0.33+ 版）：调用 API 查询最近投递状态。

0.0.33 起投递记录迁移到 messages 表（outbound_deliveries 停止写入）；
且 SQLite WAL 模式下 docker cp 单文件会漏最近提交 → 改用 API 查询。
用法: python3 easybot_deliveries.py [条数] [base_url]
依赖: python3（urllib 标准库）；admin 密码从 ~/Services/easybot-deploy-kit-*/easybot-deploy-kit/.env 读取
"""
import json
import sys
import glob
import urllib.request
import datetime
import os

N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
BASE = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:9090'

# 从最新 deploy-kit 的 .env 读 admin 密码
env_path = None
for p in sorted(glob.glob(os.path.expanduser('~/Services/easybot-deploy-kit-*/easybot-deploy-kit/.env')),
                reverse=True):
    env_path = p
    break
if not env_path:
    print('✗ 未找到 deploy-kit .env（admin 密码来源）')
    sys.exit(2)
password = None
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line.startswith('EASYBOT_ADMIN_PASSWORD='):
            password = line.split('=', 1)[1]
            break
if not password:
    print('✗ .env 中无 EASYBOT_ADMIN_PASSWORD')
    sys.exit(2)


def api(method, path, data=None, key=None):
    req = urllib.request.Request(f'{BASE}{path}', method=method)
    req.add_header('Content-Type', 'application/json')
    if key:
        req.add_header('Authorization', f'Bearer {key}')
    body = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(req, body, timeout=15) as r:
        return json.loads(r.read() or b'{}')


key = api('POST', '/admin/login', {'password': password})['key']
msgs = api('GET', f'/api/v1/messages?limit={N}', key=key)['messages']

print(f'最近 {len(msgs)} 条投递（时间 平台 状态 内容）:')
for m in msgs:
    ts = datetime.datetime.fromtimestamp(m['timestamp'] / 1000).strftime('%H:%M:%S')
    res = (m.get('raw_data') or {}).get('result') or {}
    ok = res.get('success')
    role = (m.get('role') or '').lower()
    is_out = role == 'assistant'
    mark = '✅' if ok else ('❌' if is_out else '◌')
    text = (m.get('text') or '').replace('\n', '⏎')[:44]
    print(f'{ts} {mark} {m["platform"]:7s} [{"出" if is_out else "入"}] | {text}')
    if not ok and is_out:
        print(f'      error={res.get("error") or res.get("error_code")}')
