# 快速实体统计

> 2026-08-04 沉淀：统计服务器实体构成的三种方法，按速度排序。定位实体负载/FPS 问题首选。

## 方法 1：`/paper entity list`（最快，一行命令）

```
/paper entity list * minecraft:overworld
# 输出: Total Ticking: 705, Total Non-Ticking: 7500
#        103 (583) : minecraft:zombie   ← 103 激活 + 583 休眠 = 686
# 语法: /paper entity list [filter] [world]；world 用 minecraft:overworld（不是 world）
```

- **Ticking（激活）** 吃服务端 CPU；**Non-Ticking（休眠）** 基本不吃服务器，但**客户端视野内仍渲染**——FPS 排查两者都要看
- ⚠️ filter 传 `*` 且 world 传 `world` 会报 `Could not load world`——world 必须是 `minecraft:overworld` 形式

## 方法 2：Spark JSON `world.entityCounts`（一次 profiler 顺带拿）

```
/spark profiler --timeout 30 → 链接加 ?raw → metadata.platformStatistics.world
# 结构: {totalEntities: 4812, entityCounts: {bat: 1575, glow_item_frame: 381, ...}}
# 全服按类型精确计数，含 totalEntities 总数
```

- **优点**：零额外命令，profiler 报告自动含全服实体统计
- 适合全服负载评估（如「蝙蝠 1575 个是全服最大实体群」）
- 详细见 `spark-analysis.md`

## 方法 3：计分板逐类型（慢，仅当需要玩家周边局部数据）

```bash
# 原理：scoreboard objectives add + execute as @e[...] run scoreboard players add
# 单类型一条命令，最后总数对照
```

### 计分板法踩坑（2026-08-04 实测）

- ⚠️ **Minecraft 1.20.5+ `type=` 参数不支持逗号多值 OR**（`type=zombie,type=skeleton` 全 0）——必须单类型一条命令
- ⚠️ `@e[x=X,z=Z,dx=D,dz=D]` 必须配 `y=`+`dy=`（不配 y 默认 y=0 单层，结果几乎为 0）
- ⚠️ `distance=..N` 是 3D 欧氏距离（球体）——高空玩家统计不到下方地面实体；水平区域用 dx/dz+y 范围
- ⚠️ **玩家不在线时统计全 0**（选择器基于玩家位置）——先确认在线
- ⚠️ 命令长度受控制台限制（过长被截断，日志出现 `<--[HERE]`）——命令保持短
- ⚠️ 每次统计前要 `scoreboard objectives add <name> dummy`（重启后丢失，需重建）

## 实体清理安全边界

- `/kill @e[type=!player]` 太激进（清装饰/村民/载具/经验球）且**无撤销**；唯一恢复=提前备份 world
- 安全方案：A 只清掉落物（`/kill @e[type=item]`，零风险）→ B 怪白名单 → C 排除装饰 → D spawn-limits 调低（需重启）
- 装饰类（画/框/盔甲架）**不可恢复**，清前必须备份 world
