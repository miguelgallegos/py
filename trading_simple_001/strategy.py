"""Shared strategy helpers for the SOXL rolling-threshold bot and backtest."""

from config import BUY_THRESHOLD


def calculate_buy_fraction(pct_change: float, buy_threshold: float = BUY_THRESHOLD) -> float:
    """Return the fraction of remaining buying power to deploy.

    This ladder pushes more capital into deeper pullbacks while still avoiding
    an all-in response on the first small dip. It is tuned to favor upside in
    strong downtrends without over-committing on a minor move.
    """
    if pct_change >= 0 or buy_threshold >= 0:
        return 0.0

    if abs(buy_threshold) <= 0:
        return 0.0

    magnitude = abs(pct_change) / abs(buy_threshold)
    if magnitude >= 4.0:
        return 1.0
    if magnitude >= 3.0:
        return 1.0
    if magnitude >= 2.0:
        return 0.75
    if magnitude >= 1.0:
        return 0.35
    return 0.0
