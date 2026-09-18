#!/usr/bin/env python3
from __future__ import annotations

import argparse

import pandas as pd

from data import load_market_data
from live_trader import LiveTrader
from strategies.sma_crossover import SmaCrossoverStrategy


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the live trading signal loop.")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--strategy", default="sma_crossover")
    parser.add_argument("--paper-trade", action="store_true")
    parser.add_argument("--fast", type=int, default=10)
    parser.add_argument("--slow", type=int, default=30)
    args = parser.parse_args()

    df = load_market_data(args.symbol, "2024-01-01", "2024-04-01", args.interval)
    strategy = SmaCrossoverStrategy({"fast_window": args.fast, "slow_window": args.slow})
    trader = LiveTrader(args.strategy)
    signal = trader.evaluate_signal(df, strategy)
    print(signal)


if __name__ == "__main__":
    main()
