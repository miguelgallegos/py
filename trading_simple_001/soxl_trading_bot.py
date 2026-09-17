#!/usr/bin/env python3
"""
SOXL rolling-threshold trading bot for Robinhood.

Logic (run this script on a schedule, e.g. every 2 minutes):
  - Compare the current SOXL price to the "reference price" saved from the
    previous run.
  - If price has fallen >= 1% since the reference -> BUY using all
    available buying power (fractional-dollar order).
  - If price has risen >= 1% since the reference -> SELL the entire
    current SOXL position.
  - Either way, the reference price is reset to the current price at the
    end of every run. This means the 1% band is "rolling": it always
    measures the move since the *last check*, not since some fixed
    daily open or your own cost basis. It also means the bot can stack
    multiple buys across consecutive down-moves before a sell fires.

Requires: robin_stocks, pyotp (only if using an automated TOTP 2FA secret)

Credentials are read from environment variables - see README.md.

TEST MODE (on by default): the bot logs in and reads real price/account
data, and logs exactly what it *would* buy or sell, but does not place any
orders. Set SOXL_BOT_LIVE_TRADING=true in the environment to enable real
order placement.

Each run writes its own timestamped log file under SOXL_BOT_LOG_DIR
(default: ./logs/).

IMPORTANT — read before using with real money:
  - Robinhood has no official public trading API. This uses robin_stocks,
    an unofficial library that logs in with your normal Robinhood
    credentials. Automated trading like this is against Robinhood's
    Terms of Service and carries some risk of account restriction.
  - SOXL is a 3x leveraged ETF. A 1% band checked every 2 minutes will
    trade often and leveraged-ETF decay in choppy/sideways markets can
    erode returns even if SOXL is flat over time.
  - This script is not financial advice. Test with a small amount of
    buying power before trusting it with size, and consider paper-testing
    the logic (e.g. logging signals without placing orders) first.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import robin_stocks.robinhood as rh

from config import SYMBOL, BUY_THRESHOLD, SELL_THRESHOLD
from strategy import calculate_buy_fraction

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
STATE_FILE = os.environ.get("SOXL_BOT_STATE_FILE", os.path.join(os.path.dirname(__file__), "soxl_bot_state.json"))

# Each run gets its own log file (rather than one continuously-appended file).
# Files land in SOXL_BOT_LOG_DIR/soxl_bot_<UTC timestamp>.log.
LOG_DIR = os.environ.get("SOXL_BOT_LOG_DIR", os.path.join(os.path.dirname(__file__), "logs"))

# Skip runs outside regular NYSE hours (9:30-16:00 America/New_York, Mon-Fri).
# This does NOT account for market holidays - Robinhood's price/order calls
# will simply no-op or error on holidays, which is handled below.
RESPECT_MARKET_HOURS = os.environ.get("SOXL_BOT_RESPECT_MARKET_HOURS", "true").lower() != "false"

# Allow the bot to evaluate and optionally place trades after regular hours.
# When false, the script still logs the BUY/SELL signal but refuses to send
# a live Robinhood order outside regular hours.
ALLOW_AFTER_HOURS = os.environ.get("SOXL_BOT_ALLOW_AFTER_HOURS", "false").lower() == "true"

# Optional signal-only mode for automation integrations: compute the signal,
# log the final action, and exit without submitting any order. This is useful
# when a downstream system or manual workflow wants to execute the captured
# BUY/SELL decision later.
SIGNAL_ONLY = os.environ.get("SOXL_BOT_SIGNAL_ONLY", "false").lower() == "true"

# TEST MODE IS ON BY DEFAULT. The bot will log every decision it *would*
# make (including simulated buy/sell details) but will not place any real
# orders, until you explicitly set SOXL_BOT_LIVE_TRADING=true in the
# environment. This is a deliberate safety default.
LIVE_TRADING = os.environ.get("SOXL_BOT_LIVE_TRADING", "false").lower() == "true"
TEST_MODE = not LIVE_TRADING


def _init_logging() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"soxl_bot_{timestamp}.log")

    logger = logging.getLogger("soxl_bot")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # avoid duplicate handlers if main() is ever called twice in-process

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


log = _init_logging()
log.info(f"Log file for this run: {log.handlers[0].baseFilename}")
log.info(f"Mode: {'LIVE TRADING' if LIVE_TRADING else 'TEST MODE (no orders will be placed)'}")
log.info(f"Thresholds: buy={BUY_THRESHOLD * 100:+.2f}% sell={SELL_THRESHOLD * 100:+.2f}%")
log.info(f"Market-hours enforcement: respect={RESPECT_MARKET_HOURS} allow_after_hours={ALLOW_AFTER_HOURS} signal_only={SIGNAL_ONLY}")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def market_is_open_now() -> bool:
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:  # Sat/Sun
        return False
    open_t = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    close_t = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_t <= now_et <= close_t


def login():
    username = os.environ.get("ROBINHOOD_USERNAME")
    password = os.environ.get("ROBINHOOD_PASSWORD")
    totp_secret = os.environ.get("ROBINHOOD_TOTP_SECRET")  # optional, for unattended 2FA

    if not username or not password:
        log.error("ROBINHOOD_USERNAME / ROBINHOOD_PASSWORD environment variables are not set.")
        sys.exit(1)

    mfa_code = None
    if totp_secret:
        import pyotp
        mfa_code = pyotp.TOTP(totp_secret).now()

    # store_session=True caches the login token to disk (~/.tokens) so that
    # a script run every 2 minutes by cron doesn't need to re-auth (and
    # re-trigger MFA) every single time.
    rh.login(username=username, password=password, mfa_code=mfa_code, store_session=True)


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_price() -> float:
    """
    Fetch SOXL's latest tradable price directly from Robinhood via
    robin_stocks, rather than a third-party quote source (e.g. yfinance).
    Robinhood's own quote is what matters here, since it's what the bot's
    orders will actually fill against.
    """
    result = rh.stocks.get_latest_price(SYMBOL, includeExtendedHours=True)
    if not result or result[0] is None:
        raise RuntimeError(f"Could not fetch a price for {SYMBOL}")
    return float(result[0])


def get_buying_power() -> float:
    profile = rh.profiles.load_account_profile()
    return float(profile["buying_power"])


def get_position_quantity() -> float:
    positions = rh.account.build_holdings()
    if SYMBOL in positions:
        return float(positions[SYMBOL]["quantity"])
    return 0.0


def place_buy(amount_dollars: float):
    if TEST_MODE:
        log.info(f"[TEST MODE] BUY signal -> would place fractional order for ${amount_dollars:.2f} of {SYMBOL}. "
                 f"No order sent (set SOXL_BOT_LIVE_TRADING=true to enable real trading).")
        return None

    log.info(f"BUY signal -> placing fractional order for ${amount_dollars:.2f} of {SYMBOL}")
    try:
        result = rh.orders.order_buy_fractional_by_price(SYMBOL, round(amount_dollars, 2), timeInForce="gfd")
        if result and result.get("detail"):
            # robin_stocks returns an error dict with a "detail" key on failure
            raise RuntimeError(result["detail"])
    except Exception as e:
        log.warning(f"Fractional buy failed ({e}); falling back to a whole-share market order.")
        price = get_price()
        qty = int(amount_dollars // price)
        if qty < 1:
            log.warning("Buying power is insufficient for even 1 whole share. Skipping buy.")
            return None
        result = rh.orders.order_buy_market(SYMBOL, qty)
    log.info(f"Buy order result: {result}")
    return result


def place_sell(quantity: float):
    if TEST_MODE:
        log.info(f"[TEST MODE] SELL signal -> would place market order to sell {quantity} shares of {SYMBOL}. "
                 f"No order sent (set SOXL_BOT_LIVE_TRADING=true to enable real trading).")
        return None

    log.info(f"SELL signal -> placing market order to sell {quantity} shares of {SYMBOL}")
    result = rh.orders.order_sell_market(SYMBOL, quantity)
    log.info(f"Sell order result: {result}")
    return result


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    is_market_open = market_is_open_now()
    if RESPECT_MARKET_HOURS and not is_market_open and not ALLOW_AFTER_HOURS:
        log.info("Outside regular market hours and SOXL_BOT_ALLOW_AFTER_HOURS is false. "
                 "Computing the signal only; no live order will be placed.")
    elif RESPECT_MARKET_HOURS and not is_market_open and ALLOW_AFTER_HOURS:
        log.info("Outside regular market hours, but SOXL_BOT_ALLOW_AFTER_HOURS=true. Trading is enabled.")

    login()

    state = load_state()
    reference_price = state.get("reference_price")
    current_price = get_price()

    log.info(f"Current price: ${current_price:.4f} | Reference price: {reference_price}")

    if reference_price is None:
        # First run ever - nothing to compare against yet, just set the baseline.
        log.info("No reference price on record yet. Setting baseline and exiting without trading.")
        save_state({
            "reference_price": current_price,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        })
        return

    pct_change = (current_price - reference_price) / reference_price
    signal = None
    if pct_change <= BUY_THRESHOLD:
        signal = "BUY"
    elif pct_change >= SELL_THRESHOLD:
        signal = "SELL"

    log.info(f"Change since last check: {pct_change * 100:.3f}%")
    if signal:
        log.info(f"SIGNAL: {signal} at {pct_change * 100:.3f}% vs thresholds buy={BUY_THRESHOLD * 100:.2f}% sell={SELL_THRESHOLD * 100:.2f}%")
        log.info(f"FINAL ACTION: {signal}")

    if SIGNAL_ONLY:
        log.info("SOXL_BOT_SIGNAL_ONLY=true: signal captured only; no live order will be placed.")
        save_state({
            "reference_price": current_price,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        })
        return

    if RESPECT_MARKET_HOURS and not is_market_open and not ALLOW_AFTER_HOURS:
        log.info(f"Regular market is closed; signal captured but no order will be sent. Manual execution recommended for {signal}.")
        save_state({
            "reference_price": current_price,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        })
        return

    if signal == "BUY":
        buying_power = get_buying_power()
        if buying_power < 1.0:
            log.warning(f"Buy signal triggered but buying power (${buying_power:.2f}) is too low. Skipping.")
        else:
            buy_fraction = calculate_buy_fraction(pct_change, BUY_THRESHOLD)
            if buy_fraction <= 0:
                log.info("Buy threshold reached but price move was too shallow for a pyramiding buy. No action taken.")
            else:
                buy_amount = buying_power * buy_fraction
                log.info(f"Pyramiding buy: {buy_fraction * 100:.0f}% of buying power (${buy_amount:.2f})")
                place_buy(buy_amount)

    elif signal == "SELL":
        qty = get_position_quantity()
        if qty <= 0:
            log.info("Sell signal triggered but no shares are currently held. Nothing to sell.")
        else:
            place_sell(qty)

    else:
        log.info("No threshold crossed. No action taken this run.")

    # Rolling reference: reset the baseline to the current price after every
    # check, regardless of whether a trade happened this run.
    save_state({
        "reference_price": current_price,
        "last_checked": datetime.now(timezone.utc).isoformat(),
    })


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Unhandled error during bot run")
        sys.exit(1)
