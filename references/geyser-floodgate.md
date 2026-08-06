# Geyser 基岩支持运维笔记

> 用途：基岩版玩家（手机/PE/Win10 版）通过 Geyser 进 Java 服。
> ⚠️ **当前模式（2026-08-05 起）**：三端均为**离线服 + Geyser offline 直连**，**未装 floodgate**。基岩玩家以**无前缀名字**直连（Geyser 生成随机离线 UUID），行为与 Java 玩家一致。

## ⚠️ floodgate 回退记录（2026-08-05，勿再装）

**floodgate 与 LoginSecurity 冲突，三端已回退**：
- floodgate 给基岩玩家加 `.` 前缀 → LoginSecurity `filter-special-chars` 判非法字符**拒绝登录**
- 基岩玩家走 LoginSecurity 注册（无前缀名字），floodgate 无收益纯冲突
- 回退动作：**删 floodgate.jar** + Geyser `auth-type: offline`（离线服基岩玩家无前缀直连，与 Java 玩家一致）
- 回退后验证：floodgate 日志 0 行；Geyser 正常 Enabling + UDP 19132 监听

> 📌 若未来换掉 LoginSecurity 或改前缀方案，才考虑重新评估 floodgate。

## 渠道铁律：官方下载站优先（用户拍板 2026-08-05）

**Geyser 安装/更新一律走官方下载站 `download.geysermc.org`**——Hangar/Modrinth 平台相对更新更慢，可能落后多个版本/缺失 spigot 平台版。

| 组件 | 官方渠道 | Hangar | Modrinth |
|:--|:--|:--|:--|
| Geyser | ✅ `download.geysermc.org` | 有（但慢）| 有（但慢）|
| Floodgate | ✅ `download.geysermc.org`（唯一正确）| ⚠️ **2023-03 停更** | ❌ **只有 fabric/neoforge，无 spigot** |

**查最新版 + 下载（官方站 API）**：
```bash
# 1. 查最新版本/构建
curl -s https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest
# 2. 下载 spigot 平台版（= Paper 兼容）
curl -sL -o Geyser-Spigot.jar "https://download.geysermc.org/v2/projects/geyser/versions/<版本>/builds/<构建>/downloads/spigot"
```

## 当前版本（2026-08-06 三端升级完成）

| 组件 | 版本 | 部署方式 |
|:--|:--|:--|
| Geyser-Spigot | **2.11.1-SNAPSHOT** (b1208) | 升级走 plugins/update/（MCSM 借 9:00 自动重启生效）|

- 版本号带 `-SNAPSHOT` 是 GeyserMC 下载站的正常命名（build 号才是关键）
- sha256 校验：Geyser-Spigot 2.11.1 = `632cffee2edd5f93356364e87d3ef8f9a1db93ed0fa2070fa4d1cbcdb89f1fb9`
- 升级路径（PaperMC update 机制）：新 jar 放 `plugins/update/` → 重启原子替换，update/ 自动清空

## 验证流程

### 1. 加载验证
```bash
grep -iE "Enabling Geyser" <服务器>/logs/latest.log
# 期望: [Geyser-Spigot] Enabling Geyser-Spigot v2.11.1-SNAPSHOT
# 确认 auth-type: offline（Geyser/config.yml），floodgate 无加载行
```

### 2. UDP 端口验证
```bash
grep -iE "Geyser" logs/latest.log | grep -i "UDP"
# 期望: [Geyser-Spigot] 已在 UDP 端口 19132 上启动 Geyser
```

### 3. RakNet 握手测试（无需真机，脚本化）
`scripts/regression/geyser_udp_test.py` —— 发 RakNet Unconnected Ping (0x01) 验证响应：
```bash
python3 scripts/regression/geyser_udp_test.py
# ✅ 期望: 收到 Unconnected Pong (0x1c) + 服务器名
```
- 服务器名格式（RakNet MOTD）：`名称;协议;版本;在线数;上限;GUID;副标题;模式;1;端口`
- 端口 19132 是 **UDP**（不是 TCP）——lsof 查要用 `lsof -iUDP:19132`

## 三端部署差异

| 端 | Geyser 状态 | 升级方式 |
|:--|:--|:--|
| 本地测试服 | 2.11.1 ✅ UDP 19132 | 停服→update/→start |
| Exaroton | 2.11.1 ✅ UDP 39742 | **运行中禁止写文件**：先 stop → update/ → start |
| MCSM | 2.11.1 ✅ UDP 19132 | **运行中可写 update/**（上传不锁定）→ 等 9:00 自动重启生效 |

- ⚠️ MCSM 是 Windows 主机：日志路径反斜杠（`plugins\Geyser-Spigot.jar`），文件系统大小写不敏感
- ⚠️ 插件基线要求三端 sha256 一致（文件名相同≠内容相同）

## 联动效果（offline 直连模式）
- 基岩玩家以**无前缀名**进服（与 Java 玩家一致），LoginSecurity 可正常注册/登录
- Geyser 生成随机离线 UUID（跨会话稳定）
- LuckPerms 可按基岩玩家名授权限
- SkinsRestorer 正常服务基岩皮肤

## 坑
- **Hangar Floodgate 是旧版（2023）**——别从那下（官方站优先）
- **Modrinth 无 spigot 版**——别浪费时间（官方站优先）
- **更新勿等 Hangar/Modrinth 推送**——它们比官方站慢，Geyser 一律官方站查版本
- ⚠️ **勿装 floodgate**（2026-08-05 回退原因见顶部）——除非 LoginSecurity 方案变更
