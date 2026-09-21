import unittest

import pandas as pd

from run_optimizer_scan import PRESETS
from strategies.macd_sma_strategy import MacdSmaStrategy
from strategy_optimizer import build_parameter_grid, select_best_result


class StrategyOptimizerTests(unittest.TestCase):
    def test_build_parameter_grid_expands_ranges(self) -> None:
        grid = build_parameter_grid({
            "fast_window": [5, 10],
            "slow_window": [20, 30],
            "tp_levels": [(0.02, 0.04), (0.03, 0.05)],
        })

        self.assertEqual(len(grid), 8)
        self.assertTrue(all("fast_window" in item for item in grid))
        self.assertTrue(any(item["fast_window"] == 5 and item["slow_window"] == 20 for item in grid))
        self.assertTrue(any(item["fast_window"] == 10 and item["slow_window"] == 30 for item in grid))

    def test_select_best_result_prefers_highest_return(self) -> None:
        rows = [
            {"symbol": "AAPL", "return_pct": 5.0, "final_equity": 10000.0},
            {"symbol": "AAPL", "return_pct": 12.0, "final_equity": 12000.0},
            {"symbol": "AAPL", "return_pct": 8.0, "final_equity": 11000.0},
        ]

        best = select_best_result(rows)

        self.assertEqual(best["return_pct"], 12.0)
        self.assertEqual(best["final_equity"], 12000.0)

    def test_macd_sma_intraday_preset_exists(self) -> None:
        self.assertIn("macd_sma_intraday", PRESETS)
        self.assertEqual(PRESETS["macd_sma_intraday"]["strategy"], "macd_sma")
        self.assertIn("sma_fast", PRESETS["macd_sma_intraday"])
        self.assertIn("sma_slow", PRESETS["macd_sma_intraday"])

    def test_macd_sma_strategy_marks_bullish_when_macd_and_sma_align(self) -> None:
        df = pd.DataFrame({
            "Close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111]
        })
        strategy = MacdSmaStrategy({"macd_fast": 5, "macd_slow": 10, "macd_signal": 3, "sma_fast": 8, "sma_slow": 40})

        signals = strategy.generate_signals(df)

        self.assertIn("signal", signals.columns)
        self.assertTrue((signals["signal"].iloc[-1:] == 1).all())

    def test_macd_sma_strategy_can_flip_signal_for_inverse_etfs(self) -> None:
        df = pd.DataFrame({
            "Close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111]
        })
        strategy = MacdSmaStrategy({
            "macd_fast": 5,
            "macd_slow": 10,
            "macd_signal": 3,
            "sma_fast": 8,
            "sma_slow": 40,
            "inverse_mode": True,
        })

        signals = strategy.generate_signals(df)

        self.assertIn("signal", signals.columns)
        self.assertTrue((signals["signal"].iloc[-1:] == -1).all())


if __name__ == "__main__":
    unittest.main()
