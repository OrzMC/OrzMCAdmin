# Geyser + floodgate（基岩支持）运维笔记

> 用途：基岩版玩家（手机/PE/Win10 版）通过 Geyser 进 Java 服；floodgate 负责身份映射（基岩 ID → Java UUID），让 LuckPerms/白名单/LoginSecurity 可适配。
> ⚠️ **没有 floodgate = 基岩玩家以 Geyser 生成前缀名身份进服**（如 `.joker_1234`），权限/白名单完全无法适配——**必须装**。

## 版本匹配（2026-08-05 测试服实证）

| 组件 | 版本 | 渠道 |
|:--|:--|:--|
| Geyser-Spigot | 2.11.0-SNAPSHOT (b1205) | plugins/ 直放（新装）|
| Floodgate | **2.2.5 (b138)**，显示为 2.2.5-SNAPSHOT | **官方下载站**（见下）|

**⚠️ Floodgate 渠道坑**：
- **Modrinth**：只有 fabric/neoforge 加载器，**无 bukkit/spigot/paper 版** ❌
- **Hangar**：GeyserMC 官方项目但 **2023-03 后停更**（旧版）⚠️
- **✅ 官方下载站**（与 Geyser 同源，唯一正确渠道）：
  ```bash
  # 查最新
  curl -s https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest
  # 下载 spigot 版（= Paper 兼容）
  curl -sL -o floodgate-spigot.jar "https://download.geysermc.org/v2/projects/floodgate/versions/2.2.5/builds/138/downloads/spigot"
  ```
- 安装：**新插件直放 `plugins/`**（非 update/），文件名可改 floodgate.jar

## 验证流程

### 1. 加载验证
```bash
grep -i floodgate <服务器目录>/logs/latest.log | grep -v DEBUG
# 期望: [floodgate] Enabling floodgate v2.2.5-SNAPSHOT
#       [SkinsRestorer] Floodgate skin listener registered  ← 联动正常
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
# ✅ 期望: 收到 Unconnected Pong (0x1c) + 服务器名 "perMC Server | welcome;1001;26.33;..."
```
- 服务器名格式（RakNet MOTD）：`名称;协议;版本;在线数;上限;GUID;副标题;模式;1;端口`
- 端口 19132 是 **UDP**（不是 TCP）——lsof 查要用 `lsof -iUDP:19132`

## 联动效果
- 基岩玩家进服后 floodgate 分配 **真实 Java UUID**（离线服为 随机离线 UUID，但**跨会话稳定**）
- LuckPerms 可按基岩玩家名授权限（与 Java 玩家无冲突）
- SkinsRestorer 自动注册 floodgate skin listener（基岩皮肤）

## 坑
- **Hangar Floodgate 是旧版（2023）**——别从那下
- **Modrinth 无 spigot 版**——别浪费时间
- 版本号带 `-SNAPSHOT` 是 GeyserMC 下载站的正常命名（build 号才是关键）
