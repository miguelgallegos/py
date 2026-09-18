from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def _normalize_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return frame

    if isinstance(frame.columns, pd.MultiIndex):
        frame = frame.copy()
        frame.columns = frame.columns.get_level_values(0)

    frame = frame.copy()
    parsed_index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame.loc[parsed_index.notna()].copy()
    frame.index = parsed_index[parsed_index.notna()]
    frame.columns = [str(col).strip() for col in frame.columns]

    for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

    return frame.dropna(subset=["Close"]).copy()


def load_market_data(symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    cache_file = DATA_DIR / f"{symbol.lower()}_{interval}_{start}_{end}.csv"
    if cache_file.exists():
        try:
            cached = pd.read_csv(cache_file, index_col=0)
            normalized = _normalize_price_frame(cached)
            if not normalized.empty and "Close" in normalized.columns:
                return normalized
        except Exception:
            cache_file.unlink(missing_ok=True)

    df = yf.download(symbol, start=start, end=end, interval=interval, progress=False, auto_adjust=False)
    if df.empty:
        raise ValueError(f"No market data found for {symbol} from {start} to {end} at {interval}.")

    df = _normalize_price_frame(df)
    if df.empty:
        raise ValueError(f"No usable price data found for {symbol} after normalization.")

    df.to_csv(cache_file)
    return df
