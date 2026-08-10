# OrzMC Rank 玩家在线时长数据源调研（2026-08-07 实测，最终方案已验证）

背景：Rank 晋升模块需要「累计在线时长」。用户要求**优先 PaperMC 插件 API**、与服务器同一数据源、玩家离线也能读。以下为三种方案的实测结论。

## 方案对比（实测终版）

| 方案 | 必须在线？ | 实测结果 | 结论 |
|:--|:--|:--|:--|
| 自计算（join/quit 事件差） | ✅ 必须 | 可行但崩溃丢最后一段时长；quit 事件异常断线不触发 | ❌ 放弃 |
| **读 stats 文件**（`<世界根>/players/stats/<uuid>.json`） | ❌ 不需要 | **✅ 最终采用**：与服务器同源、离线可读、零自计算误差 | ✅ 采用 |
| `OfflinePlayer.getStatistic(Statistic.PLAY_ONE_MINUTE)` | ❌ 设计上可离线 | **在线/离线都恒返回 0**（Paper 已知 bug） | ❌ 不可用 |

## ✅ 最终实现方案（已实测通过，HermesBot 显示 106 分钟）

```java
static Path statsDirectory() {
    var worlds = Bukkit.getWorlds();
    if (!worlds.isEmpty()) {
        Path p = worlds.get(0).getWorldFolder().getAbsoluteFile().toPath();
        while (p != null) {
            if (Files.exists(p.resolve("players").resolve("stats"))) {
                return p.resolve("players").resolve("stats");
            }
            p = p.getParent();
        }
    }
    // 兜底：世界容器根
    return Bukkit.getWorldContainer().getAbsoluteFile().toPath()
            .resolve("world").resolve("players").resolve("stats");
}
// 读值：Gson 解析 stats.minecraft.custom["minecraft:play_time"]，tick ÷ 1200 = 分钟
```

**⚠️ Paper 26+ 核心坑（调试日志逐层暴露）**：
- `Bukkit.getWorlds().get(0).getWorldFolder()` 返回**维度子目录**：`world/dimensions/minecraft/overworld`——不是世界根！
- stats 实际在世界根：`world/players/stats/`（players 子目录，不是 `world/stats/`）
- **固定 getParentFile() 一次/两次都错**（`.../dimensions/minecraft/overworld` 的父链是 `minecraft` → `dimensions` → `world`，层级会随版本变化）——**向上遍历找含 `players/stats` 的祖先目录**最稳
- 插件代码里 `Paths.get("world",...)` 相对路径解析到 `<server>/plugins/<PluginName>/world/...`（data folder，不存在）→ 必须绝对路径

## ✅ 已验证事实（可复用）

1. **stats 文件位置**：`<世界根>/players/stats/<uuid>.json`——注意是 **players 子目录**（`world/players/stats/`），不是 `world/stats/`
2. **时长键**：`stats.minecraft.custom["minecraft:play_time"]`（tick 单位），另有 `minecraft:total_world_time`。实测 joker=269726 ticks≈224 分钟
3. **tick→分钟**：÷1200（20 tick/s × 60 s/min）
4. **离线服 UUID 算法**：`UUID.nameUUIDFromBytes(("OfflinePlayer:"+name).getBytes())` 的 **RFC4122 v3**（bytes[6] |= 0x30、bytes[8] |= 0x80）。Java 手拼 UUID 会错版本位（如 1187 vs 3187）——用 `UUID.nameUUIDFromBytes` 或 Python `uuid.uuid3` 等价实现
5. **Paper API 无自定义 key 读统计方法**：反编译 paper-api 26.1.2 确认 `OfflinePlayer.getStatistic`/`Player.getStatistic` 只收 `Statistic` 枚举（无 NamespacedKey 版本）
6. **getStatistic(PLAY_ONE_MINUTE) 恒 0 的根因**：PaperMC/Paper#9507——Bukkit 按枚举名生成键 `play_one_minute`，但 MC 1.20.2+ 服务器内部键改名 `minecraft:play_time`，映射断裂；`TOTAL_WORLD_TIME` 同理（键名虽一致但离线玩家 getStatistic 也不读磁盘）

## 调试方法（本会话有效）

- **读 0 且原因不明时，在 getPlaytimeMinutes 加临时日志打印解析路径 + Files.exists()**——日志直接暴露真实路径（`world/dimensions/minecraft/overworld/...`）→ 才知道是维度目录问题
- 日志条件注意：只在 `ticks <= 0` 时打，避免刷屏；修完删日志
- **⚠️ 部署前确认 jar 产物名**：gradle shadowJar 产物名带版本号（`OrzMC-1.0.15-dev.jar` → bump 后变 `OrzMC-1.0.16-dev.jar`）——**一直拷贝旧文件名 = 部署旧 jar**，改代码毫无效果且无报错。构建后 `ls -la build/libs/*.jar` 看实际产物名+时间戳再部署

## 关联
- orzmc `references/permission-system.md`（user-owned：权限组设计与 LP 命令坑）
- minecraft-bot-mineflayer `scripts/perm-check.js`（LP 权限验证 bot）
