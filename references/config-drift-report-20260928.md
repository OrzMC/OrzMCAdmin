# 巡检日期：2026-09-28（周一 9:00 周巡检）

> ⚠️ **本次审查失败（STATUS: ❌ FAIL(MCSM 0 文件)）——基准端 MCSM({SERVER_NAME}) API 不可达，未能产出漂移结论。**
> 不是配置漂移，是**面板端点故障**（见下「故障判定」）。raw cmp3 报告为空壳（0 文件，全部「基准端缺失」），
> 不作为漂移依据；本次以本文件记录故障证据，待面板恢复后于下周巡检补做对比。

---

## 故障判定：mcs.{SERVER_NAME}.cn Cloudflare Tunnel 掉线（1033）

| 检查项 | 结果 |
|:--|:--|
| 面板根 `https://mcs.{SERVER_NAME}.cn/` | **HTTP 530**，body=`error code: 1033`，`server: cloudflare`，`cf-ray: a41ee6a2…-SJC` |
| 面板 API `api/instance`（带 apikey） | 同样 **HTTP 530 / 1033**（3 次重试全部一致） |
| Exaroton API（对照） | **HTTP 200** ✅ |
| 站点 `orzmc.{SERVER_NAME}.cn`（对照） | **HTTP 200** ✅ |
| EasyBot 网关 `bot.{SERVER_NAME}.cn`（同 Windows 栈，对照） | **HTTP 200** ✅ |
| `nslookup mcs.{SERVER_NAME}.cn` | 198.18.0.44（Clash TUN fake-IP，经代理出网） |

**结论**：`error code: 1033` = **Cloudflare Argo Tunnel error（隧道未连接）**，且响应头带 `server: cloudflare` + `cf-ray`，
说明请求已到达 Cloudflare 边缘、是**源站侧 cloudflared 隧道掉线**，非本机 Clash/DNS 问题，也非全站故障——
同栈的 EasyBot 网关与站点均 200，**Windows 宿主机大概率仍在线**，仅 **MCSM 面板那一条隧道（cloudflared / 面板 web 服务）** 挂了。

**影响**：
- 配置审查**无基准端**（MCSM 拉取 0 个文件）→ 本周无法判定两端配置漂移。
- 版本巡检同样读不到部署版本 → 全部显示「未部署」（见第 3 部分周报）。
- 测试服（papermc-test / folia-test）与面板均**无法经 API 操作**，直到恢复。

**建议动作（待老板/用户确认，本次只读不动手）**：登录 Windows 宿主机（`E:/orzmc`）检查
① `cloudflared`（MCSM 面板隧道）服务是否存活/需重启；② MCSM 面板 web 服务（web `10.18.0`）是否在跑；
③ 隧道配置/凭据是否变更。恢复后本脚本即自动回到正常对比。

---

## 本次执行证据（摘要）

```
MCSM({SERVER_NAME} Windows 栈): ❌ API 响应异常
Exa: 0(OFFLINE)（未重启）
配置清单已扫描并缓存: 0 个 → 配置清单: 0 个插件配置文件
拉取完成(exit=0): Exa=7  MCSM({SERVER_NAME})=0
STATUS: ❌ FAIL(MCSM 0 文件)
```

- Exaroton 端核心配置拉取 **7/7 成功**（server.properties / bukkit.yml / spigot.yml / commands.yml / wepif.yml /
  config/paper-global.yml / config/paper-world-defaults.yml），Exa 端本身正常（当前状态 OFFLINE）。
- MCSM 端 7 项核心配置**全部「签发失败（限流重试耗尽）」**——实为隧道 530 导致签发 POST 全部失败，
  非真的面板限流。

## 对照：上一次成功审查（2026-09-21）

上一次（09-21）审查成功，范围 **7 核心 + 59 插件 = 66 文件**，结论「无新增人工配置漂移需处理」，
基线差异 27 项（测试服 vs 生产服既有环境差异）。⇒ **09-21 面板可达，09-28 不可达**，为最近一周内新发生的隧道故障。

---
*本文件由「orzmc MC 每周巡检」cron 生成（只读巡检 + 故障记录，未做任何改动）。*
