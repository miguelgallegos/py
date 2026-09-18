from __future__ import annotations

from typing import Any

import pandas as pd

from strategies.base import Strategy


class BollingerStrategy(Strategy):
    name = "bollinger"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.window = int((config or {}).get("window", 20))
        self.k = float((config or {}).get("k", 2.0))

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        rolling_mean = data["Close"].rolling(window=self.window).mean()
        rolling_std = data["Close"].rolling(window=self.window).std()
        upper = rolling_mean + self.k * rolling_std
        lower = rolling_mean - self.k * rolling_std
        data["upper_band"] = upper
        data["middle_band"] = rolling_mean
        data["lower_band"] = lower
        data["signal"] = 0
        data.loc[data["Close"] < data["lower_band"], "signal"] = 1
        data.loc[data["Close"] > data["upper_band"], "signal"] = -1
        return data
