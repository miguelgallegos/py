#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from data import load_market_data
from live_trader import LiveTrader
from strategies.sma_crossover import SmaCrossoverStrategy


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


def env_float_tuple(name: str, default: tuple[float, ...]) -> tuple[float, ...]:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return default
    try:
        parts = [part.strip() for part in str(value).split(",") if part.strip()]
        return tuple(float(part) for part in parts)
    except ValueError:
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Produce a trading signal and optionally execute a paper/live order.")
    parser.add_argument("--symbol", default=os.getenv("SYMBOL", "FNGU"))
    parser.add_argument("--interval", default=os.getenv("INTERVAL", "5m"))
    parser.add_argument("--fast", type=int, default=env_int("FAST_WINDOW", 8))
    parser.add_argument("--slow", type=int, default=env_int("SLOW_WINDOW", 40))
    parser.add_argument("--tp-levels", default=os.getenv("TP_LEVELS", "0.01,0.02,0.03,0.04,0.05,0.06,0.08"))
    parser.add_argument("--sl-levels", default=os.getenv("SL_LEVELS", "0.005,0.01,0.015,0.02,0.025,0.03"))
    parser.add_argument("--paper-trade", action="store_true", default=env_flag("PAPER_TRADE", True))
    parser.add_argument("--live-orders", action="store_true", default=env_flag("ENABLE_LIVE_ORDERS", False))
    parser.add_argument("--signal-only", action="store_true", default=env_flag("SIGNAL_ONLY", True))
    parser.add_argument("--allow-after-hours", action="store_true", default=env_flag("ALLOW_AFTER_HOURS", True))
    parser.add_argument("--trading-mode", default=os.getenv("TRADING_MODE", "paper"))
    parser.add_argument("--poll-seconds", type=int, default=env_int("POLL_SECONDS", 300))
    parser.add_argument("--days-history", type=int, default=env_int("DAYS_HISTORY", 30))
    return parser.parse_args()


def _parse_levels(raw_levels: str, default: tuple[float, ...]) -> tuple[float, ...]:
    if not raw_levels or not str(raw_levels).strip():
        return default
    try:
        return tuple(float(v.strip()) for v in str(raw_levels).split(",") if v.strip())
    except ValueError:
        return default


def market_status_now() -> tuple[bool, str]:
    now = datetime.now(tz=ZoneInfo("America/New_York"))
    weekday = now.weekday()
    if weekday >= 5:
        return False, "weekend"

    regular_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    regular_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if regular_open <= now <= regular_close:
        return True, "regular_hours"

    extended_open = now.replace(hour=4, minute=0, second=0, microsecond=0)
    extended_close = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if extended_open <= now <= extended_close:
        return False, "after_hours"

    return False, "closed"


def signal_to_action(signal: int) -> str:
    if signal > 0:
        return "BUY"
    if signal < 0:
        return "SELL"
    return "HOLD"


def maybe_execute_order(symbol: str, signal: int, close_price: float, args: argparse.Namespace) -> dict | None:
    if args.signal_only or not args.live_orders:
        return None

    market_is_open, market_state = market_status_now()
    if not market_is_open and not args.allow_after_hours:
        return {"status": "blocked", "reason": f"Market is not open ({market_state})."}

    if args.trading_mode.lower() == "paper":
        from brokers import PaperBroker
        broker = PaperBroker(cash=10000.0)
    elif args.trading_mode.lower() == "robinhood":
        from brokers import RobinhoodBroker
        broker = RobinhoodBroker()
    elif args.trading_mode.lower() == "alpaca":
        from brokers import AlpacaBroker
        broker = AlpacaBroker()
    else:
        from brokers import PaperBroker
        broker = PaperBroker(cash=10000.0)

    side = "BUY" if signal > 0 else "SELL" if signal < 0 else "HOLD"
    if side == "HOLD":
        return {"status": "no_action", "reason": "Signal is HOLD"}

    qty = 1.0
    response = broker.place_order(symbol, side, qty=qty, price=close_price, order_type="market")
    return {"status": "executed", "broker": broker.name, "side": side, "qty": qty, "price": close_price, "details": response}


def main() -> int:
    args = parse_args()
    tp_levels = _parse_levels(args.tp_levels, (0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08))
    sl_levels = _parse_levels(args.sl_levels, (0.005, 0.01, 0.015, 0.02, 0.025, 0.03))

    strategy = SmaCrossoverStrategy({
        "fast_window": int(args.fast),
        "slow_window": int(args.slow),
        "tp_levels": tp_levels,
        "sl_levels": sl_levels,
    })

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=max(30, args.days_history))).strftime("%Y-%m-%d")

    df = load_market_data(args.symbol, start_date, end_date, args.interval)
    last_row = df.iloc[-1]
    signal = int(LiveTrader().evaluate_signal(df, strategy)["signal"])
    action = signal_to_action(signal)
    market_is_open, market_state = market_status_now()

    result = {
        "symbol": args.symbol.upper(),
        "timestamp": datetime.now(tz=ZoneInfo("America/New_York")).isoformat(),
        "interval": args.interval,
        "signal": signal,
        "action": action,
        "close": float(last_row["Close"]),
        "fast_sma": float(last_row.get("fast_sma", 0.0)),
        "slow_sma": float(last_row.get("slow_sma", 0.0)),
        "market_is_open": market_is_open,
        "market_state": market_state,
        "signal_only": bool(args.signal_only),
        "allow_after_hours": bool(args.allow_after_hours),
        "live_orders_enabled": bool(args.live_orders),
        "trading_mode": args.trading_mode.lower(),
        "tp_levels": list(tp_levels),
        "sl_levels": list(sl_levels),
    }

    order_result = maybe_execute_order(args.symbol.upper(), signal, float(last_row["Close"]), args)
    if order_result is not None:
        result["execution"] = order_result

    if not market_is_open and args.allow_after_hours:
        result["note"] = "Market is closed for regular hours; signal was generated for monitoring and potential after-hours execution is allowed."
    elif not market_is_open:
        result["note"] = "Market is closed for regular hours; no execution is permitted unless after-hours execution is enabled."

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI safety
        print(json.dumps({"error": str(exc), "status": "failed"}, indent=2, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
