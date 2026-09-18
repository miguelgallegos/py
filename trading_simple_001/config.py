"""
Shared configuration for the SOXL trading bot and its backtest tool.
Keeping these in one place guarantees the backtest replays the exact same
thresholds the live bot uses.

Cron-friendly note:
  - the live bot reads environment overrides first if present
  - default values below match the currently tuned daily profile: buy=-3.3%, sell=+4.5%
"""

import os

SYMBOL = "SOXL"

# FOR DAILY - I feel the last price should be anchored to the last close, not the last reference move. This is a more
# DEFAULT_BUY_THRESHOLD = -0.033  # -3.3% - orig findings
# DEFAULT_SELL_THRESHOLD = 0.045  # +4.5%

# 5m - detected - see results.txt
DEFAULT_BUY_THRESHOLD = -0.001
DEFAULT_SELL_THRESHOLD = 0.001

BUY_THRESHOLD = float(os.environ.get("SOXL_BUY_THRESHOLD", DEFAULT_BUY_THRESHOLD))
SELL_THRESHOLD = float(os.environ.get("SOXL_SELL_THRESHOLD", DEFAULT_SELL_THRESHOLD))
