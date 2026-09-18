"""
Shared configuration for the live trading bot and its backtest tool.
Keeping these in one place guarantees the backtest replays the exact same
thresholds the live bot uses.

Cron-friendly note:
  - the live bot reads environment overrides first if present
  - default values below match the tuned FNGU 5m profile: buy=-1.25%, sell=+2.5%
  - legacy SOXL env names remain supported for compatibility
"""

import os

SYMBOL = os.environ.get("TRADING_BOT_SYMBOL", os.environ.get("SOXL_BOT_SYMBOL", "SOXL")).upper()

# FNGU intraday defaults: buy=-1.25%, sell=+2.5%
DEFAULT_BUY_THRESHOLD = -0.0125
DEFAULT_SELL_THRESHOLD = 0.025

BUY_THRESHOLD = float(
    os.environ.get("TRADING_BOT_BUY_THRESHOLD",
                   os.environ.get("SOXL_BUY_THRESHOLD", DEFAULT_BUY_THRESHOLD))
)
SELL_THRESHOLD = float(
    os.environ.get("TRADING_BOT_SELL_THRESHOLD",
                   os.environ.get("SOXL_SELL_THRESHOLD", DEFAULT_SELL_THRESHOLD))
)
