# NetherNet（基岩新传输层）迁移知识库

> 状态：**迁移进行中（截止 2026-10-19 测试服未启用）** ｜ 最后更新：2026-10-19
> 来源：Geyser 官方 blog `/blog/preparing-for-nethernet`、官方 setup 文档 `geysermc.org/wiki/geyser/setup/`、**Geyser-Spigot 2.12.0-b1265 jar 反编译实证**（`GeyserConfig$BedrockConfig` / `$SignalingConfig$*`）

## 1. 是什么 / 为什么必须处理

- **NetherNet** = Mojang 为基岩版引入的新传输层：**WebRTC（UDP）承载游戏流量 + HTTP/HTTPS 信令（TCP）做连接协商**。Mojang 自 **Bedrock 26.40** 起逐步推送。
- **2026-10-27 起**，基岩客户端**不再走 RakNet** → 未切换的服务器基岩玩家进不来。
- Geyser **build ≥1237** 已支持 NetherNet，但**默认仍是 RakNet**（`transport: raknet`），必须手动开启，否则启动日志会打：
  `WARNING! NetherNet support is NOT enabled. Players will not be able to connect to your server, starting October 27th`

## 2. 机制差异（这是迁移真正的坑）

| 维度 | RakNet（旧） | NetherNet（新） |
|:--|:--|:--|
| 连接流程 | 客户端 UDP 直连 | ① **TCP** 发 HTTP(S) 问「怎么连」→ ② 服务端回 WebRTC 参数 → ③ 游戏流量走 **UDP/WebRTC** |
| 端口 | 只需 UDP 19132 | **同一端口同时占 TCP + UDP** |
| 服务器列表 MOTD / 人数 | RakNet 查询 | **也走信令**（只开 UDP → 列表都刷不出来） |
| 兼容模式 `both` | — | 需**另开一个 UDP**（`webrtc-port`），两种传输不能共用同一 UDP 端口 |
| 公网转发 | 只转 UDP | **TCP + UDP 都要转** |
| 首次进服 | 无感 | 用 IP / 非 HTTPS 域名 → 弹「信任此服务器?」(trust on first use) |

- MOTD 透传：自带信令会把客户端最初 ping 的地址回传给 Java 端做 MOTD passthrough。
- 若 Geyser 与 Java 共用端口（`clone-remote-port: true`）→ **自带信令无法用**（TCP 被 Java 占了），Geyser 会**自动回退到外部信令 Warden**，控制台打印玩家应使用的地址。

## 3. 配置结构（2.12.0-b1265 反编译实证，字段名为权威）

```yaml
bedrock:
  address: 0.0.0.0
  port: 19132                 # 基岩端口；NetherNet 下同号占 TCP+UDP
  clone-remote-port: false    # true 与自带信令不兼容
  transport: raknet           # raknet(默认) | nethernet | both
  webrtc-port: 19134          # 仅 both 需要：另开一个 UDP 给 NetherNet
  raknet-port: 19132          # both 模式下 RakNet 用的 UDP 端口
  broadcast-port: 7551        # 局域网发现（可关）
  signaling:
    mode: builtin             # builtin | hybrid | nxs(外部信令服务)
    port: 19132               # 信令 TCP 端口（默认跟 port 同号）
    builtin:
      advertise-addresses: [] # 指定对外公布地址（NAT/多网卡时用）
      https:                  # 配了就走 HTTPS，玩家不再看到「信任提示」
        certificate: /path/cert.pem
        private-key: /path/key.pem
        password: ''
    nxs:
      endpoint: ''            # 外部信令服务（如 Warden）地址
      token: ''
      advertise-addresses: []
```

**系统属性覆盖**（优先级高于 config，托管方可直接写启动命令）：
`-DgeyserTransport=nethernet`、`-DgeyserUdpPort`、`-DgeyserSignalingPort`、`-DgeyserWebrtcPort`、`-DgeyserSignalingMode=nxs`

## 4. 三种落地方案

| 方案 | 配置 | 需要开放的端口 | 优点 | 缺点 |
|:--|:--|:--|:--|:--|
| **A 最小** | `transport: nethernet` | TCP+UDP 同端口 | 最简单、端口最少 | 老客户端（<26.40）彻底进不来；26.40 的 MOTD/人数可能不显示 |
| **B 过渡（推荐）** | `transport: both` + `webrtc-port: <另一 UDP>` | TCP+UDP 主端口 + 一个 UDP webrtc | 新老客户端都能进 | 多开一个 UDP 端口 |
| **C 免 TCP/免证书** | 外部信令（Warden，免费、自带 HTTPS）| **不用开 TCP** | 不动路由器、无证书 | 玩家要用 Warden 显示的地址+端口（或注册自定义域名）；依赖第三方服务 |

> 26.60 发布、玩家全部更新后可收敛为 A，并关掉 RakNet 端口。

### HTTPS 三种做法
1. `signaling.builtin.https` 直接指向证书（Geyser 同端口提供 HTTPS）
2. 信令端口前挂反向代理（Nginx/Caddy）做 TLS
3. 外部信令服务（Warden 自带 HTTPS）
—— 不配 HTTPS 也能用，只是玩家首连要确认「信任」。

## 5. 本环境适配要点（OrzMC 现状）

### 5.1 已落地（2026-10-19，本地测试服 dev.{SERVER_NAME}.cn，both 模式）

| 项 | paper（716c2f…） | folia（8A932D…） |
|:--|:--|:--|
| `transport` | `both` ✅ | `both` ✅ |
| `bedrock.port` | 19132 | 19132（容器内） |
| `webrtc-port` | 19134 | 19135 |
| `signaling.builtin.advertise-addresses` | `["114.240.151.81:19134"]` | `["114.240.151.81:19135"]` |
| Docker 发布 | UDP 19132 + TCP 19132 + UDP 19134 | UDP 19132 + TCP 19132 + UDP 19135（宿主侧 19133/19135） |
| 玩家填的地址 | `dev.{SERVER_NAME}.cn:19132` | `dev.{SERVER_NAME}.cn:19133` |

启动日志确认（两个实例均出现，且**不再**出现 `NetherNet support is NOT enabled`）：

```
Started Geyser on 0.0.0.0:19132
Started built-in signaling server on http://0.0.0.0:19132
NetherNet WebRTC listening on UDP 19134 (or 19135 for folia)
```

> ⚠️ **本机实测：`advertise-addresses` 必须写成「公网 IP:宿主端口」**。容器内监听的是 172.x，且 webrtc 端口经 Docker NAT，若留空会把容器内网地址/端口公布给客户端 → 外网玩家拿到错误 endpoint，表现为列表能刷出来但进不了服。
> ⚠️ 公网 IP 来自动态域名（kmdns.net）→ **IP 变动后需同步改 advertise-addresses 并重启实例**，否则新客户端连不上（老客户端 RakNet 不受影响）。

### 5.2 仍未放行（截至 2026-10-19 晚）

| 层 | 现状 | 需要 |
|:--|:--|:--|
| Windows 防火墙 | 仅 `Bedrock Geyser 19132/19133 UDP` 两条入站规则 | 加 **TCP 19132、TCP 19133、UDP 19134、UDP 19135**（需管理员；本机脚本 `%LOCALAPPDATA%\hermes\scripts\bedrock_nethernet_ports.ps1`，管理员 PowerShell 运行） |
| 路由器端口转发 | 只转发 UDP 19132/19133（TCP 25565 已转发，证明 TCP 转发功能可用） | 加 **TCP 19132、TCP 19133、UDP 19134、UDP 19135** → `192.168.0.33` |
| 外部验证 | check-host 4 节点对 TCP 19132/19133 全部 `Connection timed out` | 两层都放通后复测应能连上 |

> 只差这两层：**服务端配置与端口发布已全部就绪**，本机 `127.0.0.1` 上 RakNet PONG + 信令 HTTP 均正常。

### 5.3 关键操作经验

- MCSM 实例的 `docker.ports` 在 `daemon/data/InstanceConfig/<uuid>.json`；**普通 apikey（权限 1）不能改**（`PUT /api/instance` 需 ADMIN）。
- 本次做法：停实例（`POST /api/protected_instance/stop`）→ 改 JSON + Geyser 配置 → `docker restart orzmc-mcsmanager-daemon`（daemon 启动时从磁盘重载 `InstanceConfig`）→ 启实例（`POST /api/protected_instance/open`，不是 `/start`）。
- 启动/停止路由前缀是 **`/api/protected_instance/*`**（`/open` `/stop` `/restart` `/kill` `/command`）。
- 实例停掉后容器会被移除，重启时按新 `ports` 重建，端口变更才生效。

## 6. 验证方法（含本机大坑）

- 工具：`~/OrzMC/proxy/scripts/nethernet_check.py [host] [port]`（UDP RakNet 基线 + TCP 信令 HTTP 探测 + 结论 + 退出码 0/1，带 `-h`）
- **判定标准**：TCP 信令能返回 HTTP 应答（脚本显示 `HTTP 业务码`）= 可用；`TIMEOUT` = 未转发/被丢弃；`REFUSED` = 已转发但无监听
- ⚠️⚠️ **本机经 Clash TUN 测 TCP 必假阳性**：域名被 fake-IP 成 `198.18.x.x`，TCP 握手被 TUN 本地接管后「接受并立即关闭」→ 脚本会报 `OPEN_NO_HTTP`，误判成「端口可达」。**正确做法**：
  1. DoH 查真实公网 IP：`curl -H 'accept: application/dns-json' 'https://1.1.1.1/dns-query?name=<域名>&type=A'`
  2. 用外部节点验证 TCP：`check-host.net/check-tcp?host=<IP>:<port>` 拿 `request_id` → `check-host.net/check-result/<id>`（外部节点一律 `Connection timed out` = 未转发）
  3. UDP 侧 `check-host.net/check-udp` **无意义**（普通 UDP 包 Geyser 不回，只有 RakNet 专有包才 Pong）→ UDP 用本机 `bedrock_ping.py` 拿到真实 PONG 即为通
- 官方自检：用 **Bedrock 26.40+** 客户端实连；失败先看 Geyser 控制台。

## 7. 官方错误对照表

| 控制台现象 | 原因 | 处置 |
|:--|:--|:--|
| `Built-in signaling cannot use port … because the Java server already uses it` | 基岩与 Java 共用端口（`clone-remote-port`）| 要独立端口，或继续用外部信令（Geyser 自动回退）|
| `RakNet and NetherNet each need their own UDP port` | `both` 但 `webrtc-port` = 基岩端口 | 设成另一个空闲 UDP |
| `… is a loopback address` | `bedrock.address` 是 127.0.0.1 | 改 `0.0.0.0` |
| 玩家弹「trust on first use」 | 信令走明文 HTTP | 配 HTTPS 或外部信令 |

## 8. 备选路线：GeyserNetherNet 扩展（不推荐用于生产）

- 仓库 `GeyserMC/GeyserNetherNet`：以**扩展**形式加 NetherNet（HTTP 信令），README 自述 **work in progress / 未达生产可用**；需要额外依赖 **NetworkCompatible 1.8.0+**，且要自备 `https.p12`（客户端信任的证书）+ `identity.p12`（CN 会成为玩家看到的身份域名）。
- **2.12 起 Geyser 已内置 NetherNet，无需该扩展**；仅在老版本（1237 之前）或特殊需求时考虑。

## 9. 时间线备忘

| 时间 | 事件 |
|:--|:--|
| Bedrock 26.40+ | Mojang 开始推送 NetherNet 客户端 |
| **2026-10-27** | 基岩客户端停用 RakNet → 未切换服务器基岩玩家无法连接 |
| Bedrock 26.60 | 可关掉 RakNet（收敛为纯 nethernet）；同时移除 26.30 支持 |
