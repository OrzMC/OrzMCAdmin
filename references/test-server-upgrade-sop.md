# 测试服 jar 升级 + 配置迁移 SOP（2026-09-12 实测沉淀）

> 适用：mcs.{SERVER_NAME}.cn 上的两个测试实例 **`papermc-test`**（716c2fb7，Paper）与 **`folia-test`**（8A932DD4，Folia）。
> 目标：把核心 + 全部插件升到目标渠道最新版，并把**配置文件按新版定义迁移**（缺键补齐、旧自定义值保留），最后清理所有备份残留。
> 全部操作用 MCSM API 完成（面板栈在 **Windows E:/orzmc**，Mac 端 `/Users/Shared/orzmc/...` 只是历史副本，**勿再直读**）。

## 0. 前置事实（2026-09-12 实测）

| 项 | 现状 |
|:--|:--|
| 面板 | `https://mcs.{SERVER_NAME}.cn/`，凭据 `~/.hermes/.env` 的 `MCSM_LOCAL_*`；daemon `fbb3492c...` |
| paper 实例 | docker 型，`eclipse-temurin:25-jre`，`java -Xms4G -Xmx4G -jar paper.jar nogui`，端口 `25565:25565/tcp` + `19132:19132/udp`，autoStart/autoRestart 均 false |
| folia 实例 | 同上，`-Xms2G -Xmx2G -jar folia.jar nogui`，端口 `25566:25565/tcp` + `19133:19132/udp` |
| 两实例 | **各自独立地图**，可同时启动；冷启动 Done ≈ 90~155s |
| paper 特有点 | `im.yml` = `backend: builtin`（含 QQ/飞书凭据）；`i18n.default_lang: en-US` |
| folia 特有点 | `im.yml` = `backend: easybot`（默认值）；`i18n.default_lang: zh-CN` |

> ⚠️ **双实例差异是刻意设计（老板 2026-09-12 明确确认，勿"统一修复"）**：
> - **paper = 英文语言包 + builtin 直连**（专用于验证 i18n 英文包与内置直连通道）；其群消息会以**英文**推送，`default_lang: en-US` 属预期，**不要改回 zh-CN**。
> - **folia = easybot 网关 + zh-CN**（验证网关通道）。
> - 两条 IM 通道**并行保留**（A/B 覆盖），不要合并成单通道。
> - 副作用须知：两实例的飞书通知目标**指向同一个群**（paper `player_group` == folia `admin_group` = `oc_00eb…`），因此该群会同时收到两台服消息（paper 侧英文）；如需降噪应改目标群而非改语言/通道。
> - `default_lang` 作用面（源码实证 `I18nService`）：`langFor(Player)` **跟随客户端 locale**（玩家游戏内文案不受影响）；`default_lang` 只管**群事件通知 / 控制台广播 / 维护文案 / Bot 交互兜底**。

## 1. 升级流程（六步）

```
① 抓产物本地校验 → ② 实例内备份(临时) → ③ 投递 → ④ 首启动触发迁移 → ⑤ 配置补键/改值 → ⑥ 二次启动验收 → ⑦ 清理备份
```

### ① 抓产物 + 本地 sha 校验
```bash
python3 - <<'EOF'   # 见本次实录：Modrinth/Hangar/Geyser API/metadata.luckperms.net 全部取直链 + 哈希
EOF
```
- Modrinth 版本接口给 **sha512**（`files[].hashes.sha512`）；Hangar 给 `fileInfo.sha256Hash`；Geyser 给 `downloads.spigot.sha256`；LuckPerms 走 `metadata.luckperms.net/data/all` 的 `downloads.bukkit`（无哈希，官方渠道直链）。
- **Paper 核心用 fill-data 内容寻址直链**：`https://fill-data.papermc.io/v1/objects/<sha256>/paper-26.2-123.jar` —— URL 自带哈希，投递后自带完整性保证。
- 渠道查询：`scripts/parse_papermc.py [paper|folia]`（页面内嵌 JSON → 最新 STABLE + sha256）。

### ② 实例内备份（临时，验收后删）
```python
req(inst,"POST","/api/files/mkdir",{"target":"/upgrade-bak-YYYYMMDD"})
req(inst,"POST","/api/files/copy",{"targets":[["/plugins/X.jar","/upgrade-bak-YYYYMMDD/X.jar"], ...]})
```
- `copy` 的 `targets` 是**二维数组** `[[源,目标],...]`，一次调用可批量；核心 jar 也一并复制。
- 校验：备份目录 `list` 实读文件数 == 计划数。

### ③ 投递
- **核心 jar**：`POST /api/files/download_from_url {"url":<fill-data直链>,"file_name":"/paper.jar"}` ——
  ⚠️ **实测可覆盖已存在文件**（先写 0 字节文件再投递同名 URL → 覆盖成功），所以旧 jar 必须先 copy 到备份目录。
- **插件 jar — ⚠️⚠️ 2026-10-05 起：上传通道不可用，统一走 daemon 直传**
  - ❌ `POST /api/files/upload?upload_dir=/plugins/update` 取证 → `POST {addr}/upload/{password}` multipart **实测全线失败**：凭据 `addr` 现为 **`wss://mcs-node.{SERVER_NAME}.cn:443`**（不是 localhost:24444），https 化后仍 **403 Forbidden**，部分文件报 `Broken pipe`。**别再在这条路上浪费重试**
  - ✅ **标准做法 = `POST /api/files/download_from_url`** body `{"url":官方直链,"file_name":"/plugins/update/<文件名>.jar"}` —— 2026-10-05 实测 **7 个文件（含 47MB Geyser）全部 200 一次成功**；小件同样适用，比 upload 更稳
  - ✅ 投递后 **sha256 回读验收**（`POST /api/files/download` 签发 → `GET {addr}/download/{pwd}/{文件名}`，`wss://` 换 `https://`，`localhost` 换面板主机名）——本次 7/7 与本地一致。同账号签发限流 3s/次，**串行 + sleep 3.2~3.6s**
  - 📌 老版本 upload 通道的「addr 拼 https://host/upload/<pwd>」写法保留在此仅作历史参考，勿再使用
- 投递后**立即回读校验**（`mcsm_download` 拉回 + sha256 比对本地）：本次 paper 4 个 + folia 8 个插件全部 OK。
- ⚠️ **回读要赶在服务器启动前**——启动后 `plugins/update/` 会被消费（文件移走），回读报「回读失败」是假故障。

### ④ 首启动（触发插件自带配置迁移）
- `GET /api/protected_instance/open` 启动；轮询 `latest.log` 等 `Done (`。
- OrzMC 会打**配置升级**日志（示例）：
  `配置升级: config.yml schema legacy(config-version=2) → 14，新增默认键 13 个：i18n+1 bot+3 geoip+1 prison+1 gamemode-correction+3 update+4，旧默认翻转 5 项：...，保留自定义 1 项：entity_teleport_whitelist`
  `配置升级: templates.yml ... 正文迁移（删键走语言包/翻直通壳） 33 项`
  `配置升级: easybot.yml ... 新增默认键 1 个：config-version+1（原文件已备份为 easybot.yml.bak）`
- ⚠️ **新规范**：1.0.24+ 起模板正文迁到语言包（`jar 内 messages/messages_zh-CN.yml`），templates.yml 只剩「直通壳 `{message}` + 格式表 + 配色 + 数据键」→ 旧默认正文被删键是**正常零回归**（语言包同文案），自定义正文保留。
- ⚠️ **easybot.yml 的 `cmd_prompt_char`/`discord_server_link`/`qq_group_id` 是 v12 前遗留键**：插件会自动迁到 `config.yml bot:` 并**删除**旧键（`ConfigService.migrateBotParamsToConfig`）→ **不要手工补回**，补了下次启动也会被清掉。

### ⑤ 配置补键 / 改值（`scripts/config_merge_defaults.py`）
```bash
# 1) 从新 jar 提取默认定义
python3 ~/.hermes/skills/gaming/orzmc/scripts/config_merge_defaults.py --extract OrzMC-1.0.25-dev.416.jar --extract-dir defaults/
# 2) 预览缺键（只读）
python3 .../config_merge_defaults.py --default defaults/ --target <实例配置目录> --dry-run
# 3) 生成合并文件（新定义补键 + 旧值保留 + 注释保留，ruamel 往返）
python3 .../config_merge_defaults.py --default defaults/ --out to_upload/
```
- 语义：**新默认的键集为准**，缺失键按新默认补；**既有键一律保留实例值**（自定义优先）；实例独有的键**不删**（运行时数据如 `permission.yml reviews.requests.*` 会保留并报告）。
- 写回实例：`PUT /api/files/?daemonId=&uuid=` body `{"target":"/plugins/OrzMC/config.yml","text":"<全文>"}`（**只能写已存在文件**；body 字段名是 `text`）。
- 写后回读 + 关键值断言（本次：folia `update.channel=beta`、`bot.qq_group_id=1082305302`；paper im.yml 四平台段齐全且凭据保留）。
- 三端/双实例常见待改：**OrzMC `update.channel`**（dev 验证机应为 `beta`；`release` 只收正式版）。

### ⑥ 二次启动 + 验收清单
- [ ] 核心行：`This server is running Paper version 26.2-123-main@...` / `Folia version 26.2-7-...`
- [ ] 各插件 `Enabling X vY` 与目标版本一致
- [ ] `Could not load plugin` / `SEVERE` / `not marked as supporting` = 0 条
- [ ] `plugins/update/` 已清空；`plugins/` 内 jar 名 = 新版本名
- [ ] **jar sha256 回读比对**（最终权威证据，比日志版本号可靠——Geyser 日志只打 `2.11.2-SNAPSHOT`）
- [ ] OrzMC `配置健康检查` 无**新增**告警（历史建议项：`easybot.api_server` 明文、`qq.admin_dm` 未配置 → 非本次引入）
- [ ] OrzMC `自更新已启用（通道 beta，当前 vX）`

### ⑦ 清理备份（老板要求：不留堆积）
```python
req(inst,"DELETE","/api/files/",{"targets":["/upgrade-bak-YYYYMMDD", "/plugins/OrzMC/config.yml.bak", ...]})
```
删后必须 `list` 复核真的没了；本地工作目录（产物 + before/after 配置快照）一并删。

## 2. 本次（2026-09-12）实录结果

| 实例 | 核心 | 插件升级 |
|:--|:--|:--|
| papermc-test | Paper 26.2-121 → **26.2-123** | Geyser-Spigot 1233→**1235**、LuckPerms 5.5.81→**5.5.82**、voicechat 2.6.21→**2.6.23**、OrzMC 1.0.25-dev.415→**1.0.25-dev.416** |
| folia-test | Folia 26.2-7（部署 jar sha256 = 官方，**已最新**） | Geyser 1233→**1235**、LuckPerms 5.5.81→**5.5.82**、AxGraves 1.29.0→**1.31.0**、EssentialsC 4.2.8→**4.3.0**、GriefPrevention3D 18.3.4→**18.3.10**、ExecutableEvents 3.26.8.10→**3.26.9.9**、SCore 5.26.8.10→**5.26.9.9**、OrzMC 1.0.23→**1.0.25-dev.416** |

- 保持不升（已最新/既有决策）：EssentialsX 2.22.0、WorldEdit 7.4.5、WorldGuard 7.0.18、packetevents 2.13.0、**Via 系列 5.11.0（稳定版不升 SNAPSHOT）**、GriefPrevention 16.18.7、SkinsRestorer 15.12.5、F3F4Perms 1.3.0、GrimAC 2.3.74（比 GitHub release 新）、VaultUnlocked 2.20.2、SimpleLogin 1.16.7、本地打包的 EzShops 2.5.9/LoginSecurity 3.3.2/DeathChest 3.0.1/GetMeHome 3.0.2。
- 配置：paper 已 schema 14（无迁移，仅补 `im.yml` 平台段）；folia 由 legacy(2)→14（13 键补齐 + 5 项旧默认翻转 + templates 正文迁语言包），自定义 `entity_teleport_whitelist`(16 项) 与其 QQ 群号 `1082305302` 完整保留；两实例 `update.channel` 均 = **beta**。
- 待老板决策的观察项：paper `i18n.default_lang: en-US`（folia 是 zh-CN）→ paper 群消息/游戏文案走英文语言包。

## 2b. 2026-10-05 实录（第二轮升级 + 核心版本化落地）

| 实例 | 升级项 | 启动 |
|:--|:--|:--|
| papermc-test（Paper 26.2-129） | Geyser 1247→**1248**、LuckPerms 5.5.85→**5.5.87**、SkinsRestorer 15.12.5→**15.12.6**、OrzMC 1.0.28-dev.425→**1.0.29-dev.427** | Done 179s |
| folia-test（Folia 26.2-7） | Geyser 1247→**1248**、LuckPerms→**5.5.87**、SkinsRestorer→**15.12.6**、ExecutableEvents 3.26.10.2→**3.26.10.4**、SCore 5.26.10.2→**5.26.10.4** | Done 116s |

- AxGraves 1.32.1 已最新（巡检脚本报「查询失败」属误报）
- 交付：**全部走 `download_from_url`**，7 文件 sha256 回读 7/7 一致；`plugins/update` 启动后被消费（total=0）
- OrzMC 升级触发配置迁移 `config.yml schema 14 → 15`（新增 `tnt` / `exploit_hardening`，`entity_teleport_whitelist` 16→17 项），自动留 `config.yml.bak`
- 核心改名后验证：`latest.log` = `Paper 26.2-129` / `Folia 26.2-7`，根目录只剩 `paper-26.2-129.jar` / `folia-26.2-7.jar`
  （当日曾短暂使用带 `logs/start-script.log` 审计行的加强版脚本，当日即按老板要求精简为 4 行版 → 见 §2c；如需审计行可自行加回）
- **启动日志异常（新发现，勿重复排查）**：
  - 🔴 paper `[Essentials] You are running an unsupported server version!` —— EssentialsX 最新正式版 2.22.0（2026-05-31）**未适配 26.x**，main 分支已有 26.2/26.3 修复（26-08-05 起）但**未发版**。老板决策：**不上 dev 构建，等正式版**
  - 🟠 folia `[SimpleLogin] ProtocolLib not found → /login /register 明文写控制台`。**ProtocolLib 不可装**：Folia 相关 issue 全被关成 **not_planned**、最新 release 5.4.0 早于 26.x、26.2 仍有 open bug（#3660）、26.3 修复仅在 dev 提交。SimpleLogin 配置里**无隐藏开关**（已核对 config.yml）。替代只有迁 AuthMe（Modrinth `authmereloaded` loaders 含 folia）。老板决策：**保持现状**
  - 🟡 folia `duplicate keys found: chiseled_sandstone / chiseled_red_sandstone` —— **40+ 插件 yml 全扫未命中**，疑似 jar 内置资源；影响可忽略
  - 🟡 folia Geyser 报 `ViaVersion 过旧`（5.12.0 已是最新正式版，只 SNAPSHOT 更新 → 按纪律不动）
  - ⚪ 既有噪音：offline mode / root 用户 / spark 统计超时 / EzShops 菜单 `slot -1` 越界 / GrimAC+ViaBackwards 组合提示
- **依赖插件核查结论**：packetevents 2.14.0 ✅、Vault/VaultUnlocked ✅、Via 三件套 ✅、SCore↔ExecutableEvents ✅、WorldEdit↔WorldGuard ✅；**唯一真缺口 = ProtocolLib**（见上）、唯一上游未适配 = EssentialsX
- 备份清理：删除陈旧 `/upgrade-bak-20260919`（paper 90.5MB + folia 36.9MB），保留 `/upgrade-bak-20261001`（paper 57.4MB + folia 60.4MB）

## 2c. 核心 jar 版本化命名 + `/start.sh`（2026-10-05 落地，两实例已生效）

**动机**：核心曾固定叫 `paper.jar` / `folia.jar`，文件名不含版本/构建号 → 无法判断跑的是哪个构建，版本巡检只能靠启动日志反推。

**现状（已落地）**：
- 启动命令（老板在面板改的，普通 apikey 改不了 → 见下方坑）：**`sh /server/start.sh`**
- 实例根目录核心：`paper-26.2-129.jar` / `folia-26.2-7.jar`（**真实版本名**）
- `/start.sh` 自动识别：优先 `{paper,folia}-*.jar`（`sort -V` 取版本最高），否则回退固定名

**每次核心升级的新流程**：投递 `paper-<新版本>.jar`（`download_from_url`）→ 删旧 jar → 重启；删旧前先 `copy` 到 `/upgrade-bak-YYYYMMDD/`

**脚本全文（2026-10-05 老板要求精简后的最终版，实例根目录 `/start.sh`，两实例仅 prefix 与内存不同）**：
```sh
#!/bin/sh
# MCSM 启动命令 = sh /server/start.sh ｜ 自动选版本化核心（版本最高），回退 paper.jar
J=$(ls -1 paper-*.jar 2>/dev/null | sort -V | tail -1)
exec java -XX:+UseG1GC -XX:MaxGCPauseMillis=100 -Dlog4j2.configurationFile=/server/config/log4j2.xml -Xms4G -Xmx4G -jar "${J:-paper.jar}" nogui
```
（folia 实例：`paper` → `folia`、`-Xms4G -Xmx4G` → `-Xms2G -Xmx2G`）

**精简取舍（4 行版 vs 初版 32 行，逐条已验证）**：
- ❌ 删 `cd /server`：MCSM docker 实例 cwd 本来就是 `/server`（原固定名命令直接跑通、日志里 `file:/server/libraries/...` 可证），无需 cd
- ❌ 删多 jar 计数/告警、找不到 jar 的显式报错、`[start.sh]` console echo：`sort -V | tail -1` 已保证取最高版本；echo 会被 MCSM 滚动缓冲吃掉，无实际价值
- ❌ 删 `logs/start-script.log` 审计落盘：核心版本以 `logs/latest.log` 的 `This server is running ...` + 根目录 jar 名双重核对即可
- ✅ **必须保留**：`sort -V | tail -1` 选版本化核心、`${J:-paper.jar}` 固定名回退、**`exec`**（不加 exec → MCSM 的 stop（stdin 注入 `stop`）失效，只能强杀）
- ✅ 精简版实测（4 场景 + 真实重启）：版本化 jar→选中；双版本→取最高；仅固定名→回退；都无→回退 `paper.jar`；两实例重启后 `latest.log` = `Paper 26.2-129` / `Folia 26.2-7`，零 start.sh 相关错误

**坑与验证要点**：
1. ⚠️ **`PUT /api/instance` 改实例配置对普通 apikey 是 403「密钥不正确」** → 启动命令变更**必须老板在面板做**（或换管理员 apikey）。文件类 API（touch/PUT/DELETE/move/list/download_from_url）普通 apikey 全可用。
2. 新建脚本文件：`POST /api/files/touch` `{"target":"/start.sh"}` → `PUT /api/files/` `{"target":"/start.sh","text":"<全文>"}`（PUT 只能写已存在文件；body 字段 `text`）→ 回读校验。
3. **切换顺序**：先让老板把启动命令改为 `sh /server/start.sh`（脚本含固定名回退，此时照跑 `paper.jar`）→ 再停服改名 → 启动验证。顺序颠倒会让现启动命令找不到 jar。
4. **`exec` 不能省**：不加 exec → MCSM 的 stop（stdin 注入 `stop`）失效，只能强杀。
5. ⚠️ **MCSM 的 `outputlog` 是滚动缓冲**（重启后可能只剩几十行）→ **`[start.sh]` 的 echo 会滚掉**，因此脚本额外落盘 `logs/start-script.log`（审计用）；核心版本以 `logs/latest.log` 的 `This server is running ...` 为准（`outputlog` 里可能已看不到该行）。
6. 验证清单：`logs/start-script.log` 出现 `使用核心: paper-26.2-129.jar`；`latest.log` 的版本行与 jar 名一致；根目录只剩一个核心 jar；`sh -n` + 4 场景（单版本化 / 双版本化取最新 / 仅固定名 / 都没有报错退出 1）。
7. 附带收益：`mc_version_check.py` 可**直接读文件名**判定已部署核心版本（此前 folia 只能靠日志反推）。

## 3. 机制与坑

1. **MCSM 面板/API stop 会置 `eventTask.ignore=true` 并落盘** → `autoRestart` 名存实亡（下次 daemon 重启内存复位，但磁盘仍 true）。测试实例本就手动启停，影响可控；如需恢复须改 Windows 侧 `InstanceConfig/<uuid>.json`。
2. **`download_from_url` 是 daemon 侧异步任务**：投递大文件（64MB 核心）后要等 20~30s 再启动，避免半包。
3. **读文件两步法**：`POST /api/files/download` 签发凭据（同账号 3s 限流，脚本内串行 + sleep 3.2~3.6s）→ `GET {addr}/download/{pwd}/{文件名}`。
4. **别用 `nohup` 起长任务**（Hermes 禁 shell 后台包装）→ 用 `terminal(background=true, notify_on_complete=true)`。
5. **回读失败≠投递失败**：启动后 `update/` 被消费 → 以「插件版本日志 + `plugins/` jar sha」为准。
6. **第三方插件无需人工迁配置**：Geyser/LuckPerms/AxGraves/EssentialsC/SCore/ExecutableEvents 本次升级前后配置**逐字节无变化**（或仅注释里的版本号变化）→ 它们的 schema 未变；有捆绑默认的可用配置合并工具做缺键兜底检测。
7. **GriefPrevention3D 无 `config.yml`**（默认生成在 `GriefPreventionData/`），别在 `plugins/GriefPrevention3D/` 找配置。
