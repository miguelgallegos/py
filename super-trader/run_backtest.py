#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from pprint import pprint
from typing import Any

from backtest import BacktestEngine
from optimizer import optimize_strategy
from strategy_loader import resolve_strategy


def build_strategy(name: str, config: dict) -> object:
    return resolve_strategy(name, config)


def current_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_summary_file(summary_text: str, summary_path: str | None) -> None:
    if not summary_path:
        return
    path = Path(summary_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary_text.rstrip() + "\n", encoding="utf-8")


def normalize_trade(trade: Any) -> dict[str, Any]:
    if isinstance(trade, dict):
        normalized = dict(trade)
    elif hasattr(trade, "__dict__"):
        normalized = {key: value for key, value in vars(trade).items()}
    else:
        normalized = {"value": trade}

    for key in ("timestamp", "entry_timestamp", "exit_timestamp"):
        raw_ts = normalized.get(key)
        if raw_ts is not None:
            if hasattr(raw_ts, "isoformat"):
                normalized[key] = raw_ts.isoformat()
            else:
                normalized[key] = str(raw_ts)
    return normalized


def format_money(value: Any) -> str:
    return f"${float(value):,.2f}"


def format_pct(value: Any) -> str:
    return f"{float(value):,.2f}%"


def format_rate(value: Any) -> str:
    return f"{float(value):,.2f}x"


def render_results(result: dict[str, Any], output_format: str = "text") -> str:
    fmt = (output_format or "text").lower()
    timestamp = result.get("timestamp") or result.get("generated_at") or current_timestamp()
    result_with_ts = dict(result)
    result_with_ts["timestamp"] = timestamp
    trades = [normalize_trade(trade) for trade in result_with_ts.get("trades", [])]
    result_with_ts["trades"] = trades
    initial_cash = result_with_ts.get("initial_cash", 0.0)
    final_equity = result_with_ts.get("final_equity", 0.0)
    return_pct = result_with_ts.get("return_pct", 0.0)
    rate_factor = result_with_ts.get("rate_factor", 0.0)
    max_drawdown = result_with_ts.get("max_drawdown", 0.0)
    max_drawdown_pct = result_with_ts.get("max_drawdown_pct", 0.0)

    if fmt == "json":
        return json.dumps(result_with_ts, default=str, indent=2)

    if fmt == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "symbol", "initial_cash", "final_equity", "return_pct", "rate_factor", "max_drawdown", "max_drawdown_pct", "start", "end", "interval", "trade_count"])
        writer.writerow([
            timestamp,
            result_with_ts.get("symbol", ""),
            initial_cash,
            final_equity,
            return_pct,
            rate_factor,
            max_drawdown,
            max_drawdown_pct,
            result_with_ts.get("start", ""),
            result_with_ts.get("end", ""),
            result_with_ts.get("interval", ""),
            len(trades),
        ])
        return output.getvalue()

    if fmt == "html":
        rows = "".join(
            f"<tr><td>{trade.get('timestamp', '')}</td><td>{trade.get('exit_timestamp', trade.get('timestamp', ''))}</td><td>{trade.get('side', '')}</td><td>{trade.get('entry', '')}</td><td>{trade.get('exit', '')}</td><td>{trade.get('qty', '')}</td><td>{trade.get('pnl', '')}</td><td>{trade.get('reason', '')}</td></tr>"
            for trade in trades
        )
        return f"""
<html>
  <head><title>Backtest Results</title></head>
  <body>
    <h1>{result_with_ts.get('symbol', '')} Backtest</h1>
    <p>Timestamp: {timestamp}</p>
    <p>Range: {result_with_ts.get('start', '')} to {result_with_ts.get('end', '')}</p>
    <p>Interval: {result_with_ts.get('interval', '')}</p>
    <p>Initial cash: {format_money(initial_cash)}</p>
    <p>Final equity: {format_money(final_equity)}</p>
    <p>Return: {format_pct(return_pct)}</p>
    <p>Rate factor: {format_rate(rate_factor)}</p>
    <p>Max drawdown: {format_money(max_drawdown)} ({format_pct(max_drawdown_pct)})</p>
    <p>Trades: {len(trades)}</p>
    <table>
      <thead><tr><th>Entry Date</th><th>Exit Date</th><th>Side</th><th>Entry</th><th>Exit</th><th>Qty</th><th>PnL</th><th>Reason</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </body>
</html>
""".strip()

    lines = [
        f"Backtest: {result_with_ts.get('symbol', '')}",
        f"Timestamp: {timestamp}",
        f"Range: {result_with_ts.get('start', '')} to {result_with_ts.get('end', '')}",
        f"Interval: {result_with_ts.get('interval', '')}",
        f"Initial cash: {format_money(initial_cash)}",
        f"Final equity: {format_money(final_equity)}",
        f"Return: {format_pct(return_pct)}",
        f"Rate factor: {format_rate(rate_factor)}",
        f"Max drawdown: {format_money(max_drawdown)} ({format_pct(max_drawdown_pct)})",
        f"Trades: {len(trades)}",
        "",
        "Trade Details:",
    ]

    if trades:
        lines.append("| Entry Date          | Exit Date           | Side | Entry   | Exit    | Qty | PnL    | Reason |")
        lines.append("|--------------------|---------------------|------|---------|---------|-----|--------|--------|")
        for trade in trades:
            entry = trade.get("entry", "")
            exit_price = trade.get("exit", "")
            qty = trade.get("qty", "")
            pnl = trade.get("pnl", "")
            reason = trade.get("reason", "")
            entry_date = trade.get("timestamp", "")
            exit_date = trade.get("exit_timestamp", trade.get("timestamp", ""))
            side = trade.get("side", "")
            lines.append(f"| {entry_date:<18} | {exit_date:<19} | {side:<4} | {entry:>7.2f} | {exit_price:>7.2f} | {qty:>4.1f} | {pnl:>7.2f} | {reason:<7} |")
    else:
        lines.append("No trades executed.")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest a pluggable strategy with Jesse-style trade management.")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default="2024-04-01")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--strategy", default="sma_crossover")
    parser.add_argument("--fast", type=int, default=10)
    parser.add_argument("--slow", type=int, default=30)
    parser.add_argument("--rsi-period", type=int, default=14)
    parser.add_argument("--macd-fast", type=int, default=12)
    parser.add_argument("--macd-slow", type=int, default=26)
    parser.add_argument("--bollinger-window", type=int, default=20)
    parser.add_argument("--tp", default="0.02,0.04,0.06")
    parser.add_argument("--sl", default="0.01,0.02")
    parser.add_argument("--optimize", action="store_true")
    parser.add_argument("--output-format", choices=["text", "csv", "html", "json"], default="text")
    parser.add_argument("--summary-file", help="Write the rendered backtest summary to a file.")
    args = parser.parse_args()

    base_config = {
        "tp_levels": tuple(float(v) for v in args.tp.split(",") if v.strip()),
        "sl_levels": tuple(float(v) for v in args.sl.split(",") if v.strip()),
    }

    if args.strategy == "sma_crossover":
        base_config.update({"fast_window": args.fast, "slow_window": args.slow})
    elif args.strategy == "rsi":
        base_config.update({"rsi_period": args.rsi_period})
    elif args.strategy == "macd":
        base_config.update({"fast": args.macd_fast, "slow": args.macd_slow})
    elif args.strategy == "bollinger":
        base_config.update({"window": args.bollinger_window})

    strategy = build_strategy(args.strategy, base_config)
    engine = BacktestEngine(strategy)

    if args.optimize:
        results = optimize_strategy(args.symbol, args.start, args.end, args.interval)
        output = ""
        if args.output_format == "json":
            output = json.dumps(results[:10], default=str, indent=2)
        elif args.output_format == "csv":
            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["timestamp", "fast_window", "slow_window", "final_equity", "return_pct", "trades"])
            for row in results[:10]:
                writer.writerow([current_timestamp(), row.get("fast_window", ""), row.get("slow_window", ""), row.get("final_equity", ""), row.get("return_pct", ""), row.get("trades", "")])
            output = csv_buffer.getvalue()
        elif args.output_format == "html":
            rows = "".join(f"<tr><td>{row.get('fast_window', '')}</td><td>{row.get('slow_window', '')}</td><td>{row.get('final_equity', '')}</td><td>{row.get('return_pct', '')}</td><td>{row.get('trades', '')}</td></tr>" for row in results[:10])
            output = f"<html><body><table><thead><tr><th>Timestamp</th><th>Fast</th><th>Slow</th><th>Final Equity</th><th>Return %</th><th>Trades</th></tr></thead><tbody><tr><td>{current_timestamp()}</td>{rows}</tr></tbody></table></body></html>"
        else:
            output = "Top optimization results:\n" + pprint(results[:10], indent=2, width=120, compact=True)
        if args.summary_file:
            write_summary_file(output, args.summary_file)
            if args.output_format == "text":
                print(output)
            else:
                print(render_results({
                    "symbol": args.symbol,
                    "start": args.start,
                    "end": args.end,
                    "interval": args.interval,
                    "final_equity": results[0].get("final_equity", 0) if results else 0,
                    "return_pct": results[0].get("return_pct", 0) if results else 0,
                    "trades": [],
                    "timestamp": current_timestamp(),
                }, "text"))
        else:
            print(output)
        return

    result = dict(engine.run(args.symbol, args.start, args.end, args.interval))
    result["timestamp"] = current_timestamp()
    summary_text = render_results(result, "text")
    if args.summary_file:
        write_summary_file(summary_text, args.summary_file)
        print(summary_text)
    else:
        if args.output_format == "text":
            print(summary_text)
        else:
            print(render_results(result, args.output_format))


if __name__ == "__main__":
    main()
