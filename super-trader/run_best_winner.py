#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from run_optimizer_scan import PRESETS
from strategy_optimizer import run_optimizer, select_best_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick-scan multiple symbols, pick the winner, then deep-scan the winner only.")
    parser.add_argument("--symbols", default="SOXL,TQQQ,FNGU")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2026-09-18")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--quick-preset", default="quick")
    parser.add_argument("--deep-preset", default="deep")
    parser.add_argument("--output-dir", default="winner_scan")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        raise ValueError("At least one symbol is required.")

    quick_preset = PRESETS[args.quick_preset].copy()
    comparison_rows = []
    for symbol in symbols:
        results = run_optimizer(
            symbol=symbol,
            start=args.start,
            end=args.end,
            interval=args.interval,
            strategy=quick_preset.get("strategy", "sma_crossover"),
            parameter_map={
                key: value
                for key, value in {
                    "fast_window": [int(v) for v in str(quick_preset.get("fast_window", "5,8,10")).split(",") if v.strip()],
                    "slow_window": [int(v) for v in str(quick_preset.get("slow_window", "20,30,40")).split(",") if v.strip()],
                    "tp_levels": [tuple(float(x) for x in chunk.split(",") if x.strip()) for chunk in str(quick_preset.get("tp_levels", "0.02,0.04,0.06")).split(";") if chunk.strip()],
                    "sl_levels": [tuple(float(x) for x in chunk.split(",") if x.strip()) for chunk in str(quick_preset.get("sl_levels", "0.01,0.02")).split(";") if chunk.strip()],
                }.items()
            },
            output_dir=str(Path(args.output_dir) / symbol),
            max_results=quick_preset.get("max_results", 20),
        )
        best = select_best_result(results)
        comparison_rows.append({
            "symbol": symbol,
            "best_params": best.get("params", {}),
            "final_equity": float(best.get("final_equity", 0.0)),
            "return_pct": float(best.get("return_pct", 0.0)),
            "rate_factor": float(best.get("rate_factor", 0.0)),
            "profit_factor": float(best.get("profit_factor", 0.0)),
            "win_rate": float(best.get("win_rate", 0.0)),
            "max_drawdown": float(best.get("max_drawdown", 0.0)),
            "trades": len(best.get("trades", [])),
        })

    winner = max(comparison_rows, key=lambda row: row["return_pct"])
    winner_symbol = winner["symbol"]
    deep_preset = PRESETS[args.deep_preset].copy()
    deep_param_map = {}
    for key in ["fast_window", "slow_window", "tp_levels", "sl_levels"]:
        if key not in deep_preset:
            continue
        value = deep_preset[key]
        if key in {"fast_window", "slow_window"}:
            deep_param_map[key] = [int(v) for v in str(value).split(",") if v.strip()]
        else:
            deep_param_map[key] = [tuple(float(x) for x in chunk.split(",") if x.strip()) for chunk in str(value).split(";") if chunk.strip()]

    deeper_results = run_optimizer(
        symbol=winner_symbol,
        start=args.start,
        end=args.end,
        interval=args.interval,
        strategy=deep_preset.get("strategy", "sma_crossover"),
        parameter_map=deep_param_map,
        output_dir=str(Path(args.output_dir) / f"{winner_symbol}_deep"),
        max_results=deep_preset.get("max_results", 50),
    )
    best_deep = select_best_result(deeper_results)

    print("\n=== QUICK SCAN WINNER ===")
    print(winner)
    print("\n=== DEEP SCAN BEST FOR WINNER ===")
    print({
        "symbol": winner_symbol,
        "params": best_deep.get("params", {}),
        "final_equity": float(best_deep.get("final_equity", 0.0)),
        "return_pct": float(best_deep.get("return_pct", 0.0)),
        "rate_factor": float(best_deep.get("rate_factor", 0.0)),
        "profit_factor": float(best_deep.get("profit_factor", 0.0)),
        "win_rate": float(best_deep.get("win_rate", 0.0)),
        "max_drawdown": float(best_deep.get("max_drawdown", 0.0)),
        "trades": len(best_deep.get("trades", [])),
    })

    output_summary = Path(args.output_dir) / "winner_summary.txt"
    output_summary.parent.mkdir(parents=True, exist_ok=True)
    output_summary.write_text(
        "Winner: " + winner_symbol + "\n" +
        "Quick best: " + str(winner["best_params"]) + "\n" +
        "Deep best: " + str(best_deep.get("params", {})) + "\n" +
        "Deep return: " + str(best_deep.get("return_pct", 0.0)) + "%\n" +
        "Final equity: $" + f"{float(best_deep.get('final_equity', 0.0)):,.2f}" + "\n",
        encoding="utf-8",
    )
    print(f"\nSummary written to: {output_summary.resolve()}")


if __name__ == "__main__":
    main()
