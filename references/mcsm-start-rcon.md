# 启动实例与 RCON（本机 MCSM 4.x）

## 1. 启动实例：只能走 daemon 的 socket.io，不是 HTTP

MCSM daemon（容器 `orzmc-mcsmanager-daemon`，内部 24444，**未发布到宿主**）的 HTTP 只暴露上传/下载，所有实例控制都是 socket.io 事件。

- 连接：`io('http://127.0.0.1:24444',{transports:['websocket']})`，**必须在 daemon 容器内执行**（`docker cp` 脚本进去再 `docker exec node`）。
- 认证：`emit('auth', {uuid, data: <daemon key>})`；key 取自容器内 `/opt/mcsmanager/daemon/data/Config/global.json` 的 `key`。返回 `data:true` 才算成功（false 多半是漏了 `{uuid,data}` 信封）。
- **信封格式是唯一坑**：所有 emit 必须是 `{uuid: <自定义uuid>, data: <真实载荷>}`。直接 `emit('auth', key)` 会得到 `data:false`——服务端 `parse()` 只读 `obj.data`，裸值变成 undefined。
- 启动：`emit('instance/open', {uuid, data:{instanceUuids:[...]}})`（支持批量）；停止 `instance/stop`，强杀 `instance/kill`。
- 响应事件名与请求同名，按 uuid 匹配。
- 容器名 = `MCSM-` + uuid 前 6 位；`instance/open` 返回 200 只代表已下发，MC 真正就绪要等日志 `Done (`. Paper 约 2 分钟、Folia 约 2.5 分钟（首次含 Geyser）。

## 2. 改 docker 端口映射：不能只改磁盘 JSON

daemon 启动时把实例配置读进内存，直接改 `InstanceConfig/<uuid>.json` **不会被运行中的 daemon 采用**（重启 daemon 也可能触发审批）。
做法：走 `instance/update` 让它自己写内存+落盘——

```js
emit('instance/update', {uuid, data:{instanceUuid, config:{docker:{ports:[...完整数组]}}}})
```

`parameters()` 对 `docker.ports` 是整体替换，**必须传完整数组**。改完再从磁盘 JSON 读回校验。

## 3. RCON 开启与从宿主访问

两层都要：

1. **服务端**：实例 `server.properties` 里 `enable-rcon=true`、`rcon.port=25575`、`rcon.password=<非空>`。本机两个测试服已配好。
2. **端口发布**：容器内 25575 默认不发布，宿主连不上。给每个实例的 `docker.ports` 加 `"<宿主端口>:25575/tcp"`：
   - PaperMC(716c2f)：`25575:25575/tcp`
   - FoliaMC(8A932D)：`25576:25575/tcp`（容器内都监听 25575，宿主端口错开）

MCSM 实例自己的 `enableRcon` 字段是面板内置 RCON 通道，与 MC 的 RCON 无关，**保持 false**，直接用协议客户端连宿主端口即可。

客户端：`scripts/rcon.py`（纯 stdlib，不依赖 pip）。

```bash
RCON_PASSWORD=<pw> python scripts/rcon.py 25575 list     # Paper
RCON_PASSWORD=<pw> python scripts/rcon.py 25576 list     # Folia
```

本机验证过的端口矩阵：Paper 游戏 25565 / RCON 25575；Folia 游戏 25566 / RCON 25576；基岩 19132(19133)、19134(19135)/udp。
