# DeathChest 回归测试（死亡瞬间下线 → 物品丢失）✅ 已修复

> **背景**：DeathChest 3.0.1 存在「玩家死亡瞬间下线 → 掉落物清空但箱子未创建 → 物品永久丢失」的 bug。
> 2026-08-05 在测试服实测复现、定位根因并**已修复**（自编译版 v3.0.1-fix1）。
> 脚本：`scripts/regression/`（bugtest-death3.js / bugtest-check3.js / bugtest-fall.js / bugtest-precise.js / bugtest-data.js）
> 修复代码：`~/death-chest/`（fork devcyntrix/death-chest）

## 根因（源码级定位，2026-08-05）

DeathChest 建箱是**分步异步**流程：

```
onDeath (PlayerDeathEvent)
  → createChest() 模型创建（内存）✅
  → listener.onCreate(model)
    → new BukkitRunnable().runTask(plugin)  ← 箱子方块【延迟到下一 tick】！
  → event.getDrops().clear()  ← 掉落物【同步立即清空】
```

**致命点**：`BlockCreationChestListener.onCreate` 用 `runTask` 把 `location.getBlock().setType(CHEST)` 延迟到**下一 tick**（作者注释：防下界睡觉爆炸破坏箱子）。**玩家死亡瞬间下线 → 下一 tick 时区块已卸载 → setType 写入无效区块被静默丢弃 → 但掉落物已在死亡事件同步清空 → 物品永久丢失**。

### 实测证据
| 场景 | 掉落物 | 箱子 | 结果 |
|:--|:--|:--|:--|
| 保持在线死亡 | 清空 | ✅ ~1 tick 后建成 | 正常 |
| **死亡 + 立即下线** | 清空 | ❌ setType 写入已卸载区块 | **物品丢失** 🔴 |

- debug 日志：`Creating death chest block...` 出现但 `Death chest block created at...` 位置查无箱子（原版无此确认日志，修复版新增）
- 滞留现象：重启时 `[null] Creating death chest block...` —— 死亡事件的滞留建箱任务重启补建

## ✅ 修复方案（自编译 v3.0.1-fix1）

**文件**：`src/main/java/com/github/devcyntrix/deathchest/feature/chest/views/BlockCreationChestListener.java`

**改动**：`onCreate` 的 runnable 内，`setType(CHEST)` 前**检查区块是否加载**：
- 未加载 → `world.getChunkAt(chunkX, chunkZ)` 同步强制加载
- 仍未加载 → `runTaskTimer` 每 tick 重试，最多 40 tick（2s）
- 加载后 → `placeChest()` 放箱子 + 打印确认日志

**编译**：`cd ~/death-chest && ./gradlew shadowJar --no-daemon`（需 JDK 25，build.gradle toolchain 已改 25；产物 `build/libs/deathchest.jar`）

## 测试流程（回归）

### 前置
- 测试服运行中（本地 papermc 测试目录）
- 玩家账号（HermesBot）已注册，密码用环境变量注入：`BOT_PASSWORD=xxx node <脚本>`
- DeathChest debug 保持开启（`plugins/DeathChest/config.yml` → `debug: true`）便于定位

### 脚本分工
| 脚本 | 场景 | 预期（正常）| 预期（bug）|
|:--|:--|:--|:--|
| `bugtest-fall.js` | 坠落死亡 + **保持在线** + 查箱子 | ✅ 收到通知 + 箱子命中 ≥1 | ❌ 命中 0 |
| `bugtest-precise.js` | kill + **2s 内下线** + 记坐标 | ✅ 死亡坐标写入 /tmp/death_pos.json | — |
| `bugtest-check3.js` | 读坐标 → 3x3x3 查箱子（/execute if block）| ✅ 命中 ≥1 | ❌ 命中 0 |
| `bugtest-data.js` | 读箱子 NBT/存档确认物品 | ✅ Items 含 diamond x5 | ❌ 空 |

### 执行步骤
```bash
cd ~/minecraft-bot   # 或技能 scripts/regression/

# 1. 对照组：保持在线死亡（基本功能）
BOT_PASSWORD=xxx node bugtest-fall.js

# 2. 复现组：死亡瞬间下线
BOT_PASSWORD=xxx node bugtest-precise.js
# 期望：输出"死亡坐标已存"，服务器日志 [HermesBot: Killed HermesBot]

# 3. 查箱子（等 2-3s 让建箱完成）
BOT_PASSWORD=xxx node bugtest-check3.js
# bug 判定：命中 0 → 🔴（旧版）
# 修复判定：命中 ≥1（Test passed）→ 🟢 回归通过

# 4. 物品完整性：查存档（或 bugtest-data.js）
grep -A 5 "diamond" <服务器>/world/dimensions/minecraft/overworld/death-chests.yml
# 期望：count: 5（无丢失）
```

### 判定标准
- **回归通过**：步骤 3 箱子命中 ≥1 + 步骤 4 物品 count 完整（死亡+下线也不丢物品）
- **回归失败**：命中 0 且日志有 `Creating death chest block...` 无 `created at` 确认

## 多轮回归实测记录（2026-08-05，修复版 v3.0.1-fix1）

自动化循环：`regression-loop.sh`（每轮 death3/precise + check3，轮间 30s 冷却防同账号重连拦截）

| 批次 | 轮次 | 场景 | 结果 |
|:--|:--|:--|:--|
| 1 | 1-4 | 死亡+2s 下线 | ✅ 4/4 通过（命中 1/1/1/1）|
| 2 | 5-8 | 死亡+2s 下线 | ✅ 4/4 通过（命中 2/2/2/2）|
| — | — | **累计 8/8 = 100%** | ✅ 物品 0 丢失 |

存档校验（world/dimensions/minecraft/overworld/death-chests.yml）：
- 12 个箱子条目全部含 diamond（count 5 或 10），**空箱 0**
- 修复前该场景 100% 失败（0 命中 + 物品丢失），修复后 100% 通过 → **非偶然**

> ⚠️ fall.js（保持在线对照）命中 0 是**脚本查错坐标**（记录坠落起点而非死亡落地位置）——用服务器日志 `Death chest block created at` 确认实际建箱位置即可，不影响判定。

## 阶段 4 完整回归记录（2026-08-05，修复版 v3.0.1-fix1）

| 回归项 | 结果 | 说明 |
|:--|:--|:--|
| TPS | ✅ 20.0/20.0/20.0 | 满 TPS 无退化 |
| 插件加载 | ✅ 18 全加载 | Bukkit 17 + Paper 1（含 floodgate）|
| 启动错误 | ⚠️ 2 条已知 | Essentials 版本警告 / EzShops YAML 回退（原版就有）|
| 死亡+下线建箱 | ✅ 8/8 (100%) | 核心修复场景 |
| 物品完整性 | ✅ 0 丢失 | 存档全有物品 |
| 过期机制 | ✅ 60s 测试通过 | 到期自动销毁+存档延迟写盘（关服时 saveChests）|
| 远距离建箱 | ✅ (100,61,100) | 区块加载修复覆盖 |
| 重启滞留补建 | ✅ 正常 | 过期滞留箱补建后清理 |

**已知问题（不阻塞，记录）**：
1. **Invalid model 启动竞态**：重启时过期滞留箱子与补建任务竞争 → destroyChest 抛 1 条 IllegalArgumentException（ExpirationRunnable 调 destroyChest 时模型已被移除）。一次性不影响运行，原版潜在。可优化：`destroyChest` 中 `loadedChests.remove()` 返回 null 时静默返回而非抛异常
2. **mineflayer 开箱失败**：DeathChest 用自定义 inventory holder（非方块原生 NBT），mineflayer openContainer 等不到 windowOpen——**真人客户端正常**，验证物品用存档（death-chests.yml）而非开箱

**测试辅助**：`regress-tps.js`（TPS/插件查询）、`regress-expire.js`（精确坐标查箱）、`bugtest-world.js`（跨世界死亡）、`regression-loop.sh`（自动化多轮）

## 坑（实测踩过）
- **粒子崩溃**：26.2→1.21.11 边界，坠亡掉落粒子触发 `PartialReadError: f32` —— 脚本需内置粒子 patch（115/116 映射）或 `hideErrors: true` 绕过
- **OP 默认创造模式**：创造模式死亡不掉落物品/不触发 DeathChest —— 必须先 `/minecraft:gamemode survival`
- **kill 命令**：`/minecraft:kill` 有效（日志 `Killed`），但触发不了 `death` 事件（mineflayer）——死亡检测用 health < 0.5 或 kill+计时断线
- **spawn 事件重复触发**：kill/坠落后 respawn 会再触发 spawn handler → 脚本需 `started` 标志防重入
- **/execute if block 回显**：结果发给执行者 chat（非控制台日志）→ 检查脚本需监听 message 收集；**中文服回显是 "Test passed"/"Test failed"**（非英文服 "Successfully"）——check3 已适配
- **登录检测**：message 事件可能在 spawn 前错过 → spawn 触发即可认为已登录，勿依赖 message
- **kill 后立即下线会丢命令**：kill 后需等 ≥2s 再 quit，否则命令可能未送达（tp 到未加载区块时尤其明显）
