# SOXL Rolling-Threshold Trading Bot (Robinhood)

Buys SOXL when its price drops 2% since the last check, sells the whole
position when it rises 4% or more since the last check. Designed to be run
on a schedule (e.g. every 2 minutes) via cron.

## How the logic works

- Every run, the bot compares the current price to a **reference price**
  saved from the previous run (`soxl_bot_state.json`).
- Price down ≥2% from the reference → **buy**, using a pyramided amount of
  available buying power. This is intentionally tuned for maximum-results
  momentum capture.
- The pyramiding ladder is: 35% of available cash on the first qualifying
  drop, 75% on a deeper pullback, and 100% once the decline is strong enough
  to confirm a trend continuation.
- Price up ≥4% from the reference → **sell** the entire current SOXL
  position.
- After every run — trade or no trade — the reference price resets to the
  current price. This makes the band "rolling" (measuring the move since
  the *last check*, not since the day's open or your cost basis), and it's
  what lets the bot buy again and again across consecutive down-checks
  before a sell fires (it can build a "stacked" position).
- The very first run just records a baseline price and does not trade.

## Test mode (on by default)

The bot ships in **test mode**: it logs in, reads real prices and real
account data, and logs exactly what it *would* buy or sell each run — but
it does not place any orders. This is the default, on purpose, so you can
watch it make decisions for a while before trusting it with money.

To let it place real orders, set in your `.env`:
```
SOXL_BOT_LIVE_TRADING=true
```
Test-mode log lines are prefixed `[TEST MODE]` so they're easy to spot/grep.

## Logging

Every run writes its own timestamped log file to `logs/` (e.g.
`logs/soxl_bot_2026-09-15T14-30-00.log`), rather than appending to one
ongoing file. Override the directory with `SOXL_BOT_LOG_DIR`. Each file
records: the price and reference price it compared, the % change, whether
a buy/sell signal fired, and the outcome (order placed, skipped, or
simulated in test mode).

## ⚠️ Things to know before running this with real money

1. **Unofficial API.** Robinhood has no public trading API. This uses
   [`robin_stocks`](https://github.com/jmfernandes/robin_stocks), which logs
   in with your normal Robinhood username/password (and MFA) and replicates
   what the mobile app does. Automated use like this is against Robinhood's
   Terms of Service and carries some risk of the account being flagged or
   restricted.
2. **Leverage + frequent trading.** SOXL is a 3x leveraged semiconductor
   ETF. A tight 1% band checked every 2 minutes will trade often, and
   leveraged ETFs can decay in choppy/sideways markets even when the
   underlying index is roughly flat.
3. **Pyramiding buys increase with deeper drops** — this is the optimized
   max-results profile: once the price has fallen 2% or more, the buy
   size scales up to 35%, then 75%, and then 100% of the available buying
   power as the decline keeps extending.
4. **Sells liquidate the whole position** — if you've stacked several buys,
   a single sell signal closes all of it at once, not just the most recent
   buy.
5. This is not financial advice, and this code is provided as-is. Consider
   testing with a small account balance first, or temporarily commenting
   out the order-placing calls to just log signals ("paper test") before
   trusting it with size.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set credentials.** Copy `.env.example` to `.env` and fill in your
   Robinhood username/password. If you want the bot to run fully
   unattended (no manual 2FA prompt), also set `ROBINHOOD_TOTP_SECRET` —
   this is the same secret you'd enter into an authenticator app, available
   from Robinhood's account security settings, *not* a one-time code.

   ```bash
   cp .env.example .env
   # edit .env with your values
   ```

3. **First manual run** (also lets you complete any interactive 2FA prompt
   once, and creates the initial state file):
   ```bash
   set -a && source .env && set +a
   python3 soxl_trading_bot.py
   ```

4. **Schedule it every 2 minutes with cron:**
   ```bash
   crontab -e
   ```
   Add a line like (adjust paths, and load your env vars — cron doesn't
   source your shell profile):
   ```
   */2 * * * * . /path/to/soxl_bot/.env && /usr/bin/python3 /path/to/soxl_bot/soxl_trading_bot.py >> /path/to/soxl_bot/cron.log 2>&1
   ```
   Note: the `.env` file as written uses `KEY=value` lines, which works with
   `.` (dot-source) in most shells cron invokes; if you hit issues, export
   the variables directly in your crontab or in a wrapper shell script instead.

## Backtest

`backtest.py` is a quick, no-login backtest: it downloads historical prices
for SOXL via `yfinance` and replays the exact same buy/sell logic as the
live bot (imported from `config.py`, so the two can't drift apart).

```bash
# Daily bars (default), a few years
python3 backtest.py --start 2023-01-01 --end 2026-09-01 --cash 10000

# Save the bar-by-bar log to CSV
python3 backtest.py --symbol SOXL --start 2024-01-01 --csv results.csv

# Closer to the live bot: 2-minute bars over the last few weeks
python3 backtest.py --interval 2m --start 2026-08-15 --end 2026-09-15

# Try different thresholds without touching config.py
python3 backtest.py --buy-threshold -0.02 --sell-threshold 0.02
```

It prints a bar-by-bar log of price, % change vs. the rolling reference,
any simulated buy/sell, and running equity, then a summary comparing the
strategy's ending equity to simple buy-and-hold.

### Do you need a higher threshold for daily bars?

Not necessarily higher — the issue with `--interval 1d` isn't that the
threshold is too tight, it's a mismatch in what each "check" represents:

- The live bot checks every 2 minutes. Most 2-minute windows won't move
  1%, so trades are relatively rare per-check.
- A daily bar already bakes in the *entire* day's cumulative move. SOXL,
  being a 3x leveraged ETF, very often moves more than 1% in a day — so a
  1% threshold on daily closes will trigger on most days, flipping the
  whole position in and out constantly. That's a much higher per-check
  trigger rate than the live bot sees, even though there are ~195x fewer
  checks per day (one bar vs. ~195 two-minute bars during market hours).

So bumping the threshold up for `--interval 1d` (e.g. to 3-5%) will make
the daily backtest trade less often, but it still won't reproduce what the
live bot actually does intraday — it's fundamentally simulating a
"check once a day" bot, not a "check every 2 minutes" bot. If you want the
threshold itself tested realistically, it's better to backtest at a finer
interval instead (see below) and leave the threshold as-is.

### Backtesting at smaller timeframes

Yes — pass `--interval` with any value yfinance/Yahoo Finance supports:
`1m`, `2m`, `5m`, `15m`, `30m`, `60m`/`1h`, `90m`, alongside the default
`1d`. `2m` is the closest match to the live bot's actual cadence.

Yahoo Finance limits how far back intraday data is available, and it gets
shorter the finer the interval:

| Interval        | Approx. history available |
|------------------|---------------------------|
| `1m`             | last ~7-8 days |
| `2m`, `5m`, `15m`, `30m`, `90m` | last ~60 days |
| `60m` / `1h`     | last ~730 days (2 years) |
| `1d` and coarser | full history |

So a `--interval 2m` backtest needs `--start`/`--end` within roughly the
last 60 days, or `yfinance` will just return no data (the script will tell
you if that happens). For a longer-range but still intraday-ish view,
`60m` bars can go back about 2 years.

## Files

- `soxl_trading_bot.py` — the live bot.
- `config.py` — shared symbol/threshold constants used by both the bot and
  the backtest.
- `backtest.py` — daily-bar backtest tool (see above).
- `soxl_bot_state.json` — auto-created; stores the rolling reference price
  between runs. Delete it to reset the baseline.
- `logs/` — auto-created; one timestamped log file per run, recording the
  decision made and any order placed (or, in test mode, what would have
  been placed).
- `.env.example` — template for credentials/config.

## Market hours

By default the bot skips runs outside 9:30–16:00 America/New_York, Mon–Fri
(set `SOXL_BOT_RESPECT_MARKET_HOURS=false` to disable this). It does not
know about market holidays — on a holiday it will still attempt to run
during that window, and Robinhood's own API will simply reject/no-op the
order or return a stale price.
