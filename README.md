# Py

This repository contains a small set of Python experiments and trading tools, with the main active project being the SOXL rolling-threshold strategy in `trading_simple_001`.

## Included projects

- `trading_simple_001/` — SOXL momentum/backtest bot using a rolling threshold and pyramiding buy logic
- `trading_api/` — API prototype and exchange abstraction work
- `projects-01/` — miscellaneous Python experiments and data-processing scripts
- `projects-02/` — additional scratch/project work

## Active strategy

The SOXL bot in `trading_simple_001` uses:

- Buy trigger: -2%
- Sell trigger: +4%
- Pyramiding: deeper downturns add more size aggressively before the sell exit fires

See the project README here:

- [trading_simple_001/README.md](trading_simple_001/README.md)

## Quick start

```bash
cd trading_simple_001
python3 -m pip install -r requirements.txt
python3 backtest.py --start 2025-09-15 --end 2026-09-15 --buy-threshold -0.02 --sell-threshold 0.04 --cash 50000
```

## Notes

- This repo includes personal experimentation code and trade scripts.
- Environment files and generated logs are intentionally ignored by git.
- Use your own credentials and appropriate caution when testing live trading logic.
