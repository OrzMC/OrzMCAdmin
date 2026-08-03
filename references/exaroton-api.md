# Exaroton API 参考（2026-08 全端点实测）

**官方文档**：https://developers.exaroton.com/（OpenAPI spec: `https://developers.exaroton.com/openapi.yaml`，共 29 端点）

**认证**：`Authorization: Bearer {EXAROTON_API_KEY}`（在 exaroton.com/account 生成）

## 端点表

| 动作 | 端点 | 实测 |
|:----|:----|:----:|
| status | `GET /v1/servers/{id}` | ✅ |
| start/stop/restart | `GET /v1/servers/{id}/start\|stop\|restart` | ✅ start 40s→ONLINE；stop SAVING→OFFLINE；restart 离线 400/在线 32s |
| logs | `GET /v1/servers/{id}/logs` | ✅ |
| 日志分享 mclo.gs | `GET /v1/servers/{id}/logs/share` | ✅ 返回 {id, url, raw} |
| command | `POST /v1/servers/{id}/command` | ✅（/list 日志确认执行） |
| 插件列表 | `GET /v1/servers/{id}/files/info/plugins/` | ✅ |
| 上传插件 | **PUT** `/v1/servers/{id}/files/data/plugins/{name}.jar/` | ✅ |
| 删除插件 | `DELETE /v1/servers/{id}/files/data/plugins/{name}.jar/` | ✅ |
| 配置文件读 | `GET /v1/servers/{id}/files/config/{path}/` | ✅ server.properties 返回 35 项 key/value/type/options |
| 配置文件改(白名单) | `POST /v1/servers/{id}/files/config/{path}/`（body 键值对，即时生效） | ✅ view-distance 10→11→恢复；⚠️ **只能改白名单内 35 项**（max-tick-time/sync-chunk-writes 不在列，返回 success=True 但实际不生效！） |
| **配置文件改(全量)** | **`PUT /v1/servers/{id}/files/data/{path}/`**（body `{"text": 完整文件内容}`） | ✅ 批量改 10 处；**唯一能改白名单外配置的方法**（含插件配置、spigot/paper yml）；⚠️ `POST /files/data/{path}` 是假成功（返回旧内容） |
| 改内存 | `POST /v1/servers/{id}/options/ram/`（body `{"ram": 5}`，2-16GB） | ✅ 2→3→恢复 |
| 改 MOTD | `POST /v1/servers/{id}/options/motd/`（body `{"motd": "..."}`） | ✅ 改→验→恢复 |
| 延长停止计时 | `POST /v1/servers/{id}/extend-time/`（body `{"time": 60}` 秒） | ✅ HTTP 200 |
| 玩家名单列表 | `GET /v1/servers/{id}/playerlists/` | ✅ 4 名单：whitelist/ops/banned-players/banned-ips |
| 名单内容 | `GET/PUT/DELETE /v1/servers/{id}/playerlists/{list}/`（body `{"entries": ["notch"]}`） | ✅ PUT 加→DELETE 删→恢复 |
| 账号信息 | `GET /v1/account/` | ✅ |
| 余额池 | `GET /v1/billing/pools/` | ✅ |

## 平台要点

- ⚠️ **上传必须用 PUT**（POST 触发 Cloudflare 人机验证 403）
- ⚠️ **文件端点必须带尾部斜杠**：`files/data/plugins/x.jar/`
- ⚠️ 文件列表用 `files/info/`，**没有** `files/` 裸端点
- ⚠️ 高频 API 触发 Cloudflare 风控（error 1010 全端点 403），**冷却 30s+ 自动恢复**；脚本间请求间隔 ≥ 5s
- ⚠️ **备份无 API**：官方 29 端点无 backup/snapshot。备份是 Web 面板功能（可链接 Google Drive，手动/自动备份、恢复、完整性校验）
- ✅ **插件残留目录可安全删除**：卸载后 `plugins/{名}/` 配置残留可用 `DELETE /files/data/plugins/{名}/` 整目录删除（Chunky 案例）
- ✅ 服务器无玩家在线会自动停止（省配额，世界正常保存）
- ⚠️ **启动时自动更新软件**：检测到新构建会在启动流程自动更新（STARTING→LOADING→OFFLINE→需再启动一次）
- ✅ **官方状态码枚举**：0=OFFLINE 1=ONLINE 2=STARTING 3=STOPPING 4=RESTARTING 5=SAVING 6=LOADING 7=CRASHED 8=PENDING 9=TRANSFERRING 10=PREPARING
- ✅ **生命周期实测**：start = LOADING(6)→STARTING(2)→ONLINE(1) 约 40s；stop = SAVING(5)→OFFLINE(0) 约 10s；restart（在线）= STARTING→ONLINE 约 32s；**restart 离线时 400「Server is not online」**（官方预期）
- ✅ **写操作即时生效**：MOTD / RAM / files.config 白名单项 / playerlists 修改无需重启
- ⚠️ **写配置全量法**：`PUT files/data + {"text": 全文}`（GET→改→PUT），响应 `{"success":true}`；这些修改**需重启生效**（files/config 白名单项除外）
- ⚠️ **start/stop/restart 是 GET**（POST 触发 Cloudflare 人机验证）
