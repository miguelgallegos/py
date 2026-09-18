# Super Trader

A modular trading framework for backtesting, optimization, and live/paper trading with strategy swapping and Jesse-style trade management.

## Included strategies

- SMA crossover
- RSI
- MACD
- Bollinger Bands

## Trade management features

- multiple take-profit levels
- initial stop-loss
- trailing stop logic
- partial exit ladder behavior similar to Jesse-style execution
- broker abstraction for Robinhood and Alpaca

## Project layout

- `super_trader/` — engine, strategies, optimizer, data layer, trade manager, and broker adapters
- `run_backtest.py` — CLI runner for historical backtests
- `run_live.py` — CLI runner for signal evaluation / paper trading
- `strategy_registry.json` — registry of supported strategy classes and default params

## Quick start

### SMA crossover backtest

```bash
cd /Users/miguel.gallegos/Documents/py/super-trader
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy sma_crossover --fast 10 --slow 30 --tp 0.02,0.04,0.06 --sl 0.01,0.02
```

### RSI backtest

```bash
cd /Users/miguel.gallegos/Documents/py/super-trader
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy rsi --rsi-period 14
```

### MACD backtest

```bash
cd /Users/miguel.gallegos/Documents/py/super-trader
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy macd --macd-fast 12 --macd-slow 26
```

### Bollinger backtest

```bash
cd /Users/miguel.gallegos/Documents/py/super-trader
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy bollinger --bollinger-window 20
```

### Optimize SMA values

```bash
cd /Users/miguel.gallegos/Documents/py/super-trader
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy sma_crossover --optimize
```

### Formatted output options

```bash
cd /Users/miguel.gallegos/Documents/py/super-trader
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy sma_crossover --output-format text
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy sma_crossover --output-format csv
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy sma_crossover --output-format html
python3 run_backtest.py --symbol AAPL --start 2024-01-01 --end 2024-04-01 --strategy sma_crossover --output-format json
```

### Live / paper mode

```bash
cd /Users/miguel.gallegos/Documents/py/super-trader
python3 run_live.py --symbol AAPL --strategy sma_crossover --paper-trade
```

## Design goals

- pluggable strategy architecture
- strategy registry and easy parameter overrides
- backtesting + optimization support
- Jesse-style partial exits and trailing stops
- broker abstraction for Robinhood, Alpaca, and paper trading
