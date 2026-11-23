# 升级包分类布局（三端核心 + 代理插件，含线上服同步）

> 2026-11-21 定稿。ADR-042：核心 jar 与插件**全部由 MCSM 面板实例持有**，升级 = 面板传文件 + 面板重启实例，
> 启动命令永远是 `sh /server/start.sh`。本文件只规定「包里怎么分类」和「哪一档进哪个实例」。

## 0. 落在哪

- 包目录：`E:/orzmc/packages/upgrade-<YYYYMMDD>/`（DATA_ROOT 下，与 `E:/orzmc-backups` 分开：包是待部署件，备份是回滚件）
- 包内只放**本批要变的件** + `MANIFEST.md` + `README.md`；未变组件在 MANIFEST 单列「本批不动」并写原因
  （例：`core/velocity/` 留空 + `README-本批不动.txt`，说明 4.3.2 只有 SNAPSHOT）
- 体积参考：Paper/Folia/Velocity 核心各约 42~56MB（Paperclip 自带库），Geyser 两档各 50MB → 一批约 300MB

## 1. 目录约定

```
upgrade-<YYYYMMDD>/
├── core/                       # 三端核心，同批评估、同批出包
│   ├── paper/paper-26.3-257.jar
│   ├── folia/folia-26.3-26.jar
│   └── velocity/velocity-4.3.1-45.jar     # 官方原名（带 build），面板直传不改名
├── plugins/
│   ├── proxy/                  # → 面板实例 Velocity 的 plugins/
│   │   ├── EaglerXServer.jar
│   │   └── Geyser-Velocity.jar
│   ├── paper/                  # → 面板实例 Paper 的 plugins/
│   │   ├── Geyser-Spigot-<build>.jar      # 直连模式要用，别剔除（见 §3）
│   │   ├── EaglerXPaper.jar
│   │   └── …（LuckPerms / ViaVersion / GrimAC …）
│   └── folia/                  # → 面板实例 Folia 的 plugins/
│       └── …
├── production/                 # 线上服专用档（{SERVER_HOST}），见 §4
├── MANIFEST.md                 # 每件：组件 / 当前版本 / 目标版本 / 来源 URL / sha256 / 回滚方式
└── README.md                   # 部署顺序 + 验证项（含「面板重启」不是 docker restart）
```

## 2. 出包规则

1. **三端核心同批**：`core/` 里 paper、folia、velocity 三个子目录要么都出、要么明确写「本批不动」。
   只升后端不评估代理是最常见的漏项——Velocity 与后端协议/插件（EaglerXServer、Geyser-Velocity）要一起核。
2. **代理插件单独一档 `plugins/proxy/`**：它进的是 Velocity 实例目录，不是后端 `plugins/`；
   放错档位是「档位看着都有、实例里却没生效」的典型成因。
3. **文件名一律官方原名**：核心 `paper-<版本>-<build>.jar` / `folia-…` / `velocity-<版本>-<build>.jar`；
   `start.sh` 用 `ls -1 <前缀>-*.jar | sort -V | tail -1` 选最高版本，**改名反而会选错版本**。
4. **MANIFEST 必填 sha256**：面板上传后没法一眼看出传的是不是那一件，哈希是唯一的对账凭据。
5. **回滚 = 把旧 jar 挪回实例根目录**（新 jar 移走 / 改名即可），启动命令不动。

## 3. Geyser 两份都要留（不要清理）

- `plugins/proxy/Geyser-Velocity.jar`：代理模式（ADR-036 后的常态，唯一公网入口 `orzmc-velocity`）。
- `plugins/paper|folia/Geyser-Spigot-*.jar`：**直连模式**（不经 Velocity，后端自己开 19132）。
  OrzMCDeploy 支持多部署模式，这两份是测试不同模式的必需品，删掉就没法回归直连/代理两种拓扑。
- 代理模式下 Geyser-Spigot 会打一条「behind a Velocity proxy」的 WARN 并自禁用，**属预期噪音**，不是故障、不清理。
- 出包时两份都要在 MANIFEST 里各自登记版本，避免「只升了代理侧、直连侧还是旧版」的漂移。

## 4. 线上服（production/）分类

线上服 `{SERVER_HOST}` 与测试服拓扑不同（无 Caddy/Nginx、装 EaglerXPaper、25565 只给明文 ws）：

- 只带 `core/paper/` + `plugins/paper/` + 该服特有件（EaglerXPaper 及其配置）；
- `core/velocity/`、`plugins/proxy/` 在该档 **标 `n/a`（不适用）**，不要静默省略——否则下次核对时无法区分「不需要」和「漏打」；
- 线上服没有面板托管时的落盘路径与重启方式写进 `production/README.md`（当前是手工覆盖 + 重启进程）；
- 灰度顺序：测试服跑稳 → 同批 jar 拷进 `production/` → 线上验证 Java/网页两个入口。
- 线上服若由 Exaroton 托管，写文件前服必须处于 **OFFLINE**；落地后 `GET` 回读 sha256 再 `DELETE` 旧 jar。

## 5. 件从哪来（下载 + 校验）

- **核心**：PaperMC **Fill API v3**（旧 `api.papermc.io/v2` 已 410 Gone）——
  `GET https://fill.papermc.io/v3/projects/{paper|folia|velocity}/versions/<MC版本>/builds` 返回**按时间倒序的 list**，
  只取 `channel == STABLE`；下载地址在 `downloads["server:default"].url`，官方 sha256 在 `checksums.sha256`。
  **字段名坑（写成脚本必踩）**：build 号的主键是 `id`（不是 `build`，`b["build"]` 直接 KeyError），
  版本列表 `GET /v3/projects/<project>` 返回的 `versions` 是 **dict（版本线 → 该线下版本号列表）**、首个 key 是最新线，
  不能当 list 取 `versions[0]`；脚本里应先取 key 再判断「当前版本线在不在里面」，不在才回落到最新线。
  实测 26.3 的 paper/folia 各约 55MB（Paperclip 已含依赖），比想象的大，别按 40MB 估剩余空间。
- **velocity 版本线**：`versions` 里带 `-SNAPSHOT` 的大版本号不是稳定线，稳定取不带后缀的最高版本；
  线内只有 1 个 build 时（如 4.3.1-45）直接写「本批不动」，不要把 SNAPSHOT 当新版本报给老板。
- **插件**：Modrinth `GET https://api.modrinth.com/v2/project/{slug}/version` —— **同一 `version_number` 会按 loader
  重复出现多条，每条有独立的 version id 与 CDN 路径**（Geyser 的 velocity / paper+spigot / neoforge / fabric / bungeecord 各一条）。
  拿 velocity 那条的 id 去拼 `Geyser-Spigot.jar` 的地址，CDN 会回 `403 OnDemandMigrationSourceStatus`（XML 正文里一个 403），
  看着像封禁/限流，其实是 id 与文件名不匹配 → **永远按 `files[].filename` 精确匹配选条目**，别用数组下标。
- **校验**：Paper 直接比官方 sha256；Modrinth 只给 `sha512`/`sha1` → 用 sha1 比（够用），MANIFEST 里记自算 sha256。
  落盘后再 `zipfile.is_zipfile()` 过一遍：CDN 断流会留下「体积看着差不多」的残包。
- **下载通道**：`export HTTPS_PROXY=http://127.0.0.1:7897`，`curl -sL --retry 3 --max-time 400 -o <目标>`；
  **`-o` 必须写原生正斜杠绝对路径**（`E:/orzmc/packages/...`），传给原生 curl 的 `/tmp` 或 `/e/...` 会报
  `client returned ERROR on write`（不是网络问题）。Python `urllib` 下 50MB 级文件容易撞 300s 工具超时 → 大件优先 curl。

## 6. 自动化流水线（`scripts/orzmc_upgrade_sync.py`，2026-11-21 起并入周一 cron）

一条命令跑完「检测 → 出包 → 测试服三实例 → 验收 → S: 交接件 → Exaroton 同步 → 清理旧包」：

```bash
python %LOCALAPPDATA%/hermes/scripts/orzmc_upgrade_sync.py --dry-run   # 只看差异
python %LOCALAPPDATA%/hermes/scripts/orzmc_upgrade_sync.py --require-idle  # cron 用：有玩家在线只出包不重启
python %LOCALAPPDATA%/hermes/scripts/orzmc_upgrade_sync.py --force     # 演练：即使已最新也重跑全链
python ... --exaroton-only | --skip-exaroton | --no-clean | --paper-only
```

行为约定：
- **版本判定**：Paper/Folia 取 Fill API 当前版本线的最高 `STABLE` build（不自动跳版本线，跳线只在报告里提示）；
  Geyser 取 Modrinth 最新 `2.12.1-bXXXX`，比较的是 `b` 后的 build 号（**不是整串数字**，否则 `2.12.1-b1306`
  会被当成 21211306 误判成"有新版"）。
- **下载校验**：Paper 用 Fill 给的 sha256、Geyser 用 Modrinth 的 sha1，逐件比对后才落盘；包里同名同哈希则跳过。
- **部署**：直接写实例目录（daemon 容器 bind mount，等价于面板上传）→ 删后端旧 `Geyser-Spigot-*`（先备份到
  `E:/orzmc-backups/pre-upgrade-<日期>/<实例>/`）→ **面板 API stop/open**（禁 docker restart）。
- **验收**：等 `logs/latest.log` 出现 `Done (`、目标版本串、`Geyser 2.12.1-bXXXX`；超时或缺失记 ⚠️ 并停在上线前。
- **Exaroton**：只有测试服验收通过才同步；服务器非 `status=0(OFFLINE)` 一律不动，上传后 `GET` 回读 sha256 比对，
  再删旧同名件；**不擅自开服**。核心由 Exaroton 软件版本通道管，不传 jar。
- **S: 交接件**：`S:/orzmc-upgrade/upgrade-<日期>/`（core/paper、plugins/paper + n/a 档 + MANIFEST/README）。
- **清理**：`E:/orzmc/packages` 与 `S:/orzmc-upgrade` 下只留本次 `upgrade-<日期>`，其余 `shutil.rmtree`（`--no-clean` 可关）。
- **在线人数守卫**：`--require-idle` 用 `mc_ping_probe.mc_status("127.0.0.1", 25565)["players"]["online"]` 判断，
  有玩家时**只出包+报告、不重启实例**（无人值守重启会把在线玩家踢掉）；探测失败视为未知、不阻断。
- **已有 jar 不覆盖**：除目标版本与 Geyser 同名替换外一律不动；旧核心 jar 留在实例目录做回滚，
  `orzmc_selfcheck.py` 对"版本低于基线"的 jar 显示 ℹ️ 旧版保留、不计漂移。

## 7. 写/改这条流水线的六个坑（都实测踩过）

1. **验收 needle 必须抄真实日志串，别按版本号拼**。实际打印是：
   Paper `This server is running Paper version 26.3-257-main@…`（**没有** `build 257` 这种串）、
   Folia `Folia version 26.3-26-…`、后端 Geyser `[Geyser-Spigot] Loading server plugin Geyser-Spigot v2.12.1-SNAPSHOT`
   （**后端侧不带 build 号**，只能用 `Geyser-Spigot v<major.minor.patch>`）、Velocity 侧才有完整 build
   `Loaded plugin geyser 2.12.1-b1306`。needle 写错会每次验收都 ❌、周报天天"有异常"——先 `grep` 现装 `latest.log`
   确认字样，再写进脚本。
2. **面板 uuid 保持实例目录名原样（小写）**。`os.path.basename(inst_dir).upper()` 去查 `instance?uuid=` 会拿到空
   data、`status=None`，表现为「启动超时」而实例其实早就起来了。取目录名直接用，别做大小写变换。
3. **状态读不到 ≠ 启动失败**。轮询 `status=3` 超时就回退看 `logs/latest.log` 有没有 `Done (`，有就算成功并记
   ℹ️（status 不可读），只有日志也没有才记 ⚠️。同理 `protected_instance/stop` 后 status 常停在 1/2 不归零 ——
   `open` 是幂等的，直接 open 并记一条 ℹ️，不要判整个流水线失败（否则全绿的批次会被写成"有异常"）。
4. **跳过下载时要回填待部署件清单**。包内已有同哈希件时下载会跳过，`got` 变空 → S: 导出与 Exaroton 同步会静默
   什么都不做（MANIFEST 只剩半张表、线上"未执行"）。任何"包已存在则跳过"的分支都必须从包目录把件名扫回来
   （`core/paper/paper-*.jar`、`plugins/proxy/Geyser-Velocity*`、`plugins/paper/Geyser-Spigot-*`）再往下走。
5. **所有退出路径必须吐同一套结构化输出**。这脚本是周一报告（`no_agent`）的第四段，父脚本按
   `## 升级流水线` + `### 版本与取证` + `### 动作` + `STATUS_LINE:` 解析结论。"无变更 / 有玩家在线跳过 / 全绿"
   三种提前 return 若只 `print` 几行裸文本，父报告那条就显示「段无有效结果」并把整份报告判成 ❌。
   做法：所有分支收口到一个 `emit(status_ok, note)`，先填 `EV`/`ACTIONS`/`WARN` 再调它；新增分支时不许自己 `print`。
6. **扫实例目录判"现装版本"要取最高版**，别用 `glob` 第一个命中：ADR-042 不删旧 jar，目录里常同时躺着
   `paper-26.3-253.jar` 与 `paper-26.3-257.jar`，而 `start.sh` 用 `sort -V | tail -1` 跑的是最高版。
   取首个命中会报「现装 253、落后 4 个 build」这种假告警，还会连带生成假的升级待办。
