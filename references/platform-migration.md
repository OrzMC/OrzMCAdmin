# 平台层迁移（orzmc-deploy 栈换机 / Windows 全新部署）

> 2026-09-09 Mac→Windows 迁移实录。触发：把 orzmc-deploy 平台栈（MCSM web/daemon + EasyBot + cloudflared 隧道 + MariaDB + Gatus）+ orzmusic 迁到新机。
> 数据权威源 = 迁移包；**本机无历史数据时 = 全新安装**（Docker Desktop/WSL/部署包全要从零）。

## 资产关系（迁移前必读）

- **DATA_ROOT**（Mac `/Users/Shared/orzmc`，Win `E:/orzmc`）：含 `.env`（全部密钥）、mcsmanager 数据+双实例、worlds、easybot 数据、cloudflared 凭据、mariadb 数据、status 配置。**备份=打包 DATA_ROOT**
- **部署包**（`~/Services/<svc>-deploy-<ver>`，运行时非数据，镜像 digest 锁定 compose 自拉）：orzmc-deploy-0.0.3-dev（orzmc.sh/restore.sh/docs）+ orzmusic-deploy-0.0.7
- orzmusic 数据在 **Docker 命名卷**（orzmusic_cas_data/orzmusic_db_data），不在 DATA_ROOT → 单独卷导出

## 端口架构（关键，防 AI 误解）

| 服务 | 容器内端口 | 宿主发布 |
|---|---|---|
| easybot | 8080（EASYBOT_PORT） | **不发布**（仅 expose，cloudflare/local 档） |
| status/Gatus | 8080（STATUS_PORT） | 不发布 |
| mcsmanager-web | 23333 | 不发布 |
| mcsmanager-daemon | 24444 | 不发布 |
| **orzmusic** | 8080 | **`8080:8080`（宿主 8080 唯一占用者）** |

- cloudflare 档（生产，EDGE=cloudflare）全部服务**只 expose 不发布宿主端口**，cloudflared 出站隧道内网直达；lan 档才发布宿主端口且 easybot 用 `LAN_EASYBOT_PORT`（默认 **18091**）特意避开 8080（ADR-012）
- ⚠️ **"插件直连 http://easybot:8080" = 容器内网地址（orzmc_default 网络），不是宿主映射**——AI 智能体易误解成要 -p 8080:8080
- Mac 共存方案：宿主 8080 整个让给 orzmusic

## ⚠️ Windows 端口冲突坑（2026-09-09 实测）

Windows 全新部署报「orzmusic 8080 与 easybot 8080 冲突」根因：**Windows 上残留独立部署的旧 easybot 服务（8 月验收遗留，容器体系外）占宿主 8080**。解决：清掉独立服务/进程（Windows 服务+计划任务一并移除防自启），用容器内 easybot（数据来自迁移包还原）。修复验证：
```powershell
netstat -ano | findstr :8080     # 应无 LISTEN 残留
docker ps --format "{{.Names}} {{.Ports}}" | grep easybot   # Ports 应为空（不发布）
```

## 打包步骤（源机，栈已停状态）

```bash
# 1. 起引擎等就绪
open -a Docker; for i in $(seq 1 90); do docker info >/dev/null 2>&1 && break; sleep 2; done

# 2. orzmusic 双卷导出（容器静止 = 最一致，无需 up 服务）
docker run --rm -v orzmusic_cas_data:/d -v ~/orzmc-migration:/out alpine sh -c "tar czf /out/orzmusic-cas.tgz -C /d ."
docker run --rm -v orzmusic_db_data:/d  -v ~/orzmc-migration:/out alpine sh -c "tar czf /out/orzmusic-db.tgz -C /d ."

# 3. orzmc 一致性备份（必须等 mariadb READY，见坑）
./orzmc.sh -d /Users/Shared/orzmc up
for i in $(seq 1 60); do docker exec orzmc-mariadb mariadb-admin ping >/dev/null 2>&1 && break; sleep 2; done
./orzmc.sh -d /Users/Shared/orzmc backup --stop   # down→打包→自动 up；产物 $(dirname DATA_ROOT)/orzmc-backups/

# 4. 停栈恢复原状 + 可选 quit Docker Desktop（pkill -9 -f /Applications/Docker.app 清残留）

# 5. 组装迁移包：mv 归档 + cp 部署包目录 → 外层 tar 不带顶层目录前缀
tar -cf ~/Downloads/orzmc-migration-<date>.tar -C ~/orzmc-migration <归档> <tgz...> -C ~/Services orzmc-deploy-0.0.3-dev orzmusic-deploy-0.0.7
```

## ⚠️ backup.sh dump 竞态坑（2026-09-08 实测）

- `dump_db_logical`：mariadb **未运行**时（--stop 模式）会自己拉起并 `wait_for_mariadb`；但**容器已在跑时不等待就绪直接 dump**
- 若刚 `up` 完立刻 backup，mariadb 还在冷启动 → dump 连接失败 → `rm -f dump_file` + warn（**warn 常被输出截断不易察觉**），归档只剩冷数据目录
- **必须等 mariadb ping 通再 backup**（`docker exec orzmc-mariadb mariadb-admin ping`——ping 不需要认证）
- 验证归档含 dump：`tar tzf <归档> | grep -E "database/dumps/mariadb-all|^<root>/.env$"`
- dump 失败不致命（mariadb 数据目录 = 权威冷数据，down 时干净停机即一致），但 Windows 还原多一层保险更稳

## Windows 全新环境还原步骤

```bash
# 0. 环境（全新）：Docker Desktop + WSL2（Windows 功能→wsl --update→WSL Integration）；.wslconfig networkingMode=mirrored + wsl --shutdown；vhdx 建议迁数据盘
# 1. orzmc 还原（部署包内 Git Bash/MSYS 跑 .sh）
bash restore.sh -d E:/orzmc <orzmc-backup-*.tar.gz> --force   # 自动改 .env DATA_ROOT
./orzmc.sh -d E:/orzmc validate && ./orzmc.sh -d E:/orzmc up  # Windows 下 daemon 由脚本 win_daemon_run 自动 docker run（ADR-016）
# 2. orzmusic（Windows 无 bash_history，ADMIN_API_TOKEN 留空 = adminApi disabled，与 Mac 现状一致）
docker volume create orzmusic_cas_data; docker volume create orzmusic_db_data
docker run --rm -v orzmusic_cas_data:/d -v /e/migration:/in alpine sh -c "tar xzf /in/orzmusic-cas.tgz -C /d"
docker run --rm -v orzmusic_db_data:/d  -v /e/migration:/in alpine sh -c "tar xzf /in/orzmusic-db.tgz -C /d"
cd /e/migration/orzmusic-deploy-0.0.7
IMAGE_REF="ghcr.io/orzgeeker/orzmusic@sha256:a74ad4d62b4bfb1638fc916281cd1119856d412a6b4fb225fa748a00ae201dd3" \
  docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
# 3. 验证：8 容器 Up/healthy + 4 端点 200（mcs/easybot/orzmcs/mcs-node.{SERVER_NAME}.cn）+ curl 127.0.0.1:8080/api/health
```

## 传输：macOS SMB 共享（2026-09-09 实测坑）

- macOS 共享名 = **目录显示名（中文系统 = 「下载」）**，不是路径名 Downloads → Windows 访问 `\\<IP>\下载`（或浏览根目录找共享）
- SMB 认证被拒（密码正确也拒）根因：文件共享「选项」里**没启用 SMB 账户**——系统设置→通用→共享→文件共享→选项→勾「使用 SMB 共享文件」+ 勾选账户 + 输入账户密码启用
- 排障定位法：Mac 本地 `smbutil view //bot@<IP>`（密码交互，pty+submit）；能 sudo 不能 SMB = 共享配置问题非密码问题
- 局域网兜底：python3 -m http.server <port> --directory <dir>（只暴露迁移文件目录，用后即关）

## 当前状态（2026-09-09）

- Mac：迁移包 `~/Downloads/orzmc-migration-20260909.tar`（2.7G，5 项：orzmc-backup + cas/db tgz + 双部署包）；执行提示词 `~/hermes-windows-migration-prompt.md`；**Docker 全停**（容器 0/引擎退出/隧道无）
- Windows：全新部署中（装 Docker→还原→起栈），容器 easybot 接管 easybot.{SERVER_NAME}.cn
- 隧道单点铁律：源机停 + 目标机 cloudflared 接管 {SERVER_NAME}.cn，**严禁双跑串流量**
