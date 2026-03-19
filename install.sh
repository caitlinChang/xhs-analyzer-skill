#!/bin/bash
# ============================================================
# xhs-analyzer-skill 安装脚本
# 一键安装小红书博主分析 Claude Code Skill
# ============================================================

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMANDS_DIR="$HOME/.claude/commands"
SCRIPTS_DIR="$HOME/.claude/scripts"
CONFIG_FILE="$HOME/.claude/xhs_config.json"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "=================================================="
echo "  xhs-analyzer-skill 安装程序"
echo "=================================================="
echo ""

# ── 1. 检查 Python ────────────────────────────────────────
echo "▶ 检查 Python..."
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}[错误] 未找到 python3，请先安装 Python 3.9+${NC}"
  exit 1
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  ${GREEN}✓ Python ${PYTHON_VERSION}${NC}"

# ── 2. 安装 Python 依赖 ───────────────────────────────────
echo ""
echo "▶ 安装 Python 依赖（playwright）..."
python3 -m pip install playwright --quiet
echo -e "  ${GREEN}✓ playwright 已安装${NC}"

# ── 3. 安装 Chromium ──────────────────────────────────────
echo ""
echo "▶ 安装 Playwright Chromium 浏览器..."
echo "  (首次安装约需 1-2 分钟，请耐心等待)"
python3 -m playwright install chromium --quiet
echo -e "  ${GREEN}✓ Chromium 已安装${NC}"

# ── 4. 复制 Skill 文件 ────────────────────────────────────
echo ""
echo "▶ 安装 Skill 文件..."

mkdir -p "$COMMANDS_DIR" "$SCRIPTS_DIR"

cp "$REPO_DIR/commands/xhs.md" "$COMMANDS_DIR/xhs.md"
echo -e "  ${GREEN}✓ ~/.claude/commands/xhs.md${NC}"

cp "$REPO_DIR/scripts/xhs_scrape.py" "$SCRIPTS_DIR/xhs_scrape.py"
echo -e "  ${GREEN}✓ ~/.claude/scripts/xhs_scrape.py${NC}"

# ── 5. 创建 Cookie 配置模板 ───────────────────────────────
echo ""
echo "▶ 检查 Cookie 配置..."

if [ -f "$CONFIG_FILE" ] && python3 -c "
import json
try:
    d = json.load(open('$CONFIG_FILE'))
    assert d.get('cookies', '').strip()
    print('ok')
except:
    print('empty')
" 2>/dev/null | grep -q "ok"; then
  echo -e "  ${GREEN}✓ 已有有效配置，跳过${NC}"
else
  cat > "$CONFIG_FILE" <<'EOF'
{
  "cookies": "",
  "saved_at": ""
}
EOF
  echo -e "  ${YELLOW}⚠ 已创建配置模板：~/.claude/xhs_config.json${NC}"
  echo -e "  ${YELLOW}  请在首次运行 /xhs 时按提示填入小红书 Cookie${NC}"
fi

# ── 完成 ──────────────────────────────────────────────────
echo ""
echo "=================================================="
echo -e "  ${GREEN}安装完成！${NC}"
echo "=================================================="
echo ""
echo "使用方法（在 Claude Code 中）："
echo "  /xhs 博主昵称"
echo "  /xhs https://www.xiaohongshu.com/user/profile/<ID>"
echo ""
echo "首次使用时 Claude 会引导你填入小红书 Cookie。"
echo ""
