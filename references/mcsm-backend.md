# MCSM 后端（MCSManager 面板）

> 已适配：{SERVER_HOST}:23333（2026-08-03 实测）
> 实例：{SERVER_NAME}服务器（daemonId + instanceId 存 `~/.hermes/.env`：`MCSM_DAEMON_ID` / `MCSM_INSTANCE_ID`）
> Windows 主机（daemon 跑在 `C:\Users\Administrator\...`），MC 26.2-92（2026-08-03 从 26.1.2-74 升级），端口 25565，自动启动+自动重启已开。

## 端点表（全部实测 2026-08-06 全面复核）

| 动作 | 端点 | 实测 | 说明 |
|:----|:----|:----:|:----|
| 实例状态 | `GET /api/instance?daemonId={d}&uuid={i}` | ✅ 200 | 字段见下 |
| 日志 | `GET /api/protected_instance/outputlog?daemonId={d}&uuid={i}` | ✅ 200 | |
| 玩家列表 | 从日志「当前在线(n/max)」行解析 | ✅ | |
| 登录换 token | `POST /api/auth/login` {username,password} | ✅ 200 | |
| **start/stop/restart** | **`GET /api/protected_instance/open` / `stop` / `restart`** | ✅ 实测 | |
| **command** | **`GET /api/protected_instance/command?command={cmd}`** | ✅ 实测 | |
| **读文件** | `POST /api/files/download?file_name={路径}` → addr+password → `GET http://{addr}/download/{pwd}/{文件名}` | ✅ 实测 | **必须带 daemonId+uuid**（缺 → 403「参数不正确」）|
| **写文件** | **`PUT /api/files/?daemonId={d}&uuid={i}` body `{"target":"/路径","text":"内容"}`** | ✅ **200 实测** | ⚠️ **只能写已存在文件**（新文件 → 500 Illegal access path）；**必须带 daemonId+uuid**；body 字段是 `text` |
| **删除文件/目录** | **`DELETE /api/files/?daemonId={d}&uuid={i}` body `{"targets":["/路径1","/路径2"]}`** | ✅✅ **200 实测删文件+目录都成功** | 删后必须真实 GET 验证（daemon 偶发假 200）|
| **新建目录** | `POST /api/files/mkdir?daemonId={d}&uuid={i}` body `{"target":"/路径"}` | ✅ 200 实测 | |
| 上传 | `POST /api/files/upload?upload_dir={目录}&daemonId={d}&uuid={i}` → daemon `/upload/{pwd}` multipart | ✅ 实测 | |
| **列目录** | `GET /api/files/list?target={路径}&page=0&page_size=50&file_name={过滤词}` | ⚠️✅ **可用但需 fileName** | **必须带 `page`（从 0 开始！）+ `page_size` + `file_name` 三个参数**；`file_name` 是**过滤词**（不填 → total=0 items 空，daemon 全量列出 bug）；`type` 字段 0=目录 1=文件；偶发 `Remote end closed connection`（重试即可）。源码（MCSManager Daemon `system_file.ts` list 实现）实证 |
| **touch 新建文件** | `POST /api/files/touch` body `{"target":"/路径"}` | ✅ 200 实测 | 2026-08-06 新发现 |
| **copy 复制** | `POST /api/files/copy` body `{"targets":[["源","目标"],...]}` | ✅ 200 实测 | ⚠️ **targets 是二维数组** `[["源","目标"]]`（源码注释 `// [["a.txt","b.txt"],["cxz","zzz"]]`）——一维数组会 500 |
| **move 移动** | **`PUT /api/files/move`** body `{"targets":[["源","目标"],...]}` | ✅ 200 实测 | ⚠️ **方法必须是 PUT**（POST → 500）+ **targets 二维数组**（同 copy）——2026-08-06 修正「move 不可用」误判 |
| **compress 压缩** | `POST /api/files/compress` body `{"source":"/输出.zip","targets":[文件数组],"type":1,"code":"utf-8"}` | ✅ 200 实测 | **type=1 压缩**（promiseZip：source=zip输出路径, targets=文件数组）；**type=0 解压**（promiseUnzip：source=zip路径, targets=目标目录字符串）；异步任务（fileLock 计数） |
| **URL 下载** | `POST /api/files/download_from_url` body `{"url":"...","file_name":"/路径"}` | ✅ **200 实测** | 2026-08-06 实测：GitHub raw → 5s 下载 1493B 成功；异步任务返回 taskId；`download_from_url_stop` 可停止 |

⚠️ **操作端点全部是 GET + `/api/protected_instance/` 前缀**（不是 POST /api/instance/xxx！）——这是 MCSM 10 的坑，首次按 POST 调用全 404。

**认证**（必需头：`Content-Type: application/json; charset=utf-8` + `X-Requested-With: XMLHttpRequest`）：
- **apikey 方式**：`?apikey=$MCSM_API_KEY`（实测有效，**普通用户权限**）
- token 方式：`POST /api/auth/login` 返回 token（`?token=` 与 Bearer 均未验证通过，待测）

## 适配器脚本

`scripts/adapters/mcsm.sh`（status / players / logs 只读 ✅ 实测；start / stop / restart / command / kill 内置玩家检查，有玩家在线自动拒绝；**restart / command / kill 已实测通过**）：

```bash
# 只读
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh status
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh players
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh logs 50
# 破坏性（自动检查玩家数，有玩家时拒绝；restart 已验证 PID 变更生效）
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh start|stop|restart
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh kill   # 强制终止（崩溃循环恢复用）
~/.hermes/skills/gaming/orzmc/scripts/adapters/mcsm.sh command "list"
```

日志解析依赖 `scripts/parse_mcsm_players.py` / `scripts/parse_mcsm_logs.py`（剥离 ANSI 控制字符 + 提取「当前在线(n/max)」行，位于 scripts/ 根目录非 cmp3/）。

## 平台要点（2026-08-03 实测）

- ⚠️ **apikey 是普通用户权限**：管理员端点（`/api/overview`、`/api/service/remote_services_system`、`/api/auth/search`、`/api/service/remote_service_instances`）返回 403「密钥不正确/权限不足」；只能访问自己名下的 `/api/instance`（需正确 daemonId+uuid）
- ⚠️ **查实例必须先有 daemonId + instanceId**：普通用户无法列出 daemon/实例清单，这两个 ID 从面板网页 URL 获取，存 `.env`
- ⚠️ **daemonId 稳定性**：日常运行/重启面板不变；但 **daemon 重装、迁移服务器、面板删除重绑** 会生成新 UUID（实例删除重建同理）——届时需从面板重新获取
- ✅ **实例状态字段**：`status`(-1=忙碌 0=停止 1=停止中 2=启动中 3=运行中)、`info.currentPlayers/maxPlayers`、`info.version`、`processInfo.pid/memory/elapsed`、`config.eventTask.autoStart/autoRestart`、`config.pingConfig.port`
- ✅ **日志含 ANSI 转义**：解析需先剥离 `\x1b[...` 控制字符
- ✅ **有玩家在线时只读安全**：状态/日志查询不干扰玩家，可用作运维监控
- ⚠️ **面板 23333 有路径防护**：根路径/未知路径返回 `{"status":500,"data":"Malicious Path"}`，属正常
- ⚠️ **静态资源全 SPA 回退**：`/api/overview` 等 GET 可能返回前端 HTML 而非 JSON（需要带必需头 + 正确路径才走 API 路由）
- ✅ **升级流程（2026-08-03 实测）**：上传新 paper jar 到实例根目录（`POST /api/files/upload?upload_dir=/` → daemon `/upload/{pwd}` multipart）→ `PUT /api/files/` body `{"target":"/Start.bat","text":"新内容"}` 更新 jar 引用 → restart。旧 jar 保留作回滚
- ⚠️ **MCSM 写文件（PUT /api/files/）四要点**：① **必须带 `daemonId`+`uuid` 参数**——只带 apikey → 403「参数不正确或非法访问实例」；② **只能写已存在的文件**——新文件路径 → 500 `Illegal access path`（改配置/Start.bat 都满足，无需新建文件）；③ **body 字段是 `text`**——用 `content` 返回 200 但实际不生效；④ 改配置后**需重启才生效**
- ✅✅ **MCSM 删除文件/目录可用（2026-08-06 推翻旧结论）**：`DELETE /api/files/?daemonId={d}&uuid={i}` body `{"targets":["/路径1",...]}` —— 实测删普通文件+目录都 200 成功。**旧结论「无 delete API、只能上传覆盖」是错的**（此前按 `DELETE /api/files/delete` 探测 404 误判；正确端点是 `DELETE /api/files/`）。删后必须真实 GET 验证（daemon 偶发假 200）
- ✅ **MCSM 列目录 API 可用（2026-08-06 深挖修正）**：`GET /api/files/list?target={路径}&page=0&page_size=50&file_name={过滤词}`——**必须带 `page`（从 0 开始）+`page_size`+`file_name`**；`file_name` 是过滤词（不填返回 total=0，daemon 全量列出有 bug）；`type`: 0=目录 1=文件。源码实证：MCSManager Daemon `system_file.ts`（`list(page, pageSize, searchFileName)` 实现）；面板 `filemananger_router.ts` 校验 query `{daemonId,uuid,target,page,page_size}`（page 默认 0、page_size 默认 10 上限 100）
- ⚠️ **MCSM download API 不校验文件存在性**：`POST /api/files/download` 对任何文件名都返回 200（不存在的文件也发凭证）！判断文件是否存在必须**真实 GET 下载**：500=不存在，`PK` 魔数开头=真实 jar
- ⚠️ **Paper 26.x 首次启动需下载 mojang_26.x.jar**：MCSM 服务器若下载失败会 `Hash check failed for downloaded file mojang_26.x.jar` 崩溃循环（每次自动重启重下）；**kill 恢复法**：`mcsm.sh kill` 终止 → `start` 重新启动，通常第二次下载即成功
- ⚠️ **daemon 文件操作**（2026-08-06 全面复核）：**list 需 fileName 过滤（不填空）、move 必须 PUT+二维数组、mkdir 只建单层（父目录不存在 500）、compress type=1 压缩/type=0 解压**；delete/mkdir/touch/copy 稳定可用；删后建议**真实 GET 验证**
- ⚠️ **command 空格原样**：命令中空格不要 URL 编码成 %20（MCSM 不解析），直接原始字符
- ⚠️ **命令长度限制**：过长命令被截断，日志出现 `<--[HERE]` 标记——长命令拆短

## 状态码映射（MCSM 实例，官方文档）

`-1`=忙碌 / `0`=停止 / `1`=停止中 / `2`=启动中 / `3`=运行中

## 插件更新（MCSM 端）

- ✅ **plugins/update 实测可用**（2026-08-03）：`POST /api/files/upload?upload_dir=/plugins/update` multipart 上传 → restart → Paper 自动替换并清空 update/。**文件操作期间服务器运行中无碍**（jar 上传不触发锁定，仅读取被运行中 jar 锁定会 500）
- ✅ **删除插件/文件用 `scripts/cmp3/mcsm_delete.py`**（2026-08-06 起标准方案）：`python3 mcsm_delete.py /plugins/xxx.jar` → DELETE /api/files/ + 自动删后验证（真实 GET 确认）。**旧方案「上传 0B 占位覆盖」已废弃**（Paper 会对无效 jar 报 `Directory 'plugins\xxx.jar' failed to update!` 启动 ERROR，不如直接删干净）
- 上传插件脚本：`scripts/cmp3/mcsm_upload_update.py deathchest.jar GriefPrevention.jar` + `mcsm_verify_update.py`
