from __future__ import annotations

from typing import Any

import pandas as pd

from indicators import sma
from strategies.base import Strategy


class SmaCrossoverStrategy(Strategy):
    name = "sma_crossover"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.fast_window = int((config or {}).get("fast_window", 10))
        self.slow_window = int((config or {}).get("slow_window", 30))
        self.tp_levels = tuple(float(v) for v in (config or {}).get("tp_levels", (0.02, 0.04, 0.06)))
        self.sl_levels = tuple(float(v) for v in (config or {}).get("sl_levels", (0.01, 0.02)))
        self.allow_short = bool((config or {}).get("allow_short", False))

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data["fast_sma"] = sma(data["Close"], self.fast_window)
        data["slow_sma"] = sma(data["Close"], self.slow_window)
        data["signal"] = 0

        data.loc[data["fast_sma"] > data["slow_sma"], "signal"] = 1
        data.loc[data["fast_sma"] < data["slow_sma"], "signal"] = -1

        data["position"] = data["signal"].shift(1).fillna(0).astype(int)
        data["entry_price"] = float("nan")
        data["take_profit"] = float("nan")
        data["stop_loss"] = float("nan")

        for idx in range(1, len(data)):
            row = data.iloc[idx]
            prev_row = data.iloc[idx - 1]
            prev_pos = int(prev_row["position"])
            curr_signal = int(row["signal"])
            close = float(row["Close"])

            if prev_pos == 0 and curr_signal == 1:
                data.at[data.index[idx], "entry_price"] = close
                data.at[data.index[idx], "take_profit"] = close * (1 + self.tp_levels[0])
                data.at[data.index[idx], "stop_loss"] = close * (1 - self.sl_levels[0])
            elif prev_pos == 1 and curr_signal == -1:
                data.at[data.index[idx], "entry_price"] = close
                data.at[data.index[idx], "take_profit"] = close * (1 + self.tp_levels[0])
                data.at[data.index[idx], "stop_loss"] = close * (1 - self.sl_levels[0])

        return data
