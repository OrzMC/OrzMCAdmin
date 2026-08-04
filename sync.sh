#!/bin/bash
# OrzMCAdmin 同步脚本：Hermes 本地 skill → GitHub 仓库（自动脱敏）
# 用法: ~/OrzMCAdmin/sync.sh [commit message]
# 作用:
#   1. 从 Hermes 完整版 skill 同步 scripts/ 到仓库（自动脱敏）
#   2. 检查 SKILL.md / references/ 是否有更新（提示手动同步）
#   3. 显示 git diff 摘要，提交并推送
set -euo pipefail

SRC="$HOME/.hermes/skills/gaming/papermc-server-maintenance"
DST="$HOME/OrzMCAdmin"

[ -d "$SRC" ] || { echo "❌ 源 skill 不存在: $SRC"; exit 1; }
[ -d "$DST/.git" ] || { echo "❌ 仓库不存在: $DST"; exit 1; }

echo "=== 1. 同步 scripts/（自动脱敏） ==="
# 清空旧 scripts 再复制（保证删除同步）
rm -rf "$DST/scripts"
mkdir -p "$DST/scripts/adapters" "$DST/scripts/cmp3" "$DST/scripts/bot"
cp "$SRC/scripts/adapters/"*.sh "$DST/scripts/adapters/"
cp "$SRC/scripts/cmp3/"*.py "$DST/scripts/cmp3/"
cp "$SRC/scripts/"*.sh "$SRC/scripts/"parse_*.py "$DST/scripts/" 2>/dev/null || true
cp "$SRC/scripts/bot/"*.js "$DST/scripts/bot/" 2>/dev/null || true

# 脱敏处理（只处理 Python/bash 脚本中的默认值）
for f in "$DST"/scripts/adapters/*.sh "$DST"/scripts/cmp3/*.py; do
  # 私有域名 → 空（从 .env 读）
  sed -i '' 's|http://mc\.fantuantim\.xyz:23333/||g' "$f"
  # 服务器 ID → 空（从 .env 读）
  sed -i '' 's|ATMiLQGZ43vW2k3W||g' "$f"
  # 本地测试目录 → 通用目录
  sed -i '' 's|~/papermc-test|~/minecraft-server|g' "$f"
  # 账号邮箱
  sed -i '' 's|824219521@qq.com||g' "$f"
  # jokerhub 服名 → 通用
  sed -i '' 's|jokerhub|{SERVER_NAME}|g' "$f"
  sed -i '' 's|jockerhubMC|{SERVER_NAME}|g' "$f"
done
echo "✅ scripts/ 已同步 + 脱敏"

echo ""
echo "=== 2. 检查 SKILL.md / references/（文档类，需手动同步） ==="
for doc in SKILL.md references; do
  # 对比源与仓库（仓库是通用版，源是完整版——只能人工判断是否需要更新）
  src_ts=$(stat -f %m "$SRC/SKILL.md" 2>/dev/null || echo 0)
  dst_ts=$(stat -f %m "$DST/SKILL.md" 2>/dev/null || echo 0)
  if [ "$src_ts" -gt "$dst_ts" ]; then
    echo "⚠️  $doc 源文件已更新（完整版），请人工检查是否需要同步到仓库（注意脱敏）"
    echo "   diff 提示: diff <(cat $SRC/SKILL.md) <(cat $DST/SKILL.md)"
  else
    echo "ℹ️  $doc 无更新（或需人工检查）"
  fi
done

echo ""
echo "=== 3. Git 提交 ==="
cd "$DST"
git add -A
CHANGES=$(git diff --cached --stat | tail -1)
if [ -z "$(git status --porcelain)" ]; then
  echo "ℹ️ 无变更，跳过提交"
  exit 0
fi
echo "$CHANGES"
MSG="${1:-sync: 脚本同步 $(date +%Y-%m-%d)}"
git commit -m "$MSG"
echo ""
echo "=== 4. 推送 ==="
git push origin main 2>&1 | tail -2
echo "✅ 同步完成"
