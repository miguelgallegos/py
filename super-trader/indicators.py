from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    if window <= 1:
        return series.copy()
    return series.rolling(window=window, min_periods=1).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()
