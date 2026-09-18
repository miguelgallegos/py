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
    exit_timestamp: pd.Timestamp | None = None


class BacktestEngine:
    def __init__(self, strategy: Strategy):
        self.strategy = strategy

    def run(self, symbol: str, start: str, end: str, interval: str = "1d", cash: float = 10000.0) -> dict[str, Any]:
        df = load_market_data(symbol, start, end, interval)
        signal_df = self.strategy.generate_signals(df)

        initial_cash = float(cash)
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
                trade = Trade(idx, "LONG", entry_price, close, qty, pnl, "signal_flip")
                trade.exit_timestamp = idx
                trades.append(trade)
                cash += pnl + qty * close
                position = 0
                qty = 0.0
                entry_price = 0.0

            equity_curve.append({"timestamp": idx, "equity": cash + (position * qty * close)})

        final_equity = cash + (position * qty * signal_df["Close"].iloc[-1])
        equity_df = pd.DataFrame(equity_curve)
        peak = equity_df["equity"].cummax()
        drawdown_amount = (peak - equity_df["equity"]).max() if not equity_df.empty else 0.0
        drawdown_pct = (drawdown_amount / peak.max()) * 100.0 if not equity_df.empty and peak.max() else 0.0
        rate_factor = (final_equity / initial_cash) if initial_cash else 0.0

        return {
            "symbol": symbol,
            "start": start,
            "end": end,
            "interval": interval,
            "initial_cash": initial_cash,
            "final_equity": final_equity,
            "return_pct": ((final_equity / initial_cash) - 1.0) * 100.0 if initial_cash else 0.0,
            "rate_factor": rate_factor,
            "max_drawdown": drawdown_amount,
            "max_drawdown_pct": drawdown_pct,
            "trades": trades,
            "equity_curve": equity_df,
        }
