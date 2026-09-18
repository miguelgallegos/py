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
        "roc_lookback": int(strategy.get("roc_lookback", 5)),
        "entry_drop_pct": float(strategy.get("entry_drop_pct", 0.015)),
        "exit_interval": strategy.get("exit_interval", "1m"),
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


def compute_roc(series: pd.Series, lookback: int = 5) -> float:
    if len(series) <= lookback:
        return 0.0
    return float(series.iloc[-1] / series.iloc[-lookback - 1] - 1.0)


def load_exit_data_if_available(symbol: str, start: str, end: str) -> pd.DataFrame | None:
    try:
        return load_price_data(symbol, start, end, interval="1m", use_cache=True)
    except RuntimeError:
        return None


def simulate_backtest(
    data: pd.DataFrame,
    starting_cash: float,
    buy_threshold: float,
    sell_threshold: float,
    ladder: Iterable[float],
    symbol: str | None = None,
    interval: str = "5m",
    entry_roc_lookback: int = 5,
    entry_drop_pct: float = 0.015,
    exit_interval: str | None = None,
    exit_data: pd.DataFrame | None = None,
) -> Tuple[List[List[Any]], List[Dict[str, Any]], float, float, int]:
    cash = float(starting_cash)
    shares = 0.0
    reference_price = None
    trades: List[Dict[str, Any]] = []
    rows: List[List[Any]] = []
    buy_signal_used = False

    for idx, (timestamp, row) in enumerate(data.iterrows()):
        price = float(row["Close"])

        if reference_price is None:
            reference_price = price
            rows.append([timestamp, price, 0.0, "BASELINE", cash + shares * price])
            continue

        pct_change = (price - reference_price) / reference_price
        action = "HOLD"

        buy_allowed = False
        if str(interval).lower() in {"1d", "1day"}:
            recent_window = data.iloc[max(0, idx - entry_roc_lookback):idx + 1]["Close"]
            if not recent_window.empty:
                recent_high = float(recent_window.max())
                price_drop = (recent_high - price) / recent_high if recent_high > 0 else 0.0
                roc_pct = compute_roc(recent_window, lookback=entry_roc_lookback)
                buy_allowed = (
                    price_drop >= max(abs(float(buy_threshold)), float(entry_drop_pct))
                    and roc_pct <= 0.0
                    and price <= recent_high * (1.0 + float(buy_threshold))
                )
        else:
            buy_allowed = pct_change <= buy_threshold

        if buy_allowed and cash > 1.0:
            if str(interval).lower() in {"1d", "1d", "1day"}:
                buy_fraction = 1.0 if cash > 1.0 else 0.0
            else:
                buy_fraction = calculate_buy_fraction(pct_change, buy_threshold, tuple(float(x) for x in ladder))
            if buy_fraction > 0:
                buy_amount = cash * buy_fraction
                qty = buy_amount / price
                shares += qty
                cash -= buy_amount
                action = f"BUY {qty:.4f} sh ({buy_fraction * 100:.0f}% cash pyramid)"
                equity = cash + shares * price
                trades.append({
                    "timestamp": timestamp.isoformat(),
                    "side": "BUY",
                    "price": price,
                    "qty": qty,
                    "equity": equity,
                    "return_pct": ((equity / starting_cash) - 1.0) * 100.0,
                })
                buy_signal_used = True

        elif shares > 0:
            if str(interval).lower() in {"1d", "1day"} and exit_data is not None:
                day_slice = exit_data[exit_data.index.date == timestamp.date()]
                if not day_slice.empty:
                    avg_cost = (starting_cash - cash) / (shares if shares > 0 else 1.0)
                    for intraday_price in [float(v) for v in day_slice["Close"].tolist()]:
                        if intraday_price >= avg_cost * (1.0 + float(sell_threshold)):
                            action = f"SELL {shares:.4f} sh (1m exit)"
                            sell_qty = shares
                            cash += shares * intraday_price
                            shares = 0.0
                            equity = cash + shares * intraday_price
                            trades.append({
                                "timestamp": timestamp.isoformat(),
                                "side": "SELL",
                                "price": intraday_price,
                                "qty": sell_qty,
                                "equity": equity,
                                "return_pct": ((equity / starting_cash) - 1.0) * 100.0,
                            })
                            break
            if shares > 0 and (pct_change >= sell_threshold or str(interval).lower() not in {"1d", "1day"} and pct_change >= sell_threshold):
                action = f"SELL {shares:.4f} sh"
                sell_qty = shares
                cash += shares * price
                shares = 0.0
                equity = cash + shares * price
                trades.append({
                    "timestamp": timestamp.isoformat(),
                    "side": "SELL",
                    "price": price,
                    "qty": sell_qty,
                    "equity": equity,
                    "return_pct": ((equity / starting_cash) - 1.0) * 100.0,
                })

        reference_price = price
        equity = cash + shares * price
        rows.append([timestamp, price, pct_change, action, equity])

    final_price = float(data["Close"].iloc[-1])
    final_equity = cash + shares * final_price
    return rows, trades, final_equity, (final_equity / starting_cash - 1) * 100, len(trades)


def trade_log_to_dataframe(trade_log: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for entry in trade_log:
        if isinstance(entry, dict):
            records.append({
                "timestamp": entry.get("timestamp", ""),
                "side": entry.get("side", ""),
                "price": entry.get("price", 0.0),
                "qty": entry.get("qty", 0.0),
                "equity": entry.get("equity", 0.0),
                "return_pct": entry.get("return_pct", 0.0),
            })
        elif isinstance(entry, (list, tuple)) and len(entry) >= 3:
            records.append({
                "timestamp": "",
                "side": entry[0],
                "price": entry[1],
                "qty": entry[2],
                "equity": 0.0,
                "return_pct": 0.0,
            })
    return pd.DataFrame(records, columns=["timestamp", "side", "price", "qty", "equity", "return_pct"])


def run_once(symbol: str, interval: str, start: str, end: str, cash: float, strategy: Dict[str, Any]) -> Dict[str, Any]:
    data = load_price_data(symbol, start, end, interval=interval, use_cache=True)
    exit_data = None
    if str(interval).lower() in {"1d", "1day"}:
        exit_data = load_exit_data_if_available(symbol, start, end)
    rows, trades, final_equity, return_pct, trade_count = simulate_backtest(
        data,
        cash,
        strategy["buy_threshold"],
        strategy["sell_threshold"],
        strategy["ladder"],
        symbol=symbol,
        interval=interval,
        entry_roc_lookback=strategy.get("roc_lookback", 5),
        entry_drop_pct=strategy.get("entry_drop_pct", 0.015),
        exit_interval=strategy.get("exit_interval", "1m"),
        exit_data=exit_data,
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
        "trade_log": trades,
    }


def optimize_strategy(symbol: str, interval: str, start: str, end: str, cash: float, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
    buy_candidates = strategy.get("buy_candidates")
    sell_candidates = strategy.get("sell_candidates")

    if strategy.get("buy_threshold") is not None and buy_candidates is not None and len(buy_candidates) == 1:
        buy_candidates = [float(strategy["buy_threshold"])]
    if strategy.get("sell_threshold") is not None and sell_candidates is not None and len(sell_candidates) == 1:
        sell_candidates = [float(strategy["sell_threshold"])]

    if buy_candidates is None:
        buy_candidates = [float(strategy["buy_threshold"])]
    if sell_candidates is None:
        sell_candidates = [float(strategy["sell_threshold"])]

    results: List[Dict[str, Any]] = []

    for buy_threshold in buy_candidates:
        for sell_threshold in sell_candidates:
            data = load_price_data(symbol, start, end, interval=interval, use_cache=True)
            exit_data = None
            if str(interval).lower() in {"1d", "1day"}:
                exit_data = load_exit_data_if_available(symbol, start, end)
            _, trade_log, final_equity, return_pct, trade_count = simulate_backtest(
                data,
                cash,
                float(buy_threshold),
                float(sell_threshold),
                strategy["ladder"],
                symbol=symbol,
                interval=interval,
                entry_roc_lookback=strategy.get("roc_lookback", 5),
                entry_drop_pct=strategy.get("entry_drop_pct", 0.015),
                exit_interval=strategy.get("exit_interval", "1m"),
                exit_data=exit_data,
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
                "trade_log": trade_log,
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


def format_result_summary(symbol: str, interval: str, start: str, end: str, starting_cash: float, strategy: Dict[str, Any], result: Dict[str, Any]) -> str:
    equity = float(result.get("final_equity", 0.0))
    return_pct = float(result.get("return_pct", 0.0))
    trade_count = int(result.get("trades", 0))
    buy_count = int(result.get("buy_count", 0))
    sell_count = int(result.get("sell_count", 0))
    if buy_count == 0 and sell_count == 0 and trade_count > 0:
        buy_count = trade_count
        sell_count = 0
    lines = [
        f"Backtest: {symbol}  {start} -> {end}  interval={interval}  ({result.get('bars', 0)} bars)",
        f"Thresholds:         buy <= {strategy.get('buy_threshold', 0.0) * 100:+.2f}%   sell >= {strategy.get('sell_threshold', 0.0) * 100:+.2f}%",
        f"Starting cash:      ${starting_cash:,.2f}",
        f"Strategy equity:    ${equity:,.2f}   ({return_pct:+.2f}%)",
        f"Trades simulated:   {trade_count}  ({buy_count} buys, {sell_count} sells)",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generic strategy runner for SOXL-like laddered buy/sell systems.")
    parser.add_argument("--symbol", default="TQQQ", help="Ticker symbol to test, e.g. TQQQ or FNGU.")
    parser.add_argument("--interval", default="5m", help="Yahoo chart interval, e.g. 2m, 5m, 15m, 30m, 60m, 1d")
    parser.add_argument("--cash", type=float, default=5000.0, help="Starting cash for the backtest.")
    parser.add_argument("--start", default="2026-08-16", help="Backtest start date, YYYY-MM-DD.")
    parser.add_argument("--end", default="2026-09-16", help="Backtest end date, YYYY-MM-DD.")
    parser.add_argument("--strategy-file", default="strategy_presets.json", help="JSON file with strategy presets.")
    parser.add_argument("--strategy-name", default="pyramid_buy_sell", help="Strategy name in strategy file.")
    parser.add_argument("--buy-threshold", type=float, default=None, help="Override the preset buy threshold, e.g. -0.01.")
    parser.add_argument("--sell-threshold", type=float, default=None, help="Override the preset sell threshold, e.g. 0.02.")
    parser.add_argument("--buy", dest="buy_threshold_alias", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--sell", dest="sell_threshold_alias", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--optimize", action="store_true", help="Grid-search the configured buy/sell thresholds and print the best few results.")
    parser.add_argument("--live", action="store_true", help="Run the wrapper in live mode; this keeps the same symbol/strategy framework but marks the run as live.")
    parser.add_argument("--results-file", default="strategy_results_history.json", help="JSON file used to store symbol/preset/result references.")
    parser.add_argument("--trade-csv", default="", help="Optional path to export the trade ledger as CSV. Example: --trade-csv fngu_trades.csv")
    parser.add_argument("--summary-file", default="", help="Optional path to write the formatted backtest summary text to disk.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    strategy = load_strategy_config(args.strategy_file, args.strategy_name)

    if args.buy_threshold is not None:
        strategy["buy_threshold"] = args.buy_threshold
        strategy["buy_candidates"] = [args.buy_threshold]
    elif args.buy_threshold_alias is not None:
        strategy["buy_threshold"] = args.buy_threshold_alias
        strategy["buy_candidates"] = [args.buy_threshold_alias]

    if args.sell_threshold is not None:
        strategy["sell_threshold"] = args.sell_threshold
        strategy["sell_candidates"] = [args.sell_threshold]
    elif args.sell_threshold_alias is not None:
        strategy["sell_threshold"] = args.sell_threshold_alias
        strategy["sell_candidates"] = [args.sell_threshold_alias]

    if args.live:
        print(f"LIVE MODE: symbol={args.symbol} interval={args.interval} strategy={args.strategy_name}")

    if args.optimize:
        best = optimize_strategy(args.symbol, args.interval, args.start, args.end, args.cash, strategy)
        best_result = best[0] if best else None
        print(f"=== BEST {args.symbol} {args.interval} RESULTS ===")
        for idx, item in enumerate(best[:10], 1):
            print(idx, item)

        if best_result:
            summary_text = format_result_summary(args.symbol, args.interval, args.start, args.end, args.cash, strategy, best_result)
            print(summary_text, end="")
            if args.summary_file:
                Path(args.summary_file).write_text(summary_text, encoding="utf-8")
                print(f"Summary written to {args.summary_file}")

        if args.trade_csv:
            output_path = Path(args.trade_csv)
            if best_result and "trade_log" in best_result:
                trade_df = trade_log_to_dataframe(best_result.get("trade_log", []))
                trade_df.to_csv(output_path, index=False)
                print(f"Trade CSV written to {output_path}")

        if best_result:
            record_result(args.symbol, args.strategy_name, args.interval, args.start, args.end, args.cash, best_result, args.results_file)
        return

    result = run_once(args.symbol, args.interval, args.start, args.end, args.cash, strategy)
    record_result(args.symbol, args.strategy_name, args.interval, args.start, args.end, args.cash, result, args.results_file)
    if args.summary_file:
        summary_text = format_result_summary(args.symbol, args.interval, args.start, args.end, args.cash, strategy, result)
        Path(args.summary_file).write_text(summary_text, encoding="utf-8")
        print(summary_text, end="")
        print(f"Summary written to {args.summary_file}")
    if args.trade_csv:
        trade_df = trade_log_to_dataframe(result.get("trade_log", []))
        trade_df.to_csv(args.trade_csv, index=False)
        print(f"Trade CSV written to {args.trade_csv}")
    print(result)


if __name__ == "__main__":
    main()
