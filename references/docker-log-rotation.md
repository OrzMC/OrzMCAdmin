# Docker 容器日志轮转（宿主级 daemon.json）

用途：容器 `json-file` 日志默认**不轮转**（不设 `max-size` 就是无限增长）。`docker logs` 看得爽，长期跑迟早把盘写满，且写满后是**静默故障**（容器重启/写盘炸掉，报错跟日志无关，极难追）。

## 本机现状（2026-11-23 已落地）

`/etc/docker/daemon.json`（WSL Ubuntu 26.04 内）：

```json
{
  "userland-proxy": false,
  "live-restore": true,
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "3" }
}
```

备份与原文件副本都在 `E:/orzmc/docker/`（`daemon.json.bak-<日期>`、`daemon.json.new`）。全部 10 个容器已确认 `HostConfig.LogConfig = {max-size:50m, max-file:3}`。

量级参考：easybot 每个 HTTP 请求一条 INFO（后台日志页轮询），实测 239 KB/24min ≈ **14 MB/天 ≈ 5 GB/年**；orzmusic-app 6.9 MB；面板 daemon 736 KB。

## 改法（必须两步，缺一无效）

1. 写 `/etc/docker/daemon.json` → `systemctl restart docker`（**需审批**：stop/restart system service）。
   用 `wsl -e sh -c 'cp ... && systemctl restart docker'`，重启后 `systemctl is-active docker` + `docker info --format '{{.ContainersRunning}}'` 核对。
2. **重建容器**。daemon 默认值只作用于**新建**容器，老容器再怎么重启也还是空 `LogConfig`。

## ⚠️ 本机最大坑：重启 dockerd 会吃掉 MCSM 实例容器

`live-restore: true` 能保住 compose 起的 7 个容器（caddy/easybot/webmc/面板/music），**但 MCSM 面板管理的游戏实例容器（`MCSM-xxxx` / `orzmc-velocity`）会被销毁**（实测：`docker ps -a` 里直接消失）。之后面板 daemon 自己重启、按实例配置重建并拉起三个实例，paper/folia 各 ~105–128s、velocity ~11s，全过程约 2.5–3 分钟。

→ **只能安排在无人在线时**，并预留 3 分钟；重建是幂等的（数据在 `InstanceData/<uuid>/` 宿主目录，无损失），但看起来像「莫名其妙重启」。

## 重建命令（本机实测可用）

```bash
# 站点层 + 面板 web + easybot（不含 daemon，避免和实例启动撞车）
wsl -e docker compose --env-file /mnt/e/orzmc/.env.wsl \
  -f /mnt/e/deploy/orzmc/compose.yaml -f /mnt/e/orzmc/compose.site.yaml \
  --profile easybot up -d --force-recreate caddy webmc mcsmanager-web easybot

# 面板 daemon 最后单独来（实例已 Done 后再重建；实测重启后能按 label 认领运行中的实例容器，不会杀）
wsl -e docker compose --env-file /mnt/e/orzmc/.env.wsl \
  -f /mnt/e/deploy/orzmc/compose.yaml -f /mnt/e/orzmc/compose.site.yaml \
  --profile easybot up -d --force-recreate --no-deps mcsmanager-daemon

# orzmusic 是独立 project，且必须显式给 IMAGE_REF（否则 compose 报 IMAGE_REF is required）
wsl -e sh -c 'cd /mnt/e/deploy/orzmusic-deploy-0.0.12 && IMAGE_REF=ghcr.io/orzgeeker/orzmusic:0.0.12 docker compose \
  -f docker-compose.yml -f docker-compose.production.yml up -d --force-recreate --no-deps app db'
```

`--no-deps` 很关键：不加会把 `cas-init`/`migrate` 这类一次性容器也拉起来跑一遍。

## 验收（别只看配置写完）

```bash
wsl -e docker inspect --format '{{.Name}} {{json .HostConfig.LogConfig}}' $(wsl -e docker ps -q)   # 每个都要有 max-size/max-file
wsl -e docker ps --format '{{.Names}}\t{{.Status}}'                                                # 10 个容器都在
python <skills>/gaming/orzmc/scripts/connectivity_check.py                                        # 三个入口 FAIL 0
```
再加：面板实例 status 全为 3（`GET /api/instance`）、`https://{mcs,easybot,webmc,music}.{SERVER_NAME}.cn` 返回 200 且 `ssl_verify_result=0`、实例容器 `Config.Env` 仍有 `TZ=Asia/Shanghai`。

## 更符合上游的做法（未做）

上游自己的生产 compose 是「JSON 容器日志按大小轮转」的，**我们部署包 `E:/deploy/orzmc/compose.yaml` 里没有 `logging:` 块**。长期正解是在部署包给各服务补：

```yaml
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "3" }
```

（属 OrzMC 仓库改动，走 PR；改包内文件会在下次部署覆盖，别手改运行树。）

## 相关上游 issue

- `EasyIndie/EasyBot#203`：日志时间戳固定 UTC、TZ 不生效（Alpine 镜像缺 tzdata）。
- `EasyIndie/EasyBot#204`：`logging.output=file` 无轮转参数、Docker 文档未提示日志默认无限增长。
