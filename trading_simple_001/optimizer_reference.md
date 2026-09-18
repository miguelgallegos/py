# Intraday optimizer reference

This file records the exact commands and the current best-known settings for the SOXL-style laddered strategy used on TQQQ and FNGU.

## Current best intraday presets

### TQQQ
- Symbol: TQQQ
- Interval: 5m
- Buy threshold: -1.5%
- Sell threshold: +2.5%
- Ladder: (0.35, 0.75, 1.0)
- Result: +1.47% in the tested 2026-08-16 to 2026-09-16 window
- Preset name: `tqqq_intraday_2pct_goal`

### FNGU
- Symbol: FNGU
- Interval: 5m
- Buy threshold: -1.25%
- Sell threshold: +2.5%
- Ladder: (0.35, 0.75, 1.0)
- Result: +11.58% in the tested 2026-08-16 to 2026-09-16 window
- Preset name: `fngu_intraday_2pct_goal`

## Commands used for verification

From the project folder:

```bash
cd /Users/miguel.gallegos/Documents/py/trading_simple_001
. ../.venv/bin/activate
python3 -m py_compile multi_strategy_bot.py
python3 multi_strategy_bot.py --symbol TQQQ --interval 5m --cash 5000 --start 2026-08-16 --end 2026-09-16 --strategy-file strategy_presets.json --strategy-name tqqq_intraday_2pct_goal --optimize --results-file strategy_results_history.json | head -n 20
python3 multi_strategy_bot.py --symbol FNGU --interval 5m --cash 5000 --start 2026-08-16 --end 2026-09-16 --strategy-file strategy_presets.json --strategy-name fngu_intraday_2pct_goal --optimize --results-file strategy_results_history.json | head -n 20
```

To inspect the saved history:

```bash
cd /Users/miguel.gallegos/Documents/py/trading_simple_001
python3 - <<'PY'
import json
from pathlib import Path
p = Path('strategy_results_history.json')
print('history_file_exists', p.exists())
if p.exists():
    data = json.loads(p.read_text())
    print('entries', len(data.get('history', [])))
    for item in data.get('history', [])[-4:]:
        print(item['symbol'], item['strategy_name'], item['result']['buy_threshold'], item['result']['sell_threshold'], round(item['result']['return_pct'], 2))
PY
```

## Notes

- This is the same pyramid/ladder logic used by the SOXL bot: buy on a falling reference, increase quantity with deeper drops, and sell on a recovery threshold.
- The preset file is the easiest place to keep a reusable catalog of symbol-specific intraday settings.
- These settings are valid as a reference check, but they should be re-optimized periodically as market conditions change.
