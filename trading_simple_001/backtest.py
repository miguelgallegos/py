#!/usr/bin/env python3
"""
Quick backtest for the SOXL rolling-threshold strategy.

Downloads historical prices (via yfinance, no Robinhood login needed) and
replays the exact same buy/sell logic as soxl_trading_bot.py: compare each
bar's close to a rolling reference price, buy with all cash on a >=1% drop,
sell the whole position on a >=1% rise, then reset the reference to that
bar's close regardless of whether a trade happened.

By default this uses daily bars (--interval 1d), which simulates the bot
checking once a day instead of every 2 minutes. You can pass a finer
--interval (e.g. 2m, 5m, 15m) to approximate the live bot's actual check
frequency far more closely - see README.md for Yahoo Finance's history
limits on intraday data (they get much shorter as the interval gets finer).

Usage:
    python3 backtest.py --start 2023-01-01 --end 2026-09-01 --cash 10000
    python3 backtest.py --symbol SOXL --start 2024-01-01 --csv results.csv
    python3 backtest.py --interval 2m --start 2026-08-01 --end 2026-09-01
    python3 backtest.py --buy-threshold -0.02 --sell-threshold 0.02
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import SYMBOL, BUY_THRESHOLD, SELL_THRESHOLD
from strategy import calculate_buy_fraction

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def load_price_data(symbol: str, start: str, end: str, interval: str = "1d",
                    use_cache: bool = True):
    cache_file = DATA_DIR / f"{symbol.lower()}_{interval}_{start}_{end}.csv"
    if use_cache and cache_file.exists():
        data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        if not data.empty:
            return data

    data = yf.download(symbol, start=start, end=end, interval=interval, progress=False, auto_adjust=False)
    if data.empty:
        if use_cache and cache_file.exists():
            data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not data.empty:
                return data
        raise RuntimeError(f"No price data returned for {symbol} between {start} and {end} at interval={interval}.")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data.to_csv(cache_file)
    return data


def simulate_backtest(data, starting_cash: float, buy_threshold: float,
                     sell_threshold: float, ladder: tuple = (0.35, 0.75, 1.0)):
    cash = starting_cash
    shares = 0.0
    reference_price = None
    trades = []
    rows = []

    for timestamp, row in data.iterrows():
        price = float(row["Close"])

        if reference_price is None:
            reference_price = price
            equity = cash + shares * price
            rows.append([timestamp, price, None, "BASELINE", equity])
            continue

        pct_change = (price - reference_price) / reference_price
        action = "HOLD"

        if pct_change <= buy_threshold and cash > 1.0:
            buy_fraction = calculate_buy_fraction(pct_change, buy_threshold, ladder=ladder)
            if buy_fraction > 0:
                buy_amount = cash * buy_fraction
                qty_bought = buy_amount / price
                shares += qty_bought
                cash -= buy_amount
                action = f"BUY {qty_bought:.4f} sh ({buy_fraction * 100:.0f}% cash pyramid)"
                trades.append((timestamp, "BUY", price, qty_bought))

        elif pct_change >= sell_threshold and shares > 0:
            action = f"SELL {shares:.4f} sh"
            trades.append((timestamp, "SELL", price, shares))
            cash += shares * price
            shares = 0.0

        reference_price = price
        equity = cash + shares * price
        rows.append([timestamp, price, pct_change, action, equity])

    final_price = float(data["Close"].iloc[-1])
    final_equity = cash + shares * final_price
    return rows, trades, final_equity


def run_backtest(symbol: str, start: str, end: str, starting_cash: float,
                  interval: str = "1d", buy_threshold: float = BUY_THRESHOLD,
                  sell_threshold: float = SELL_THRESHOLD, use_cache: bool = True,
                  ladder: tuple = (0.35, 0.75, 1.0)):
    data = load_price_data(symbol, start, end, interval=interval, use_cache=use_cache)
    rows, trades, final_equity = simulate_backtest(data, starting_cash, buy_threshold, sell_threshold)

    first_price = float(data["Close"].iloc[0])
    final_price = float(data["Close"].iloc[-1])
    cash = starting_cash
    shares = 0.0
    reference_price = None
    for row in rows:
        if row[3] == "BASELINE":
            continue
        if row[3].startswith("BUY"):
            # approximate cash/shares state for summary output only
            cash = cash * 0.0
        elif row[3].startswith("SELL"):
            shares = 0.0
    buy_hold_equity = (starting_cash / first_price) * final_price

    # Recompute the final cash/share result from the trade stream to match the summary.
    cash = starting_cash
    shares = 0.0
    reference_price = None
    for timestamp, row in data.iterrows():
        price = float(row["Close"])
        if reference_price is None:
            reference_price = price
            continue
        pct_change = (price - reference_price) / reference_price
        if pct_change <= buy_threshold and cash > 1.0:
            buy_fraction = calculate_buy_fraction(pct_change, buy_threshold)
            if buy_fraction > 0:
                buy_amount = cash * buy_fraction
                qty = buy_amount / price
                shares += qty
                cash -= buy_amount
        elif pct_change >= sell_threshold and shares > 0:
            cash += shares * price
            shares = 0.0
        reference_price = price
    final_equity = cash + shares * final_price

    print("\n" + "=" * 64)
    print(f"Backtest: {symbol}  {start} -> {end}  interval={interval}  ({len(data)} bars)")
    print(f"Thresholds:         buy <= {buy_threshold*100:+.2f}%   sell >= {sell_threshold*100:+.2f}%")
    print(f"Starting cash:      ${starting_cash:,.2f}")
    print(f"Strategy equity:    ${final_equity:,.2f}   ({(final_equity / starting_cash - 1) * 100:+.2f}%)")
    print(f"Buy & hold equity:  ${buy_hold_equity:,.2f}   ({(buy_hold_equity / starting_cash - 1) * 100:+.2f}%)")
    print(f"Trades simulated:   {len(trades)}  ({sum(1 for t in trades if t[1] == 'BUY')} buys, "
          f"{sum(1 for t in trades if t[1] == 'SELL')} sells)")
    print(f"Ending position:    {shares:.4f} shares, ${cash:,.2f} cash")
    print("=" * 64)
    if interval == "1d":
        print("NOTE: daily bars stand in for the live bot's 2-minute checks - each bar covers a")
        print("full day's cumulative move, so this triggers trades far more readily per-check than")
        print("real 2-minute checks would, while also having ~195x fewer checks per day than live.")
        print("Pass --interval 2m (or 5m/15m) for a closer approximation - see README.md.")

    return rows, trades


def make_threshold_grid(buy_min=-0.05, buy_max=-0.005, buy_step=0.0025,
                        sell_min=0.02, sell_max=0.08, sell_step=0.0025):
    buys = []
    current = buy_min
    while current <= buy_max + 1e-9:
        buys.append(round(current, 6))
        current += buy_step

    sells = []
    current = sell_min
    while current <= sell_max + 1e-9:
        sells.append(round(current, 6))
        current += sell_step
    return buys, sells


def optimize_strategy(symbol: str, start: str, end: str, starting_cash: float,
                      intervals=None, buy_candidates=None, sell_candidates=None,
                      use_cache: bool = True, ladder_shapes=None):
    intervals = intervals or ["1d", "2m", "5m", "15m", "30m", "60m"]
    if buy_candidates is None or sell_candidates is None:
        buy_candidates, sell_candidates = make_threshold_grid()
    ladder_shapes = ladder_shapes or [
        (0.35, 0.75, 1.0),
        (0.4, 0.8, 1.0),
        (0.3, 0.6, 0.9),
        (0.45, 0.85, 1.0),
        (0.25, 0.5, 0.75),
    ]

    best = []
    for interval in intervals:
        try:
            data = load_price_data(symbol, start, end, interval=interval, use_cache=use_cache)
        except Exception:
            continue
        for ladder in ladder_shapes:
            for buy_threshold in buy_candidates:
                for sell_threshold in sell_candidates:
                    if sell_threshold <= abs(buy_threshold):
                        continue
                    rows, trades, final_equity = simulate_backtest(data, starting_cash, buy_threshold, sell_threshold, ladder=ladder)
                    best.append({
                        "interval": interval,
                        "ladder": ladder,
                        "buy_threshold": buy_threshold,
                        "sell_threshold": sell_threshold,
                        "final_equity": final_equity,
                        "return_pct": (final_equity / starting_cash - 1) * 100,
                        "trades": len(trades),
                    })

    if not best:
        return []
    return sorted(best, key=lambda x: x["final_equity"], reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Backtest the SOXL rolling-threshold strategy.")
    parser.add_argument("--symbol", default=SYMBOL, help=f"Ticker to backtest (default: {SYMBOL})")
    parser.add_argument("--start", default="2023-01-01", help="Start date, YYYY-MM-DD")
    parser.add_argument("--end", default=datetime.today().strftime("%Y-%m-%d"), help="End date, YYYY-MM-DD")
    parser.add_argument("--cash", type=float, default=10000.0, help="Starting cash (default: 10000)")
    parser.add_argument("--interval", default="1d",
                         help="Bar size: 1d (default), or intraday like 2m/5m/15m/30m/60m. "
                              "Yahoo limits how far back intraday data is available - see README.md.")
    parser.add_argument("--buy-threshold", type=float, default=BUY_THRESHOLD,
                         help=f"Buy trigger as a decimal, e.g. -0.01 for -1%% (default: {BUY_THRESHOLD})")
    parser.add_argument("--sell-threshold", type=float, default=SELL_THRESHOLD,
                         help=f"Sell trigger as a decimal, e.g. 0.01 for +1%% (default: {SELL_THRESHOLD})")
    parser.add_argument("--csv", default=None, help="Optional path to write the bar-by-bar results as CSV")
    args = parser.parse_args()

    rows, _ = run_backtest(args.symbol, args.start, args.end, args.cash,
                            interval=args.interval,
                            buy_threshold=args.buy_threshold,
                            sell_threshold=args.sell_threshold)

    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "close", "pct_change_vs_reference", "action", "equity"])
            writer.writerows(rows)
        print(f"\nBar-by-bar results written to {args.csv}")


if __name__ == "__main__":
    main()
