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

import yfinance as yf

from config import SYMBOL, BUY_THRESHOLD, SELL_THRESHOLD
from strategy import calculate_buy_fraction


def run_backtest(symbol: str, start: str, end: str, starting_cash: float,
                  interval: str = "1d", buy_threshold: float = BUY_THRESHOLD,
                  sell_threshold: float = SELL_THRESHOLD):
    data = yf.download(symbol, start=start, end=end, interval=interval, progress=False, auto_adjust=False)
    if data.empty:
        print(f"No price data returned for {symbol} between {start} and {end} at interval={interval}.")
        print("Tip: Yahoo Finance limits how far back intraday intervals go - see README.md.")
        sys.exit(1)

    # yfinance can return MultiIndex columns even for a single ticker in
    # some versions - flatten to plain column names if so.
    if isinstance(data.columns, __import__("pandas").MultiIndex):
        data.columns = data.columns.get_level_values(0)

    cash = starting_cash
    shares = 0.0
    reference_price = None
    trades = []
    rows = []  # for optional CSV export

    for timestamp, row in data.iterrows():
        price = float(row["Close"])

        if reference_price is None:
            # First bar: just establish the baseline, same as the live bot's
            # first-ever run.
            reference_price = price
            equity = cash + shares * price
            rows.append([timestamp, price, None, "BASELINE", equity])
            print(f"{timestamp} | close=${price:.2f} | (baseline - no prior reference yet)")
            continue

        pct_change = (price - reference_price) / reference_price
        action = "HOLD"

        if pct_change <= buy_threshold and cash > 1.0:
            buy_fraction = calculate_buy_fraction(pct_change, buy_threshold)
            if buy_fraction <= 0:
                action = "HOLD"
            else:
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

        # Rolling reference: reset every bar, trade or not - mirrors the
        # live bot's behavior exactly.
        reference_price = price
        equity = cash + shares * price
        rows.append([timestamp, price, pct_change, action, equity])

        print(f"{timestamp} | close=${price:>8.2f} | chg={pct_change*100:6.2f}% | "
              f"{action:16s} | equity=${equity:,.2f}")

    first_price = float(data["Close"].iloc[0])
    final_price = float(data["Close"].iloc[-1])
    final_equity = cash + shares * final_price
    buy_hold_equity = (starting_cash / first_price) * final_price

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
