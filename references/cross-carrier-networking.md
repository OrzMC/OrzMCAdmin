# 跨网互联：电信服务器 × 联通/移动玩家（延迟高/被拒绝）

> **触发场景**：玩家报延迟高、连不上、"Connection throttled"、"Timed out"、掉线；服务器部署在单一运营商网络（如电信家宽），联通/移动玩家受害。2026-08-13 沉淀。
>
> **部署资产（完整工具链在 `OrzMC/OrzMCProxy` 仓库，2026-08-13 建仓、本地实验 100% 闭环）**：
> - 一键安装：`scripts/install-frp.sh`（Linux/macOS + systemd/launchd）、`scripts/install-frp.ps1`（Windows + 计划任务自愈）
> - 验证：`scripts/verify-tunnel.sh`（TCP+MC 握手）、`scripts/health-check.sh`、`scripts/bedrock_ping.py`（基岩入口，无需真客户端）
> - 配置模板：`configs/frps.toml.example`、`configs/frpc.toml.example`（含 `[proxies.transport] proxyProtocolVersion = "v2"`）
> - 文档：`docs/architecture.md`（延迟链路/成本）、`docs/setup-guide.md`（部署+灰度+回滚）、`docs/manual-apply-windows.md`（MCSM 面板不可用时 2 文件手动改法+重启）、`docs/troubleshooting.md`
> - 档位选择：临时（一天活动，不开 proxy-protocol，`connection-throttle: 0`）/ 正式（proxy-protocol 真实 IP 透传，三处联动）

## 根因：三大运营商骨干网独立，跨网走"独木桥"

电信/联通/移动骨干网**各自独立、互不相通**，跨网流量必须经过少数国家级互联互通节点（北京/上海/广州/郑州等）。这些节点带宽远小于网内带宽，晚高峰（19:00–23:00）严重拥塞：

| 场景 | 典型 RTT | 丢包率 |
|:--|:--|:--|
| 同网（电信→电信） | 10–30ms | ≈0 |
| 跨网（联通→电信） | 60–200ms+ | 1–10% |
| 跨网（移动→电信） | 100–300ms+ | 5–30% |

**移动最严重**：跨网互联带宽最少 + 大量 CGNAT（运营商级 NAT，玩家共享出口 IP）+ 路由可能绕路。

## "被主动拒绝"的四个机制

1. **Paper `connection-throttle`（默认 4000ms）——最典型的"主动拒绝"**
   限制**同一 IP** 4 秒内只能建立一次连接（防登录洪水）。CGNAT 下多个玩家共享同一公网出口 IP → 服务器误判为攻击 → 日志出现 `Connection throttled! Please wait 4000 ms`，直接拒连。
2. **TCP 握手丢包**：跨网拥塞时 SYN 丢失 → 客户端重传多次后放弃 → 表现为"连接超时/连接被拒绝"。
3. **登录超时被踢**：`server.properties` 的 `connection-timeout` 默认 30 秒；跨网拥塞时「加密握手+正版认证+区块加载」超过 30 秒 → 服务端踢 `Timed out`。
4. **OS SYN backlog 耗尽**：慢速跨网握手占满半连接队列 → 内核直接丢弃新 SYN。

## 解法（按性价比）

| 方案 | 说明 | 效果 |
|:--|:--|:--|
| 多线 BGP 机房/云主机 | 阿里云/腾讯云轻量均为三网直连 | ⭐⭐⭐ 根治 |
| **中转机（家里服务器首选）** | 三线轻量云做中转（FRP / Tailscale / iptables 转发），玩家连中转 IP，中转再连家里服务器。**MCSM 电信家宽 50M 上行场景即此类** | ⭐⭐⭐ 根治级 |
| 玩家加速器 | 玩家自己走优化线路 | ⭐⭐ |
| 配置治标 | `connection-timeout` 调 60–120s；`connection-throttle` 谨慎放宽（有被刷风险）；Paper 1.19.3+ packet-limiter 放宽 | ⭐ 缓解 |

## 同源问题解法：PROXY protocol 真实 IP 透传（2026-08-13 本地实测 ✅）

中转后所有玩家同源 IP（中转机 IP）会误伤 connection-throttle 等按 IP 功能。解法 = PROXY protocol 透传真实 IP：

**配置（三处联动）**：
1. frpc 每个代理（frp ≥0.60 语法）：`[proxies.transport]` 子表配 `proxyProtocolVersion = "v2"`——⚠️ **不在 proxies 顶层**（顶层报 `unknown field "proxyProtocolVersion"`）
2. Paper：`config/paper-global.yml` → `proxies.proxy-protocol: true`——⚠️ **不是 spigot.yml 的 bungeecord**（bungeecord 模式解析 BungeeCord 转发数据 `\00IP\00UUID`，不认 PROXY 头；两者是独立机制）
3. Geyser（基岩）：`plugins/Geyser-Spigot/config.yml` java 段 `use-haproxy-protocol: true`——否则基岩玩家挂

**实测验证（本地测试服 paper-26.2-111 + frp v0.70.1）**：
- 手写 PROXY v2 头伪造 IP（203.0.113.5:40000）直连 → 服务器日志如实显示 `/203.0.113.5:40000`，IP+端口透传 100% 工作
- 开 proxy-protocol 后**直连（无 PROXY 头）被服务器静默拒绝/超时**（官方行为：normal clients 无法连接）→ 直连地址从此不可用
- frp 隧道全链路：握手→Login Start→白名单检查完整走通

**档位选择**：
| 档位 | 配置 | 适用 |
|:--|:--|:--|
| 临时（一天活动） | 不开 proxy-protocol，Paper `connection-throttle: 0` | 快速零风险，接受同源 IP |
| 正式（长期） | 开 proxy-protocol（frpc + paper-global.yml + Geyser haproxy） | 真实 IP，防误伤 |

**实验坑备注**：Paper 26.2 = MC 1.21.11 = 协议 **776**；1.21.11 的 Login Start（serverbound/minecraft:hello）含 **playerUUID** 字段。**⚠️ 1.21.1 (767) 的 Login Start 也有 playerUUID**（2026-08-14 查 minecraft-data 确认）——写离线登录测试脚本统一发 `name + UUID(16B)`；只发 name 必报 `Failed to decode packet 'serverbound/minecraft:hello'`（曾误判为 ViaVersion/proxy 问题，实为脚本格式 bug）。

**ViaVersion 兼容性（2026-08-14 补测 ✅）**：proxy-protocol 模式下 767/768/770/775/776 全协议版本经隧道登录流程完整（ViaVersion 5.11.0 翻译正常）——老版本玩家无影响。

**Geyser 基岩入口验证法（2026-08-14 补测 ✅）**：无需基岩客户端——RakNet Unconnected Ping（UDP 19132，packet 0x01 + magic）→ 收 Pong(0x1c)+MOTD = Geyser 存活且 Geyser→Java 连接（haproxy 头）被 Paper 接受。工具：`OrzMCProxy/scripts/bedrock_ping.py`。正式档配置生效标志：Geyser 启动日志 WARN「Geyser is configured to use proxy protocol when connecting to the Java server」。

## 诊断

- 服务端日志 grep：`Connection throttled` / `Timed out` / `Lost connection`
- 玩家端对服务器 IP 做 ping/mtr，跨网 vs 同网对比 RTT 与丢包率，确认是否互联节点拥塞
- proxy-protocol 相关：frpc 日志 `unknown field` = 配置位置错；服务器日志无记录 + 客户端超时 = PROXY 头没到/没开 proxy-protocol
