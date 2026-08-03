# PaperMC 版本与构建机制（2026-08 实测）

## 下载机制（重要！）

- ⚠️ **旧 API `api.papermc.io/v2` 已完全废弃（410 Gone / sunset）**，所有版本列表/构建端点失效——**不要再用 v2**
- ✅ **新机制（唯一正解）**：官网下载页 `https://papermc.io/downloads/paper` 内嵌每个构建的 sha256 → 直链 `https://fill-data.papermc.io/v1/objects/{sha256}/{jar名}` 下载
- `scripts/parse_papermc.py` 已封装：`curl -s https://papermc.io/downloads/paper | python3 parse_papermc.py` → 输出 `paper-{版本}-{构建}.jar {sha256}`
- 下载后校验：`shasum -a 256 paper-*.jar` 与页面值一致

## Java 版本要求

- **PaperMC 26.x 需要 Java 25**（LTS）
- 老版本 PaperMC 需要旧 JDK（如 1.20.x 用 Java 17/21）
- 多版本共存时用 `PAPER_JAVA` 指定

## 版本命名

- 格式：`paper-{MC版本}-{构建号}.jar`（如 `paper-26.2-92.jar`）
- 通道：STABLE（稳定）/ EXPERIMENTAL（实验）
- 升级时注意跨版本世界转换：26.1→26.2 首次启动会自动转换世界（`Starting upgrade for world`，启动耗时明显变长），确认无玩家时段操作

## 升级流程（local）

1. `parse_papermc.py` 获取最新版
2. 备份旧 jar 到 `backups/paper-{ver}-{build}.jar`
3. 下载新 jar（sha256 校验）
4. 移除旧 jar → 同步 start.sh → 重启
5. 验证日志出现 `Done (Xs)!`

## 插件机制

- **plugins/update/ 热更新**：新 jar 放入 → 重启时 PaperMC 自动原子替换同名插件 → update/ 自动清空
- **插件升级无需备份 jar**（官方源 Modrinth/Hangar 可重下）
- **插件对齐判定 = sha256 对比**（文件名相同 ≠ 内容相同）
- 插件必须匹配 MC 版本（Modrinth API 用 `game_versions` 过滤）
