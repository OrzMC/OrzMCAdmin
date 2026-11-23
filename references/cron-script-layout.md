# 巡检/运维脚本的存放与 cron 入口（单真源 + stub）

## 为什么

`hermes cron create --script X.py` **只**解析 `%LOCALAPPDATA%/hermes/scripts/X.py`，不会去技能目录找。
而 OrzMC 的脚本真源必须放在技能 `scripts/` 里（能跨设备同步、能随技能版本发布）。
两份都是真身就必然漂移——本机就出现过 `orzmc_paths.py` 主机侧 4.7KB 旧版、技能侧 8.3KB，
巡检脚本读到的常量取决于谁先 import。

**规则：真身只存技能 `scripts/`；`%LOCALAPPDATA%/hermes/scripts/` 下的同名文件一律是 6 行转发 stub。**
新增脚本先落技能目录，再在主机目录放 stub；不要反过来。

## Host stub 模板

```python
#!/usr/bin/env python3
"""主机级 cron 入口（stub）—— 真源在技能目录，本文件只做转发，避免两份副本漂移。"""
import pathlib
import runpy
import sys

TARGET = pathlib.Path("C:/Users/<user>/AppData/Local/hermes/skills/<cat>/<skill>/scripts/X.py")
if not TARGET.is_file():
    print(f"❌ 脚本真源缺失: {TARGET}")
    sys.exit(1)

sys.path.insert(0, str(TARGET.parent))      # 让 orzmc_paths 等同目录模块可导入

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
else:                                        # 被 import_path 方式加载时也要能用
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(__name__ + "_real", TARGET)
    _mod = _ilu.module_from_spec(_spec)
    sys.modules[_spec.name] = _mod
    _spec.loader.exec_module(_mod)
    globals().update({k: v for k, v in vars(_mod).items() if k not in ("__name__", "__file__")})
```

- `TARGET` 用**正斜杠**绝对路径，别在 raw string 里塞 `\\`（`r"C:\\Users"` 会变成字面双反斜杠）。
- 脚本内部自己算 `SCRIPTS = os.path.dirname(os.path.abspath(__file__))`，不要写死 `%LOCALAPPDATA%/hermes/scripts`；
  否则子进程/import 又会绕回主机目录的旧副本。

## 写 stub 的坑（会丢文件）

`io.open(p, "w").write(TEMPLATE.format(...))` —— `open("w")` **先截断**，参数里的 `.format()` 若抛异常（例如模板里的
`{k: v}` 被当成占位符），文件已被清成 0 字节。**先算好字符串再 open**，或用 `str.replace("@@TARGET@@", path)`
而不是 `str.format`。写完用 `os.path.getsize` 复核。

## 验收方式

改完必须**从主机路径**跑一遍（`cd %LOCALAPPDATA%/hermes/scripts && python X.py`），而不是跑技能副本——
cron 走的是前者。看退出码 + `STATUS_LINE`，别只看有没有异常。

## 判活口径（ADR-040..042 之后）

- **docker CLI 不在本机（WSL dockerd）**：没有 Windows 版 `docker.exe`，脚本里裸写 `["docker", ...]` 会 `FileNotFoundError`。
  一律用 `orzmc_paths.docker_argv()`（有本地 CLI 用之，否则自动退回 `wsl -e docker`）。
- **「命令起不来」与「对象不存在」必须分开报**：`rc != 0` 就把结论写成「容器查不到」是错的——先看是
  `FileNotFoundError`/超时（环境问题）还是 docker 真的返回 no such container（对象问题）。错误文本要带进告警
  （`docker inspect 失败：<stderr 前 160 字>`），否则每天一条一模一样的假红、没人能定位。
- 容器：`docker ps` 的 Up 才算跑（`orzmc-velocity`/`orzmc-caddy`/`orzmc-easybot` + daemon）。
- **面板容器名 = `MCSM-` + uuid 前 6 位**（`MCSM-716c2f`/`MCSM-8A932D`）。取 8 位拼名字会永远 `missing`，
  看上去像「实例没起」实则名字拼错。
- MCSM 实例（paper/folia/velocity）跑在 **daemon 容器内的 java 进程**，不是独立容器；
  状态以面板 API 为准：`status` **0=停止、3=运行中**。别再靠 `ps -C java` 猜、也别断言「paper/folia 应 stopped」。
- 面板实例列表里 **`uuid=global0001` / `nickname=__MCSM_GLOBAL_INSTANCE__` / `type=universal`** 是全局实例组，
  不是可运行实例——遍历 `InstanceConfig/*.json` 时必须跳过，否则巡检永远报一条 ❌。
- 同理，**`nickname` 仍是 `Undefined` 且 `InstanceData/<uuid>/` 里 0 个文件的记录是建实例的半途残骸**：
  既没配置也没数据，判 `ℹ️ 面板占位记录 N 个`、不计失败（要清就删配置 + 空目录，零数据损失，删前先列清单让老板拍板）。
- 面板 apikey 现读 `E:/orzmc/mcsmanager/web/data/User/*.json`（`permission==10`），不写死、不进仓库。

## 数据路径已迁移（别再写 eagler/proxy）

Velocity 的核心 jar、`velocity.toml`、`plugins/Geyser-Velocity/config.yml`、`plugins/EaglerXServer.jar`
都在**面板 Velocity 实例目录** `E:/orzmc/mcsmanager/daemon/data/InstanceData/<velocity-uuid>/`；
脚本一律用 `orzmc_paths.velocity_dir()` 解析，写死旧 `E:/orzmc/eagler/proxy` 会静默读到空目录/旧文件。

## 顺带清理（同一轮做掉，否则下次又被误导）

- 删主机目录里没真身的遗留脚本（CF 隧道时代的东西、渲染 watcher、一次性 helper）。
- 文档里引用已删脚本/旧路径的段落同步改掉，**只把历史段落标注废弃**，不留「现在也能这么用」的错觉。
- **`Geyser-Spigot*.jar` 不是残留，禁止删**：OrzMCDeploy 支持代理 / 直连多种部署模式，后端那一份是直连模式回归的必需品；
  代理模式下它检测到 Velocity 会自禁用并持续刷「behind a Velocity proxy」WARN，**属预期噪音**，不是故障。
  同理别把 `plugins/proxy/Geyser-Velocity.jar` 与后端 `Geyser-Spigot*` 当重复件择一删掉。
- 判定「真残留」的唯一标准是**没有任何部署模式会加载它**（CF 隧道时代的 helper、一次性渲染 watcher、
  已被 stub 取代的旧真身）。拿不准的先列进清单让老板拍板，不要直接删。
- **报告口径：既定关闭 / 不适用的项用 `ℹ️ 已关闭`、`n/a`，不要用 ❌/🔴**。反例：周报把「后端 RCON 已关闭」
  判成 🔴，于是「N 项待处理」永远清不掉，真问题被噪音埋掉。判定顺序 = 先看该项在配置里是否本就没开，再决定符号。
