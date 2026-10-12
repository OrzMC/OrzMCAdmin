# 巡检日期：2026-10-12（周一 9:00 周巡检，脚本 cmp3 自动生成，基准端 = MCSM {SERVER_NAME}）

> **本周状态：❌ FAIL —— MCSM({SERVER_NAME}) 面板再次因 Cloudflare 隧道故障不可达，配置对比无法完成。**
> 回显 `MCSM({SERVER_NAME} Windows 栈): ❌ API 响应异常`；MCSM 端配置拉取 **0/7 文件**（全部「签发失败（限流重试耗尽）」）。
> Exaroton 端拉取正常（Exa=7 文件，ok=7 fail=0）。**因基准端（MCSM）为空，脚本判定「全部核心配置基准端缺失」→ 无任何有效漂移数据。**
>
> **⚠️ 复发趋势**：上一份报告（2026-10-05）曾记录「面板已从 09-28 的 Cloudflare 隧道故障中恢复」——
> **本次为同一故障 2 周内第 2 次复发**（09-28 一次、10-12 一次），隧道可用性已成周期性问题，建议排查 Windows 侧
> `cloudflared` 服务自启/守护与计划任务，或改用更稳的隧道方案。
>
> **执行环境**：Exaroton `{SERVER_NAME}` 服 status=0(OFFLINE)，软件 PaperMC 26.2 (133)；两端均停止/离线态，
> 审查为只读拉取，**未做任何重启或改动**。
>
> **结论：本周无有效配置漂移结论（基准端缺失导致无法比对）。** 待 MCSM 面板恢复后需补跑一次审查。

---

# 两端配置差异审计报告（2026-09-09 v3·迁移后两端模型）

> 巡检端：**MCSM**（{SERVER_NAME}.cn Windows 运行栈，原本地测试服迁移后） + **Exaroton**（海外服）。

## 审计范围：0 个核心 + 0 个插件配置文件（应到 7 + 59 = 66）

| 类别 | 数量 |
|:--|:--|
| 核心配置（服务端） | 0（Exa 侧实际拉到 7） |
| 插件配置 | 0（清单来源=MCSM 端 API 递归扫描，扫描结果 0） |
| **合计** | **0** |

判定口径：**交集语义**（两端共同 key 值同=完全一致；单端独有 key 另计）

## 一、核心配置（服务端）

MCSM 基准端 0 文件 → `server.properties` / `bukkit.yml` / `spigot.yml` / `commands.yml` /
`config_paper-global.yml` / `config_paper-world-defaults.yml` / `wepif.yml` 均标记「基准端缺失」，
无有效对比。

## 二、插件配置（按插件分组）

共检查 0 个插件配置文件，其中差异 0 个。（MCSM `plugins/` 递归扫描返回 0 项。）

## 三、汇总

| 状态 | 核心 | 插件 | 合计 |
|:--|:--|:--|:--|
| ✅ 两端完全一致 | 0 | 0 | 0 |
| ❌ 配置差异 | 0 | 0 | 0 |
| ℹ️ 运行时数据差异（正常） | 0 | 0 | 0 |
| **合计** | **0** | **0** | **0** |

> 注：本次所有「0」均为 **MCSM 基准端不可达（拉取 0 文件）** 所致，**不代表两端真的没有差异**。

---

## 附：MCSM 面板故障取证（2026-10-12）

| 探测 | 结果 |
|:--|:--|
| `https://mcs.{SERVER_NAME}.cn/` | HTTP **530**，响应体 `error code: 1033`（Cloudflare **Argo Tunnel error**） |
| `https://mcs.{SERVER_NAME}.cn/api/files/list` | HTTP 530（同一 Cloudflare 边缘错误，非鉴权/限流问题） |
| `https://orzmc.{SERVER_NAME}.cn/`（同域网站） | HTTP 200 ✅（**网站/Pages 正常，故障仅限 MCSM 面板隧道**） |
| DNS | `mcs.{SERVER_NAME}.cn` → 198.18.0.66（Clash TUN fake-ip，路由正常，返回的是真实 Cloudflare 错误页） |
| Exaroton API | 正常可达（`{SERVER_NAME}` 服 OFFLINE） |

**判定**：Cloudflare 边缘可达，但 `cloudflared` 回源隧道无健康 origin（error 1033）→ Windows 侧
MCSM 面板进程或 `cloudflared` 隧道未运行。**非我方脚本/凭据问题**（脚本 URL 拼接、UA 头均正确，直连同样 530）。

---
*本文件由「orzmc MC 每周巡检」cron 生成（只读巡检 + 落盘报告，未做任何改动）。*
