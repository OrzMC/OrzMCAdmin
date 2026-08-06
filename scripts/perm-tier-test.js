// 权限分级测试：三档 bot 自动测试权限系统（default/member/builder）
// 用法: cd ~/minecraft-bot && node perm-tier-test.js <端口>
// 前置: 三个测试账号需在白名单 + 已分配 LP 组（TestNewbie→default, TestMember→member, TestBuilder→builder）
// 判定: 命令输出"你没有使用该命令的权限"=被拒(❌)；无拒绝消息=执行成功(✅)；Unknown=命令本身不存在
const mineflayer = require('mineflayer');
const path = require('path');

const PORT = parseInt(process.argv[2] || '25565');
const HOST = '127.0.0.1';
const BOTS = {
  TestNewbie:   { group: 'default', password: 'NewbiePass123' },
  TestMember:   { group: 'member', password: 'MemberPass123' },
  TestBuilder:  { group: 'builder', password: 'BuilderPass123' },
};

// 粒子 patch（26.2→1.21.11 兼容）
const mcDataPath = path.join(require.resolve('minecraft-data'), '../..', 'minecraft-data', 'data', 'pc', '1.21.11', 'protocol.json');
try {
  const fs = require('fs');
  const proto = JSON.parse(fs.readFileSync(mcDataPath, 'utf8'));
  const mappings = proto.types.Particle[1][0].type[1].mappings;
  mappings['115'] = 'block_crumble';
  mappings['116'] = 'firefly';
  fs.writeFileSync(mcDataPath, JSON.stringify(proto));
} catch (e) {}

function log(bot, msg) {
  const clean = msg.replace(/§[0-9a-fk-or]/g, '');
  console.log(`[${bot}] ${clean}`);
}

function runBot(username) {
  const cfg = BOTS[username];
  console.log(`\n===== 测试: ${username} (${cfg.group}) =====`);
  let cmdSeq = 0;

  const bot = mineflayer.createBot({
    host: HOST, port: PORT, username,
    version: '1.21.11', auth: 'offline', hideErrors: true,
  });

  const testCommands = [
    { cmd: '/fly', tag: 'fly(飞行)' },
    { cmd: '/gamemode creative', tag: 'gamemode(创造)' },
    { cmd: '//wand', tag: 'we-wand(WE)' },
  ];

  bot.on('message', (msg) => {
    const text = msg.toString().replace(/§[0-9a-fk-or]/g, '');
    if (/请输入 \/login/.test(text)) bot.chat(`/login ${cfg.password}`);
    else if (/请输入 \/register/.test(text)) bot.chat(`/register ${cfg.password} ${cfg.password}`);
    if (text.trim()) log(username, text);
  });

  bot.on('login', () => {
    const runTests = () => {
      if (cmdSeq >= testCommands.length) {
        console.log(`[${username}] 测试完成`);
        bot.quit();
        return;
      }
      const { cmd, tag } = testCommands[cmdSeq++];
      console.log(`[${username}] >>> 执行: ${cmd} (${tag})`);
      bot.chat(cmd);
      setTimeout(runTests, 4000);
    };
    setTimeout(() => {
      bot.chat(`/login ${cfg.password}`);
      setTimeout(runTests, 3000);
    }, 2000);
    setTimeout(() => { bot.quit(); }, 40000);
  });

  bot.on('error', (err) => {
    if (err.code === 'ECONNREFUSED') { console.log(`[${username}] 服务器未就绪`); process.exit(1); }
  });

  setTimeout(() => { bot.quit(); }, 30000);
}

(async () => {
  for (const name of Object.keys(BOTS)) {
    await new Promise((resolve) => {
      runBot(name);
      setTimeout(resolve, 38000);
    });
  }
  console.log('\n===== 全部测试完成 =====');
  process.exit(0);
})();
