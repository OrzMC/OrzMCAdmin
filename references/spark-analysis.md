# Spark 性能分析（Paper 内置）

> PaperMC 1.19+ **内置 Spark**，直接 `/spark` 命令即可，**不要另装插件**。卡顿排查首选。

## 命令速查

| 命令 | 用途 |
|:----|:----|
| `/spark health` | 一键健康报告（TPS/MSPT/CPU/内存/磁盘）|
| `/spark tps` | TPS 历史（5s/10s/1m/5m/15m）|
| `/spark profiler --timeout 60` | CPU 采样，生成报告链接 |
| `/spark profiler --timeout 60 --only-ticks-over 100` | 只采卡顿 tick（>100ms）|
| `/spark tickmonitor` | 实时 tick 监测（卡顿 tick 时长+增幅）|
| `/spark gc` | GC 统计（Young/Concurrent/Old 次数+时长+频率）|
| `/spark heapsummary` | 堆内存对象分布（.sparkheap 需 viewer 解析）|
| `/spark healthreport --upload` | 上传健康报告 |

## 读取报告数据（关键技巧）

- **报告链接后加 `?raw` 直接得 JSON**（2026-08-03 实测）：
  ```bash
  curl -sL "https://spark.lucko.me/{code}?raw" -o report.json
  # metadata.systemStatistics → CPU/内存/GC/磁盘/Java 参数
  # metadata.platformStatistics → tps/mspt/memory 均值+峰值
  # metadata.platformStatistics.world → 全服实体统计（totalEntities + entityCounts 按类型）！
  ```
- **`world.entityCounts` 是全服实体精确构成**（一次 profiler 顺带拿到，无需计分板）：`{totalEntities, entityCounts: {bat: ..., glow_item_frame: ...}}`——按类型精确计数，适合评估实体负载
- 报告页是 Next.js SPA（无内嵌数据），**必须用 `?raw`** 拿数据
- profiler 完成后控制台输出 `https://spark.lucko.me/{code}` 链接
- ⚠️ `?raw` 只含 metadata + platformStatistics，**无 classContributions/threads 采样明细**（`"threads":24` 是 CPU 核数）

## 判断标准

| 指标 | 健康 | 需关注 | 严重 |
|:--|:--|:--|:--|
| TPS | 20.0（满帧）| <19 | <15 |
| MSPT 中位 | <50ms | 50-60ms | >60ms |
| MSPT 95% | <60ms | 60-100ms | >100ms |
| 内存占用 | <70% | 70-85% | >85% |
| 磁盘 | <80% | 80-90% | >90% |

## 典型诊断流程（卡顿排查）

1. `/spark health` 看整体
2. 内存高跑 `/spark gc` 看 GC 频率：Young 每 <30s 满 = 堆太小；Old 有 Full GC = 泄漏/堆不足
3. TPS 低但 CPU 低（<10%）= **主线程被阻塞**（实体 AI/插件同步/GC）
4. `/spark profiler --only-ticks-over 100` 采 60-90s → `?raw` 分析热点
5. `/spark tickmonitor` 持续观察

## 踩坑（2026-08-03 实测）

- ⚠️ **Windows 服务器 async-profiler 不可用**，自动降级 built-in Java 引擎（功能正常）——日志提示属正常
- ⚠️ **`/spark activity` 报 `NoClassDefFoundError: net/kyori/examination/Examinable`**：内置 Spark 1.10.152 bug——用 profiler/tickmonitor 替代
- ⚠️ `/spark exporter` 不是子命令（打印帮助）；导出用报告链接 `?raw` 即可
- ⚠️ heapsummary 生成的 `.sparkheap` 是二进制 protobuf，需官方 viewer 解析
- ✅ profiler 有采样开销，选玩家少时段；tickmonitor 先跑 6s 基线后持续报告卡顿 tick
