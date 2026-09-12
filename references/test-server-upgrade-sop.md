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
- **插件 jar**：`POST /api/files/upload?upload_dir=/plugins/update` 取凭据 → `POST {addr}/upload/{password}` multipart。
  ⚠️ 凭据返回的 `addr` 可能是 **`wss://mcs-node.{SERVER_NAME}.cn:443`**（不是 localhost:24444）→ 拼 `https://host/upload/<pwd>`。
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

## 3. 机制与坑

1. **MCSM 面板/API stop 会置 `eventTask.ignore=true` 并落盘** → `autoRestart` 名存实亡（下次 daemon 重启内存复位，但磁盘仍 true）。测试实例本就手动启停，影响可控；如需恢复须改 Windows 侧 `InstanceConfig/<uuid>.json`。
2. **`download_from_url` 是 daemon 侧异步任务**：投递大文件（64MB 核心）后要等 20~30s 再启动，避免半包。
3. **读文件两步法**：`POST /api/files/download` 签发凭据（同账号 3s 限流，脚本内串行 + sleep 3.2~3.6s）→ `GET {addr}/download/{pwd}/{文件名}`。
4. **别用 `nohup` 起长任务**（Hermes 禁 shell 后台包装）→ 用 `terminal(background=true, notify_on_complete=true)`。
5. **回读失败≠投递失败**：启动后 `update/` 被消费 → 以「插件版本日志 + `plugins/` jar sha」为准。
6. **第三方插件无需人工迁配置**：Geyser/LuckPerms/AxGraves/EssentialsC/SCore/ExecutableEvents 本次升级前后配置**逐字节无变化**（或仅注释里的版本号变化）→ 它们的 schema 未变；有捆绑默认的可用配置合并工具做缺键兜底检测。
7. **GriefPrevention3D 无 `config.yml`**（默认生成在 `GriefPreventionData/`），别在 `plugins/GriefPrevention3D/` 找配置。
