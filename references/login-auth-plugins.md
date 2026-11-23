# 登录/认证插件选型：密码为什么会落盘、ProtocolLib 为什么必要、Folia 上为什么危险

服务器是 Velocity（offline-mode + forwarding）+ 后端 Paper/Folia 时，登录在**后端**完成，于是密码是否落盘成了插件的事。

## 1. 机制：没有 ProtocolLib 就有明文密码写进磁盘

Bukkit 系服务端把 `/<cmd> <args>` 当**聊天消息**处理：玩家输入 → 进入服务端聊天通道 → 才轮到插件截获。这条通道自带一个日志分支，原样把**整行**打进控制台和 `logs/latest.log`（典型形态 `<player> issued server command: /login hunter2`，也有插件自己 `getLogger().info(...)` 版本）。所以：

- **没有 ProtocolLib**：密码以明文出现在 `latest.log`、`logs/<日期>-<n>.log.gz` 归档、以及任何日志采集端（面板日志查看器、spark、docker logs）。这是真实凭据泄露，不是「日志噪声」。
- **有 ProtocolLib**：它在 Netty 管道层先截走这个包，消息根本进不了聊天分支 → 控制台看不到、其他玩家也收不到。SimpleLogin 因此把 ProtocolLib 列为 softdepend：有则拦截，无则降级成「明文登录」。
- 症状识别：启动日志出现 `ProtocolLib not found - /login and /register will be logged to console in plaintext.` 即坐实。

## 2. ProtocolLib 在 Folia 上为什么不能随手装

ProtocolLib 本质是 Netty 管道注入 + 反射，天然假设「包处理在主线程」。Folia 的 region 化线程模型打破这个前提，官方没有 Folia 支持（只有第三方分支试验）。失败模式有两条，都很难看：

- 插件 enable 失败（等于没装，密码照旧落盘，还以为已经修好）；
- enable 成功但多 region 并发下发包处理异常，**登录流程卡死 → 玩家进不来**。账号安全问题搭上登录不可用，比原来的日志落盘严重。

结论：**「Folia 缺 ProtocolLib 导致明文登录」不要用装 ProtocolLib 来解决**。先说明机制与风险，把选项交用户拍板。

## 3. 三条替代路径（按成本排序）

| 方案 | 做法 | 代价/风险 |
|:--|:--|:--|
| 消除需求 | 只在 lobby 登录一次，后端（Folia）关掉登录插件的 `login` 流程 | 依赖 Velocity 不允许绕过 lobby 直连后端：`try=lobby` 只管首次落地，`/server <backend>` 是放行的 → 先确认转服时的会话判定（`forwarding` 模式 + 后端 `online-mode=false` 时后端会当成新玩家） |
| 换插件 | 换不依赖 ProtocolLib 的认证插件（AuthMe 系有 Folia 兼容分支） | 要迁移账号（哈希算法不同，BCrypt 与自研哈希不通用）；Folia 上仍需实测登录链路 |
| 装 ProtocolLib | 用非官方 Folia 分支 | 登录链路断裂风险不可控，不推荐在生产 |

## 4. 多后端登录插件必须统一

两个后端分别用 LoginSecurity(BCrypt) 与 SimpleLogin(自有哈希) 时，同一份账号密码在另一服**不可登录**，玩家看到的是「密码错」而非「换了插件」。巡检时把两侧插件名+版本并列核对；要统一就一次迁完（迁完先在影子端口压测一轮登录，再切主入口）。

## 5. 缓解措施（不动架构时）

- 日志权限收紧 + 归档 gz 不进备份上传（明文已经落盘时，唯一能做的是缩小暴露面）；
- 巡检脚本对 `issued server command: /login` 和 `will be logged to console in plaintext` 两类行单独告警，避免「知道有泄漏但没人看」；
- 引导玩家改用 `/login` 的 GUI/物品栏形式（若插件支持 InventoryGUI），减少命令行走聊天通道的比例——治标。
