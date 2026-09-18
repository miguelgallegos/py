#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
  cat <<'EOF'
Usage: ./run_trading_bot.sh [options]

Runs the generic trading bot with sensible defaults for FNGU intraday signal checks.

Options:
  -s, --symbol SYMBOL            Symbol to trade (default: FNGU)
  -b, --buy-threshold VALUE     Buy threshold as decimal (default: -0.0125)
  -l, --sell-threshold VALUE    Sell threshold as decimal (default: 0.025)
  -i, --interval VALUE          Yahoo interval, e.g. 5m/15m/1h (default: 5m)
      --respect-market-hours X  true/false (default: true)
      --allow-after-hours X     true/false (default: false)
      --signal-only X           true/false (default: true)
      --live X                 true/false (default: false)
      --loop                   Run continuously until stopped
      --sleep-seconds N        Sleep interval in seconds when looping (default: 300)
  -h, --help                    Show this help

Examples:
  ./run_trading_bot.sh
  ./run_trading_bot.sh --symbol FNGU --buy-threshold -0.0125 --sell-threshold 0.025 --interval 5m --signal-only true
  ./run_trading_bot.sh --symbol FNGU --loop --sleep-seconds 300 --signal-only true
  ./run_trading_bot.sh --symbol FNGU --signal-only false --live true
EOF
}

SYMBOL="${TRADING_BOT_SYMBOL:-${SOXL_BOT_SYMBOL:-FNGU}}"
BUY_THRESHOLD="${TRADING_BOT_BUY_THRESHOLD:-${SOXL_BUY_THRESHOLD:--0.0125}}"
SELL_THRESHOLD="${TRADING_BOT_SELL_THRESHOLD:-${SOXL_SELL_THRESHOLD:=0.025}}"
INTERVAL="${TRADING_BOT_INTERVAL:-5m}"
RESPECT_MARKET_HOURS="${TRADING_BOT_RESPECT_MARKET_HOURS:-true}"
ALLOW_AFTER_HOURS="${TRADING_BOT_ALLOW_AFTER_HOURS:-false}"
SIGNAL_ONLY="${TRADING_BOT_SIGNAL_ONLY:-true}"
LIVE_TRADING="${TRADING_BOT_LIVE_TRADING:-false}"
LOOP=false
SLEEP_SECONDS="${TRADING_BOT_SLEEP_SECONDS:-300}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--symbol)
      SYMBOL="$2"
      shift 2
      ;;
    -b|--buy-threshold)
      BUY_THRESHOLD="$2"
      shift 2
      ;;
    -l|--sell-threshold)
      SELL_THRESHOLD="$2"
      shift 2
      ;;
    -i|--interval)
      INTERVAL="$2"
      shift 2
      ;;
    --respect-market-hours)
      RESPECT_MARKET_HOURS="${2:-true}"
      shift 2
      ;;
    --allow-after-hours)
      ALLOW_AFTER_HOURS="${2:-false}"
      shift 2
      ;;
    --signal-only)
      SIGNAL_ONLY="${2:-true}"
      shift 2
      ;;
    --live)
      LIVE_TRADING="${2:-true}"
      shift 2
      ;;
    --loop)
      LOOP=true
      shift
      ;;
    --sleep-seconds)
      SLEEP_SECONDS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

export TRADING_BOT_SYMBOL="$SYMBOL"
export TRADING_BOT_BUY_THRESHOLD="$BUY_THRESHOLD"
export TRADING_BOT_SELL_THRESHOLD="$SELL_THRESHOLD"
export TRADING_BOT_INTERVAL="$INTERVAL"
export TRADING_BOT_RESPECT_MARKET_HOURS="$RESPECT_MARKET_HOURS"
export TRADING_BOT_ALLOW_AFTER_HOURS="$ALLOW_AFTER_HOURS"
export TRADING_BOT_SIGNAL_ONLY="$SIGNAL_ONLY"
export TRADING_BOT_LIVE_TRADING="$LIVE_TRADING"
export TRADING_BOT_SLEEP_SECONDS="$SLEEP_SECONDS"

if [[ "$LOOP" == "true" ]]; then
  echo "Starting continuous polling loop for ${SYMBOL} every ${SLEEP_SECONDS}s"
  while true; do
    python3 trading_bot.py
    sleep "$SLEEP_SECONDS"
  done
else
  python3 trading_bot.py
fi
