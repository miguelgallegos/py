#!/usr/bin/env python3
"""Run a quick multi-symbol backtest sweep using the config-driven ladder strategy.

Examples:
  python3 run_all_backtests.py
  python3 run_all_backtests.py --symbols SOXL,TQQQ,FNGU --cash 5000 --start 2026-08-16 --end 2026-09-16
"""

from __future__ import annotations

import argparse
from pathlib import Path

from multi_strategy_bot import load_strategy_config, optimize_strategy

DEFAULT_PRESETS = {
    "SOXL": ("soxl_best_1d", "1d"),
    "TQQQ": ("tqqq_best_1h", "1h"),
    "FNGU": ("fngu_best_5m", "5m"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest SOXL, TQQQ, and FNGU with the ladder strategy preset map.")
    parser.add_argument("--symbols", default="SOXL,TQQQ,FNGU", help="Comma-separated symbols to test.")
    parser.add_argument("--cash", type=float, default=5000.0, help="Starting cash per symbol.")
    parser.add_argument("--start", default="2026-08-16", help="Backtest start date, YYYY-MM-DD.")
    parser.add_argument("--end", default="2026-09-16", help="Backtest end date, YYYY-MM-DD.")
    parser.add_argument("--strategy-file", default="strategy_presets.json", help="JSON file containing presets.")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    base_dir = Path(__file__).resolve().parent
    strategy_file = base_dir / args.strategy_file

    print("=== MULTI-SYMBOL BACKTEST ===")
    for symbol in symbols:
        preset_name, interval = DEFAULT_PRESETS.get(symbol, ("pyramid_buy_sell", "5m"))
        strategy = load_strategy_config(strategy_file, preset_name)
        results = optimize_strategy(symbol, interval, args.start, args.end, args.cash, strategy)
        best = results[0] if results else None
        print(f"\n--- {symbol} ({interval}) ---")
        if not best:
            print("NO_DATA")
            continue
        print(best)


if __name__ == "__main__":
    main()
