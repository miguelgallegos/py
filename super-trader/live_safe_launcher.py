#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep

from live_signal_runner import market_status_now


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def parse_levels(raw: str | None, default: tuple[float, ...]) -> tuple[float, ...]:
    if raw is None or not str(raw).strip():
        return default
    try:
        return tuple(float(v.strip()) for v in str(raw).split(",") if v.strip())
    except ValueError:
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe launcher for signal generation and ordered execution.")
    parser.add_argument("--once", action="store_true", help="Run a single check and exit.")
    parser.add_argument("--loop", action="store_true", help="Keep looping until interrupted.")
    parser.add_argument("--poll-seconds", type=int, default=env_int("POLL_SECONDS", 300))
    parser.add_argument("--days-history", type=int, default=env_int("DAYS_HISTORY", 30))
    parser.add_argument("--symbol", default=os.getenv("SYMBOL", "FNGU"))
    parser.add_argument("--interval", default=os.getenv("INTERVAL", "5m"))
    parser.add_argument("--mode", default=os.getenv("TRADING_MODE", "signal"), choices=["signal", "paper", "live"])
    parser.add_argument("--fast", type=int, default=env_int("FAST_WINDOW", 8))
    parser.add_argument("--slow", type=int, default=env_int("SLOW_WINDOW", 40))
    parser.add_argument("--tp-levels", default=os.getenv("TP_LEVELS", "0.01,0.02,0.03,0.04,0.05,0.06,0.08"))
    parser.add_argument("--sl-levels", default=os.getenv("SL_LEVELS", "0.005,0.01,0.015,0.02,0.025,0.03"))
    parser.add_argument("--allow-after-hours", action="store_true", default=env_flag("ALLOW_AFTER_HOURS", True))
    parser.add_argument("--log-file", default=os.getenv("LOG_FILE", "logs/live_safe_launcher.log"))
    return parser.parse_args()


def ensure_safe_mode(mode: str, allow_after_hours: bool) -> tuple[bool, str]:
    live_orders = env_flag("ENABLE_LIVE_ORDERS", False)
    signal_only = env_flag("SIGNAL_ONLY", True)
    market_open, market_state = market_status_now()

    if mode == "signal":
        return True, "ok"

    if mode in {"paper", "live"}:
        if signal_only:
            return False, "execution mode requires SIGNAL_ONLY=0"

        if not live_orders and mode == "live":
            return False, "live mode requires ENABLE_LIVE_ORDERS=1"

        if not env_flag("PAPER_TRADE", True) and mode == "paper":
            return False, "paper mode requires PAPER_TRADE=1"

        if not market_open and not allow_after_hours:
            return False, f"market is closed ({market_state}); set ALLOW_AFTER_HOURS=1 or use signal mode"

        required = [
            "ROBINHOOD_USERNAME",
            "ROBINHOOD_PASSWORD",
        ]
        missing = [key for key in required if not os.getenv(key)]
        if mode == "live" and missing:
            return False, f"live mode is missing required Robinhood credentials: {', '.join(missing)}"

        if mode == "paper":
            return True, "ok"

    return True, "ok"


def append_log(path: str, payload: dict) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def run_once(args: argparse.Namespace) -> dict:
    mode = args.mode.lower()
    allow_after_hours = bool(args.allow_after_hours)
    safe, reason = ensure_safe_mode(mode, allow_after_hours)
    market_open, market_state = market_status_now()

    payload = {
        "timestamp": datetime.now().isoformat(),
        "symbol": str(args.symbol).upper(),
        "interval": args.interval,
        "mode": mode,
        "fast_window": args.fast,
        "slow_window": args.slow,
        "market_is_open": market_open,
        "market_state": market_state,
        "allow_after_hours": allow_after_hours,
        "live_orders_enabled": env_flag("ENABLE_LIVE_ORDERS", False),
        "signal_only": env_flag("SIGNAL_ONLY", True),
        "safe": safe,
    }

    if not safe:
        payload["status"] = "blocked"
        payload["reason"] = reason
        append_log(args.log_file, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        raise SystemExit(2)

    tp_levels = parse_levels(args.tp_levels, (0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08))
    sl_levels = parse_levels(args.sl_levels, (0.005, 0.01, 0.015, 0.02, 0.025, 0.03))

    from live_signal_runner import signal_to_action
    from data import load_market_data
    from strategies.sma_crossover import SmaCrossoverStrategy
    from live_trader import LiveTrader

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=max(30, args.days_history))).strftime("%Y-%m-%d")
    df = load_market_data(args.symbol, start_date, end_date, args.interval)
    strategy = SmaCrossoverStrategy({
        "fast_window": args.fast,
        "slow_window": args.slow,
        "tp_levels": tp_levels,
        "sl_levels": sl_levels,
    })
    signal = int(LiveTrader().evaluate_signal(df, strategy)["signal"])
    action = signal_to_action(signal)

    payload.update({
        "signal": signal,
        "action": action,
        "close": float(df.iloc[-1]["Close"]),
        "status": "signal_only",
    })

    if mode in {"paper", "live"}:
        payload["status"] = "execution_check"
        payload["execution_allowed"] = bool(market_open or allow_after_hours)
        if not payload["execution_allowed"]:
            payload["reason"] = "market closed and after-hours not allowed"
            append_log(args.log_file, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            raise SystemExit(3)

        if mode == "live" and not env_flag("ENABLE_LIVE_ORDERS", False):
            payload["reason"] = "live execution attempted without ENABLE_LIVE_ORDERS=1"
            append_log(args.log_file, payload)
            print(json.dumps(payload, indent=2, sort_keys=True))
            raise SystemExit(4)

        payload["status"] = "order_attempted" if mode == "paper" else "live_order_attempted"

    append_log(args.log_file, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    args = parse_args()
    if args.loop and args.once:
        raise SystemExit("Use either --once or --loop, not both")

    if args.loop:
        while True:
            try:
                run_once(args)
            except SystemExit as exc:
                if exc.code in (2, 3):
                    print(f"Blocked: {exc.code}", file=sys.stderr)
                else:
                    raise
            sleep(args.poll_seconds)
        return 0

    run_once(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
