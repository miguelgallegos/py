#!/usr/bin/env python3
"""Generic multi-symbol intraday runner with config-driven ladder strategy.

Usage examples:
  python3 multi_strategy_bot.py --symbol TQQQ --interval 5m --cash 5000 --strategy-file strategy_presets.json --strategy-name pyramid_buy_sell
  python3 multi_strategy_bot.py --symbol FNGU --interval 15m --cash 5000 --strategy-file strategy_presets.json --strategy-name pyramid_buy_sell --optimize
  python3 multi_strategy_bot.py --symbol TQQQ --interval 5m --cash 5000 --strategy-file strategy_presets.json --strategy-name tqqq_intraday_2pct_goal --live
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd
import yfinance as yf

from strategy import calculate_buy_fraction

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def load_strategy_config(path: str | Path, strategy_name: str) -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    strategies = payload.get("strategies", {})
    if not strategies:
        raise ValueError(f"No strategies found in {config_path}")
    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy '{strategy_name}'. Available: {sorted(strategies)}")

    strategy = strategies[strategy_name]
    ladder = tuple(float(v) for v in strategy.get("ladder", [0.35, 0.75, 1.0]))
    return {
        "name": strategy_name,
        "buy_threshold": float(strategy.get("buy_threshold", -0.02)),
        "sell_threshold": float(strategy.get("sell_threshold", 0.03)),
        "ladder": ladder,
        "buy_candidates": [float(x) for x in strategy.get("buy_candidates", [])],
        "sell_candidates": [float(x) for x in strategy.get("sell_candidates", [])],
    }


def load_price_data(symbol: str, start: str, end: str, interval: str = "5m", use_cache: bool = True) -> pd.DataFrame:
    cache_file = DATA_DIR / f"{symbol.lower()}_{interval}_{start}_{end}.csv"
    if use_cache and cache_file.exists():
        data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        if not data.empty:
            return data

    data = yf.download(symbol, start=start, end=end, interval=interval, progress=False, auto_adjust=False)
    if data.empty:
        if use_cache and cache_file.exists():
            cached = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not cached.empty:
                return cached
        raise RuntimeError(f"No price data returned for {symbol} between {start} and {end} at interval={interval}.")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data.to_csv(cache_file)
    return data


def simulate_backtest(data: pd.DataFrame, starting_cash: float, buy_threshold: float, sell_threshold: float, ladder: Iterable[float]) -> Tuple[List[List[Any]], List[Tuple[str, float, float]], float, float, int]:
    cash = float(starting_cash)
    shares = 0.0
    reference_price = None
    trades: List[Tuple[str, float, float]] = []
    rows: List[List[Any]] = []

    for timestamp, row in data.iterrows():
        price = float(row["Close"])

        if reference_price is None:
            reference_price = price
            rows.append([timestamp, price, 0.0, "BASELINE", cash + shares * price])
            continue

        pct_change = (price - reference_price) / reference_price
        action = "HOLD"

        if pct_change <= buy_threshold and cash > 1.0:
            buy_fraction = calculate_buy_fraction(pct_change, buy_threshold, tuple(float(x) for x in ladder))
            if buy_fraction > 0:
                buy_amount = cash * buy_fraction
                qty = buy_amount / price
                shares += qty
                cash -= buy_amount
                action = f"BUY {qty:.4f} sh ({buy_fraction * 100:.0f}% cash pyramid)"
                trades.append(("BUY", price, qty))

        elif pct_change >= sell_threshold and shares > 0:
            action = f"SELL {shares:.4f} sh"
            cash += shares * price
            shares = 0.0
            trades.append(("SELL", price, shares))

        reference_price = price
        equity = cash + shares * price
        rows.append([timestamp, price, pct_change, action, equity])

    final_price = float(data["Close"].iloc[-1])
    final_equity = cash + shares * final_price
    return rows, trades, final_equity, (final_equity / starting_cash - 1) * 100, len(trades)


def run_once(symbol: str, interval: str, start: str, end: str, cash: float, strategy: Dict[str, Any]) -> Dict[str, Any]:
    data = load_price_data(symbol, start, end, interval=interval, use_cache=True)
    rows, trades, final_equity, return_pct, trade_count = simulate_backtest(
        data,
        cash,
        strategy["buy_threshold"],
        strategy["sell_threshold"],
        strategy["ladder"],
    )
    return {
        "symbol": symbol,
        "interval": interval,
        "buy_threshold": strategy["buy_threshold"],
        "sell_threshold": strategy["sell_threshold"],
        "ladder": strategy["ladder"],
        "final_equity": final_equity,
        "return_pct": return_pct,
        "trades": trade_count,
        "bars": len(data),
    }


def optimize_strategy(symbol: str, interval: str, start: str, end: str, cash: float, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
    buy_candidates = strategy.get("buy_candidates") or [strategy["buy_threshold"]]
    sell_candidates = strategy.get("sell_candidates") or [strategy["sell_threshold"]]
    results: List[Dict[str, Any]] = []

    for buy_threshold in buy_candidates:
        for sell_threshold in sell_candidates:
            if sell_threshold <= abs(buy_threshold):
                continue
            data = load_price_data(symbol, start, end, interval=interval, use_cache=True)
            _, _, final_equity, return_pct, trade_count = simulate_backtest(
                data,
                cash,
                float(buy_threshold),
                float(sell_threshold),
                strategy["ladder"],
            )
            results.append({
                "symbol": symbol,
                "interval": interval,
                "buy_threshold": float(buy_threshold),
                "sell_threshold": float(sell_threshold),
                "ladder": strategy["ladder"],
                "final_equity": final_equity,
                "return_pct": return_pct,
                "trades": trade_count,
            })

    return sorted(results, key=lambda item: item["final_equity"], reverse=True)


def record_result(symbol: str, strategy_name: str, interval: str, start: str, end: str, cash: float, result: Dict[str, Any], results_file: str | Path = "strategy_results_history.json") -> None:
    path = Path(results_file)
    payload = {"history": []}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except json.JSONDecodeError:
            payload = {"history": []}

    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "strategy_name": strategy_name,
        "interval": interval,
        "start": start,
        "end": end,
        "cash": cash,
        "result": result,
    }
    history = payload.setdefault("history", [])
    history.append(entry)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generic strategy runner for SOXL-like laddered buy/sell systems.")
    parser.add_argument("--symbol", default="TQQQ", help="Ticker symbol to test, e.g. TQQQ or FNGU.")
    parser.add_argument("--interval", default="5m", help="Yahoo chart interval, e.g. 2m, 5m, 15m, 30m, 60m, 1d")
    parser.add_argument("--cash", type=float, default=5000.0, help="Starting cash for the backtest.")
    parser.add_argument("--start", default="2026-08-16", help="Backtest start date, YYYY-MM-DD.")
    parser.add_argument("--end", default="2026-09-16", help="Backtest end date, YYYY-MM-DD.")
    parser.add_argument("--strategy-file", default="strategy_presets.json", help="JSON file with strategy presets.")
    parser.add_argument("--strategy-name", default="pyramid_buy_sell", help="Strategy name in strategy file.")
    parser.add_argument("--optimize", action="store_true", help="Grid-search the configured buy/sell thresholds and print the best few results.")
    parser.add_argument("--live", action="store_true", help="Run the wrapper in live mode; this keeps the same symbol/strategy framework but marks the run as live.")
    parser.add_argument("--results-file", default="strategy_results_history.json", help="JSON file used to store symbol/preset/result references.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    strategy = load_strategy_config(args.strategy_file, args.strategy_name)

    if args.live:
        print(f"LIVE MODE: symbol={args.symbol} interval={args.interval} strategy={args.strategy_name}")

    if args.optimize:
        best = optimize_strategy(args.symbol, args.interval, args.start, args.end, args.cash, strategy)
        best_result = best[0] if best else None
        print(f"=== BEST {args.symbol} {args.interval} RESULTS ===")
        for idx, item in enumerate(best[:10], 1):
            print(idx, item)

        if best_result:
            record_result(args.symbol, args.strategy_name, args.interval, args.start, args.end, args.cash, best_result, args.results_file)
        return

    result = run_once(args.symbol, args.interval, args.start, args.end, args.cash, strategy)
    record_result(args.symbol, args.strategy_name, args.interval, args.start, args.end, args.cash, result, args.results_file)
    print(result)


if __name__ == "__main__":
    main()
