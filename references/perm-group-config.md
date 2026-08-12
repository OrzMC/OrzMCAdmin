# 权限组配置（指针版 — 2026-08-12 方案①收敛）

> **唯一权威来源：`OrzMC/plugin/docs/permission-groups.md`**（git 版本化，含每项验证指令 / 验收记录 / 插件默认权限盘点）。
> 本文件只留指针与关键决策，**不再维护节点明细**——改权限 = 改仓库文档 → 重新生成，防止多源漂移（旧摘要版已出现 L2 31 vs 实际 33 的漂移，故收敛）。

## 生成与同步

```bash
# 1. 从权威文档生成 LP 命令清单（输出含父链命令 + 高危注释）
python3 ~/.hermes/skills/gaming/orzmc/scripts/gen_perm_commands.py -o /tmp/perm.txt
# 2. 三端同步：每端先 lp export 备份 → 每组 permission clear + 逐条 set
#    （执行前 grep -v '^#' 过滤注释）→ 完成后 export 对比验证（组节点数+继承链）→ LP 实时生效
```

## 关键决策（防回归）

- 四组增量：default(13) / member(13) / builder(33) / admin(32)；继承链 member→default、builder→member、admin→builder（LuckPermsBootstrap 启动自动校正）
- **高危节点任何组不授**：`*`、`luckperms.*`、`minecraft.command.op`、`bukkit.command.op`、`essentials.stop/reload`
- builder 必须显式 `essentials.gamemode.others false`（父权限含 .others，防改他人模式）
- Litematica 投影三件套：`minecraft.command.setblock/fill/data`；**不授 `summon`**
- 插件 default:true 权限（未声明也生效）盘点 → `references/plugin-default-perms.md`
