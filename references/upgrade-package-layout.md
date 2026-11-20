# 升级包分类布局（三端核心 + 代理插件，含线上服同步）

> 2026-11-21 定稿。ADR-042：核心 jar 与插件**全部由 MCSM 面板实例持有**，升级 = 面板传文件 + 面板重启实例，
> 启动命令永远是 `sh /server/start.sh`。本文件只规定「包里怎么分类」和「哪一档进哪个实例」。

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
