# Eaglercraft 网页客户端接入（给没有代理层的服加 wss 入口）

老板要「让网页客户端能进服」时用本文。核心口径：**这不是装一个插件的事**——网页客户端必须有一个 **wss://** 入口 + 后端能翻译 1.8 协议，缺一个都进不去。

## 先判现状：这台服有没有代理层

从外部对 25565 做状态包握手，看返回的版本串：

```bash
PYTHONPATH="" python "$LOCALAPPDATA/hermes/scripts/connectivity_check.py" --host <域名> --java
# 回 "Paper 26.3"           → 无代理层，Paper 直占 25565
# 回 "Velocity 1.7.2-26.3"  → 已有代理层，只加 EaglerXServer 插件 + wss 反代即可
```

国内生产服实测（2026-11）：`{SERVER_HOST}:25565` 回 **Paper 26.3**（无 Velocity），Geyser-Spigot `both` 模式占 `19132/tcp+udp` + `19134/udp`，`online-mode=false`。

## 两条路线，先选再动手

| | **EaglerXPaper**（Paper 插件，无代理） | **Velocity + EaglerXServer**（补一层代理） |
|:--|:--|:--|
| 改动面 | 只加 1 个 jar（双栈复用原端口）+ 一个 wss 反代 | Paper 退到 `127.0.0.1:25566` + 转发密钥 + 代理进程 |
| 真实 IP | 直连 Paper，天然真实 | 配 `MODERN` 转发才真实，配错即全 `127.0.0.1` |
| 停服代价 | 一次重启（Paper 冷启动 90–110s） | 端口迁移，失败会让 Java 玩家全被拒 |
| Folia | ❌ 不支持 | ✅ |
| 维护风险 | 单人 fork，靠 NMS 反射名表，Paper 大改后可能失效 | 上游维护，稳定 |
| 只能面板手维（无 APIKey） | ✅ 回滚 = 删 jar | 多一个常驻进程 + 服务化 |

**选择口径**：无代理层 + 只有 Paper + 要最小改动 → EaglerXPaper；要覆盖 Folia，或需要转发真实 IP/多后端 → Velocity 方案。Velocity 方案留作 EaglerXPaper 失效后的备胎。

## EaglerXPaper 事实表（用前重新核对，别照抄）

```bash
# 仓库/README/依赖一律用 gh CLI 取原文
export HTTPS_PROXY=http://127.0.0.1:7897
gh api repos/PlanetDogeCodes/EaglerXPaper --jq '{pushed:.pushed_at,stars:.stargazers_count}'
gh api repos/PlanetDogeCodes/EaglerXPaper/readme -H "Accept: application/vnd.github.raw"
gh release download v1.1.1-S2 -R PlanetDogeCodes/EaglerXPaper -p '*.jar' -O eaglerxpaper.jar
PYTHONPATH="" python -c "import zipfile;print(zipfile.ZipFile('eaglerxpaper.jar').read('plugin.yml').decode())"  # 确认真实插件名/api-version
```

- jar 内 `plugin.yml` 的 `name` 是 **`EaglercraftXServer`**，所以配置目录是 `plugins/EaglercraftXServer/`；配置结构与上游 EaglerXServer 一致，可直接套用。
- **硬依赖 ViaVersion + ViaBackwards**（作者原文 "NEEDED for this plugin to function"）；要 1.8 客户端进来还需 **ViaRewind**。后端 26.3 时，1.8.8 网页客户端全靠这层翻译。
- 支持 **Paper 1.12.2 – 1.21.11+**，26.x 需 **Java 25+**，**不支持 Folia**。
- 与 Geyser/Floodgate 可共存；`online-mode=true` 的正版验证服不能开箱即用（离线服才行）。
- 它**不发客户端文件**：玩家得自己填 `wss://域名/`，或另装 EaglerWeb（上游标注未在 1.21+ 实测，不算承诺）。

## 双栈（同一端口同时吃 WebSocket 和原生 TCP）怎么配

机制：看每个连接的**首包**——HTTP 升级请求进 Eagler 的 WS 管线，原生 Minecraft 握手原样透传给 Paper。不需要第二个端口，Java 玩家无感。**`dual_stack` 默认就是 true。**

`plugins/EaglercraftXServer/listeners.toml`：

```toml
[[listener_list]]
	listener_name = "listener0"
	inject_address = "0.0.0.0:25565"      # 必须等于 Paper 实际监听；server-ip 留空就用 0.0.0.0
	dual_stack = true                      # 核心开关，默认 true
	forward_ip = false                     # 有反代时置 true
	forward_ip_header = "X-Real-IP"        # 与反代实际传的头名对齐
	spoof_player_address_forwarded = true  # 让 Paper 侧看到真 IP（IP 封禁/限流才有效）
	forward_secret = false                 # 25565 直接暴露公网时设 true，防伪造头绕过反代
	forward_secret_header = "X-Eagler-Secret"
	server_motd = ["&6OrzMC 网页版"]
```

协议窗口看 `settings.toml` 的 `[protocols]`（详见 `references/client-version-range.md`）。

## TLS 两种做法，**二选一，绝不能同时开**

**① 反代终结（推荐，证书轮换省心）** —— 插件侧 `tls_config.enable_tls = false`：

```
mc.example.com {
    reverse_proxy 127.0.0.1:25565 {
        flush_interval -1                 # 缺这行 = 长连接被缓冲，网页客户端连上即断
        header_up X-Real-IP {remote_host} # 头名要与 forward_ip_header 一致
    }
}
```

**② 插件自带 HTTPS**（不想引 Caddy）：

```toml
	[listener_list.tls_config]
	enable_tls = true
	require_tls = false                       # false = 同端口兼收 ws/wss（按首字节 0x16 区分 TLS）
	tls_public_chain_file = "fullchain.pem"   # 必须是含中间证书的完整链
	tls_private_key_file = "privatekey.pem"
	tls_auto_refresh_cert = true
```

证书走 **DNS-01**（国内机房/家宽 80 端口验证常不通，未备案 443 也可能被拦）；Cloudflare **橙云代理不了 25565**，只能当 DNS + 证书源，流量走自己的 443。

## 上线验证（顺序固定）

```bash
# 1) WS 侧：期望 101 Switching Protocols
curl -i -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" \
  http://127.0.0.1:25565/
# 2) 只有一个监听者（不是偷偷起了第二端口）
netstat -ano | findstr :25565
# 3) Java 侧没被弄坏
PYTHONPATH="" python "$LOCALAPPDATA/hermes/scripts/connectivity_check.py" --host <域名> --java
# 4) 真跑：浏览器 wss://域名/ 进服 + 基岩 19132 仍通 + 三个 Java 客户端（1.8.8 / 中间版 / 服务端版本）各进一次
```

## 坑

- **`inject_address` 与 Paper 实际绑定不一致 → 静默失效**：日志不报错，WS 一律超时。改完先看启动日志有没有注入行。
- **`server.properties` 里 `server-ip=127.0.0.1`**：外网连 WS 也进不来，双栈绑定跟着变回环。
- **`forward_ip=true` 但反代没传对应头**：网页玩家 IP 全变 `127.0.0.1`，限流与 IP 封禁一起失效；`forward_secret` 不开又暴露 25565，别人可伪造该头绕过反代。
- **反代 + 插件自带 TLS 同时启用 = 双重 TLS**，握手必然失败。
- **Netty 管道会抢**：EaglerX 系靠注入 pipeline 工作，与同样改管道的插件（`packetevents`、`GrimAC` 内嵌 packetevents）叠加时，「登录后 Bad packet id」「偶发断连」是典型症状。**上生产前先在一份实例副本上灰度。**
- **核对作者实测过的核心版本**：README 写 "up to 26.x" 但列出的是 1.21.11–26.2；跑 26.3 属「大概率行、未验证」，出问题先怀疑反射名表，不是配置。
- **网页客户端只能 `wss://`**：https 页面里的 `ws://` 会被当混合内容拦掉，TLS 这层躲不掉。

## 回滚

EaglerXPaper：停服 → 删 `plugins/EaglerXPaper*.jar`（配置目录可留）→ 启动，Java 入口零改动。
Velocity 方案：`velocity.toml` 恢复 + Paper 端口改回 + 转发密钥置空 → 重启，先备份实例目录。
