from __future__ import annotations

from typing import Any

import pandas as pd

from strategies.base import Strategy


class RsiStrategy(Strategy):
    name = "rsi"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.period = int((config or {}).get("rsi_period", 14))
        self.oversold = float((config or {}).get("oversold", 30.0))
        self.overbought = float((config or {}).get("overbought", 70.0))

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        delta = data["Close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)
        data["rsi"] = rsi
        data["signal"] = 0
        data.loc[(data["rsi"] < self.oversold), "signal"] = 1
        data.loc[(data["rsi"] > self.overbought), "signal"] = -1
        return data
