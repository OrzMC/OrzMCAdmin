# EasyBot IM 网关运维（2026-08-11 从 easybot-gateway-ops 技能合并）

> 场景：排查/运维 EasyBot IM 网关（本机 docker，OrzMC 机器人接入）。所有 IM 网关相关问题先查本节。

## 概述
EasyBot（`ghcr.io/easyindie/easybot`）是统一 IM 网关：OrzMC 插件通过它接入 QQ/飞书/Telegram/Discord/微信。**本机以 docker 方式运行**（容器名 `easybot`，端口 `9090→8080`，数据卷 easybot-data → `/var/lib/easybot`）。**2026-08-12 升级至 0.0.33（schema v3）**，部署 kit 在 `~/Services/easybot-deploy-kit-0.0.33/easybot-deploy-kit/`（0.0.31 旧 kit 保留在 `~/Services/easybot-deploy-kit/` 作参照）。升级法：备份 DB（`easybot-backup.sh backup sqlite` 或 docker cp+sqlite3 .backup）→ 下载新 kit 校验 checksum → 拉镜像 → `EASYBOT_PORT=9090 EASYBOT_BIND_ADDRESS=0.0.0.0 ./deploy.sh`（保留卷）→ 验证 health/adapters（`schema_version: 3`、adapters 5/5）。

**架构链路**：
```
OrzMC 插件 (easybot.yml) → https://test-bot.{SERVER_NAME}.cn (反代在【另一台设备】) → 本机 easybot:9090 → 平台 adapter (QQ wss://api.sgroup.qq.com 等)
```

## 快速健康检查
```bash
docker ps --filter name=easybot                # Up (healthy)
curl -s http://127.0.0.1:9090/api/v1/health    # 200
docker logs easybot --since 10m | tail          # 看 adapter 状态
# 插件侧：
grep -E "WebSocket|认证|重连" ~/minecraft-server/logs/latest.log | tail
```
- 插件 `/bot` 输出 `enabled httpUnknown wsNotOk`：`httpUnknown` = HTTP 健康检查异步未完成（设计态黄色警示，**非 bug**）
- WS 正常 = 日志 `WebSocket连接建立` + `EasyBot WebSocket 认证成功`

## 机器重启后恢复清单（Mac 重启后按序执行）
```bash
open -a Docker                                   # 1. 启动 Docker Desktop
for i in $(seq 1 6); do docker info >/dev/null 2>&1 && break || sleep 2; done
docker ps --filter name=easybot                  # 2. ⚠️ 容器常停在 Exited(255)——daemon 起来≠容器在跑
docker start easybot
curl -s http://127.0.0.1:9090/api/v1/health      # 3. 期望 healthy + adapters 5/5 connected
```
- ⚠️ **Docker daemon 自启后 easybot 容器不会自动 start**（Exited 残留），必须手动 `docker start easybot`，然后 health 端点确认 5/5 adapter
- Shadowrocket 由用户手动开；确认直连规则：`ifconfig utun3` 存在（UP）+ `curl https://www.baidu.com` 快（~0.1s，直连）+ `curl https://www.google.com` 通（~2s，代理）+ `dig test-bot.{SERVER_NAME}.cn` 返 **198.18.x.x fake-IP 是正常**（隧道在工作），不是服务故障
- 测试服：启动前 `rm -f world/session.lock`（异常退出残留锁）→ `./start.sh` → grep `Done (`
- 最终验证闭环：插件日志 `WebSocket连接建立` + `认证成功` + 投递诊断（`scripts/easybot_deliveries.py`）最近记录全 ✅

## 发送失败诊断（核心：gateway.db / API）
> ⚠️ **0.0.33 变更（2026-08-12 实测）**：投递记录从 `outbound_deliveries` 迁移到 **`messages` 表**（`outbound_deliveries` 停止写入，仅留历史）；且 SQLite WAL 模式下 `docker cp` 单文件**漏最近提交**（-wal 未合并）→ **不要再用 docker cp+sqlite 查投递**。诊断用脚本（已更新为 API 版）：`python3 scripts/easybot_deliveries.py`（自动 admin login → `GET /api/v1/messages`，出站标 [出]/入站标 [入]，失败显示 error）
```bash
python3 scripts/easybot_deliveries.py   # 最近投递状态（API 版，0.0.33+）
# 手动查：POST /admin/login {password} → GET /api/v1/messages?limit=30
```
关键表（0.0.33，仅 docker cp 全量备份时用）：
- `messages`：**当前投递/消息记录**（platform/chat_id/role/text/raw_data.result.success/timestamp）
- `sessions`：会话 key ↔ chat_type（**Group=群 / Dm=私聊**）——判断 target 配错类型
- `api_keys`：key 权限（插件 key 仅 `messagessend`+`websocketconnect`；面板 admin key 权限全）
- 容器日志被面板 `/api/v1/logs` 每秒轮询刷屏 → 用 grep 过滤具体路径

## QQ token 生命周期
- QQ access token 有效期 **7200s (2h)**，过期后发送报 **11244 "token not exist or expire"**
- **刷新**：`POST /api/v1/adapters/qq/start`（需 API key）→ 日志依次出现 `QQ access token refreshed` → `QQ adapter connected` → `QQ Gateway ready`；面板操作等效
- **拿全权限 key**：`POST /admin/login {"password":"<EASYBOT_ADMIN_PASSWORD>"}` → 返回 `eb_...`（面板密码登录，短时管理 Session，权限全——插件 key 只有 messagessend+websocketconnect，查 sessions/adapters 会 403）
- **API 文档**：`GET /openapi.json`（89KB 完整 OpenAPI，所有端点+权限清单）——探索 EasyBot 能力先拉这个，别盲探端点
- **11255 "invalid request"**：token 刷新瞬间的暂时性错误，或 target 类型错（把 Dm openid 当群 id 发 `/v2/groups/`）
- 恢复确认：deliveries 最近记录全部 `succeeded`

## 会话 target 格式
- `qq:XXX` / `feishu:XXX` / `telegram:conv_XXX` / `discord:conv_XXX` / `wechat:conv_XXX`
- QQ 的 key 语义：群 = Group chat_id；私聊 = Dm openid —— 用 `sessions.chat_type` 区分
- 插件 easybot.yml 三目标：`admin_group` / `player_group`（PUBLIC 默认目标，空则降级 admin_group）/ `admin_dm`（私聊）

## 坑
1. **域名可能被 Shadowrocket VPN 劫持**：`dig test-bot.{SERVER_NAME}.cn` 返回 198.18.0.188（fake-IP 保留段）≠ 真实反代地址 —— 先 dig 再判断"服务挂了"
2. **反代不在本机**：本机 nginx 没有 test-bot 配置是正常的（反代在另一台设备）——别在本机 nginx 里找
3. 容器 env 含敏感项（QQ_CLIENT_SECRET / FEISHU_APP_SECRET / EASYBOT_ADMIN_PASSWORD / 各平台 token）——输出/入库前脱敏
4. 诊断用 db 副本用完即删，不留 /tmp 残留
5. **没有"模拟入站消息"的 API**：`/api/v1/messages/ingest|inject|emit` 均 404/405（未定义路径伪装），openapi.json 也无此端点——**无法用 API 伪造群消息触发插件 Bot 命令**；`/admin` 面板的 Debug 面板只是 API Key 权限验证器（验证 target + 发 probe），不是消息注入。要测 Bot 命令用测试服控制台 `orzdebug $<cmd>` 或真实群消息
6. 405 可能是"未定义路径"的默认响应——探测前先拉 `/openapi.json` 确认端点真实存在，别被 405/404 误导
7. **反代 Cloudflare 按 UA 拦截**（2026-08-12 实测）：urllib/python 默认 UA 请求 https://test-bot.{SERVER_NAME}.cn 返回 **403 + error code: 1010**；curl 带浏览器 UA 正常 200。手动测 API 走反代必须带浏览器 UA；本机 9090 直连无此限制

## 验证闭环
改完/刷新后：bot 上线触发通知 → 插件日志无 `失败目标` → gateway.db deliveries 最新记录全 `succeeded` → 以表格汇报（平台/目标/状态）
