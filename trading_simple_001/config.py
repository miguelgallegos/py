"""
Shared configuration for the SOXL trading bot and its backtest tool.
Keeping these in one place guarantees the backtest replays the exact same
thresholds the live bot uses.
"""

SYMBOL = "SOXL"
BUY_THRESHOLD = -0.025  # -2.5%
SELL_THRESHOLD = 0.035  # +3.5%
