#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caddy 证书到期 / 续期失败哨兵（静默设计：全绿不输出）。

检查项：
  1. E:/orzmc/caddy/data 下每张 LE 证书的剩余天数（<21 天告警）
  2. 期望覆盖的子域是否都有证书（缺失即告警）
  3. orzmc-caddy 容器是否在跑
  4. 过去 24h 日志里是否有 ACME / tls 相关 error

有任何一项异常才打印（cron 用 no_agent，空 stdout = 不发消息）。
"""
import subprocess, sys, datetime, pathlib

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from orzmc_paths import docker_argv  # noqa: E402  本机无 Windows docker.exe → 自动退回 wsl -e docker

DOCKER = docker_argv()
DATA = pathlib.Path(r"E:/orzmc/caddy/data/caddy/certificates")
EXPECTED = {"dev.{SERVER_NAME}.cn", "mcs.{SERVER_NAME}.cn", "easybot.{SERVER_NAME}.cn", "music.{SERVER_NAME}.cn"}
MIN_DAYS = 21
problems, rows = [], []

def sh(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")
    except Exception as e:
        return 999, str(e)

def enddate(crt):
    rc, out = sh(["openssl", "x509", "-in", str(crt), "-noout", "-enddate"])
    if rc != 0 or "notAfter=" not in out:
        return None, out.strip()[:120]
    raw = out.split("notAfter=")[1].strip().split("\n")[0].strip()
    try:
        return datetime.datetime.strptime(raw, "%b %d %H:%M:%S %Y GMT"), None
    except Exception:
        return None, raw

# 1+2 证书
seen = set()
certs = sorted(DATA.glob("**/*.crt")) if DATA.exists() else []
if not certs:
    problems.append(f"证书目录为空或不存在：{DATA}（Caddy 数据卷被删？）")
for crt in certs:
    domain = crt.stem
    seen.add(domain)
    exp, err = enddate(crt)
    if exp is None:
        problems.append(f"{domain}: 无法读取到期时间（{err}）")
        continue
    days = (exp - datetime.datetime.utcnow()).total_seconds() / 86400
    rows.append(f"{domain}: 剩 {days:.0f} 天（{exp:%Y-%m-%d}）")
    if days < 0:
        problems.append(f"{domain}: 证书已过期 {-days:.0f} 天")
    elif days < MIN_DAYS:
        problems.append(f"{domain}: 只剩 {days:.0f} 天，续期未按期完成")

for d in sorted(EXPECTED - seen):
    problems.append(f"{d}: 没有找到证书文件")

# 3 容器
rc, out = sh(DOCKER + ["inspect", "-f", "{{.State.Running}}", "orzmc-caddy"], timeout=60)
if rc != 0:
    problems.append("orzmc-caddy 容器查不到（docker inspect 失败：" + out.strip()[:160] + "）")
elif "true" not in out.lower():
    problems.append("orzmc-caddy 容器未运行")

# 4 ACME 报错
rc, logs = sh(DOCKER + ["logs", "--since", "24h", "orzmc-caddy"], timeout=90)
if rc == 0:
    # 只认 TLS/ACME 子系统的 error；http.log.error.* 里的 404/EOF 是正常扫描与探测噪声
    bad = [l for l in logs.splitlines()
           if '"level":"error"' in l
           and ('"logger":"tls' in l or '"logger":"http.acme_client"' in l or 'acme' in l.lower() and '"logger":"http' not in l)]
    if bad:
        problems.append("过去 24h ACME/TLS 报错 " + str(len(bad)) + " 条，末条：\n    " + bad[-1][:300])

if problems:
    print("Caddy 证书哨兵｜发现问题 " + str(len(problems)) + " 项")
    for p in problems:
        print("  - " + p)
    print("")
    print("当前证书状态：")
    for r in rows:
        print("  " + r)
    print("")
    print("排查：docker logs --since 72h orzmc-caddy | grep -i 'acme\\|renew'")
    print("     宿主目录 E:/orzmc/caddy/data 不要删（删了会重签，触发 LE 配额）")
