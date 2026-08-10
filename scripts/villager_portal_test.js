#!/usr/bin/env node
// 本地测试服实体传送门复现脚本（2026-08-09 实测有效）
// 用法: node villager_portal_test.js [X Y Z]   （默认 200 70 200）
// 前提: 本地 Paper 服运行中（127.0.0.1:25565），~/minecraft-bot 有 mineflayer 依赖
// 依赖: HermesBot 账号 + $e 控制台通道（/orzdebug $e，无需 op 权限）
// 流程: 拆旧门 → 建标准 4×5（内 2×3）→ kill 旧村民 → summon 普通村民 → 等 8s → mineflayer 扫描验证
// 注意: 不要用 $e data get / 复杂 @e 选择器（引号/逗号被拆坏报 CommandException）——验证用 bot.entities 扫描
const mineflayer = require('mineflayer');
const bot = mineflayer.createBot({
  host: '127.0.0.1', port: 25565, username: 'HermesBot',
  version: '1.21.11', auth: 'offline', hideErrors: true,
});
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const X = Number(process.argv[2] || 200);
const Y = Number(process.argv[3] || 70);
const Z = Number(process.argv[4] || 200);

bot.once('spawn', async () => {
  await sleep(2500);
  bot.chat('/login {BOT_PASSWORD}');
  await sleep(3500);
  bot.chat(`/orzdebug $e tp HermesBot ${X} ${Y} ${Z}`);
  await sleep(3000);
  console.log('--- 拆旧门 ---');
  bot.chat(`/orzdebug $e fill ${X} ${Y} ${Z} ${X + 3} ${Y + 4} ${Z} minecraft:air`);
  await sleep(2000);
  console.log('--- 建标准 4x5（内 2x3，最小有效尺寸）---');
  bot.chat(`/orzdebug $e fill ${X} ${Y} ${Z} ${X + 3} ${Y} ${Z} minecraft:obsidian`);
  await sleep(1500);
  bot.chat(`/orzdebug $e fill ${X} ${Y + 4} ${Z} ${X + 3} ${Y + 4} ${Z} minecraft:obsidian`);
  await sleep(1500);
  bot.chat(`/orzdebug $e fill ${X} ${Y + 1} ${Z} ${X} ${Y + 3} ${Z} minecraft:obsidian`);
  await sleep(1500);
  bot.chat(`/orzdebug $e fill ${X + 3} ${Y + 1} ${Z} ${X + 3} ${Y + 3} ${Z} minecraft:obsidian`);
  await sleep(1500);
  bot.chat(`/orzdebug $e fill ${X + 1} ${Y + 1} ${Z} ${X + 2} ${Y + 3} ${Z} minecraft:nether_portal`);
  await sleep(2000);
  console.log('--- 清理旧村民 + 召唤普通村民（门中心，勿用 NoAI）---');
  bot.chat('/orzdebug $e kill @e[type=villager]');
  await sleep(2000);
  bot.chat(`/orzdebug $e summon villager ${X + 1} ${Y + 2} ${Z}`);
  await sleep(3000);
  console.log('--- 等 8 秒观察传送 ---');
  await sleep(8000);
  // 验证：tp bot 回测试点扫描实体（不用 data get）
  bot.chat(`/orzdebug $e tp HermesBot ${X} ${Y} ${Z}`);
  await sleep(4000);
  let v = 0;
  for (const e of Object.values(bot.entities)) {
    if ((e.name || '').toLowerCase().includes('villager')) {
      v++;
      console.log('VILLAGER:', Math.round(e.position.x), Math.round(e.position.y), Math.round(e.position.z));
    }
  }
  console.log(v === 0
    ? '主世界测试点无村民 → 已传送 ✅（若之前有「实体传送被禁用」日志=插件拦截，本次无=修复生效）'
    : `主世界村民数: ${v} → 未传送（检查插件 EntityTeleportEvent 拦截 / 传送门结构）`);
  // 清理测试产物
  bot.chat('/orzdebug $e kill @e[type=villager]');
  await sleep(1500);
  bot.chat(`/orzdebug $e fill ${X} ${Y} ${Z} ${X + 3} ${Y + 4} ${Z} minecraft:air`);
  await sleep(2000);
  console.log('CLEAN_DONE');
  bot.end();
  process.exit(0);
});
bot.on('kicked', (r) => {
  // tp 进传送门时被踢可能是玩家自身被传送（维度切换）——若测试目标只是村民则忽略
  console.log('KICKED:', JSON.stringify(r).slice(0, 80));
  process.exit(1);
});
setTimeout(() => process.exit(1), 70000);
