# DeathChest 回归测试（死亡瞬间下线 → 物品丢失）

> **背景**：DeathChest 3.0.1 存在「玩家死亡瞬间下线 → 掉落物清空但箱子未创建 → 物品永久丢失」的 bug。
> 2026-08-05 在测试服实测复现并定位根因。**换插件（AxGraves）后需用此流程回归验证**。
> 脚本：`scripts/regression/`（bugtest-death3.js / bugtest-check3.js / bugtest-fall.js）

## 根因（已定位，debug 日志实证）

DeathChest 3.0.1 创建箱子是**分步异步**流程：

```
PlayerDeathEvent
  → Clearing drops...          ← ① 立即清空掉落物（此刻物品已从世界移除！）
  → Starting break animation... ← ② 开始创建动画（异步）
  → Creating death chest block... ← ③ 创建箱子方块（异步队列）
  → Spawning block crack particle / Resetting block ← ④ 完成（在线场景有这步）
```

**玩家下线 → ③④ 步中断**，只留下 hologram/particle runner。后果：
- 掉落物已在 ① 被清空
- 箱子在 ③ 未建成
- **= 物品永久丢失**（既不在箱子也不在地面）

### 关键实测数据
| 场景 | 掉落物 | 箱子 | 结果 |
|:--|:--|:--|:--|
| 保持在线死亡 | 清空 | ✅ ~6s 延迟后建成（break animation → crack → reset）| 正常 |
| **死亡 + 800ms 下线** | 清空 | ❌ 创建中断 | **物品丢失** 🔴 |

- 正常创建延迟：死亡 → 箱子建成约 **6 秒**（06:27:16 死亡 → 06:27:22 reset）
- 生成条件：world-filter 黑名单（默认无限制）、thief-protection 默认关
- 遗留现象：重启服务器时会出现 `[null] Creating death chest block...` —— 之前死亡事件的滞留创建任务

## 测试流程（回归）

### 前置
- 测试服运行中（本地 papermc 测试目录）
- 玩家账号（HermesBot）已注册，密码用环境变量注入：`BOT_PASSWORD=xxx node <脚本>`
- **服务器需开 DeathChest debug**（定位用）：`plugins/DeathChest/config.yml` → `debug: true`（测完可关）

### 三个脚本分工
| 脚本 | 场景 | 预期（正常）| 预期（bug）|
|:--|:--|:--|:--|
| `bugtest-fall.js` | 坠落死亡 + **保持在线** + 查箱子 | ✅ 收到 "put into a chest" 通知 + 箱子命中 ≥1 | ❌ 通知无 + 命中 0 |
| `bugtest-death3.js` | kill + **800ms 内下线** | ✅ 死亡坐标写入 /tmp/death_pos.json | — |
| `bugtest-check3.js` | 读死亡坐标 → 3x3x3 查箱子（/execute if block）| ✅ 命中 ≥1（等 15s 让延迟创建完成）| ❌ 命中 0 |

### 执行步骤
```bash
cd ~/minecraft-bot   # 或技能 scripts/regression/

# 1. 对照组：保持在线死亡（确认基本功能）
BOT_PASSWORD=xxx node bugtest-fall.js
# 期望：✅ 命中 ≥1（箱子在 ~6s 延迟后建成）

# 2. 复现组：死亡瞬间下线
BOT_PASSWORD=xxx node bugtest-death3.js
# 期望：输出"死亡点坐标已存"，服务器日志出现 [HermesBot: Killed HermesBot]

# 3. 等 15 秒（延迟创建窗口）后查箱子
sleep 15
BOT_PASSWORD=xxx node bugtest-check3.js
# bug 判定：命中 0 → 🔴 bug 存在（物品丢失）
# 修复判定：命中 ≥1 → 🟢 箱子正常（回归通过）
```

### 判定标准
- **回归通过**：步骤 3 箱子命中 ≥1（死亡+下线也不丢物品）
- **回归失败**：命中 0 且服务器日志只有 `Creating death chest block...` 无 `Resetting`

## 替换插件后验证点（AxGraves 或其他）
1. 同样的「死亡+立即下线」场景 → 箱子必须生成
2. 箱子内物品 = 死亡时背包物品（give 的 diamond 5 应在箱内）
3. 箱子过期机制正常（默认 600s）
4. 重启后无滞留创建任务（无 `[null] Creating death chest block` 日志）

## 坑（实测踩过）
- **粒子崩溃**：26.2→1.21.11 边界，坠亡掉落粒子触发 `PartialReadError: f32` —— 脚本需内置粒子 patch（115/116 映射）或 `hideErrors: true` 绕过
- **OP 默认创造模式**：创造模式死亡不掉落物品/不触发 DeathChest —— 必须先 `/minecraft:gamemode survival`
- **kill 命令**：`/minecraft:kill` 有效（日志 `Killed`），但触发不了 `death` 事件（mineflayer）——死亡检测用 health < 0.5 或直接 kill+计时断线
- **spawn 事件重复触发**：kill/坠落后 respawn 会再触发 spawn handler → 脚本需 `started` 标志防重入
- **/execute if block 回显**：结果发给执行者 chat（非控制台日志）→ 检查脚本需监听 message 收集
- **登录检测**：message 事件可能在 spawn 前错过 → spawn 触发即可认为已登录，勿依赖 message
