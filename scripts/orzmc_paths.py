"""orzmc_paths —— Windows 端统一路径 / 交付 / 脱敏工具（2026-11-16 迁移）

三件事：
1. `env(key)`：读 Hermes .env（%LOCALAPPDATA%\\hermes\\.env），已存在的环境变量优先
2. `deliver_dir()`：交付目录。老板的 S: 盘 = Mac 共享 `\\\\{LAN_IP}\\下载`；
   顺序：S:\\ → UNC → 本机 E:/orzmc/deliver（全部失败也不抛异常，返回最后一个并置 .fallback=True）
3. `redact(text)`：公网 IP 脱敏（报告/文档落盘前强制），保留 127.0.0.1 / 0.0.0.0 / 私网段

用法：
    from orzmc_paths import env, deliver_dir, redact, reports_dir, save_report
"""
from __future__ import annotations

import sys
try:  # Windows 控制台默认 GBK：统一转 UTF-8，避免 emoji/中文触发 UnicodeEncodeError 中断巡检
    import sys as _sys
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os
import pathlib
import re
import socket

LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
HERMES_HOME = pathlib.Path(LOCALAPPDATA) / "hermes"
ENV_FILE = HERMES_HOME / ".env"

UNC_DELIVER = r"\\{LAN_IP}\下载"
LOCAL_DELIVER = pathlib.Path("E:/orzmc/deliver")
REPORTS = pathlib.Path("E:/orzmc/reports")

_ENV_CACHE = None


def env(key: str, default: str = "") -> str:
    global _ENV_CACHE
    if key in os.environ and os.environ[key]:
        return os.environ[key]
    if _ENV_CACHE is None:
        _ENV_CACHE = {}
        if ENV_FILE.is_file():
            for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    _ENV_CACHE[k.strip()] = v.strip().strip('"').strip("'")
    return _ENV_CACHE.get(key, default)


def _writable(p: pathlib.Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ("_w_" + str(os.getpid()) + ".tmp")
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def deliver_dir() -> tuple[pathlib.Path, str]:
    """返回 (可写交付目录, 说明)。顺序 S:\\ → UNC → E:/orzmc/deliver"""
    cands = []
    if os.path.exists("S:\\"):
        cands.append((pathlib.Path("S:/"), "S: 映射盘（= Mac 共享「下载」）"))
    cands.append((pathlib.Path(UNC_DELIVER), "UNC " + UNC_DELIVER))
    cands.append((LOCAL_DELIVER, "本机兜底 E:/orzmc/deliver"))
    for p, note in cands:
        if _writable(p):
            return p, note
    return LOCAL_DELIVER, "全部不可写（已强行创建本机目录）"


def reports_dir() -> pathlib.Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    return REPORTS


def save_report(name: str, text: str, also_deliver: bool = True) -> list[str]:
    """报告脱敏后落盘到 reports/ 并（可选）拷到交付目录；返回写入路径列表"""
    clean = redact(text)
    written = []
    p = reports_dir() / name
    p.write_text(clean, encoding="utf-8")
    written.append(str(p))
    if also_deliver:
        d, _ = deliver_dir()
        q = d / name
        try:
            q.write_text(clean, encoding="utf-8")
            written.append(str(q))
        except Exception:
            pass
    return written


_PUBLIC_IP = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")


def redact(text: str, placeholder: str = "<公网IP>") -> str:
    """把公网 IPv4 替换成占位符；私网/回环/保留地址保留原样（技能落盘纪律）"""
    def sub(m):
        a, b = int(m.group(1)), int(m.group(2))
        if a == 127 or a == 0 or a == 10:
            return m.group(0)
        if a == 192 and b == 168:
            return m.group(0)
        if a == 172 and 16 <= b <= 31:
            return m.group(0)
        if a == 169 and b == 254:
            return m.group(0)
        if a >= 224:
            return m.group(0)
        return placeholder
    return _PUBLIC_IP.sub(sub, text)


def lan_ip() -> str:
    """本机 LAN IP（UDP 假连接取默认出口地址，不真发包）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.0.1", 9))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return env("LAN_HOST_IP", "127.0.0.1")


# ---------------------------------------------------------------- MCSM 面板 / 代理实例（ADR-040..042）
DATA_ROOT = pathlib.Path(os.environ.get("ORZMC_DATA_ROOT") or "E:/orzmc")
INSTANCE_DATA = DATA_ROOT / "mcsmanager" / "daemon" / "data" / "InstanceData"
INSTANCE_CONFIG = DATA_ROOT / "mcsmanager" / "daemon" / "data" / "InstanceConfig"
MCSM_WEB = "http://127.0.0.1:23333/api"


def data_env(key: str) -> str:
    """读 DATA_ROOT/.env（部署侧真 env；注意与 Hermes 的 ~/.hermes/.env 不是一个文件）"""
    try:
        for line in (DATA_ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def velocity_dir() -> pathlib.Path | None:
    """代理（Velocity）实例目录：.env 的 VELOCITY_DIR → 扫 InstanceData（velocity.toml / velocity*.jar）→ None

    ADR-040 起代理数据在面板实例目录里，$DATA_ROOT/eagler/proxy 已废弃。"""
    override = data_env("VELOCITY_DIR")
    if override:
        p = pathlib.Path(override)
        if p.is_dir():
            return p
    if INSTANCE_DATA.is_dir():
        for d in sorted(INSTANCE_DATA.iterdir()):
            if d.is_dir() and ((d / "velocity.toml").is_file() or any(d.glob("velocity*.jar"))):
                return d
    return None


def mcsm_apikey() -> str:
    """管理员 apikey（permission==10）——从面板 web 数据目录读，不写死、不打印"""
    import json
    for p in sorted((DATA_ROOT / "mcsmanager/web/data/User").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("apiKey") and d.get("permission") == 10:
            return d["apiKey"]
    return ""


def mcsm_get(path: str, **params) -> dict | None:
    """调面板 API；自动摘掉 HTTP(S)_PROXY（localhost 会被 Clash 劫持），失败返回 None"""
    import json
    import urllib.parse
    import urllib.request
    key = mcsm_apikey()
    if not key:
        return None
    params["apikey"] = key
    url = "%s/%s?%s" % (MCSM_WEB, path, urllib.parse.urlencode(params))
    saved = {k: os.environ.pop(k) for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy") if k in os.environ}
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return None
    finally:
        os.environ.update(saved)


def mcsm_daemon_id() -> str:
    r = mcsm_get("service/remote_services_list") or {}
    for d in (r.get("data") or []):
        if d.get("uuid"):
            return d["uuid"]
    return ""


def mcsm_instances() -> list[dict]:
    """[{uuid, nickname, status, type, startCommand}]；status 语义实测：0=停止、3=运行中（MCSM 10.22.1）"""
    dm = mcsm_daemon_id()
    if not dm:
        return []
    out = []
    for cfg in sorted(INSTANCE_CONFIG.glob("*.json")):
        uuid = cfg.stem
        if uuid.startswith("__"):   # __MCSM_GLOBAL_INSTANCE__ 是全局实例组配置，不是实例
            continue
        r = mcsm_get("instance", daemonId=dm, uuid=uuid) or {}
        d = r.get("data") or {}
        c = d.get("config") or {}
        _nick = str(d.get("nickname") or c.get("nickname") or "")
        if _nick.startswith("__") or uuid.startswith("global"):
            continue   # 全局实例组（uuid=global0001、type=universal），不是可运行实例
        out.append({
            "uuid": uuid,
            "nickname": d.get("nickname") or c.get("nickname") or uuid[:8],
            "status": d.get("status"),
            "type": c.get("type") or d.get("type") or "",
            "startCommand": c.get("startCommand") or "",
        })
    return out

if __name__ == "__main__":
    d, note = deliver_dir()
    print("deliver_dir:", d, "|", note)
    print("lan_ip:", lan_ip())
    print("redact test:", redact("real {HOME_IP} lan {LAN_IP} loop 127.0.0.1"))
