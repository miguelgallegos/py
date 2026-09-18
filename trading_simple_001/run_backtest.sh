#!/usr/bin/env bash
set -u

if [ -n "${BASH_SOURCE:-}" ] && [ -n "${BASH_SOURCE[0]:-}" ]; then
  SCRIPT_PATH="${BASH_SOURCE[0]}"
else
  SCRIPT_PATH="$0"
fi

SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f "$SCRIPT_DIR/set_backtest_env.sh" ]]; then
  . "$SCRIPT_DIR/set_backtest_env.sh"
fi

SYMBOL="${1:-${BACKTEST_SYMBOL:-SOXL}}"
INTERVAL="${BACKTEST_INTERVAL:-5m}"
CASH="${BACKTEST_CASH:-5000}"
START="${BACKTEST_START:-2026-08-16}"
END="${BACKTEST_END:-2026-09-16}"
BUY_THRESHOLD="${BACKTEST_BUY_THRESHOLD:--0.0125}"
SELL_THRESHOLD="${BACKTEST_SELL_THRESHOLD:=0.025}"
STRATEGY_FILE="${BACKTEST_STRATEGY_FILE:-strategy_presets.json}"
STRATEGY_NAME="${BACKTEST_STRATEGY_NAME:-pyramid_buy_sell}"
OPTIMIZE="${BACKTEST_OPTIMIZE:-true}"
MULTI="${BACKTEST_MULTI:-false}"
MULTI_SYMBOLS="${BACKTEST_MULTI_SYMBOLS:-SOXL,TQQQ,FNGU}"
TRADE_CSV=""
SUMMARY_FILE=""

# Optional arguments: symbol, interval, cash, start, end, buy, sell, strategy-name, optimize, multi, trade-csv
# Supports both --flag=value and --flag value forms.
while [ "$#" -gt 0 ]; do
  case "$1" in
    --symbol)
      shift
      SYMBOL="${1:-}"
      ;;
    --symbol=*)
      SYMBOL="${1#*=}"
      ;;
    --interval)
      shift
      INTERVAL="${1:-}"
      ;;
    --interval=*)
      INTERVAL="${1#*=}"
      ;;
    --cash)
      shift
      CASH="${1:-}"
      ;;
    --cash=*)
      CASH="${1#*=}"
      ;;
    --start)
      shift
      START="${1:-}"
      ;;
    --start=*)
      START="${1#*=}"
      ;;
    --end)
      shift
      END="${1:-}"
      ;;
    --end=*)
      END="${1#*=}"
      ;;
    --buy)
      shift
      BUY_THRESHOLD="${1:-}"
      ;;
    --buy=*)
      BUY_THRESHOLD="${1#*=}"
      ;;
    --buy-threshold)
      shift
      BUY_THRESHOLD="${1:-}"
      ;;
    --buy-threshold=*)
      BUY_THRESHOLD="${1#*=}"
      ;;
    --sell)
      shift
      SELL_THRESHOLD="${1:-}"
      ;;
    --sell=*)
      SELL_THRESHOLD="${1#*=}"
      ;;
    --sell-threshold)
      shift
      SELL_THRESHOLD="${1:-}"
      ;;
    --sell-threshold=*)
      SELL_THRESHOLD="${1#*=}"
      ;;
    --strategy-file)
      shift
      STRATEGY_FILE="${1:-}"
      ;;
    --strategy-file=*)
      STRATEGY_FILE="${1#*=}"
      ;;
    --strategy-name)
      shift
      STRATEGY_NAME="${1:-}"
      ;;
    --strategy-name=*)
      STRATEGY_NAME="${1#*=}"
      ;;
    --optimize)
      shift
      OPTIMIZE="${1:-true}"
      ;;
    --optimize=*)
      OPTIMIZE="${1#*=}"
      ;;
    --multi)
      shift
      MULTI="${1:-true}"
      ;;
    --multi=*)
      MULTI="${1#*=}"
      ;;
    --multi-symbols)
      shift
      MULTI_SYMBOLS="${1:-}"
      ;;
    --multi-symbols=*)
      MULTI_SYMBOLS="${1#*=}"
      ;;
    --trade-csv)
      shift
      TRADE_CSV="${1:-}"
      ;;
    --trade-csv=*)
      TRADE_CSV="${1#*=}"
      ;;
    --summary-file)
      shift
      SUMMARY_FILE="${1:-}"
      ;;
    --summary-file=*)
      SUMMARY_FILE="${1#*=}"
      ;;
    *)
      ;;
  esac
  shift
 done

if [[ "$MULTI" == "true" ]]; then
  python3 run_all_backtests.py \
    --symbols "$MULTI_SYMBOLS" \
    --cash "$CASH" \
    --start "$START" \
    --end "$END" \
    --strategy-file "$STRATEGY_FILE"
  exit 0
fi

CMD=(
  python3 multi_strategy_bot.py
  --symbol "$SYMBOL"
  --interval "$INTERVAL"
  --cash "$CASH"
  --start "$START"
  --end "$END"
  --strategy-file "$STRATEGY_FILE"
  --strategy-name "$STRATEGY_NAME"
  --optimize
)

if [[ -n "$TRADE_CSV" ]]; then
  CMD+=(--trade-csv "$TRADE_CSV")
fi

if [[ -n "$SUMMARY_FILE" ]]; then
  CMD+=(--summary-file "$SUMMARY_FILE")
fi

if [[ -n "$BUY_THRESHOLD" ]]; then
  CMD+=(--buy-threshold "$BUY_THRESHOLD")
fi

if [[ -n "$SELL_THRESHOLD" ]]; then
  CMD+=(--sell-threshold "$SELL_THRESHOLD")
fi

"${CMD[@]}"
