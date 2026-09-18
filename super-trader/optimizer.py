from __future__ import annotations

from itertools import product
from typing import Any

from backtest import BacktestEngine
from strategies.sma_crossover import SmaCrossoverStrategy


def optimize_strategy(symbol: str, start: str, end: str, interval: str = "1d", fast_range: list[int] | None = None, slow_range: list[int] | None = None) -> list[dict[str, Any]]:
    fast_range = fast_range or [5, 8, 10, 12, 15, 20]
    slow_range = slow_range or [20, 30, 40, 50, 60]

    results: list[dict[str, Any]] = []

    for fast in fast_range:
        for slow in slow_range:
            if slow <= fast:
                continue
            config = {"fast_window": fast, "slow_window": slow, "tp_levels": (0.02, 0.04, 0.06), "sl_levels": (0.01, 0.02)}
            strategy = SmaCrossoverStrategy(config)
            engine = BacktestEngine(strategy)
            result = engine.run(symbol, start, end, interval)
            results.append({
                "fast_window": fast,
                "slow_window": slow,
                "final_equity": float(result["final_equity"]),
                "return_pct": float(result["return_pct"]),
                "trades": len(result["trades"]),
            })

    return sorted(results, key=lambda x: x["return_pct"], reverse=True)
