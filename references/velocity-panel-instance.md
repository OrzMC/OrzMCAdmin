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

启动后别只看 HTTP 200，轮询 `docker ps --filter name=<containerName>` 到 `Up` 再读日志；`done` 判据是日志里的 `Done (x.xs)`。

## 3. 改实例配置（踩过的坑，必须照抄）

```bash
# 正确：扁平字段
PUT /api/instance?daemonId=&uuid=&apikey=
{ "startCommand": "java ... -jar /server/velocity-4.4.0.jar" }
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
5. 面板实例没有 compose 的 `restart: unless-stopped` 自愈能力，容器被杀后只剩 autoStart（仅在 daemon 启动时生效）→ 需要额外的存活告警/自动拉起。

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
1. 新 jar（保持带版本号 `velocity-4.4.0.jar`）传到实例根：面板「文件管理」或宿主 `E:/orzmc/mcsmanager/daemon/data/InstanceData/<uuid>/`（同一目录，bind mount）。
2. 改 `startCommand` 的 jar 名（见 §3，扁平字段 + 实例停止），保留 `--sun-misc-unsafe-memory-access=allow` 与 `-Xms256M -Xmx768M`。
3. 重启实例，确认 `Done (x.xs)`；`Unable to access jarfile /server/xxx.jar` = 名字写错或文件放进了 `<instance>/server/` 子目录。
4. 旧 jar 留几天再删，回滚就是改回名字重启。

**插件**（`plugins/` 下的 `EaglercraftXServer`、`Geyser-Velocity`）
1. 新 jar 传进 `plugins/`，**先删旧版本同名插件**（两版本共存会双加载报错）。
2. 重启实例（插件 jar 无热重载，`/velocity reload` 无效）。
3. 日志确认 `Loaded plugin geyser <新版本>` / `Enabling EaglercraftXServer <新版本>`。
4. `plugins/eaglerxserver/`、`plugins/Geyser-Velocity/` 配置目录、`forwarding.secret`、`eagler_skins_cache.db` 不动，升级沿用。

**两条联动约束**
- EaglerXServer 与 paper 实例里的 `EaglerXPaper` 版本必须匹配，**不能只升一侧**，否则网页端连不上。
- `templates/eagler/versions.env` 的 Velocity 版本锁只影响「实例目录里没有任何 `velocity*.jar` 时的首次下载」。面板升版后要同步改锁，否则某天清空 jar 时 `up` 会拉回旧版。`up` 绝不覆盖已存在的 jar，也不会改 `startCommand`。
