#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pprint import pprint

from backtest import BacktestEngine
from optimizer import optimize_strategy
from strategy_loader import resolve_strategy


def build_strategy(name: str, config: dict) -> object:
    return resolve_strategy(name, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest a pluggable strategy with Jesse-style trade management.")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2024-04-01")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--strategy", default="sma_crossover")
    parser.add_argument("--fast", type=int, default=10)
    parser.add_argument("--slow", type=int, default=30)
    parser.add_argument("--rsi-period", type=int, default=14)
    parser.add_argument("--macd-fast", type=int, default=12)
    parser.add_argument("--macd-slow", type=int, default=26)
    parser.add_argument("--bollinger-window", type=int, default=20)
    parser.add_argument("--tp", default="0.02,0.04,0.06")
    parser.add_argument("--sl", default="0.01,0.02")
    parser.add_argument("--optimize", action="store_true")
    args = parser.parse_args()

    base_config = {
        "tp_levels": tuple(float(v) for v in args.tp.split(",") if v.strip()),
        "sl_levels": tuple(float(v) for v in args.sl.split(",") if v.strip()),
    }

    if args.strategy == "sma_crossover":
        base_config.update({"fast_window": args.fast, "slow_window": args.slow})
    elif args.strategy == "rsi":
        base_config.update({"rsi_period": args.rsi_period})
    elif args.strategy == "macd":
        base_config.update({"fast": args.macd_fast, "slow": args.macd_slow})
    elif args.strategy == "bollinger":
        base_config.update({"window": args.bollinger_window})

    strategy = build_strategy(args.strategy, base_config)
    engine = BacktestEngine(strategy)

    if args.optimize:
        results = optimize_strategy(args.symbol, args.start, args.end, args.interval)
        print("Top optimization results:")
        pprint(results[:10])
        return

    result = engine.run(args.symbol, args.start, args.end, args.interval)
    print(f"Final equity: {result['final_equity']:.2f}")
    print(f"Return: {result['return_pct']:.2f}%")
    print(f"Trades: {len(result['trades'])}")


if __name__ == "__main__":
    main()
