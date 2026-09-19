#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any, Iterable

from backtest import BacktestEngine
from strategy_loader import resolve_strategy


DEFAULT_QUESTION = "Set the search values like: fast_window=5,10,15; slow_window=20,30,40; tp_levels=0.02,0.04,0.06; sl_levels=0.01,0.02"


def current_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_range_spec(raw: str | None, *, coerce_float: bool = False) -> list[Any]:
    if raw is None or raw.strip() == "":
        return []
    values: list[Any] = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [item.strip() for item in chunk.split(",") if item.strip()]
        if not parts:
            continue
        for item in parts:
            values.append(float(item) if coerce_float else int(item) if item.lstrip("-").isdigit() else float(item))
    return values


def parse_config_value(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return None
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text.startswith("(") and text.endswith(")"):
        inner = text[1:-1].strip()
        return tuple(parse_config_value(part) for part in inner.split(",") if part.strip())
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [parse_config_value(part) for part in inner.split(",") if part.strip()]
    try:
        if "." in text or "e" in text.lower():
            return float(text)
        return int(text)
    except ValueError:
        return text


def build_parameter_grid(parameter_map: dict[str, list[Any] | tuple[Any, ...]]) -> list[dict[str, Any]]:
    keys = list(parameter_map.keys())
    value_lists = [list(parameter_map[key]) for key in keys]
    grid: list[dict[str, Any]] = []

    for combo in product(*value_lists):
        payload: dict[str, Any] = {}
        for key, value in zip(keys, combo):
            payload[key] = value
        grid.append(payload)
    return grid


def select_best_result(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(results)
    if not rows:
        raise ValueError("No optimization results were produced.")

    def sort_key(item: dict[str, Any]) -> tuple[float, float]:
        trade_count = len(item.get("trades", [])) if isinstance(item.get("trades", []), list) else 0
        if trade_count == 0:
            return (-1_000_000.0, float(item.get("final_equity", 0.0)))
        return (float(item.get("return_pct", 0.0)), float(item.get("final_equity", 0.0)))

    return max(rows, key=sort_key)


def ensure_output_dir(path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def write_results_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = ensure_output_dir(path)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with target.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_results_json(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = ensure_output_dir(path)
    target.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")


def render_summary(best: dict[str, Any], parameter_map: dict[str, Any], symbol: str, start: str, end: str, interval: str) -> str:
    lines = [
        "Best strategy candidate",
        f"Timestamp: {current_timestamp()}",
        f"Symbol: {symbol}",
        f"Range: {start} to {end}",
        f"Interval: {interval}",
        "",
        "Recommended parameters:",
    ]
    for key in sorted(parameter_map):
        lines.append(f"- {key}: {parameter_map[key]}")
    trade_count = len(best.get("trades", [])) if isinstance(best.get("trades", []), list) else int(best.get("trades", 0))
    lines += [
        "",
        "Performance:",
        f"- Final equity: ${float(best.get('final_equity', 0.0)):,.2f}",
        f"- Return: {float(best.get('return_pct', 0.0)):,.2f}%",
        f"- Rate factor: {float(best.get('rate_factor', 0.0)):,.2f}x",
        f"- Profit factor: {float(best.get('profit_factor', 0.0)):,.2f}x",
        f"- Win rate: {float(best.get('win_rate', 0.0)):,.2f}%",
        f"- Max drawdown: ${float(best.get('max_drawdown', 0.0)):,.2f}",
        f"- Trades: {trade_count}",
    ]
    return "\n".join(lines) + "\n"


def run_optimizer(symbol: str, start: str, end: str, interval: str = "1d", strategy: str = "sma_crossover", parameter_map: dict[str, list[Any] | tuple[Any, ...]] | None = None, output_dir: str | None = None, max_results: int | None = None) -> list[dict[str, Any]]:
    parameter_map = parameter_map or {
        "fast_window": [5, 8, 10, 12, 15, 20],
        "slow_window": [20, 30, 40, 50, 60],
        "tp_levels": [(0.02, 0.04, 0.06), (0.03, 0.05, 0.08)],
        "sl_levels": [(0.01, 0.02), (0.02, 0.03)],
    }

    if strategy not in {"sma_crossover", "rsi", "macd", "bollinger"}:
        raise ValueError(f"Unsupported strategy '{strategy}'.")

    results: list[dict[str, Any]] = []
    for candidate in build_parameter_grid(parameter_map):
        config = deepcopy(candidate)
        config.setdefault("tp_levels", (0.02, 0.04, 0.06))
        config.setdefault("sl_levels", (0.01, 0.02))

        strategy_obj = resolve_strategy(strategy, config)
        engine = BacktestEngine(strategy_obj)
        result = engine.run(symbol, start, end, interval)
        result["strategy"] = strategy
        result["params"] = config
        results.append(result)

    def score_result(item: dict[str, Any]) -> tuple[float, float, float]:
        trade_count = len(item.get("trades", [])) if isinstance(item.get("trades", []), list) else 0
        if trade_count == 0:
            return (-1_000_000.0, float(item.get("final_equity", 0.0)), 0.0)
        return (float(item.get("return_pct", 0.0)), float(item.get("final_equity", 0.0)), float(item.get("win_rate", 0.0)))

    ranked = sorted(results, key=score_result, reverse=True)
    if max_results:
        ranked = ranked[:max_results]

    if output_dir:
        out_dir = ensure_output_dir(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_results_csv(out_dir / "optimizer_results.csv", [{
            "symbol": item.get("symbol", symbol),
            "strategy": item.get("strategy", strategy),
            "return_pct": item.get("return_pct", 0.0),
            "final_equity": item.get("final_equity", 0.0),
            "rate_factor": item.get("rate_factor", 0.0),
            "profit_factor": item.get("profit_factor", 0.0),
            "win_rate": item.get("win_rate", 0.0),
            "max_drawdown": item.get("max_drawdown", 0.0),
            "trades": len(item.get("trades", [])),
            "params": json.dumps(item.get("params", {}), default=str),
        } for item in ranked])
        write_results_json(out_dir / "optimizer_results.json", ranked)

        best = select_best_result(ranked)
        best_params = best.get("params", {})
        summary_path = out_dir / "best_strategy.txt"
        summary_path.write_text(render_summary(best, best_params, symbol, start, end, interval), encoding="utf-8")

    return ranked


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize a trading strategy over a user-defined parameter grid.")
    parser.add_argument("--symbol", default="SOXL")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-09-18")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--strategy", default="sma_crossover")
    parser.add_argument("--output-dir", default="optimization_results")
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--fast-window", default="5,8,10,12,15,20")
    parser.add_argument("--slow-window", default="20,30,40,50,60")
    parser.add_argument("--tp-levels", default="0.02,0.04,0.06;0.03,0.05,0.08")
    parser.add_argument("--sl-levels", default="0.01,0.02;0.02,0.03")
    args = parser.parse_args()

    param_map: dict[str, list[Any] | tuple[Any, ...]] = {
        "fast_window": [int(v) for v in args.fast_window.split(",") if v.strip()],
        "slow_window": [int(v) for v in args.slow_window.split(",") if v.strip()],
        "tp_levels": [tuple(float(x) for x in chunk.split(",") if x.strip()) for chunk in args.tp_levels.split(";") if chunk.strip()],
        "sl_levels": [tuple(float(x) for x in chunk.split(",") if x.strip()) for chunk in args.sl_levels.split(";") if chunk.strip()],
    }

    results = run_optimizer(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        interval=args.interval,
        strategy=args.strategy,
        parameter_map=param_map,
        output_dir=args.output_dir,
        max_results=args.max_results,
    )

    best = select_best_result(results)
    print(render_summary(best, best.get("params", {}), args.symbol, args.start, args.end, args.interval))
    print(f"Top {min(len(results), args.max_results)} configurations saved to {args.output_dir}")


if __name__ == "__main__":
    main()
