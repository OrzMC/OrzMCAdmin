# MCSManager（MCSM）API 参考（2026-08 实测）

**适用**：MCSManager 10 面板托管的 Minecraft 服务器。
**实例标识**：`daemonId` + `instanceId`（普通用户无法列出，从面板网页 URL 获取，存 `.env`）

## 端点表

| 动作 | 端点 | 实测 |
|:----|:----|:----:|
| 实例状态 | `GET /api/instance?daemonId={d}&uuid={i}` | ✅ 200 |
| 日志 | `GET /api/protected_instance/outputlog?daemonId={d}&uuid={i}` | ✅ 200 |
| 玩家列表 | 从日志「当前在线(n/max)」行解析 | ✅ |
| 登录换 token | `POST /api/auth/login` {username,password} → data=token | ✅ 200 |
| **start/stop/restart** | **`GET /api/protected_instance/open` / `stop` / `restart`?daemonId={d}&uuid={i}`** | ✅ restart 实测（PID 变更） |
| **command** | **`GET /api/protected_instance/command?daemonId={d}&uuid={i}&command={cmd}`** | ✅ list 执行成功 |
| 文件列表 | `GET /api/files/list?daemonId={d}&uuid={i}&target={path}` | ⚠️ 不稳定（常 500） |
| 读文件 | `POST /api/files/download?file_name={path}` → 拿 password+addr → `GET http://{addr}/download/{pwd}/{文件名}` | ✅ |
| 写文件 | `PUT /api/files/` body `{"target": "/路径", "text": "内容"}` | ✅ |
| 删除文件 | `DELETE /api/files/` body `{"targets": ["/路径"]}` | ⚠️ 偶发 200 未删，删后必须真实 GET 验证 |
| 上传文件 | `POST /api/files/upload?upload_dir={目录}` → daemon `/upload/{pwd}` multipart | ✅ |
| kill（强制终止） | `GET /api/protected_instance/kill?daemonId={d}&uuid={i}` | ✅ 崩溃循环恢复用 |

⚠️ **操作端点全部是 GET + `/api/protected_instance/` 前缀**（不是 POST /api/instance/xxx！）
——MCSM 10 的坑，首次按 POST 调用全 404。

## 认证

必需头：`Content-Type: application/json; charset=utf-8` + `X-Requested-With: XMLHttpRequest`
- **apikey 方式**：`?apikey=$MCSM_API_KEY`（实测有效，**普通用户权限**）
- token 方式：`POST /api/auth/login` 返回 token（`?token=` 与 Bearer 均未验证通过，待测）

## 平台要点

- ⚠️ **apikey 是普通用户权限**：管理员端点（/api/overview、/api/service/*、/api/auth/search）返回 403；只能访问自己名下的 `/api/instance`（需正确 daemonId+uuid）
- ⚠️ **daemonId 稳定性**：日常稳定；daemon 重装/迁移/删除重绑会生成新 UUID——届时需从面板重新获取
- ✅ **实例状态字段**：`status`(-1=忙碌 0=停止 1=停止中 2=启动中 3=运行中)、`info.currentPlayers/maxPlayers`、`info.version`、`processInfo.pid/memory/elapsed`、`config.eventTask.autoStart/autoRestart`、`config.pingConfig.port`
- ✅ **日志含 ANSI 转义**：解析需先剥离 `\x1b[...` 控制字符
- ✅ **有玩家在线时只读安全**：状态/日志查询不干扰玩家，可用作运维监控
- ⚠️ **面板有路径防护**：根路径/未知路径返回 `{"status":500,"data":"Malicious Path"}`，属正常
- ⚠️ **静态资源全 SPA 回退**：GET 可能返回前端 HTML 而非 JSON（需带必需头 + 正确路径）
- ✅ **升级流程**：上传新 paper jar 到实例根目录（`POST /api/files/upload?upload_dir=/` → daemon `/upload/{pwd}` multipart）→ `PUT /api/files/` body `{"target":"/Start.bat","text":"新内容"}` 更新 jar 引用 → restart。旧 jar 保留作回滚
- ⚠️ **MCSM 写文件 body 字段是 `text`**（不是 content！content 返回 200 但实际不生效）
- ⚠️ **Paper 26.x 首次启动需下载 mojang_26.x.jar**：下载失败会 `Hash check failed for downloaded file mojang_26.x.jar` 崩溃循环；**kill 恢复法**：kill → start，通常第二次成功
- ⚠️ **download API 不校验文件存在性**：对任何文件名返回 200！判断存在必须**真实 GET**：500=不存在，`PK` 魔数=真实 jar
- ⚠️ **运行中 jar 读取 500=Java 锁定**：版本对比用启动日志 `Enabling X vY` 行
- ⚠️ **daemon 文件操作不稳定**：list/mkdir/move 常 500；delete 偶发假成功，删后必须真实 GET 验证
- ✅ **插件热更新（plugins/update/）**：`POST /api/files/upload?upload_dir=/plugins/update` multipart 上传 → restart → Paper 自动替换并清空 update/。**运行中上传无碍**（jar 上传不触发锁定）

## 状态码映射（MCSM 实例）

`-1`=忙碌 / `0`=停止 / `1`=停止中 / `2`=启动中 / `3`=运行中
