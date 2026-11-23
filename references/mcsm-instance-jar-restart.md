# 换插件 jar 并重启测试服实例

OrzMC 测试服的每个实例是 WSL2 Ubuntu 里一个独立容器，由 MCSManager daemon 起，
**不在 Windows 进程列表里**。换 jar、重启、查日志都按下面的路径走。

## 1. 先确认实例在跑、jar 在哪

```bash
wsl.exe -d Ubuntu -e sh -c 'docker ps --format "{{.Names}}\t{{.Image}}"' | tr -d '\0'
```

容器名 = `MCSM-<实例UUID 前 6 位>`（如 `MCSM-716c2f` = Paper lobby、`MCSM-8A932D` = Folia survival）。

宿主机数据目录直接就是挂载源：

```
/mnt/e/orzmc/mcsmanager/daemon/data/InstanceData/<UUID>  ->  /server   (容器内)
```

所以换 jar 就是改宿主机 `.../InstanceData/<UUID>/plugins/<Plugin>-<ver>.jar`，
再用 `docker exec <容器> ls -l /server/plugins/...` 确认容器内看得见同一个文件。

> 坑：`tasklist | grep java` / `Get-CimInstance Win32_Process java.exe` 在宿主机上是**空的**，
> 因为 JVM 跑在 WSL 容器内。判断服务在不在，只看 `docker ps`。

## 2. 备份（换 jar 前必做）

```bash
cp -p $D/$i/plugins/X.jar $D/$i/plugins/X.jar.bak-<日期>
tar -czf $D/$i/plugins/X-shop-backup-<日期>.tgz -C $D/$i/plugins X/shop
```

第二个是为了防**新 jar 重新释放样例配置覆盖运行时改动**（插件把 `resources/` 下的样例
写到 `plugins/X/` 时，有时是覆盖而不是“不存在才写”）。重启后对比一次，被盖了直接从 tgz 还原。

## 3. 重启

```bash
wsl.exe -d Ubuntu -e sh -c 'docker restart MCSM-716c2f MCSM-8A932D'
```

- 这会发 SIGTERM，Paper/Folia 会正常存档退出再起，是安全的“重启”而非硬杀。
- `docker restart` 会被 Hermes 当成破坏性命令要审批；用户没及时点批准就**停在那里报告**，
  不要换别的命令绕（另一个可用出口是请用户在 MCSM 面板点重启）。
- 面板 apikey（`$MCSM_LOCAL_API_KEY`）只够读列表：`/api/instance` 拿错 daemonId 会回一个
  `nickname=Undefined` 的幽灵实例，`/api/service/remote_services_list` 等端点直接 403。
  别花时间靠猜 daemonId 打通重启，优先 `docker restart` 或让用户点面板。

## 4. 验证

```bash
# 启动完成（Paper ~107s、Folia ~85s）
grep -a "Done (" $D/$i/logs/latest.log | tail -1
# 插件自身问题
grep -a "EzShops" $D/$i/logs/latest.log | grep -aiE "warn|error|exception|outside the menu" | tail -20
```

换版验收至少看四项：插件 enable 无异常、菜单能打开且缺失项回位、写盘类功能（交易/统计）
真的产生记录、日志里原有的告警消失。回滚 = 把 `.bak-<日期>` 改回原名再 `docker restart`。
