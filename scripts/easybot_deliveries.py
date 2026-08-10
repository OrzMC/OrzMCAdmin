#!/usr/bin/env python3
"""EasyBot 投递诊断：自动 docker cp gateway.db 并打印最近 N 条投递状态。
用法: python3 easybot_deliveries.py [条数] [容器名]
依赖: docker、python3（sqlite3 标准库）
"""
import sqlite3
import datetime
import sys
import subprocess
import os

N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
CONTAINER = sys.argv[2] if len(sys.argv) > 2 else 'easybot'
DB_PATH = '/tmp/easybot_gateway.db'

# db 超过 60s 旧或不存在则重新拷贝
need_copy = True
if os.path.exists(DB_PATH):
    age = datetime.datetime.now().timestamp() - os.path.getmtime(DB_PATH)
    need_copy = age > 60
if need_copy:
    subprocess.run(
        ['docker', 'cp', f'{CONTAINER}:/var/lib/easybot/data/gateway.db', DB_PATH],
        check=True, capture_output=True,
    )
    print(f'[copied] {DB_PATH}\n')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute('''SELECT platform, chat_id, state, created_at, substr(result_json,1,300)
               FROM outbound_deliveries ORDER BY created_at DESC LIMIT ?''', (N,))
rows = cur.fetchall()
if not rows:
    print('(无投递记录)')
    sys.exit(0)

print(f'最近 {len(rows)} 条投递（时间 平台 目标 状态）:')
for platform, chat_id, state, created, result in rows:
    ts = datetime.datetime.fromtimestamp(created / 1000).strftime('%H:%M:%S') if created else '?'
    mark = '✅' if state == 'succeeded' else '❌'
    print(f'{ts} {mark} {platform:8s} {(chat_id or "")[:28]:28s} {state}')
    if state != 'succeeded' and result and result != 'None':
        print(f'      {result[:240]}')

conn.close()
