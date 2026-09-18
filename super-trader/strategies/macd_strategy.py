from __future__ import annotations

from typing import Any

import pandas as pd

from indicators import ema
from strategies.base import Strategy


class MacdStrategy(Strategy):
    name = "macd"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.fast = int((config or {}).get("fast", 12))
        self.slow = int((config or {}).get("slow", 26))
        self.signal_period = int((config or {}).get("signal_period", 9))

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        fast_ema = ema(data["Close"], self.fast)
        slow_ema = ema(data["Close"], self.slow)
        macd = fast_ema - slow_ema
        signal_line = macd.ewm(span=self.signal_period, adjust=False).mean()
        data["macd"] = macd
        data["signal_line"] = signal_line
        data["signal"] = 0
        data.loc[data["macd"] > data["signal_line"], "signal"] = 1
        data.loc[data["macd"] < data["signal_line"], "signal"] = -1
        return data
