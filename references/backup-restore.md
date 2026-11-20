# 数据备份与恢复（backup.sh）

## 用法

```bash
cd E:/deploy/orzmc
./orzmc.sh -d E:/orzmc backup                    # 在线打包（best-effort 快照）
./orzmc.sh -d E:/orzmc backup --stop             # 先停 compose 再打包再拉起
./orzmc.sh -d E:/orzmc backup -o E:/orzmc-backups --keep 3
```

- 归档默认落 `${DATA_ROOT%/*}/orzmc-backups/`，即 `E:/orzmc-backups`（**唯一备份根**）。
- 归档名 `orzmc-backup-YYYYMMDD-HHMMSS.tar.gz`，**含 `.env` 等密钥**，只留本机，不外传。
- `--stop` 只停 compose 服务；MCSManager 托管的 PaperMC 实例不在 compose 里，要一致快照得先在面板停实例。
- 体积参考：5.8G 数据 → 3.9G 归档（world 已压缩，gzip 收益低），耗时约 13 分钟。

## Windows 上 tar 的坑（2026-11-20 修，OrzMCDeploy#18）

症状：`tar: E\:: Cannot open` / `tar (child): Cannot connect to E: resolve failed`。

GNU tar 把 `X:/...` 当远程主机（`host:path`），三段都中招：

| 位置 | 错法 | 修法 |
|---|---|---|
| `-C` 父目录 | `dirname E:/orzmc` → `E:`（被当主机名） | 盘符根补斜杠 `E:/` |
| 归档路径 | `-czf E:/orzmc-backups/x.tar.gz`（同上） | Windows 下加 `--force-local` |
| 校验 | `tar tzf E:/...` | `tar --force-local -tzf …`（**必须带短横线**，裸 `tzf` 跟在 long option 后不被解析） |

第二条的边界：只有父目录**恰为** `X:` 时才补斜杠，`C:/Users/x/data` 的父目录是 `C:/Users/x`，
早期写成 `[A-Za-z]:/*` 分支会把深层路径算成盘符根，tar 报 `data: Cannot stat`。

## 验证与恢复

```bash
tar --force-local -tzf E:/orzmc-backups/orzmc-backup-2026xxxx.tar.gz | wc -l   # 28657 量级
tar --force-local -xzf E:/orzmc-backups/orzmc-backup-2026xxxx.tar.gz -C E:/     # 解出 ./orzmc
```

恢复前先 `./orzmc.sh -d E:/orzmc stop`，解包后 `up`；实例目录属于 MCSManager，恢复 world 时确认面板里实例已停。

## 注意

- 修复在 `deploy` 仓库（`5c139d8`）。**部署目录 `E:/deploy/orzmc/backup.sh` 仍是旧版**，等下次 Release 覆盖；
  眼下要备份就跑仓库副本：`bash E:/dev/OrzMC/deploy/backup.sh -d E:/orzmc`。
- 备份脚本不含排除项，`tools/`（JDK/Gradle/Hugo，521M）也会打进归档——恢复时不要用它覆盖 `JAVA_HOME` 指向的工具链。
- 从未有过自动备份计划任务；归档增长快（每次近 4G），定期 `--keep` 或手工清理旧包。
