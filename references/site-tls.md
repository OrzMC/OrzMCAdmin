# 站点层 TLS 供给（`orzmc.sh site`，OrzMCDeploy v0.4.0 起）

## 为什么有这一层

ADR-027 之后项目本体**不带边缘层**：公网入口（Caddy + Let's Encrypt DNS-01）落在站点自备的两份文件里 ——
`$DATA_ROOT/compose.site.yaml`（caddy 服务定义）与 `$DATA_ROOT/site/Caddyfile`（站点块）。
这两份文件此前是**手抄**的：新增子域要复制整段 block，`flush_interval -1` 少一行＝WS 握手被攒住，
`header_up X-Real-IP` 少一行＝EaglerXServer `forward_ip=true` 直接拒连。`site` 把它们变成「一条声明生成」。

## 命令

```bash
cd /e/deploy/orzmc
./orzmc.sh -d E:/orzmc site init     # 从现有 Caddyfile 反推 SITE_ROUTES 写进 .env，确保 compose 受管区块存在
./orzmc.sh -d E:/orzmc site init --force   # 声明与落盘不一致时，用落盘反推结果覆盖声明（唯一会改 SITE_ROUTES 的情形）
./orzmc.sh -d E:/orzmc site render   # 只打印渲染结果，不落盘（review / diff 用）
./orzmc.sh -d E:/orzmc site apply    # 渲染 → caddy adapt 校验 → 备份 .bak-<ts> → 落盘 → caddy reload（热重载）
./orzmc.sh -d E:/orzmc site status   # 声明 vs 落盘是否一致 + 容器状态 + 交给 cert.sh 报证书天数
```

## 声明写法（`.env`）

```
SITE_ROUTES="域=上游|选项;域=上游|选项"
选项：ws（flush_interval -1，长连接必须）/ xrip（header_up X-Real-IP {remote_host}）/ encode（zstd gzip）
      wscheck（该域的 `/` 本身就是 WebSocket 入口，`status --probe` 会对它做 Upgrade 探测）
```

现网实证（四域，`site init` 自动反推出来的就是这个形状）：

```
SITE_ROUTES="mcs.{SERVER_NAME}.cn=mcsmanager-web:23333|encode,ws;
             easybot.{SERVER_NAME}.cn=easybot:8080|encode;
             dev.{SERVER_NAME}.cn=orzmc-velocity:25565|ws,xrip;
             music.{SERVER_NAME}.cn=host.docker.internal:8080|encode"
```

- 用 `|` 分隔选项而不是 `:`，因为上游本身含冒号（`host:port`），按最后一个冒号切会歧义。
- 走宿主发布端口的站点（如 vendor compose 管的 orzmusic）写 `host.docker.internal:<宿主端口>`：vendor 重建容器会丢手工 network connect，走宿主端口与重建解耦。
- **`ws` ≠ 「这个域是 WebSocket 入口」**：面板的 `ws` 只是终端长连接，对 `/` 发 Upgrade 会让上游直接 EOF。
  只有真·WS 入口（`orzmc-velocity:25565` 这类，Eaglercraft 浏览器客户端连的就是它）才加 `wscheck`；
  `site init` 反推时对 `velocity` 或 `:25565` 上游自动补这个标记，其余不加。
- 日志文件名按域名首段生成（`access-dev.log`、`access-mcs.log`）。与手写文件里的自定义名（如 `access-eagler.log`）不同名属正常，认名字时别当成丢站。

## 受管区块与不变量

- `compose.site.yaml` 里只重写 `# >>> orzmc:site:caddy` 与 `# <<< orzmc:site:caddy` 之间的区块；区块外的站点增量（velocity 的 `dns:`、easybot 的 `FEISHU_*`）**不受影响**。编码上分三支：有标记→改标记区；**无标记但已有手写 `^  caddy:` 服务→ `awk` 按「下一个 `^  <name>:` 或文末」边界就地替换整块**；两者都没有才插在 `services:` 之后。
- **绝不能「没有标记就再插一块」**：早期手抄的 `compose.site.yaml` 就带着手写 caddy 服务，插第二块会让 compose 报 `service "caddy" is duplicated`，整栈起不来。改这段逻辑前先在夹具（复制现网 `compose.site.yaml` + `site/Caddyfile`，`.env` 的 `DATA_ROOT` 指向夹具）上跑一遍，再 `python -c "yaml.safe_load(...)"` 断言 `services` 键唯一、`caddy` 只出现一次。
- 证书由 Caddy 自己续，ACME 状态在 `$DATA_ROOT/caddy/data` —— **本命令绝不改该目录，也绝不手工续期**。
- caddy 端口固定 `"443:443"`：运营商封的是**外网** 443，宿主内网 443 正常；公网由路由器「外网高位端口 → 宿主 443」映射。改成 `18443:443` 会让宿主 443 无人监听，路由器转发打到空端口。玩家地址写 `wss://<域>:<路由器外侧端口>`。
- 不碰 25565 的 Java 明文 TCP：在该端口开 TLS 会把 Java 玩家全部挡在外面。

## 改这个模块时踩过的坑（都是会静默出错的）

1. **`while read` 丢掉没有尾换行的最后一行**：`printf '%s' "$routes" | tr ';' '\n' | while read` 会让**最后一个域静默消失**（`site status` 里两边都少它，看着还挺「一致」）。一律 `printf '%s\n'`，或先用 `sed`/`awk` 末尾补换行。
2. **空 `{$ACME_EMAIL}` 让 `caddy adapt` 报得像语法错**：报错是 `parsing caddyfile tokens for 'email': wrong argument count … after 'email'`。校验容器里必须把 `.env` 的 `ACME_EMAIL` 与 `CF_DNS_API_TOKEN` 一起传进去（`-e ACME_EMAIL=… -e CF_DNS_API_TOKEN=…`），并在 `apply` 前置校验 `ACME_EMAIL` 非空，否则你会去改模板语法，越改越远。
3. **`reverse_proxy` 无选项时不要写空 `{ }`**：Caddy 接受，但和手写文件 diff 噪音大，review 时容易以为改错了。
4. **reload 失败要能自动回滚**：`caddy reload` 前先备份 `Caddyfile.bak-<ts>`；reload 失败就 `cp` 回备份再 reload 一次，然后非零退出并提示看 `docker logs orzmc-caddy`。只落盘不 reload＝文件改了但线上还是旧配置，最坑。
5. **校验失败必须不落盘**：渲染到 `Caddyfile.new`，`caddy adapt` 过了才 `mv`；失败直接删临时文件并报「原文件未动」。
6. **别用「文件逐字相同」判等价**：手写文件含大量注释与自定义日志名。比对用「去注释 + 压空白」的语义 diff（`grep -vE "^\s*#|^\s*$" … | sed 's/[[:space:]]\+/ /g'`），剩下只该有个位数 cosmetic 差异。
7. **`site init` 要区分「已一致」与「不一致」**：声明已存在就静默「保持不变」＝把「改了 Caddyfile 没改声明」这类漂移永久藏起来。三条分支：无声明→写入反推；与反推一致→报一致；不一致→**打印声明与反推两行原文并拒绝改**，提示 `--force` 才以落盘为准覆盖。
8. **dispatcher 里 `shift` 之后子命令的选项在 `$1`**：`local cmd="$1"; shift; case $cmd in init) site_cmd_init "${2:-}"` 永远拿到空值（`$2` 已是原 `$3`），表现是 `--force` 静默无效——症状与「分支没写」一模一样，别去怀疑 set_env_value。
9. **`wscheck` 探测失败的分级**：`000`（curl 无响应）＝TLS/反代通但上游把升级请求直接断开，判 WARN 并写明原因；`502/503` ＝上游根本没起，判 FAIL；`101` 才是 OK。把 `000` 判 FAIL 会在一切都正常时报红，久而久之探测结果就没人看了。

## `status --probe`：按真实协议验收（`lib/probe.sh`）

`docker ps` 全 Up + 面板 200 不等于「能玩」。`status --probe` 按真实协议逐项探，分区输出：

| 段 | 判据 | 典型失败含义 |
|:--|:--|:--|
| 面板 / EasyBot | `curl` 200 | 容器在但进程崩 |
| Velocity / Geyser | TCP 连得上 | 端口没发布 / 代理没起 |
| 站点域 TLS+HTTP | `curl -sk --resolve <域>:443:127.0.0.1` 得 200/404 | `000`=TLS 或 Caddy 挂；`502`=上游没起（404 是上游活着且没有该路径，属正常） |
| ws（仅 `wscheck` 域） | Upgrade 请求 101 | `502` 上游没起；`000` 上游断开握手 |
| 实例 | daemon 内 `java` 进程数 | 0 = 平台在跑、世界没在跑（`autoStart=false` 的必然结果） |

- TLS 一律 `--resolve <域>:443:127.0.0.1` 打回环，**绕开 DNS/DDNS/路由器**：这样失败才能归因到本机，而不是「可能运营商」这种无法行动的说法。
- **本机回连自己的 LAN IP 不可靠**（Windows 上 `192.168.x.x:23333` 会让整条命令挂到超时）→ 凡「经 LAN IP」的探测都只算 WARN，回环才是硬指标（FAIL 时 exit 1）。
- 探测本身是只读的，可以随时对现网跑；但**别用 `bash -c '...'` 一行串起来跑**（多引号嵌套 + 审批拦截会把整轮排查打断），把探测写成脚本文件再 `bash 文件`。

## 上线顺序（这个模块动的是入口，别在现网直接试）

1. 造沙箱：`E:/sitetest` 放一份 `.env`（`DATA_ROOT` 指向它、`CF_DNS_API_TOKEN`、`ACME_EMAIL`）＋ `site/Caddyfile` 从现网拷过来。
2. 沙箱里跑 `site init`（验证反推对不对）→ `site render` → `site apply`（验证校验/落盘/热重载）。
   注意 `apply` 末尾的 `caddy reload` 打到**真容器**上、读的是真挂载文件，沙箱跑不会污染现网配置，但别在沙箱里改真文件。
3. 与现网做语义 diff，确认差异只剩 cosmetic 项，再对现网执行一次 `site init` → `site apply`。
4. 回滚：`site/Caddyfile.bak-<ts>` 在手，`cp` 回去 + `caddy reload` 即可；`compose.site.yaml.bak-<ts>` 同理。
