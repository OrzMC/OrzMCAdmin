# NetherNet（基岩新传输层）迁移知识库

> 状态：**测试服已落地并双协议验证通过（both 模式）；生产端仍为 raknet，待切** ｜ 最后更新：2026-11-02
> 来源：Geyser 官方 blog `/blog/preparing-for-nethernet`、官方 setup 文档 `geysermc.org/wiki/geyser/setup/`、**Geyser-Spigot 2.12.0-b1265 jar 反编译实证**（`GeyserConfig$BedrockConfig` / `$SignalingConfig$*`）+ **2.12.1（build 1280）实装 config.yml 字段核对**

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

## 3. 配置结构（以 **2.12.1 / build 1280 实装 config.yml** 为准）

> ⚠️ **改配置前先对照本节键名**：2.12.0 反编译出的 `signaling.port`、`signaling.builtin.advertise-addresses`、`bedrock.raknet-port` 在 2.12.1 里**已不是这些位置**——写错位置 Geyser 静默忽略，表现为「配置改了但不生效」。

```yaml
bedrock:
  address: 0.0.0.0
  port: 19132                 # 玩家连的端口；NetherNet 下同号还要占 TCP（信令）
  webrtc-port: 19134          # NetherNet/WebRTC 的 UDP；0 = 与上面同端口（单端口模式）
  transport: both             # raknet(默认) | nethernet | both；改动需重启
  clone-remote-port: false    # true 与内置信令不兼容（TCP 被 Java 占）

  signaling:
    mode: builtin             # builtin | hybrid | nxs | none
    # 对外公布地址；支持「域名/IP[:端口]」，缺省端口=NetherNet UDP 端口。留空则用本机地址 + stun-discovery
    advertise-addresses:
      ["mc.example.com:19134"]
    stun-discovery: true      # 设置了 advertise-addresses 时不生效
    builtin:
      https:                  # 同端口同时提供 HTTPS；配了玩家就看不到「信任此服务器」
        certificate: ''       # PEM 链 或 PKCS12（PKCS12 时 private-key 留空）
        private-key: ''
        password: ''          # 可用 file:/path/to/password
    nxs:                      # 外部信令（Warden 等），mode=nxs/hybrid 或内置信令起不来时用
      token: ''
      endpoint: https://agent.warden.cloud
```

**端口语义速查（回答「是不是单端口模式」就靠这张表）**：

| 模式 | 配置 | 实际占用 | 老客户端(<26.40) |
|:--|:--|:--|:--|
| RakNet（默认/生产现状） | `transport: raknet` | UDP port | ✅ |
| **both（测试服）** | `transport: both` + `webrtc-port: <另一 UDP>` | **TCP+UDP port** + **UDP webrtc-port** | ✅ |
| **nethernet 单端口** | `transport: nethernet` + `webrtc-port: 0` | **TCP+UDP 同一个 port** | ❌ |

> 「单端口」= TCP 与 UDP 同号（信令跑在 TCP 上），**不是只开 UDP**；只放 UDP → 服务器列表都刷不出来。

**系统属性覆盖**（优先级高于 config，托管方可直接写启动命令）：
`-DgeyserTransport=nethernet`、`-DgeyserUdpPort`、`-DgeyserSignalingPort`、`-DgeyserWebrtcPort`、`-DgeyserSignalingMode=nxs`

> ⚠️ **「单端口」的唯一判定标准 = `webrtc-port: 0`**（注释原文 `0 means the same port as above`）。此时 NetherNet 与 RakNet 共用 `bedrock.port`，但**信令 TCP 仍占该端口** → 「单端口」= TCP+UDP 同号，只转 UDP 时玩家列表都刷不出来。
> `webrtc-port` 填了另一个端口（如 19134）= `both` 双端口模式：UDP 19132(RakNet) + UDP 19134(WebRTC) + **TCP 19132(信令)**，共 3 条放行规则。测试服即此模式（paper 19134 / folia 19135）。
> 2026-11-02 核对：`transport: both` 的日志形态为 `Started Geyser on UDP port 19132` + `Built-in signaling started on http://0.0.0.0:19132, with NetherNet on UDP port 19134`；单端口模式日志里的 webrtc 端口号会与 bedrock 端口相同。

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
—— **不配 HTTPS 也能用，但只对纯 IP 地址成立**：客户端填纯 IP 时才回退到明文 HTTP，弹一次「信任此服务器」后即可进服；**填域名时客户端强制 TLS**（抓包可见 `16 03 01` ClientHello、SNI=域名、ALPN=h2,http/1.1），明文 HTTP 信令无法应答，客户端会卡在「加载延迟」，而服务端连一行日志都不会有。域名入口必须配 HTTPS。

## 5. 本环境适配要点（OrzMC 现状）

### 5.1 已落地（2026-10-19，本地测试服 dev.{SERVER_NAME}.cn，both 模式）

| 项 | paper（716c2f…） | folia（8A932D…） |
|:--|:--|:--|
| `transport` | `both` ✅ | `both` ✅ |
| `bedrock.port` | 19132 | 19132（容器内） |
| `webrtc-port` | 19134 | 19135 |
| `signaling.builtin.advertise-addresses` | `["{HOME_IP}:19134"]` | `["{HOME_IP}:19135"]` |
| Docker 发布 | UDP 19132 + TCP 19132 + UDP 19134 | UDP 19132 + TCP 19132 + UDP 19135（宿主侧 19133/19135） |
| 玩家填的地址 | `dev.{SERVER_NAME}.cn:19132` | `dev.{SERVER_NAME}.cn:19133` |

启动日志确认（两个实例均出现，且**不再**出现 `NetherNet support is NOT enabled`）：

```
Started Geyser on 0.0.0.0:19132
Started built-in signaling server on http://0.0.0.0:19132
NetherNet WebRTC listening on UDP 19134 (or 19135 for folia)
```

> ⚠️ **`advertise-addresses` 必须写「玩家可达的公网地址」（容器内监听 172.x，webrtc 端口经 Docker NAT）。** 2.12.1 起**支持域名**（含端口，如 `["dev.example.com:19134"]`），域名在信令启动时解析，解析失败信令就不启动；留空则用本机地址 + `stun-discovery`（跨 NAT 时公布的很可能是错误 endpoint，表现为列表能刷、进不去）。
> ⚠️ 公网 IP 动态（kmdns.net）→ 用 `scripts/nethernet_advertise_sync.py`（技能脚本目录，运行时副本在 `%LOCALAPPDATA%\hermes\scripts\`）自动跟进：DoH 查 A 记录 → 与配置比对 → 变更时改写并 `geyser reload`（只重载 Geyser，不踢 Java 玩家）。已挂 cron `orzmc-nethernet-advertise-sync`（no_agent，每 15 分钟，包装脚本 `nethernet_advertise_cron.py`，无变化时静默）。

> ✅ **2026-10-20 全链路验证通过（纯 IP 直连）**：`GET /v1/join` → 200，`POST /v1/join/<id>` → 200（返回 SDP answer），随后 UDP 19134 上 DTLS/WebRTC 建立，玩家成功进服。说明 both 模式、advertise-addresses、Docker NAT、路由器端口转发、防火墙全部正确。

> ⚠️ **域名入口当前不可用（未配 HTTPS）**：客户端填**域名**时强制 TLS，明文 HTTP 信令收到 ClientHello 后直接断开，玩家卡「加载延迟」且服务端无任何日志。测试期客户端一律用 **`{HOME_IP}:19132`**（首连弹一次「信任此服务器」）。生产上线前必须给域名补 HTTPS。

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

### 6.0 一键体检（2026-11-02 起首选）

```bash
python3 ~/.hermes/skills/gaming/orzmc/scripts/connectivity_check.py            # 全部内置目标
python3 .../connectivity_check.py --only paper,prod-mcsm --external            # 指定 + 外部节点
python3 .../connectivity_check.py --host example.com --java 25565 --bedrock 19132  # 自定义
python3 .../connectivity_check.py --json                                       # 周巡检用
```

一次输出六层结论：DNS（**自动识别本机 Clash TUN 的 `198.18.x` fake-IP，并用 DoH 取真值**）→ Java 协议握手（版本/协议号/人数/MOTD）→ 基岩**旧协议 RakNet** Pong → 基岩**新协议 NetherNet** 信令 `GET /v1/join`（返回服务端支持的 Bedrock 协议号/版本/实时人数）→ 基岩端口 **HTTPS 信令**是否可用 → 可选公网 TCP 外部节点。

判读纪律（血泪）：
- **`RakNet 无应答` ≠ 故障**：`transport: nethernet` 单端口模式本来就不答 RakNet；UDP 未转发也一样表现为无应答 → 必须与配置里的 `transport` 对照再定性。
- **`HTTPS 信令不可用` = 域名入口必挂**：客户端对域名强制 TLS，明文 HTTP 信令会被断开，玩家卡「加载延迟」且**服务端零日志**；纯 IP 直连不受影响（弹一次 TOFU 信任）。
- 生产端（2026-11-02 实测 `{SERVER_HOST}`）：Java ✅、NetherNet 信令 HTTP 200 ✅、RakNet 无应答、HTTPS ❌ → 用域名连基岩必失败，用纯 IP 可能可连。

### 6.1 单项工具

- 工具：`~/OrzMC/proxy/scripts/nethernet_check.py [host] [port]`（UDP RakNet 基线 + TCP 信令 HTTP 探测 + 结论 + 退出码 0/1，带 `-h`）
- **判定标准**：TCP 信令能返回 HTTP 应答（脚本显示 `HTTP 业务码`）= 可用；`TIMEOUT` = 未转发/被丢弃；`REFUSED` = 已转发但无监听
- ⚠️⚠️ **本机经 Clash TUN 测 TCP 必假阳性**：域名被 fake-IP 成 `198.18.x.x`，TCP 握手被 TUN 本地接管后「接受并立即关闭」→ 脚本会报 `OPEN_NO_HTTP`，误判成「端口可达」。**正确做法**：
  1. DoH 查真实公网 IP：`curl -H 'accept: application/dns-json' 'https://1.1.1.1/dns-query?name=<域名>&type=A'`
  2. 用外部节点验证 TCP：`check-host.net/check-tcp?host=<IP>:<port>` 拿 `request_id` → `check-host.net/check-result/<id>`（外部节点一律 `Connection timed out` = 未转发）
  3. UDP 侧 `check-host.net/check-udp` **无意义**（普通 UDP 包 Geyser 不回，只有 RakNet 专有包才 Pong）→ UDP 用本机 `bedrock_ping.py` 拿到真实 PONG 即为通
### 6.1 双协议连通性验证矩阵（无真实客户端也能判定到哪一层）

| 层 | 探法 | 判据 |
|:--|:--|:--|
| 旧协议 RakNet | `nethernet_check.py <host> <port>` 第 [1] 步（UDP ping） | 回 Pong + MOTD = RakNet 通 |
| 新协议信令（TCP） | `curl http://<host>:<port>/v1/join` | **200 + JSON**（`dataVersion/protocol/version/players`）= 信令服务在线且能读实时人数 |
| 新协议根路径 | `curl http://<host>:<port>/` | **404 是正常的**（根路径无 handler），不要当故障 |
| 新协议 join 握手 | `POST /v1/join/<id>` | 未带客户端流程时 **401 属预期**，不能据此判「服务坏了」 |
| 新协议真实会话 | latest.log 线程名 | `[NetherNet Built-in Signaling-N-x] Player connected with username X (2225)` = 真客户端走新传输进服成功 |
| 外网 TCP 可达 | DoH 取公网 IP → `check-host.net/check-tcp` 3 节点 | 有连接耗时 = 已转发；全 `timed out` = 未转发/被封 |
| UDP/WebRTC 端口 | ⚠️ **不要用匿名 STUN 判定** | ICE 服务忽略未认证 Binding Request，**无应答 ≠ 端口不通**；改用「docker/面板端口发布清单 + 真实会话日志」作证 |

- **两条协议不能互相替代地证明**：RakNet Pong 只证明 UDP 老通道；`/v1/join` 只证明 TCP 信令；真正进服由日志线程名区分（`localSession-*` vs `NetherNet Built-in Signaling-*`）。
- **无法自测的部分**：旧版本客户端实际登录（需客户端本体）；协议版本上限取自 `/v1/join` 的 `protocol/version`（如 2225 / 26.60），低于 Geyser 支持范围的客户端会被要求升级，与传输层无关。
- 判定纪律：结论要写清「验到哪一层」，不要用「信令通」等价于「玩家能进服」。

- 官方自检：用 **Bedrock 26.40+** 客户端实连；失败先看 Geyser 控制台。

## 7. 官方错误对照表

| 控制台现象 | 原因 | 处置 |
|:--|:--|:--|
| `Built-in signaling cannot use port … because the Java server already uses it` | 基岩与 Java 共用端口（`clone-remote-port`）| 要独立端口，或继续用外部信令（Geyser 自动回退）|
| `RakNet and NetherNet each need their own UDP port` | `both` 但 `webrtc-port` = 基岩端口 | 设成另一个空闲 UDP |
| `… is a loopback address` | `bedrock.address` 是 127.0.0.1 | 改 `0.0.0.0` |
| 玩家弹「trust on first use」 | 信令走明文 HTTP（纯 IP 直连） | 配 HTTPS 或外部信令 |
| 域名连接卡「加载延迟」、服务端无任何日志 | 客户端对域名强制 HTTPS，明文 HTTP 信令收到 TLS ClientHello 后直接断开 | 给该域名配 HTTPS（内置证书/反代/外部信令）；临时可用纯 IP 直连验证 |
| `Error while getting Paper ping passthrough: java.lang.reflect.InvocationTargetException` | Geyser 2.12.x 的 `integrated-ping-passthrough` 在 Paper 26.3 上反射失败 → 基岩看到的是 Geyser 自己的 MOTD（`motd.primary/secondary`）而不是 Java 服 MOTD | 要么 `integrated-ping-passthrough: false`（改走 `ping-passthrough-interval` 轮询），要么 `passthrough-motd: false` + 自定 `motd.*`；不影响连接 |

## 8. 备选路线：GeyserNetherNet 扩展（不推荐用于生产）

- 仓库 `GeyserMC/GeyserNetherNet`：以**扩展**形式加 NetherNet（HTTP 信令），README 自述 **work in progress / 未达生产可用**；需要额外依赖 **NetworkCompatible 1.8.0+**，且要自备 `https.p12`（客户端信任的证书）+ `identity.p12`（CN 会成为玩家看到的身份域名）。
- **2.12 起 Geyser 已内置 NetherNet，无需该扩展**；仅在老版本（1237 之前）或特殊需求时考虑。

## 9. 时间线备忘

| 时间 | 事件 |
|:--|:--|
| Bedrock 26.40+ | Mojang 开始推送 NetherNet 客户端 |
| **2026-10-27** | 基岩客户端停用 RakNet → 未切换服务器基岩玩家无法连接 |
| Bedrock 26.60 | 可关掉 RakNet（收敛为纯 nethernet）；同时移除 26.30 支持 |
