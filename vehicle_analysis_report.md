# SOXL vs alternative vehicles: optimized comparison report

Date: 2026-09-16
Window analyzed: 2025-09-15 to 2026-09-15
Strategy: rolling threshold + pyramiding ladder
Ladder used: (0.35, 0.75, 1.0)
Optimization model: dense buy/sell threshold sweep on daily bars using the same backtest engine and cached price data

## Summary

The current optimized laddered strategy performs best on SOXL by a wide margin over the same 1-year test window.

## Results

| Ticker | Buy trigger | Sell trigger | Final equity | Return | Trades |
|---|---:|---:|---:|---:|---:|
| SOXL | -3.4% | +4.2% | $286,115.44 | +472.23% | 91 |
| KOLD | -2.2% | +4.0% | $97,657.55 | +95.32% | 100 |
| TQQQ | -2.6% | +3.2% | $84,482.34 | +68.96% | 76 |
| BOIL | -2.0% | +5.2% | $73,085.19 | +46.17% | 77 |
| FNGU | -7.6% | +8.2% | $54,630.16 | +9.26% | 11 |
| ETHU | -8.0% | +8.2% | $46,300.05 | -7.40% | 53 |

## Ranking

1. SOXL
2. KOLD
3. TQQQ
4. BOIL
5. FNGU
6. ETHU

## Interpretation

- SOXL remains the strongest performer in this strategy profile.
- KOLD is the only real secondary option that produced a meaningful positive return, but it is still far behind SOXL.
- TQQQ and BOIL were viable but materially weaker.
- FNGU and ETHU underperformed in this exact setup and are not competitive for the current ladder-driven model.

## Recommended direction

The current recommendation remains to stay with the optimized SOXL profile unless a different market exposure is desired intentionally.

Primary configuration to keep:
- Buy threshold: -3.4%
- Sell threshold: +4.2%
- Ladder: (0.35, 0.75, 1.0)

This report reflects the current optimization run and is intended to be committed alongside the project code and config updates.
