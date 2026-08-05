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
| 插件列表 | `GET /v1/servers/{id}/files/info/plugins/` | ✅ |
| 上传插件 | **PUT** `/v1/servers/{id}/files/data/plugins/{name}.jar/` | ✅ |
| 删除插件 | `DELETE /v1/servers/{id}/files/data/plugins/{name}.jar/` | ✅ |
| 配置文件读 | `GET /v1/servers/{id}/files/config/{path}/` | ✅ server.properties 返回 35 项 key/value/type/options 结构化数据 |
| 配置文件改(白名单) | `POST /v1/servers/{id}/files/config/{path}/`（body 键值对，改后即时生效） | ✅ 实测（view-distance 10→11→恢复）；⚠️ **只能改 API 白名单内 35 项**（max-tick-time/sync-chunk-writes 等不在列，POST 返回 success=True 但实际不生效！） |
| **配置文件改(全量)** | **`PUT /v1/servers/{id}/files/data/{path}/`**（body `{"text": 完整文件内容}`，GET→文本替换→PUT 覆盖） | ✅ 实测（2026-08-03 批量改 10 处）；**唯一能改白名单外配置的方法**（含插件配置、spigot/paper yml），响应 `{"success":true}`；⚠️ `POST /files/data/{path}` 是假成功（返回旧内容，别用） |
| 改内存 | `POST /v1/servers/{id}/options/ram/`（body `{"ram": 5}`，2-16GB） | ✅ 实测（2→3→恢复） |
| 改 MOTD | `POST /v1/servers/{id}/options/motd/`（body `{"motd": "..."}`） | ✅ 实测（改→验→恢复） |
| 延长停止计时 | `POST /v1/servers/{id}/extend-time/`（body `{"time": 60}` 秒） | ✅ 实测（HTTP 200） |
| 玩家名单列表 | `GET /v1/servers/{id}/playerlists/` | ✅ 4 名单：whitelist/ops/banned-players/banned-ips |
| 名单内容 | `GET/PUT/DELETE /v1/servers/{id}/playerlists/{list}/`（body `{"entries": ["notch"]}`） | ✅ 全部实测（PUT 加→DELETE 删→恢复） |
| 账号信息 | `GET /v1/account/` | ✅ jokerhub / 824219521@qq.com |
| 余额池 | `GET /v1/billing/pools/` | ✅ 1 池 309.14 积分 |

## 平台要点（2026-08 实测）

- ⚠️ **上传必须用 PUT**（POST 会触发 Cloudflare 人机验证 403）；**PUT 也必须带 `User-Agent: Mozilla/5.0`**（2026-08-05 实测：不带 UA 直接 403 error code 1010 Cloudflare 拦截；`exa_upload_update.py` 已内置）
- ⚠️ 上传到 plugins/update/ 用 `files/data/plugins/update/{name}.jar/`（PUT 裸字节 body，Content-Type application/java-archive）——离线时可直接写
- ⚠️ **文件端点必须带尾部斜杠**：`files/data/plugins/x.jar/`
- ⚠️ 文件列表用 `files/info/`，**没有** `files/` 裸端点
- ⚠️ 高频 API 调用会触发 Cloudflare 风控（error 1010，全部端点 403），**冷却 30s+ 自动恢复**；脚本间请求间隔 ≥ 5s
- ⚠️ **备份无 API**：官方 OpenAPI 全部 29 端点无 backup/snapshot。备份是 Web 面板功能（需链接 Google Drive 等云存储，支持手动/自动备份、恢复、完整性校验）。**自动备份已由用户在面板配置**，脚本不做备份
- ✅ **插件残留目录可安全删除**（2026-08-03 实测）：卸载插件后 `plugins/{插件名}/` 配置残留（config.yml + 空子目录）可用 `DELETE /files/data/plugins/{名}/` 整目录删除，不影响运行（Chunky 案例）
- ⚠️ 服务器无玩家在线会自动停止（Exaroton 默认行为，省配额，日志会正常保存世界）
- ⚠️ **启动时自动更新软件**：Exaroton 检测到 PaperMC 有新构建会在启动流程中自动更新（状态流转：STARTING→LOADING→OFFLINE→需再启动一次），用户无需手动升级核心
- ✅ 本机 Java 25 兼容 PaperMC 26.2；本地测试服与线上 jokerhub 均为 **26.2 (92)**（2026-08-03 三端对齐）
- ✅ **无玩家自动停止**：启动后约 3-4 分钟无玩家会自动停（日志显示正常关闭、世界完整保存），属预期行为
- ✅ **官方状态码枚举**（OpenAPI spec 权威）：0=OFFLINE 1=ONLINE 2=STARTING 3=STOPPING 4=RESTARTING 5=SAVING 6=LOADING 7=CRASHED 8=PENDING 9=TRANSFERRING 10=PREPARING
- ✅ **生命周期实测**（2026-08-03）：start = LOADING(6)→STARTING(2)→ONLINE(1) 约 40s；stop = SAVING(5)→OFFLINE(0) 约 10s；restart（在线）= STARTING→ONLINE 约 32s；**restart 在离线时返回 400「Server is not online」**（官方预期）
- ✅ **写操作即时生效**：MOTD / RAM / files.config / playerlists 修改无需重启服务器
- ⚠️ **写配置文件用 PUT files/data + `{"text": 全文}`**（2026-08-03 实测）：GET→改文本→PUT 覆盖，可改任意配置（server.properties/spigot/paper/插件 config.yml 均可用）；响应 `{"success":true}`。**POST files/data 是假成功**（返回旧内容不生效）；**POST files/config 仅支持 API 白名单 35 项**（max-tick-time/sync-chunk-writes 等不在其中，返回 success=True 但实际不改）。⚠️ 这些配置修改**需重启服务器才生效**（files/config 白名单项除外）
- ⚠️ **start/stop/restart 是 GET**（官方 OpenAPI 确认；POST 会触发 Cloudflare 人机验证）
- ⚠️ Exaroton 大文件（>10MB）上传易触发 Cloudflare 524，停服后重试即可
- ⚠️ Exaroton 服务器**运行中禁止写文件**（API 返回 `File access is currently unavailable`），上传插件/升级必须**先停服**
