import unittest

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


if __name__ == "__main__":
    unittest.main()
