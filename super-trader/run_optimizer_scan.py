#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from strategy_optimizer import run_optimizer, select_best_result


PRESETS = {
    "quick": {
        "strategy": "sma_crossover",
        "fast_window": "5,8,10,12",
        "slow_window": "20,30,40",
        "tp_levels": "0.02,0.04,0.06;0.03,0.05,0.08",
        "sl_levels": "0.01,0.02;0.02,0.03",
        "max_results": 20,
    },
    "deep": {
        "strategy": "sma_crossover",
        "fast_window": "5,8,10,12,15,20,25",
        "slow_window": "20,30,40,50,60,80",
        "tp_levels": "0.01,0.02,0.03,0.04,0.05,0.06,0.08;0.02,0.04,0.06,0.08,0.10",
        "sl_levels": "0.005,0.01,0.015,0.02,0.025,0.03;0.01,0.02,0.03,0.04",
        "max_results": 50,
    },
    "leverage": {
        "strategy": "sma_crossover",
        "symbols": "SOXL,TQQQ,FNGU",
        "fast_window": "5,8,10,12",
        "slow_window": "20,30,40",
        "tp_levels": "0.02,0.04,0.06;0.03,0.05,0.08",
        "sl_levels": "0.01,0.02;0.02,0.03",
        "max_results": 20,
    },
    "rsi": {
        "strategy": "rsi",
        "rsi_period": "7,12,14,21,30",
        "oversold": "20,25,30,35",
        "overbought": "65,70,75,80",
        "max_results": 30,
    },
    "macd": {
        "strategy": "macd",
        "fast": "8,12,16",
        "slow": "20,26,34",
        "signal_period": "5,9,12",
        "max_results": 30,
    },
    "bollinger": {
        "strategy": "bollinger",
        "window": "10,15,20,25,30",
        "k": "1.5,2.0,2.5,3.0",
        "max_results": 30,
    },
}


def build_parameter_map(args: argparse.Namespace) -> dict:
    param_map: dict[str, list] = {}
    if hasattr(args, "fast_window") and args.fast_window:
        param_map["fast_window"] = [int(v) for v in args.fast_window.split(",") if v.strip()]
    if hasattr(args, "slow_window") and args.slow_window:
        param_map["slow_window"] = [int(v) for v in args.slow_window.split(",") if v.strip()]
    if hasattr(args, "rsi_period") and args.rsi_period:
        param_map["rsi_period"] = [int(v) for v in args.rsi_period.split(",") if v.strip()]
    if hasattr(args, "oversold") and args.oversold:
        param_map["oversold"] = [float(v) for v in args.oversold.split(",") if v.strip()]
    if hasattr(args, "overbought") and args.overbought:
        param_map["overbought"] = [float(v) for v in args.overbought.split(",") if v.strip()]
    if hasattr(args, "fast") and args.fast:
        param_map["fast"] = [int(v) for v in args.fast.split(",") if v.strip()]
    if hasattr(args, "slow") and args.slow:
        param_map["slow"] = [int(v) for v in args.slow.split(",") if v.strip()]
    if hasattr(args, "signal_period") and args.signal_period:
        param_map["signal_period"] = [int(v) for v in args.signal_period.split(",") if v.strip()]
    if hasattr(args, "window") and args.window:
        param_map["window"] = [int(v) for v in args.window.split(",") if v.strip()]
    if hasattr(args, "k") and args.k:
        param_map["k"] = [float(v) for v in args.k.split(",") if v.strip()]
    if hasattr(args, "tp_levels") and args.tp_levels:
        param_map["tp_levels"] = [tuple(float(x) for x in chunk.split(",") if x.strip()) for chunk in args.tp_levels.split(";") if chunk.strip()]
    if hasattr(args, "sl_levels") and args.sl_levels:
        param_map["sl_levels"] = [tuple(float(x) for x in chunk.split(",") if x.strip()) for chunk in args.sl_levels.split(";") if chunk.strip()]

    if not param_map:
        preset = PRESETS[args.preset]
        param_map = {
            key: value for key, value in (
                ("fast_window", [int(v) for v in preset["fast_window"].split(",") if v.strip()]) if "fast_window" in preset else (key, value)
                for key, value in []
            )
        }

    return param_map


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch a quick or deep optimization scan and save the best candidate.")
    parser.add_argument("--preset", choices=["quick", "deep", "leverage", "rsi", "macd", "bollinger"], default="quick")
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-09-18")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--output-dir", default="optimization_results")
    parser.add_argument("--fast-window", default=None)
    parser.add_argument("--slow-window", default=None)
    parser.add_argument("--tp-levels", default=None)
    parser.add_argument("--sl-levels", default=None)
    parser.add_argument("--rsi-period", default=None)
    parser.add_argument("--oversold", default=None)
    parser.add_argument("--overbought", default=None)
    parser.add_argument("--fast", default=None)
    parser.add_argument("--slow", default=None)
    parser.add_argument("--signal-period", default=None)
    parser.add_argument("--window", default=None)
    parser.add_argument("--k", default=None)
    parser.add_argument("--max-results", type=int, default=None)
    args = parser.parse_args()

    preset = PRESETS[args.preset].copy()
    if args.strategy:
        preset["strategy"] = args.strategy
    if args.fast_window:
        preset["fast_window"] = args.fast_window
    if args.slow_window:
        preset["slow_window"] = args.slow_window
    if args.tp_levels:
        preset["tp_levels"] = args.tp_levels
    if args.sl_levels:
        preset["sl_levels"] = args.sl_levels
    if args.rsi_period:
        preset["rsi_period"] = args.rsi_period
    if args.oversold:
        preset["oversold"] = args.oversold
    if args.overbought:
        preset["overbought"] = args.overbought
    if args.fast:
        preset["fast"] = args.fast
    if args.slow:
        preset["slow"] = args.slow
    if args.signal_period:
        preset["signal_period"] = args.signal_period
    if args.window:
        preset["window"] = args.window
    if args.k:
        preset["k"] = args.k
    if args.max_results:
        preset["max_results"] = args.max_results

    param_map: dict[str, list] = {}
    for key in [
        "fast_window",
        "slow_window",
        "tp_levels",
        "sl_levels",
        "rsi_period",
        "oversold",
        "overbought",
        "fast",
        "slow",
        "signal_period",
        "window",
        "k",
    ]:
        if key not in preset:
            continue
        value = preset[key]
        if key in {"fast_window", "slow_window", "rsi_period", "fast", "slow", "signal_period", "window"}:
            param_map[key] = [int(v) for v in str(value).split(",") if v.strip()]
        elif key in {"oversold", "overbought", "k"}:
            param_map[key] = [float(v) for v in str(value).split(",") if v.strip()]
        elif key in {"tp_levels", "sl_levels"}:
            param_map[key] = [tuple(float(x) for x in chunk.split(",") if x.strip()) for chunk in str(value).split(";") if chunk.strip()]

    strategy_name = preset.get("strategy", args.strategy or "sma_crossover")
    symbols = [item.strip() for item in (args.symbols or preset.get("symbols") or (args.symbol or "SOXL")).split(",") if item.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    comparison_rows: list[dict] = []
    for symbol in symbols:
        symbol_output_dir = output_dir / symbol
        results = run_optimizer(
            symbol=symbol,
            start=args.start,
            end=args.end,
            interval=args.interval,
            strategy=strategy_name,
            parameter_map=param_map,
            output_dir=str(symbol_output_dir),
            max_results=preset.get("max_results", args.max_results or 20),
        )
        best = select_best_result(results)
        comparison_rows.append({
            "symbol": symbol,
            "best_params": json.dumps(best.get("params", {}), default=str),
            "final_equity": float(best.get("final_equity", 0.0)),
            "return_pct": float(best.get("return_pct", 0.0)),
            "rate_factor": float(best.get("rate_factor", 0.0)),
            "profit_factor": float(best.get("profit_factor", 0.0)),
            "win_rate": float(best.get("win_rate", 0.0)),
            "max_drawdown": float(best.get("max_drawdown", 0.0)),
            "trades": len(best.get("trades", [])),
        })
        print(f"\n=== {symbol} ===")
        print(f"Best: {best.get('params')} | return={best.get('return_pct')} | final_equity={best.get('final_equity')} | trades={len(best.get('trades', []))}")

    comparison_file = output_dir / "symbol_comparison.csv"
    with comparison_file.open("w", newline="", encoding="utf-8") as fh:
        import csv
        writer = csv.DictWriter(fh, fieldnames=["symbol", "best_params", "final_equity", "return_pct", "rate_factor", "profit_factor", "win_rate", "max_drawdown", "trades"])
        writer.writeheader()
        writer.writerows(comparison_rows)

    print(f"\nComparison file saved to: {comparison_file.resolve()}")

    if len(symbols) > 1:
        print("\nSymbol comparison ranking:")
        for row in sorted(comparison_rows, key=lambda x: x["return_pct"], reverse=True):
            print(f"- {row['symbol']}: return={row['return_pct']}% final_equity=${row['final_equity']:,.2f} best={row['best_params']}")


if __name__ == "__main__":
    main()
