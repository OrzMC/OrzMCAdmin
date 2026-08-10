#!/bin/bash
# OrzMCAdmin 同步脚本：Hermes 本地 orzmc skill → GitHub 仓库（自动脱敏）
# 用法: ~/OrzMCAdmin/sync.sh [commit message]
# 作用:
#   1. 从 Hermes 完整版 skill（gaming/orzmc）同步 scripts/ + references/ + templates/ + SKILL.md（自动脱敏）
#   2. 显示 git diff 摘要，提交并推送
set -euo pipefail

SRC="$HOME/.hermes/skills/gaming/orzmc"
DST="$HOME/OrzMCAdmin"

[ -d "$SRC" ] || { echo "❌ 源 skill 不存在: $SRC"; exit 1; }
[ -d "$DST/.git" ] || { echo "❌ 仓库不存在: $DST"; exit 1; }

echo "=== 1. 同步 SKILL.md + references/ + templates/ ==="
cp "$SRC/SKILL.md" "$DST/SKILL.md"
rm -rf "$DST/references"; mkdir -p "$DST/references"
cp "$SRC/references/"*.md "$DST/references/"
rm -rf "$DST/templates"; mkdir -p "$DST/templates"
cp "$SRC/templates/"* "$DST/templates/" 2>/dev/null || true

echo "=== 2. 同步 scripts/（自动脱敏） ==="
rm -rf "$DST/scripts"
mkdir -p "$DST/scripts/adapters" "$DST/scripts/cmp3" "$DST/scripts/bot" "$DST/scripts/regression"
cp "$SRC/scripts/adapters/"*.sh "$DST/scripts/adapters/"
cp "$SRC/scripts/cmp3/"*.py "$DST/scripts/cmp3/"
cp "$SRC/scripts/"*.sh "$SRC/scripts/"*.py "$DST/scripts/" 2>/dev/null || true
cp "$SRC/scripts/bot/"*.js "$DST/scripts/bot/" 2>/dev/null || true
cp "$SRC/scripts/regression/"* "$DST/scripts/regression/" 2>/dev/null || true
cp "$SRC/scripts/"*.js "$DST/scripts/" 2>/dev/null || true

echo "=== 3. 脱敏（scripts + references + SKILL.md） ==="
for f in "$DST"/scripts/adapters/*.sh "$DST"/scripts/cmp3/*.py "$DST"/scripts/*.py "$DST"/scripts/*.sh "$DST"/scripts/*.js "$DST"/scripts/bot/*.js "$DST"/scripts/regression/*.js "$DST"/scripts/regression/*.py "$DST"/scripts/regression/*.sh "$DST"/templates/*.js "$DST"/references/*.md "$DST"/SKILL.md; do
  [ -f "$f" ] || continue
  sed -i '' \
    -e 's|http://mc\.fantuantim\.xyz:23333/||g' \
    -e 's|ATMiLQGZ43vW2k3W||g' \
    -e 's|~/papermc-test|~/minecraft-server|g' \
    -e 's|824219521@qq.com||g' \
    -e 's|jokerhub|{SERVER_NAME}|g' \
    -e 's|jockerhubMC|{SERVER_NAME}|g' \
    -e 's|mc\.fantuantim\.xyz|{SERVER_HOST}|g' \
    -e 's|HermesBotPass123|{BOT_PASSWORD}|g' \
    -e 's|192\.168\.0\.35|{LAN_IP}|g' \
    "$f"
done
echo "✅ 脱敏完成"

echo "=== 4. 私有信息复扫（必须 0 命中，排除 sync.sh 自身的脱敏规则） ==="
LEAKS=$(grep -rnE "fantuantim|jokerhub|HermesBotPass123|824219521|192\.168\.0\.35|ATMiLQGZ" "$DST" --include="*.md" --include="*.sh" --include="*.py" --include="*.js" 2>/dev/null | grep -v "^Binary" | grep -v "sync.sh:" | head -5 || true)
if [ -n "$LEAKS" ]; then
  echo "⚠️ 发现私有信息残留："
  echo "$LEAKS"
  exit 1
fi
echo "✅ 复扫 0 命中"

echo "=== 5. 提交推送 ==="
cd "$DST"
git add -A
git diff --cached --stat | tail -5
MSG="${1:-sync: orzmc 统一技能整合 v2.0（45 references + 29 scripts）}"
git commit -m "$MSG" || echo "（无改动）"
git push origin main 2>&1 | tail -2
echo "✅ 同步完成"
