#!/usr/bin/env bash
set -u

if [ -n "${BASH_SOURCE:-}" ] && [ -n "${BASH_SOURCE[0]:-}" ]; then
  SCRIPT_PATH="${BASH_SOURCE[0]}"
else
  SCRIPT_PATH="$0"
fi

SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f "$SCRIPT_DIR/set_fngu_signal_env.sh" ]]; then
  . "$SCRIPT_DIR/set_fngu_signal_env.sh"
fi

python3 trading_bot.py
