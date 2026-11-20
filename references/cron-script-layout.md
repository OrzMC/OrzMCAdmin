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

- 容器：`docker ps` 的 Up 才算跑（`orzmc-velocity`/`orzmc-caddy`/`orzmc-easybot` + daemon）。
- MCSM 实例（paper/folia/velocity）跑在 **daemon 容器内的 java 进程**，不是独立容器；
  状态以面板 API 为准：`status` **0=停止、3=运行中**。别再靠 `ps -C java` 猜、也别断言「paper/folia 应 stopped」。
- 面板实例列表里 **`uuid=global0001` / `nickname=__MCSM_GLOBAL_INSTANCE__` / `type=universal`** 是全局实例组，
  不是可运行实例——遍历 `InstanceConfig/*.json` 时必须跳过，否则巡检永远报一条 ❌。
- 面板 apikey 现读 `E:/orzmc/mcsmanager/web/data/User/*.json`（`permission==10`），不写死、不进仓库。

## 数据路径已迁移（别再写 eagler/proxy）

Velocity 的核心 jar、`velocity.toml`、`plugins/Geyser-Velocity/config.yml`、`plugins/EaglerXServer.jar`
都在**面板 Velocity 实例目录** `E:/orzmc/mcsmanager/daemon/data/InstanceData/<velocity-uuid>/`；
脚本一律用 `orzmc_paths.velocity_dir()` 解析，写死旧 `E:/orzmc/eagler/proxy` 会静默读到空目录/旧文件。

## 顺带清理（同一轮做掉，否则下次又被误导）

- 删主机目录里没真身的遗留脚本（CF 隧道时代的东西、渲染 watcher、一次性 helper）。
- 文档里引用已删脚本/旧路径的段落同步改掉，**只把历史段落标注废弃**，不留「现在也能这么用」的错觉。
- paper/folia 的 `plugins/Geyser-Spigot*.jar` 是残留：检测到 Velocity 会自禁用并持续刷 WARN，纯噪音，可删。
