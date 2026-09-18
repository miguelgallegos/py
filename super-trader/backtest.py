from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from data import load_market_data
from strategies.base import Strategy


@dataclass
class Trade:
    timestamp: pd.Timestamp
    side: str
    entry: float
    exit: float
    qty: float
    pnl: float
    reason: str = ""


class BacktestEngine:
    def __init__(self, strategy: Strategy):
        self.strategy = strategy

    def run(self, symbol: str, start: str, end: str, interval: str = "1d", cash: float = 10000.0) -> dict[str, Any]:
        df = load_market_data(symbol, start, end, interval)
        signal_df = self.strategy.generate_signals(df)

        position = 0
        entry_price = 0.0
        qty = 0.0
        trades: list[Trade] = []
        equity_curve: list[dict[str, Any]] = []

        for idx, row in signal_df.iterrows():
            close = float(row["Close"])
            signal = int(row.get("signal", 0))

            if position == 0 and signal == 1:
                qty = cash / close
                position = 1
                entry_price = close
            elif position == 1 and signal == -1:
                pnl = (close - entry_price) * qty
                trades.append(Trade(idx, "LONG", entry_price, close, qty, pnl, "signal_flip"))
                cash += pnl + qty * close
                position = 0
                qty = 0.0
                entry_price = 0.0

            equity_curve.append({"timestamp": idx, "equity": cash + (position * qty * close)})

        final_equity = cash + (position * qty * signal_df["Close"].iloc[-1])
        return {
            "symbol": symbol,
            "start": start,
            "end": end,
            "interval": interval,
            "final_equity": final_equity,
            "return_pct": ((final_equity / 10000.0) - 1.0) * 100.0,
            "trades": trades,
            "equity_curve": pd.DataFrame(equity_curve),
        }
