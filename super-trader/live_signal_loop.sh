#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

: "${SYMBOL:=FNGU}"
: "${INTERVAL:=5m}"
: "${FAST_WINDOW:=8}"
: "${SLOW_WINDOW:=40}"
: "${TP_LEVELS:=0.01,0.02,0.03,0.04,0.05,0.06,0.08}"
: "${SL_LEVELS:=0.005,0.01,0.015,0.02,0.025,0.03}"
: "${POLL_SECONDS:=300}"
: "${SIGNAL_ONLY:=1}"
: "${ENABLE_LIVE_ORDERS:=0}"
: "${TRADING_MODE:=paper}"
: "${ALLOW_AFTER_HOURS:=1}"
: "${DAYS_HISTORY:=30}"

run_once() {
  python3 live_signal_runner.py \
    --symbol "$SYMBOL" \
    --interval "$INTERVAL" \
    --fast "$FAST_WINDOW" \
    --slow "$SLOW_WINDOW" \
    --tp-levels "$TP_LEVELS" \
    --sl-levels "$SL_LEVELS" \
    --signal-only "${SIGNAL_ONLY:-1}" \
    --live-orders "${ENABLE_LIVE_ORDERS:-0}" \
    --allow-after-hours "${ALLOW_AFTER_HOURS:-1}" \
    --trading-mode "$TRADING_MODE" \
    --days-history "$DAYS_HISTORY"
}

if [[ "${1:-}" == "--once" ]]; then
  run_once
  exit 0
fi

while true; do
  echo "$(date '+%Y-%m-%d %H:%M:%S %Z') - polling ${SYMBOL}"
  run_once || true
  echo "Waiting ${POLL_SECONDS}s before the next check..."
  sleep "${POLL_SECONDS}"
done
