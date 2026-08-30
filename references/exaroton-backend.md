# Exaroton 后端（云端服务器）

> 已适配（API Key 在 `~/.hermes/.env`：`EXAROTON_API_KEY` + `EXAROTON_SERVER_ID`）。
> **API 官方文档**：https://developers.exaroton.com/（OpenAPI spec: `https://developers.exaroton.com/openapi.yaml`，共 29 端点）
> 认证：`Authorization: Bearer $EXAROTON_API_KEY`

## 端点表（全部实测）

| 动作 | 端点 | 实测 |
|:----|:----|:----:|
| status | `GET /v1/servers/{id}` | ✅ |
| start/stop/restart | `GET /v1/servers/{id}/start\|stop\|restart` | ✅ 全部实测（start 40s→ONLINE；stop SAVING→OFFLINE；restart 离线 400/在线 32s） |
| logs | `GET /v1/servers/{id}/logs` | ✅ |
| 日志分享 mclo.gs | `GET /v1/servers/{id}/logs/share` | ✅ 返回 {id, url, raw} |
| command | `POST /v1/servers/{id}/command` | ✅ 实测（/list 日志确认执行） |
| 插件列表 | `GET /v1/servers/{id}/files/info/plugins/` | ✅ **响应键是 `data.children` 不是 `data.files`**（2026-08-13 实测：解析 `files` 恒返回空列表误判"未找到"；`children[].name/.size/.isDirectory` 核验 jar 用） |
| 上传插件 | **PUT** `/v1/servers/{id}/files/data/plugins/{name}.jar/` | ✅ |
| 删除插件 | `DELETE /v1/servers/{id}/files/data/plugins/{name}.jar/` | ✅ |
| 配置文件读 | `GET /v1/servers/{id}/files/config/{path}/` | ✅ server.properties 返回 35 项 key/value/type/options 结构化数据 |
| 配置文件改(白名单) | `POST /v1/servers/{id}/files/config/{path}/`（body 键值对，改后即时生效） | ✅ 实测（view-distance 10→11→恢复）；⚠️ **只能改 API 白名单内 35 项**（max-tick-time/sync-chunk-writes 等不在列，POST 返回 success=True 但实际不生效！） |
| **配置文件改(全量)** | **`PUT /v1/servers/{id}/files/data/{path}/`**（body = **裸文本文件内容**，Content-Type text/plain） | ✅ 实测（2026-08-09 修正）：**PUT body 原文即文件内容**；⚠️ **切勿用 `{"text": ...}` JSON 包装**——会被原样存为文件内容（config.yml 变 JSON 字符串，插件 YAML 解析静默回退默认值）；GET 若返回 JSON 包装需解包 text 字段 |
| 改内存 | `POST /v1/servers/{id}/options/ram/`（body `{"ram": 5}`，2-16GB） | ✅ 实测（2→3→恢复） |
| 改 MOTD | `POST /v1/servers/{id}/options/motd/`（body `{"motd": "..."}`） | ✅ 实测（改→验→恢复） |
| 延长停止计时 | `POST /v1/servers/{id}/extend-time/`（body `{"time": 60}` 秒） | ✅ 实测（HTTP 200） |
| 玩家名单列表 | `GET /v1/servers/{id}/playerlists/` | ✅ 4 名单：whitelist/ops/banned-players/banned-ips |
| 名单内容 | `GET/PUT/DELETE /v1/servers/{id}/playerlists/{list}/`（body `{"entries": ["notch"]}`） | ✅ 全部实测（PUT 加→DELETE 删→恢复） |
| 账号信息 | `GET /v1/account/` | ✅ {SERVER_NAME} /  |
| 余额池 | `GET /v1/billing/pools/` | ✅ 1 池 309.14 积分（2026-08-11：实际 294.73，账户 credits=0 但池内充足——**服务器计费看池不看账户**，端点在 billing 命名空间，`account/creditpool` 等 400） |

## 平台要点（2026-08 实测）

- ⚠️ **Exaroton 与 MCSM 都是离线服（online-mode=false）**；Exaroton 的 server.properties 文件里可能有一行 `{"text":"..."}` JSON 污染（早期 API 写入的垃圾行，Minecraft 忽略）——判断真实 online-mode 必须看 `#Minecraft server properties` 开头的纯文本行，不要 grep 到 JSON 污染行
- ❌ **floodgate 与 LoginSecurity 冲突（三端已回退 2026-08-05）**：floodgate 给基岩玩家加 `.` 前缀 → LoginSecurity `filter-special-chars` 判非法字符拒绝。基岩玩家走 LoginSecurity 注册（无前缀名字），floodgate 无收益纯冲突 → 三端移除 floodgate.jar + Geyser auth-type 改回 `offline`（离线服基岩玩家无前缀直连，与之前行为一致）
- ✅ **MCSM 文件 API 全套可用（2026-08-06 全面复核，详见 mcsm-backend.md）**：删除 `DELETE /api/files/`、写 `PUT /api/files/`、列目录 `GET /api/files/list`（需 page=0+page_size+file_name）——**旧结论「无 delete API」「PUT 404」已全部推翻**
- ⚠️ **上传必须用 PUT**（POST 会触发 Cloudflare 人机验证 403）；**PUT 也必须带 `User-Agent: Mozilla/5.0`**（2026-08-05 实测：不带 UA 直接 403 error code 1010 Cloudflare 拦截；`exa_upload_update.py` 已内置）
- ⚠️ 上传到 plugins/update/ 用 `files/data/plugins/update/{name}.jar/`（PUT 裸字节 body，Content-Type application/java-archive）——离线时可直接写
- ⚠️ **文件端点必须带尾部斜杠**：`files/data/plugins/x.jar/`
- ⚠️ 文件列表用 `files/info/`，**没有** `files/` 裸端点
- ⚠️ 高频 API 调用会触发 Cloudflare 风控（error 1010，全部端点 403），**冷却 30s+ 自动恢复**；脚本间请求间隔 ≥ 5s
- ⚠️⚠️ **PUT 写操作会被 Cloudflare managed challenge 拦截（2026-08-30 实测）**：GET 文件正常，但 PUT 返回 403 "Just a moment..." JS 挑战页（curl/urllib/完整浏览器 UA 均过不了——managed challenge 需真实浏览器执行 JS 通过挑战）；触发后**不是冷却能解决的**，需真实浏览器（browser_exec 或面板）或等待数小时风控自然解除；写文件失败先看响应体是不是 `<!DOCTYPE html>...Just a moment`（区分 Cloudflare 拦截 vs API 报错）
- ⚠️ **备份无 API**：官方 OpenAPI 全部 29 端点无 backup/snapshot。备份是 Web 面板功能（需链接 Google Drive 等云存储，支持手动/自动备份、恢复、完整性校验）。**自动备份已由用户在面板配置**，脚本不做备份
- ✅ **插件残留目录可安全删除**（2026-08-03 实测）：卸载插件后 `plugins/{插件名}/` 配置残留（config.yml + 空子目录）可用 `DELETE /files/data/plugins/{名}/` 整目录删除，不影响运行（Chunky 案例）
- ⚠️ 服务器无玩家在线会自动停止（Exaroton 默认行为，省配额，日志会正常保存世界）
- ⚠️ **启动时自动更新软件**：Exaroton 检测到 PaperMC 有新构建会在启动流程中自动更新（状态流转：STARTING→LOADING→OFFLINE→需再启动一次），用户无需手动升级核心
- ✅ 本机 Java 25 兼容 PaperMC 26.2；本地测试服与线上 {SERVER_NAME} 均为 **26.2 (92)**（2026-08-03 三端对齐）
- ✅ **无玩家自动停止**：启动后约 3-4 分钟无玩家会自动停（日志显示正常关闭、世界完整保存），属预期行为
- ✅ **官方状态码枚举**（OpenAPI spec 权威）：0=OFFLINE 1=ONLINE 2=STARTING 3=STOPPING 4=RESTARTING 5=SAVING 6=LOADING 7=CRASHED 8=PENDING 9=TRANSFERRING 10=PREPARING
- ✅ **生命周期实测**（2026-08-03）：start = LOADING(6)→STARTING(2)→ONLINE(1) 约 40s；stop = SAVING(5)→OFFLINE(0) 约 10s；restart（在线）= STARTING→ONLINE 约 32s；**restart 在离线时返回 400「Server is not online」**（官方预期）
- ✅ **写操作即时生效**：MOTD / RAM / files.config / playerlists 修改无需重启服务器
- ⚠️ **写配置文件用 PUT files/data + 裸文本 body**（2026-08-09 修正，**2026-08-03 的 `{"text": 全文}` JSON 包装结论已作废**）：GET→改文本→PUT 覆盖，可改任意配置（server.properties/spigot/paper/插件 config.yml 均可用）；**切勿 JSON 包装**——会被原样存为文件内容（config.yml 变 JSON 字符串，插件 YAML 解析静默回退默认值；server.properties 尾残留 `{"text"="..."}` 垃圾块，Exaroton 已中招）。统一用 `scripts/exa_file.py`（GET 自动解包 JSON/裸文本，PUT 裸文本）。**POST files/data 是假成功**（返回旧内容不生效）；**POST files/config 仅支持 API 白名单 35 项**（max-tick-time/sync-chunk-writes 等不在其中，返回 success=True 但实际不改）。⚠️ 这些配置修改**需重启服务器才生效**（files/config 白名单项除外）
- ⚠️ **start/stop/restart 是 GET**（官方 OpenAPI 确认；POST 会触发 Cloudflare 人机验证）
- ⚠️ Exaroton 大文件（>10MB）上传易触发 Cloudflare 524，停服后重试即可
- ⚠️ Exaroton 服务器**运行中禁止写文件**（API 返回 `File access is currently unavailable`），上传插件/升级必须**先停服**
- ⚠️ **server.properties 平台重写（2026-08-11 实测）**：Exaroton 平台**每次启动时重写 server.properties**（平台模板 + files/config 白名单 35 项）；**非白名单项（sync-chunk-writes/max-tick-time 等）即使 PUT files/data 修改，重启后也被平台重置**（sync-chunk-writes PUT=true 重启后变回 false）——放弃对齐，记录为**平台保留差异**（默认值是性能优化，无害）；白名单项（resource-pack-prompt/view-distance 等）须用 `POST /files/config/{path}/` 修改（重启不丢失）。普通文件（paper-*.yml/插件 config.yml）不受平台管理，PUT 裸文本修改可长期保留
- ⚠️ **启动反复失败现象（2026-08-11 实测，待平台侧排查）**：积分充足时仍 `2(LOADING)→1(STARTING)→5(STOPPING)→0(STOPPED)` 循环，`GET /v1/servers/{id}/logs` 始终空（Java 无输出）。已排除余额不足（池内 294.73）、jar 缺失（paper.jar 存在但读取 403 平台保护，正常）、配置损坏。疑似平台软件状态异常，API 无法修复，需面板手动或等待
