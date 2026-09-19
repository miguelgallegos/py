#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def render_report(template_path: str | Path, values: dict[str, object]) -> str:
    template = Path(template_path).read_text(encoding="utf-8")
    return template.format(**values)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a polished report using a text template and values file.")
    parser.add_argument("--template", default="report_template.txt")
    parser.add_argument("--output", default="winner_report.txt")
    parser.add_argument("--symbol", default="SOXL")
    parser.add_argument("--quick-fast-window", default="8")
    parser.add_argument("--quick-slow-window", default="30")
    parser.add_argument("--quick-tp-levels", default="(0.02, 0.04, 0.06)")
    parser.add_argument("--quick-sl-levels", default="(0.01, 0.02)")
    parser.add_argument("--deep-fast-window", default="20")
    parser.add_argument("--deep-slow-window", default="30")
    parser.add_argument("--deep-tp-levels", default="(0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08)")
    parser.add_argument("--deep-sl-levels", default="(0.005, 0.01, 0.015, 0.02, 0.025, 0.03)")
    parser.add_argument("--return-pct", default="755.59")
    parser.add_argument("--final-equity", default="85559.46")
    parser.add_argument("--strategy", default="sma_crossover")
    args = parser.parse_args()

    values = {
        "symbol": args.symbol,
        "quick_fast_window": args.quick_fast_window,
        "quick_slow_window": args.quick_slow_window,
        "quick_tp_levels": args.quick_tp_levels,
        "quick_sl_levels": args.quick_sl_levels,
        "deep_fast_window": args.deep_fast_window,
        "deep_slow_window": args.deep_slow_window,
        "deep_tp_levels": args.deep_tp_levels,
        "deep_sl_levels": args.deep_sl_levels,
        "return_pct": args.return_pct,
        "final_equity": float(args.final_equity),
        "strategy": args.strategy,
    }

    rendered = render_report(args.template, values)
    target = Path(args.output)
    target.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
