# 公网入口排障：域名/端口映射都配好了，外网就是连不上

> 2026-09-11~12 本机（Windows + Clash TUN + Docker Desktop WSL2 mirrored + MCSM 实例）实测定论。
> 结论先行：**问题常不在路由器/运营商，而在本机 Clash 的 TUN 抢了默认路由，把「入站连接的应答包」送进了代理隧道。**

## 1. 症状特征（一套组合拳就能判定）

| 现象 | 说明 |
|:--|:--|
| 局域网内直连 `192.168.0.33:25565` **通** | 服务本身没问题 |
| 外网（手机蜂窝/check-host/mcsrvstat）**全超时** | 卡在入站这一跳 |
| 外网 **ICMP ping 通**、**TCP/UDP 全挂** | 包能到公网 IP，但转发后的应答回不去 |
| 本机跑 **Clash TUN 模式**（有 `198.18.0.0/15` 假 IP 网段） | 头号嫌疑 |
| 同一公网 IP 下**另一台设备**的服务（映射到别的机器）**外网可通** | 反证路由器/运营商没问题 |

⚠️ 在**本机**上测域名/公网 IP 全是假结果（Clash DNS 劫持成 `198.18.x.x`、默认路由走 TUN、路由器不支持 hairpin）。
必须从**外部节点**测：check-host.net（TCP/UDP 全球节点）、api.mcsrvstat.us（Java+基岩真实协议）、api.mcstatus.io（基岩）。

## 2. 根因链

```
Clash TUN 网卡(198.18.0.1) 默认路由 metric=1  <  Wi-Fi(192.168.0.33) metric=45
        ↓ 所以「本机发出的包」（包括入站连接的应答）走 TUN
入站 SYN 到达 192.168.0.33:25565（抓包可见 eth4 In）
        ↓
应答包按默认路由进 TUN：Java 的 SYN-ACK 钻隧道、基岩 pong 源地址被定成 198.18.0.1
        ↓
客户端收不到正确来源的应答 → 超时（所以「内网通、外网不通」）
```

抓包定位（WSL 内，`tcpdump -n -i any`）：
```
eth4  In  IP <外网IP> > 192.168.0.33.25565: Flags [S]     ← 入站正常
eth0  Out IP 192.168.0.33.25565 > <外网IP>: Flags [S.]    ← 应答从 TUN(eth0) 走了 ✗
```

## 3. 修复：通用策略路由（按源地址，与端口无关）

原理：让应答包在**第一次查路**时就用 LAN 出口 + LAN 源地址，完全不依赖 NAT。

```bash
ip route replace default via 192.168.0.1 dev eth4 src 192.168.0.33 table 100
ip route replace 192.168.0.0/24 dev eth4 src 192.168.0.33 table 100
ip rule add from 192.168.0.33 table 100 pref 85          # 通用：任意端口
ip rule add ipproto tcp sport 25565 table 100 pref 90    # 兜底：已知端口
ip rule add ipproto udp sport 19132 table 100 pref 90
```

`from <LAN IP>` 的语义 = **所有监听在 LAN IP 上的服务（容器发布端口、宿主服务，任意端口）**的应答都走 Wi-Fi 正门；Clash 代理流量源地址是 `198.18.x` → 不受影响（实测：加规则后出站出口 IP 仍为 Clash 出口，代理未破坏）。**→ 以后新增任何自定义端口都不需要再改这一层。**

验证路由决策（不需要外部客户端）：`ip route get 1.1.1.1 from 192.168.0.33 ipproto tcp sport 40000` → 应 `via 192.168.0.1 dev eth4 table 100`。

⚠️ 区分：`from` 规则管的是**源地址**（服务应答），因此对 Windows 宿主服务同样适用（mirrored 共享网络栈）；而 `iptables -j MARK` 方案只能改出口、**改不了已被 TUN 定死的源地址**，UDP 会因此失效。

脚本（幂等、自带 `--check` 自愈）: `scripts/orzmc-mc-reply-route.sh`
部署位置（本机）: `/usr/local/bin/orzmc-mc-reply-route.sh`（WSL Ubuntu 内）+ 规范副本 `E:/orzmc/scripts/orzmc-mc-reply-route.sh`
持久化: Windows 计划任务 **OrzMC-MC-Reply-Route**（`wsl -d Ubuntu -u root -- bash /usr/local/bin/orzmc-mc-reply-route.sh`）——`wsl --shutdown`/重启后规则会丢，靠它自愈。**2026-10-04 起重复间隔 10min → 3min**（`schtasks /change /tn OrzMC-MC-Reply-Route /RI 3 /DU 24:00`，改完 `Get-ScheduledTask` 确认 `LogonType=Interactive` 未被改动），脚本日志 `/var/log/orzmc-mc-reply-route.log`。

### ⚠️ 3b. 自愈会「静默失效」：ip rule 活着、table 100 路由没了（2026-10-04 实测复发）

**症状**：内网直连 25565/19132 正常，外网 Java/Bedrock 全部超时；计划任务 `LastTaskResult=0`（看起来一直在成功自愈）。

**根因**：`ip rule`（from/sport 规则）与 table 100 的路由**生命周期不同**——路由会丢、规则不会。旧脚本 `need_apply()` 虽能发现路由缺失，但**应用后不校验**：`ip route replace` 失败（网卡/命名空间瞬态异常）时 `ip rule add` 照样成功，脚本照旧 `exit 0` → 计划任务永远显示成功，自愈通道静默死亡。已用 `ORZMC_IFACE=eth9` 伪造场景复现出完全相同的「有规则、无路由」残局。

**一条命令判定**：`ip rule show | grep 'from <LAN IP> lookup 100'`（有）但 `ip route show table 100`（空）→ 就是这个。

**为何会丢**：table 100 **不是本方案专属**——WSL mirrored 网络栈存在自带规则 `100: from all fwmark 0x9 lookup 100`（非本脚本添加），该表可能被 WSL/HNS 网络事件重写。实测排除项：Docker 容器起停（`docker run -p` / `rm -f`）**不会**清表；`wsl` 发行版 uptime 连续 24 天未重启也复现过，故不是 WSL 重启导致。

**v2 脚本修复（已部署 E:/orzmc/scripts → WSL /usr/local/bin 与 Hermes 技能副本，三处 md5 一致）**：
- 应用后**自校验**（table 100 含 `src <LAN IP>` + from 规则 + 每条 sport 规则），最多重试 3 次；失败 `exit 1` + 日志，计划任务 `LastTaskResult≠0` 可见。
- **自动探测** LAN 网卡/网关/本机 IP（从 main 表里排除 `198.18.0.0/15` 的默认路由取），不再硬编码 `eth4`/`192.168.0.33`——换 Wi-Fi/换网段/换机不再需要改脚本；`ORZMC_IFACE/ORZMC_GW/ORZMC_SIP` 仍可覆盖。
- 日志 `/var/log/orzmc-mc-reply-route.log`（`OK 已就位` / `DETECT 需要修复` / `APPLIED … 校验通过` / `FAIL …`）。
- 自测方法：`ip route flush table 100` → 跑脚本应打印 `DETECT`+`APPLIED …校验通过`；`--check` 此时应输出 `MISSING:` 并 `exit 1`。

### 3c. 排障顺序（2026-10-04 定稿，照这个走 10 分钟出结论）

1. **服务在不在**：`wsl -d Ubuntu -u root -- ss -lntup | grep -E '25565|19132'`（宿主 Windows `netstat` 在 mirrored 模式下**看不到**容器发布端口 → 别据此判「没监听」）。
2. **路由层有没有坏**：`ip rule show | grep 100` vs `ip route show table 100`（见 3b）。
3. **入站到没到**：WSL 内 `nohup timeout 60 tcpdump -n -i eth4 -l 'tcp port 25565 or udp port 19132' > /tmp/cap.txt &`，再从外部触发探测；看 `eth4 In` 有没有包、应答源地址是不是 `192.168.0.33` 且从 eth4 出。**入站有 + 应答正常 = 本机没问题**。
4. **外部多节点**：`check-host.net/check-tcp?host=域名:端口`（Node 命名空间直接看结果）+ `api.mcstatus.io`。
5. **DDNS/公网 IP**：`dev.{SERVER_NAME}.cn → CNAME home.{SERVER_NAME}.cn → CNAME wangzhizhou.kmdns.net → A <公网IP>`；用 DoH 取真实 IP（`223.5.5.5/resolve?name=dev.{SERVER_NAME}.cn&type=A`），本机 `ping/nslookup` 只会给 Clash 假 IP `198.18.x.x`。抓到入站包即证明 DDNS/路由器映射都正常。

### 3d. 防火墙三条规则已存在（核对用，别重复加）
`OrzMC Java 25565 TCP` / `Bedrock Geyser 19132 UDP`（另 25566/19133）均为 `Allow / Any`，`Get-NetFirewallRule -Direction Inbound -Enabled True` 可查。

## 4. 走过的弯路（别重复）

| 尝试 | 结果 |
|:--|:--|
| `iptables -t mangle -j MARK` + `ip rule fwmark` | 只改了出口网卡，**源地址仍被 TUN 定死**（源选择发生在打标前的首次查路）→ Java 能好、UDP 不行 |
| `-t nat POSTROUTING -j SNAT --to-source 192.168.0.33` | 计数在涨但包在内核里消失（nat 后无输出）→ 弃用 |
| 直接 `ip rule add sport 19132 ...` | 语法错，须写成 `ip rule add ipproto udp sport 19132 ...` |
| 在**本机**测公网域名/端口 | 全是假结果，必须用外部节点 |

## 5. 验证

```bash
# 外部实测（必做）
curl -s 'https://api.mcsrvstat.us/3/<域名或IP>:25565'        # Java → online:true + MOTD
curl -s 'https://api.mcsrvstat.us/bedrock/3/<IP>:19132'      # 基岩 → online:true
curl -s 'https://api.mcstatus.io/v2/status/bedrock/<域名>:19132'
# 抓包确认应答从 eth4 出去且源地址 = LAN IP
wsl -d Ubuntu -u root -- bash -c "tcpdump -n -i any 'tcp port 25565'"
```
⚠️ mcsrvstat 有缓存（30min 级）与偶发解析抖动：同一端口可能「域名形式 False / 裸 IP 形式 True」→ **至少两源交叉验证**（mcsrvstat 裸 IP + mcstatus.io）再下结论。

⚠️⚠️ **2026-10-04 实测：mcsrvstat.us 会误报 False，不能当首选判据**——同一时刻 `api.mcstatus.io` 双通道 `online:true`、`check-host.net` 6 个全球节点 TCP 全部 OK，而 mcsrvstat 的 java/bedrock 都报 False；同时在 WSL 抓包（`tcpdump -i eth4 'tcp port 25565 or udp port 19132'`）**看不到 mcsrvstat 的探测包到达**（只看到 mcstatus.io 的 RakNet ping/33B 与 SYN 到达，且我们的应答确实从 `192.168.0.33` 经 eth4 发出）。→ 结论：该源自身探测链路/缓存有问题。**判据优先级：本机抓包（入站+应答源地址）= 决定性的；其次 check-host.net TCP/ping 多节点 + mcstatus.io（Java/Bedrock 双协议）；mcsrvstat 仅作参考。**

## 6. 与端口映射的关系

- 路由器「虚拟服务器」规则 + Windows 防火墙 Allow 规则是**必要**的，但不是充分条件——本机 Clash TUN 不修，映射再对也连不上。
- 基岩无 SRV，玩家必须手填端口；`cloudflared` 隧道**不支持 UDP**，基岩没法走隧道（要走就用 frp/playit.gg）。

## 7. 老板决策（2026-09-12）：新端口要不要免配置

- **防火墙 / 路由器：坚持逐端口配置**（老板原话：「按单端口配置安全一些，需要时再加」）→ **不要再建议 DMZ 主机或端口段映射**（曾提议 A/B 方案被否）。
- **WSL 策略路由层：已用通用 `from <LAN IP>` 规则**，零维护（新增端口不用改这里）。
- 所以新增一个自定义端口的完整流程 = ①路由器加一条映射 ②Windows 防火墙加一条 Allow ③MCSM 实例 `docker.ports` 加一条 —— 共三处，路由层不用动。
- 验收记录：2026-09-12 老板手机蜂窝实连 Java 双实例（25565/25566）+ 基岩双实例（19132/19133）均连通 ✅。
