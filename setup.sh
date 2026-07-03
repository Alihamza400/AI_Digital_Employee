#!/usr/bin/env bash
set -e

# ─── Colors ───────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

info()  { printf "${CYAN}➜${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}✓${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}⚠${NC} %s\n" "$*"; }
fail()  { printf "${RED}✗${NC} %s\n" "$*"; exit 1; }
header(){ printf "\n${BOLD}━━━ %s ━━━${NC}\n" "$*"; }

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

header "AI Digital Employee — Setup"
echo ""

# ─── 1. Python ─────────────────────────────────────────────────────────────
header "1/8  Checking Python"

if command -v python3 &>/dev/null; then
    PY=$(command -v python3)
elif command -v python &>/dev/null; then
    PY=$(command -v python)
else
    fail "Python not found. Install Python 3.12+ first (https://python.org)"
fi

PY_VER=$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Found Python $PY_VER at $PY"
if [ "$(echo "$PY_VER" | cut -d. -f1)" -lt 3 ] || { [ "$(echo "$PY_VER" | cut -d. -f1)" -eq 3 ] && [ "$(echo "$PY_VER" | cut -d. -f2)" -lt 12 ]; }; then
    fail "Python 3.12+ required (found $PY_VER)"
fi
ok "Python $PY_VER"

# ─── 2. uv ─────────────────────────────────────────────────────────────────
header "2/8  Checking uv (Python package manager)"

if ! command -v uv &>/dev/null; then
    warn "uv not found — installing via pip"
    $PY -m pip install uv
fi
ok "uv $(uv --version 2>/dev/null || echo 'installed')"

# ─── 3. Install dependencies ──────────────────────────────────────────────
header "3/8  Installing Python dependencies"

uv sync --quiet
ok "Dependencies installed"

# ─── 4. Environment variables ──────────────────────────────────────────────
header "4/8  Setting up .env"

if [ ! -f .env ]; then
    cp .env.example .env
    warn ".env created from .env.example — you need to fill in your credentials"
    echo ""
    info "You need a Google Cloud Project with two OAuth 2.0 Desktop clients:"
    echo "  1. Gmail client — with Gmail API enabled"
    echo "  2. Calendar client — with Calendar API enabled"
    echo ""
    info "Create them at: https://console.developers.google.com/apis/credentials"
    echo ""
    read -rp "  Press Enter after you've filled in .env (or type 'skip' to do it later): " REPLY
    if [ "$REPLY" = "skip" ]; then
        warn "Skipping .env config — run setup.sh again when ready"
    fi
else
    ok ".env already exists"
fi

# ─── 5. Gmail OAuth ────────────────────────────────────────────────────────
header "5/8  Gmail authentication"

if grep -q "GMAIL_REFRESH_TOKEN=.*[a-zA-Z0-9]" .env 2>/dev/null; then
    ok "Gmail refresh token found"
else
    echo ""
    warn "No GMAIL_REFRESH_TOKEN in .env"
    echo ""
    read -rp "  Run Gmail OAuth now? (Y/n): " REPLY
    if [ "$REPLY" != "n" ] && [ "$REPLY" != "N" ]; then
        uv run python -m src.scripts.auth_gmail
        ok "Gmail authenticated"
    else
        warn "Skipped — run 'uv run python -m src.scripts.auth_gmail' later"
    fi
fi

# ─── 6. Calendar OAuth ─────────────────────────────────────────────────────
header "6/8  Calendar authentication"

if grep -q "CALENDAR_REFRESH_TOKEN=.*[a-zA-Z0-9]" .env 2>/dev/null; then
    ok "Calendar refresh token found"
else
    echo ""
    warn "No CALENDAR_REFRESH_TOKEN in .env"
    echo ""
    read -rp "  Run Calendar OAuth now? (Y/n): " REPLY
    if [ "$REPLY" != "n" ] && [ "$REPLY" != "N" ]; then
        uv run python -m src.scripts.auth_calendar
        ok "Calendar authenticated"
    else
        warn "Skipped — run 'uv run python -m src.scripts.auth_calendar' later"
    fi
fi

# ─── 7. opencode CLI ───────────────────────────────────────────────────────
header "7/8  Checking opencode (AI reasoning engine)"

if command -v opencode &>/dev/null; then
    ok "opencode CLI found"
    echo ""
    info "Make sure you're logged in to an LLM provider:"
    info "  opencode providers login"
    echo ""
    read -rp "  Log in now? (Y/n): " REPLY
    if [ "$REPLY" != "n" ] && [ "$REPLY" != "N" ]; then
        opencode providers login || warn "Login command failed — try manually later"
    fi
else
    warn "opencode CLI not found"
    echo ""
    info "Install it:"
    info "  npm install -g opencode-ai"
    info "Then log in:"
    info "  opencode providers login"
    echo ""
    read -rp "  Press Enter after installing opencode (or 'skip'): " REPLY
fi

# ─── 8. Playwright browsers ────────────────────────────────────────────────
header "8/8  Checking Playwright browsers"

if uv run python -c "from playwright.sync_api import sync_playwright; print('ok')" 2>/dev/null; then
    ok "Playwright browsers already installed"
else
    echo ""
    info "Installing Playwright Chromium browser..."
    uv run playwright install chromium
    ok "Playwright Chromium installed"
fi

echo ""
echo ""
header "Setup complete!"
echo ""
info "Next steps:"
echo ""
echo "  1. Start the AI Employee:"
echo "     ${CYAN}uv run python -m src.scripts.main${NC}"
echo ""
echo "  2. Approve pending actions via:"
echo "     ${CYAN}uv run python -m src.scripts.approve list${NC}"
echo "     ${CYAN}uv run python -m src.scripts.approve approve <file>${NC}"
echo ""
echo "  3. Browse to ${CYAN}http://localhost:8080${NC} for the web approval UI"
echo ""
echo "  4. Tunnel mode (public URL):"
echo "     ${CYAN}uv run python -m src.scripts.main --tunnel${NC}"
echo ""
echo "Need help? Visit https://github.com/Alihamza400/AI_Digital_Employee"
echo ""
