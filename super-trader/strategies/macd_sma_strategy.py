from __future__ import annotations

from typing import Any

import pandas as pd

from indicators import ema, sma
from strategies.base import Strategy


class MacdSmaStrategy(Strategy):
    name = "macd_sma"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.macd_fast = int((config or {}).get("macd_fast", 12))
        self.macd_slow = int((config or {}).get("macd_slow", 26))
        self.macd_signal = int((config or {}).get("macd_signal", 9))
        self.sma_fast = int((config or {}).get("sma_fast", 8))
        self.sma_slow = int((config or {}).get("sma_slow", 40))

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        if data.empty or "Close" not in data.columns:
            data["signal"] = 0
            return data

        macd_fast = ema(data["Close"], self.macd_fast)
        macd_slow = ema(data["Close"], self.macd_slow)
        macd_line = macd_fast - macd_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()

        data["macd_line"] = macd_line
        data["macd_signal"] = signal_line
        data["sma_fast"] = sma(data["Close"], self.sma_fast)
        data["sma_slow"] = sma(data["Close"], self.sma_slow)
        data["signal"] = 0

        bullish = (
            (data["macd_line"] > data["macd_signal"]) &
            (data["macd_line"] > 0) &
            (data["sma_fast"] > data["sma_slow"])
        )
        bearish = (
            (data["macd_line"] < data["macd_signal"]) |
            (data["macd_line"] < 0) |
            (data["sma_fast"] < data["sma_slow"])
        )

        data.loc[bullish, "signal"] = 1
        data.loc[bearish & (data["signal"] == 0), "signal"] = -1
        data.loc[data["sma_fast"].isna() | data["sma_slow"].isna(), "signal"] = 0

        data["signal"] = data["signal"].fillna(0).astype(int)
        return data
