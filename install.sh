#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_SRC="$SCRIPT_DIR/skill/SKILL.md"
CLI_SRC="$SCRIPT_DIR/imggen"

# --- Defaults ---
BIN_DIR="${HOME}/.local/bin"
SKILL_DIR="${HOME}/.claude/skills/generate-image"

# --- Colors ---
bold="\033[1m"
green="\033[32m"
yellow="\033[33m"
red="\033[31m"
reset="\033[0m"

info()  { echo -e "${bold}${green}[+]${reset} $*"; }
warn()  { echo -e "${bold}${yellow}[!]${reset} $*"; }
error() { echo -e "${bold}${red}[x]${reset} $*"; }

# --- Parse args ---
SKIP_SKILL=false
SKIP_AUTH=false
CUSTOM_BIN=""

usage() {
    cat <<EOF
Usage: install.sh [OPTIONS]

Options:
  --bin DIR        Install CLI symlink to DIR (default: ~/.local/bin)
  --no-skill       Skip Claude Code skill installation
  --no-auth        Skip interactive API key setup
  -h, --help       Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --bin)       CUSTOM_BIN="$2"; shift 2 ;;
        --no-skill)  SKIP_SKILL=true; shift ;;
        --no-auth)   SKIP_AUTH=true; shift ;;
        -h|--help)   usage; exit 0 ;;
        *)           error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

[[ -n "$CUSTOM_BIN" ]] && BIN_DIR="$CUSTOM_BIN"

# --- Preflight checks ---
echo ""
echo -e "${bold}imggen installer${reset}"
echo "━━━━━━━━━━━━━━━━"
echo ""

# Python 3
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install Python 3.9+ first."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
info "Found Python ${PY_VERSION}"

# Source files exist
if [[ ! -f "$CLI_SRC" ]]; then
    error "CLI script not found at $CLI_SRC"
    exit 1
fi

# --- Install CLI ---
info "Installing CLI..."
mkdir -p "$BIN_DIR"
ln -sf "$CLI_SRC" "$BIN_DIR/imggen"
chmod +x "$CLI_SRC"
info "Symlinked: $BIN_DIR/imggen -> $CLI_SRC"

# Check if BIN_DIR is on PATH
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
    warn "$BIN_DIR is not on your PATH"
    echo ""
    echo "  Add this to your shell profile (~/.zshrc or ~/.bashrc):"
    echo ""
    echo "    export PATH=\"$BIN_DIR:\$PATH\""
    echo ""
fi

# --- Install Claude Code skill ---
if [[ "$SKIP_SKILL" == false ]]; then
    if [[ -d "${HOME}/.claude" ]]; then
        info "Installing Claude Code skill..."
        mkdir -p "$SKILL_DIR"
        cp "$SKILL_SRC" "$SKILL_DIR/SKILL.md"
        info "Skill installed to $SKILL_DIR/SKILL.md"
    else
        warn "~/.claude not found — skipping skill install (Claude Code not detected)"
    fi
else
    info "Skipping Claude Code skill (--no-skill)"
fi

# --- API key setup ---
echo ""

# Check if any keys are already configured (env vars or config file)
HAS_GEMINI=false
HAS_FREEPIK=false
[[ -n "${GEMINI_API_KEY:-}" ]] && HAS_GEMINI=true
[[ -n "${FREEPIK_API_KEY:-}" ]] && HAS_FREEPIK=true

# Also check config file
CONFIG_FILE="${HOME}/.config/imggen/keys.json"
if [[ -f "$CONFIG_FILE" ]]; then
    # Simple check — does the config contain non-empty values
    python3 -c "
import json, sys
cfg = json.load(open('$CONFIG_FILE'))
if cfg.get('gemini', '').strip(): print('gemini')
if cfg.get('freepik', '').strip(): print('freepik')
" 2>/dev/null | while read -r provider; do
        if [[ "$provider" == "gemini" ]]; then HAS_GEMINI=true; fi
        if [[ "$provider" == "freepik" ]]; then HAS_FREEPIK=true; fi
    done
fi

if [[ "$HAS_GEMINI" == true ]]; then
    info "Gemini API key: configured"
else
    warn "Gemini API key: not configured"
fi

if [[ "$HAS_FREEPIK" == true ]]; then
    info "Freepik API key: configured"
else
    warn "Freepik API key: not configured"
fi

if [[ "$SKIP_AUTH" == false ]] && { [[ "$HAS_GEMINI" == false ]] || [[ "$HAS_FREEPIK" == false ]]; }; then
    echo ""
    read -rp "Would you like to configure API keys now? [Y/n] " ANSWER
    ANSWER="${ANSWER:-y}"
    if [[ "${ANSWER,,}" == "y" || "${ANSWER,,}" == "yes" ]]; then
        "$BIN_DIR/imggen" auth
    else
        echo ""
        echo "  You can configure keys later with: imggen auth"
        echo "  Or set env vars: export GEMINI_API_KEY='...'  /  export FREEPIK_API_KEY='...'"
        echo ""
        echo "  Get keys at:"
        echo "    Gemini:  https://aistudio.google.com/apikey"
        echo "    Freepik: https://www.freepik.com/api"
        echo ""
    fi
fi

# --- Done ---
echo -e "${bold}${green}Installation complete!${reset}"
echo ""
echo "  Quick test:  imggen \"a golden retriever in a meadow\""
echo "  Claude Code: /generate-image a golden retriever in a meadow"
echo "  All models:  imggen --list-models"
echo "  Auth setup:  imggen auth"
echo ""
