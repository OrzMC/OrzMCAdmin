# 面板实例运维：MCSM REST + Velocity 启动日志分诊 + 升级

适用：代理（Velocity）已按 ADR-040 收成 MCSM 面板实例，不再是 compose 服务；以及任何要改面板实例配置的场合。

## 1. 取 apikey 与实例坐标

```bash
# apikey 只在脚本内读，值不落聊天/不进仓库
python - <<'EOF'
import json,glob
for p in glob.glob("E:/orzmc/mcsmanager/web/data/User/*.json"):
    d=json.load(open(p,encoding="utf-8"))
    if d.get("permission")==10: print(d["apiKey"])   # 必须是管理员账户的 key
EOF
```

- 多用户时挑 `permission == 10`（管理员）的 key；普通用户 key 调 protected_instance 会返回 `403 参数不正确或非法访问实例`，不要误判成「接口不存在」。
- `daemonId` 取 `docker exec orzmc-mcsmanager-daemon` 侧配置或面板「节点」页；web 在 `127.0.0.1:23333`。

## 2. 启停 / 查状态

| 动作 | 请求 |
|---|---|
| 启 | `POST /api/protected_instance/open?uuid=&daemonId=&apikey=` |
| 停 | `POST /api/protected_instance/stop?uuid=&daemonId=&apikey=` |
| 查 | `GET /api/instance?daemonId=&uuid=&apikey=` → `status`：`0` 停 / `3` 运行 |

启动后别只看 HTTP 200，轮询 `docker ps --filter name=<containerName>` 到 `Up` 再读日志；`done` 判据是日志里的 `Done (x.xs)`。「等停止」要等 `status==0`，别按官方枚举去等 `1` —— 本架构里 `1`/`2` 从未出现。

🔴 **调 `127.0.0.1:23333` 之前先清掉代理环境变量**。拉 GitHub/Release 时会 `export HTTPS_PROXY=http://127.0.0.1:7897`，同一个 shell 或同一个 Python kernel 里紧接着 `urllib` 调面板就会走 Clash，返回 **`502 Bad Gateway`**——看着像面板挂了，其实是被代理劫持。写法：`for k in ("HTTPS_PROXY","HTTP_PROXY","https_proxy","http_proxy"): os.environ.pop(k,None)`，或 curl 加 `--noproxy '*'`。同一个 kernel 里变量是持久的，前面某次 cell 设过的也要清。

## 3. 改实例配置（踩过的坑，必须照抄）

```bash
# 正确：扁平字段
PUT /api/instance?daemonId=&uuid=&apikey=
{ "startCommand": "java --sun-misc-unsafe-memory-access=allow -Xms256M -Xmx768M -jar /server/velocity-4.3.1-45.jar" }   # jar 名用官方原名（带 build）
```

- 🔴 **`{"config": {...}}` 形式返回 200 但静默不生效**——不报错、不回滚、值也不变，极易误以为已写入。改完必须 `GET /api/instance` 复核字段值。
- 🔴 **实例必须在停止状态**改配置；运行中改同样返回 200 而不落盘。顺序：stop → 轮询 status==0 → PUT → GET 复核 → open。
- 🔴 `PUT /api/instance/update` 不存在（404）。
- PUT 后要复核 **`docker.ports` 与 `eventTask.autoStart/autoRestart` 没被清空** —— 误传结构时这些字段最容易被整体覆盖。

## 4. 「突然没有启动 / 容器不见了」的定位顺序

1. `docker ps -a --filter name=orzmc-velocity` —— 容器**不存在**（不是 Exited）说明被失败清理删掉了，不是进程崩溃。
2. `docker logs --since 4h orzmc-mcsmanager-daemon | grep -E "启动成功|启动时错误"` 取时间线。
3. 典型连锁：反复点启动 → 前一个容器仍占着 19132 → `Bind for 0.0.0.0:19132 failed: port is already allocated` → 失败那次把容器清掉 → 实例 `status=0` 且容器消失。其它同族报错：`此容器的开放端口配置有误！`、`实例容器额外挂载路径配置长度不正确！`（后者= `extraVolumes` 里写了 Windows 路径的冒号）。
4. 恢复：确认只有一个同名容器、端口没被占 → `POST /protected_instance/open` → 轮询 `Up` → 验证 `./orzmc.sh -d <DATA_ROOT> status --probe` 里 `Velocity java`/`Geyser tcp`/`ws dev.<域>` 三项。
4b. 若容器卡在 `Created`（典型成因：启动命令里写了 `sh -c '...'`，MCSM 按空格硬切后参数非法），此时面板 `stop` 返回 **500**，`open` 也不会重建：先 `docker rm -f <该容器名>`（只删这一个已知的半成品容器，属于上面的禁则之外的唯一例外），再 PUT 修正 `startCommand`，最后走面板 `open`。
4c. 恢复完要回头确认面板视图和容器一致；`docker start` 手工拉起会让 daemon 与面板状态错位，宁可删了重新 `open`。
5. 面板实例没有 compose 的 `restart: unless-stopped` 自愈能力：容器被杀后只剩 autoStart（仅在 daemon 启动时生效）。自愈已由两条脚本固定下来——`orzmc_entry_probe.py` 判到容器**不存在**（非 stopped）时用面板 `open` 自动拉起并轮询 25565（INFO，不进告警）；advertise-sync 的 `restart_entry()` 也只走面板 `stop`→`open`。🔴 任何脚本里都不要对面板托管容器写 `docker restart/stop/rm`：外部改动会让 daemon 以为状态漂移→重复起容器→端口冲突→失败清理删容器，入口整段消失。

## 5. 启动日志分诊表（Velocity 4.x + EaglerXServer + Geyser）

| 日志 | 判定 | 处置 |
|---|---|---|
| `ERROR [eaglerxserver] Could not load server icon: server-icon.png` / `IllegalArgumentException: Image is not 64x64 (found NxN)` | 真错误 | 图标必须是 **64×64 PNG**，放实例根（= 容器 `/server`）。128×128 会被拒；用 Pillow 生成即可，无需外部素材 |
| `WARNING: sun.misc.Unsafe::staticFieldBase has been called by com.google.inject... will be removed in a future release` | 真告警（JDK 24+ 对 Guice 反射的提示） | 启动命令加 `--sun-misc-unsafe-memory-access=allow`（JDK 24+ 参数） |
| `WARN: The proxy is running in offline mode!` | 设计如此 | 不要开 online-mode：Eaglercraft 网页端与基岩端都依赖离线模式，开了两端全断 |
| `WARN: The server channel initializer has been replaced by ...DirectMethodHandleAccessor` | EaglerXServer 注入自己的 initializer | 忽略 |
| `WARN [eaglerxserver] Update certificate was loaded: $dl.<sha>.cert` | `$dl.` 是它的下载中间文件名，证书本身已加载 | 忽略 |
| `> [ERROR] [connected player] <name> (/172.18.0.1:...): disconnected ... not on the whitelist` | 不是故障 | 白名单策略，要放人加白名单 |

## 6. 升级 Velocity / 插件（面板实例路径）

**Velocity 本体**
1. 新 jar（用官方下载原名 `velocity-<版本>-<build>.jar`）传到实例根：面板「文件管理」或宿主 `E:/orzmc/mcsmanager/daemon/data/InstanceData/<uuid>/`（同一目录，bind mount）。
2. 改 `startCommand` 的 jar 名（见 §3，扁平字段 + 实例停止），保留 `--sun-misc-unsafe-memory-access=allow` 与 `-Xms256M -Xmx768M`。**文件名写字面量、不能用通配**（见下）。
3. 重启实例，确认 `Done (x.xs)`；`Unable to access jarfile /server/xxx.jar` = 名字写错或文件放进了 `<instance>/server/` 子目录。
4. 旧 jar 留几天再删，回滚就是改回名字重启。

**插件**（`plugins/` 下的 `EaglercraftXServer`、`Geyser-Velocity`）
1. 新 jar 传进 `plugins/`，**先删旧版本同名插件**（两版本共存会双加载报错）。
2. 重启实例（插件 jar 无热重载，`/velocity reload` 无效）。
3. 日志确认 `Loaded plugin geyser <新版本>` / `Enabling EaglercraftXServer <新版本>`。
4. `plugins/eaglerxserver/`、`plugins/Geyser-Velocity/` 配置目录、`forwarding.secret`、`eagler_skins_cache.db` 不动，升级沿用。

**两条联动约束**
- EaglerXServer 与 paper 实例里的 `EaglerXPaper` 版本必须匹配，**不能只升一侧**，否则网页端连不上。
- **版本完全由面板管（OrzMCDeploy 0.6.0 / ADR-041）**：`up` 不下 Velocity jar、不改 `startCommand`；`validate` 只判实例目录里有没有 `velocity-*.jar`。
- **启动走 start.sh（OrzMCDeploy 0.6.1 / ADR-042）**：实例目录 `start.sh` 里 `ls -1 velocity-*.jar | sort -V | tail -1`，面板启动命令 `sh /server/start.sh`（与 paper/folia 同构）。升级 = 传官方 jar + 面板重启，命令不动。
- **插件也由面板管（ADR-042）**：`plugins/EaglerXServer.jar`、`plugins/Geyser-Velocity.jar` 面板上传；`templates/eagler/versions.env` 与 `eagler_lock`/`eagler_fetch` 已删除，仓库里没有任何版本锁。
- jar 用**官方原名** `velocity-<版本>-<build>.jar`（如 `velocity-4.3.1-45.jar`），启动命令写完整路径 `/server/<该文件名>`。
- **启动命令不能写 shell**：MCSM 按空格硬切后直接传 entrypoint，`sh -c '... $(ls velocity-*.jar) ...'` 实测会让容器停在 `Created`（daemon 日志：`Entrypoint: sh` + `-c,'exec,java,...,"$(ls ...)"'`）。换版本 = 面板传新 jar + 手改启动命令里的文件名 + 重启。

## 7. 改部署脚本本身的两个必做验收

- 🔴 **`set -e` 下不要把命令替换直接赋给变量**：`vjar="$(eagler_proxy_jar)"` 里 `find` 在目录不存在时 rc=1，会让整个 `validate` **无任何输出直接 exit 1**（本地与 CI 表现一致，只剩 `Process completed with exit code 1`）；赋值写成 `$(... || true)`，或用 `if [ -z "$(...)" ]` 形式（条件里的替换失败不算失败）。
- 改完 `lib/eagler.sh` 这类文件必须跑**两种**数据目录各一次：无 jar 的临时树（走 warn 分支）和有 jar 的现网（走正常分支）。只测现网会漏掉「目录不存在」路径。
- 临时数据目录用 `./orzmc.sh -d <tmp> init` 造，再用 `sed -i` 改 `.env` 造象限；脚本里带 `rm -rf` 的清理命令会触发审批，不要把验证和清理写进同一条命令。`mktemp -d ...; ./orzmc.sh init; printf >> .env` 拼成一条也可能被拦，宁可分三步写。
