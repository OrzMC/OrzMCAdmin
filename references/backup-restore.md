# 数据备份 / 还原 / 自检 / 证书检查（orzmc.sh 命令）

## 命令（v0.3.0 起都挂在 `orzmc.sh` 上，程序目录只从 Release 包取得）

```bash
cd E:/deploy/orzmc
./orzmc.sh -d E:/orzmc backup                    # 在线打包（best-effort 快照）
./orzmc.sh -d E:/orzmc backup --stop             # 先停 compose 再打包再拉起
./orzmc.sh -d E:/orzmc backup -o E:/orzmc-backups --keep 3
./orzmc.sh -d E:/orzmc restore <归档> [--force] [--start]   # 还原/迁移
./orzmc.sh -d E:/orzmc doctor                    # 部署自检（有 FAIL 则 exit 1）
./orzmc.sh -d E:/orzmc cert [--min-days 21]      # 证书到期检查（只读，不续期）
```

- 归档默认落 `${DATA_ROOT%/*}/orzmc-backups/`，即 `E:/orzmc-backups`（**唯一备份根**）。
  换 `-d` 就换根：`-d E:/x/data` → `E:/x/orzmc-backups`，`-d E:/x` → `E:/orzmc-backups`（父目录就是 `E:/`），不是 bug。
- 归档名 `orzmc-backup-YYYYMMDD-HHMMSS.tar.gz`，**含 `.env` 等密钥**，只留本机，不外传。
- `--stop` 只停 compose 服务；MCSManager 托管的 PaperMC 实例不在 compose 里，要一致快照得先在面板停实例。
- 体积参考：5.8G 数据 → 3.9G 归档（world 已压缩，gzip 收益低），耗时约 13 分钟。
- `restore` 解包后会**自动改写归档里 `.env` 的 `DATA_ROOT`** 指向目标目录（迁移/换盘靠这个，别再手工 sed）。

## doctor / cert 各自判什么

`doctor` 唯一写操作 = 在 `DATA_ROOT` 与备份根各写一个探针文件后立即删除；其余只读。分组：

| 分组 | 判什么 | 典型故障 |
|:--|:--|:--|
| 环境 | docker CLI / daemon / compose 插件 / openssl | Docker Desktop 落在会话 0 里起不来 |
| 数据目录 | 存在、可写、`.env` 齐全、`.env` 里 `DATA_ROOT` 与实际一致 | 迁移后 `.env` 残留旧路径 |
| 备份 | 备份根可写、最近归档、磁盘水位 | 单次近 4G，空间不足会写坏归档 |
| 运行时 | 容器数、**容器 `config_files` 是否指同一棵程序树**、期望端口是否真发布 | 改 A 树、容器跑 B 树 |
| 工具链 | `JAVA_HOME` 指向存在 | 清理误删 tools 目录 |

判定语义：`[FAIL]` exit 1；容器由**另一棵**树启动只 `[WARN]`（开发克隆里跑属正常），
**分散在多棵树**下才 `[FAIL]`。看 `[WARN]` 先分清「我在仓库里跑」还是「真的漂移」。

`cert` 读 `$DATA_ROOT/caddy/data/caddy/certificates/acme-v02.api.letsencrypt.org-directory/<domain>/<domain>.crt`，
打印域名/到期日/剩余天数；任一不足 `--min-days` 即 exit 1，可直接挂 cron/监控。
**只读**：不续期、不动 `caddy/data`（手工续期会打乱 Caddy 的 ACME 状态）；无 `caddy/data` 时报「站点层未启用」exit 0。

**`cert` 不能顶替现有的证书哨兵 cron**（`caddy-cert-watch`，每天 09:05）：`cert` 只判剩余天数，
哨兵还判**期望子域是否齐全、`orzmc-caddy` 容器是否在跑、过去 24h 有无 ACME/TLS 报错**——`cert` 是它的子集。
把哨兵换成 `cert` 看似「去 python 依赖」，实际会丢掉三类告警。`cert` 的定位是人工查、CI 门禁、新机器接入时的快速体检。
同理，任何「新命令能否替代旧脚本」的判断都要先比**检查项的集合关系**，别只比主判据。

## Windows 上 tar 的坑

症状：`tar: E\:: Cannot open` / `tar (child): Cannot connect to E: resolve failed`。

GNU tar 把 `X:/...` 当远程主机（`host:path`），三段都中招：

| 位置 | 错法 | 修法 |
|---|---|---|
| `-C` 父目录 | `dirname E:/orzmc` → `E:`（被当主机名） | 盘符根补斜杠 `E:/` |
| 归档路径 | `-czf E:/orzmc-backups/x.tar.gz`（同上） | Windows 下加 `--force-local` |
| 校验 | `tar tzf E:/...` | `tar --force-local -tzf …`（**必须带短横线**，裸 `tzf` 跟在 long option 后不被解析） |

第二条的边界：只有父目录**恰为** `X:` 时才补斜杠，`C:/Users/x/data` 的父目录是 `C:/Users/x`，
早期写成 `[A-Za-z]:/*` 分支会把深层路径算成盘符根，tar 报 `data: Cannot stat`。

脚本侧收敛：`lib/common.sh` 的 `tar_local`（Windows 下自动补 `--force-local`）与 `tar_parent_of`（父目录推导），
backup 与 restore 共用，别再各写一份。**用函数封装，不要写 `tar $(tar_win_opts) …`**——未加引号的命令替换
触发 SC2046，且空值/多值时会退化成「参数消失」；`tar_local -tzf "$a"` 读起来也没有选项解析悬念。

## 改脚本后怎么自测（别直接对真实数据跑）

1. 造一个假 DATA_ROOT，**并用 `-o` 指到临时目录**——默认备份根是 `${DATA_ROOT%/*}/orzmc-backups`，不传 `-o` 时测试归档会落进真实备份根的兄弟位置，事后还得手工清。
2. **两种路径形态都要测**：盘符根（`E:/btest`，考验父目录补斜杠那支）和深层路径（`C:/Users/<u>/…/data`，考验「父目录不是盘符根」那支）。只测盘符根会让深层路径算错成 `C:/` 的 bug 漏网。
3. 判据：脚本自报「备份完成并校验通过」+ `tar --force-local -tzf <归档> | wc -l` 给出万级项数。**列表只吐 1–2 行且秒回 = 参数被误解析**，不是「归档小」。
4. 往返测：备份 → `restore` 到另一个目录 → `cat` 内容一致 + `.env` 的 `DATA_ROOT` 已改写成目标路径。
5. **本机 lint 要先转 LF**：git 在 Windows 上 checkout 出 CRLF，直接 `shellcheck` 会刷 SC1017(CRLF) /
   SC1094(被 source 的文件解析失败) 等假警报。做法：`tr -d '\r' < f > $W/f` 复制一份到临时树再跑
   `shellcheck -x --shell=bash *.sh lib/*.sh`，和 CI 看的是同一份（仓库存 LF）。没装 shellcheck 就用
   `docker run --rm -v "$(cygpath -m $W):/mnt" -w /mnt koalaman/shellcheck:stable …`。
6. 导出函数名的写法要过 shellcheck 的**可移植性**关：`find -printf` 是 GNU 专有（macOS 无），
   取最新归档还是用 `ls -1t`，真被 SC2012 咬就加 `# shellcheck disable=SC2012` 说明理由，别为讨好 lint 引入平台专有参数。

## 验证与恢复

```bash
tar --force-local -tzf E:/orzmc-backups/orzmc-backup-2026xxxx.tar.gz | wc -l   # 28657 量级
./orzmc.sh -d E:/orzmc restore E:/orzmc-backups/orzmc-backup-2026xxxx.tar.gz --force --start
```

恢复前先 `./orzmc.sh -d E:/orzmc stop`，解包后 `up`；实例目录属于 MCSManager，恢复 world 时确认面板里实例已停。

**`stop` → `up` 之后实例不会自己回来**：实例的 `autoStart=false` 是刻意的（停了要报警，不能自动拉起把故障掩盖掉），
所以整栈重启后 `docker exec orzmc-mcsmanager-daemon sh -c 'ps aux | grep -c "[j]ava"'` 返回值是 0 ——
面板 200、TLS 200、`doctor` 全绿都只证明**平台在跑，世界没在跑**。这件事有两层后果：
① 任何 `stop`/`up`/还原/升级动作的汇报都必须显式写「两个实例需人工在面板启动」，别用容器 5/5 Up 收尾；
② 启实例要面板交互，面板凭据按既有规则走 vault、**永不进聊天**，MCSM v4 daemon 直连也没有公开的
`POST /api/instance/start`（实测 `Not Found`，路由是动态注册的）——所以别把它写进自动化脚本，
固定给两条路：「你去面板点启动」或「面板设置里开 API Key 后我脚本化」。
手工解包也行（`tar --force-local -xzf <归档> -C E:/` 解出 `./orzmc`），但那样 `.env` 的 `DATA_ROOT` 要自己改。

## 恢复的实操验收（用真实归档，不停现网）

1. **还原到「兄弟目录 + 同名」**：归档顶层目录名 = 备份时 `basename DATA_ROOT`（现网 `orzmc`），所以还原目标写 `E:/restore-test/orzmc`。换个名字（`orzmc-restore-test`）会被脚本以「归档顶层目录与目标目录名不一致」拒绝——**这是护栏，不要用 `--force` 绕过命名对齐**：那会把目录改名，`.env` 的 `DATA_ROOT` 改写也跟着错位。
2. **文件级验收不需要停机**：还原到另一个路径与运行中的栈零冲突（端口只由现网占着）。
3. 四项判据：
   - `find <源> -type f | wc -l` 与 `find <还原> -type f | wc -l` 相差**恰好 1**（多出的是 `.env.bak-restore`）
   - 关键文件 md5 逐个相同：两个实例的 `server.properties`、代理的 `velocity.toml`、`forwarding.secret`
   - `<还原>/.env` 里 `DATA_ROOT` 已改写成目标路径，原文件留成 `.env.bak-restore`
   - 顶层目录齐：`mcsmanager/ eagler/ caddy/ easybot/ tools/`
4. **别用 `du -sh` 判体积**：机械盘上 5.8G 目录的 `du` 要几分钟，前台调用必超时。用 `find|wc -l` 与 md5 更快给结论；真要看体积就把 `du`/`tar` 放 `background=true` + `notify=true`。
5. **启动级验收有两条路，先选轻的那条**：
   - **轻量（不占端口、优先用）**：在主机的还原副本里直接跑本体 jar 验世界能否加载 ——
     `cd <还原>/mcsmanager/daemon/data/InstanceData/<uuid> && <还原>/tools/jdk25/bin/java -Xms1G -Xmx2G -jar paper-*.jar --nogui --port 25599`，
     然后 `grep -E "Done \(|Preparing level|ERROR" logs/latest.log`。判据是 **`Done (…s)!`**（实测约 130s）。
     Paper/JDK 都支持 `--port`，**不要为此改 `server.properties`**（改了就是动真数据副本，测试完还得改回）。
   - **完整（整栈起服，需停机窗口）**：顺序 `stop`（现网）→ 副本 `up` → 面板 200 + `https --resolve <域>:443:127.0.0.1` 走副本证书 200 → 副本 `stop` → 现网 `up` → `doctor` 复核（19 OK / 0 WARN）。整轮约 6 分钟。
   - 副本 `up` 的副作用要预先知道：它**占满同一批端口**（23333/443/25565/19132），且 `orzmc-caddy` 会用**副本里的证书**对真域名回 200 —— 看到 200 别当成「现网还在跑」，那一刻现网其实是停的。
   - 只做文件级时，汇报里必须写明「启动未验」；别让「恢复已验收」被理解成能起服。
6. **还原验收完把副本删掉要单独问**：副本约 5.8G，是当次验收的证据；先汇报体积与结论，等拍板再删（并入磁盘清理清单走同一套流程）。

## 注意

- 备份脚本不含排除项，`tools/`（JDK/Gradle/Hugo，521M）也会打进归档——恢复时不要用它覆盖 `JAVA_HOME` 指向的工具链。
- **在线快照会打印 `tar: ... world: file changed as we read it`，属正常**（实例在跑、世界在写）。判据是退出码 0 +
  条目数与上一份一致（万级，如此前 28657 对 28657），不是「有警告就当备份坏了」。要绝对一致需 `--stop` 或先在面板停实例。
- **自动备份已排期**：测试服跑每日 04:00 的 `backup --keep 1`（老板口径：测试服只保留一份，用途是验证备份功能本身是否正常，不是留历史）。汇报模板＝归档名＋体积＋`tar --force-local -tzf | wc -l` 项数＋`ls -1 orzmc-backup-*.tar.gz | wc -l` 必须为 1＋`df -h` 剩余；异常才展开报错原文。真数据（生产/不可重建）的保留策略与是否 `--stop` 仍需单独拍板。
- 临时快照/程序目录快照同样踩盘符坑：手工 `tar -czf E:/...` 也要 `--force-local`，否则静默产出 0 字节（`2>/dev/null` 时连报错都看不到）。
- 程序目录里没有 `doctor`/`cert`/`restore` 说明跑的仍是旧 Release：重跑 `install.sh` 升级（见 `deploy-layer-boundaries.md` §7），别去手改程序目录。
