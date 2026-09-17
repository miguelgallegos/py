import unittest

from strategy import calculate_buy_fraction, calculate_position_pnl_pct


class StrategyTests(unittest.TestCase):
    def test_calculate_buy_fraction_pyramids_as_price_keeps_falling(self):
        self.assertEqual(calculate_buy_fraction(-0.010, -0.010), 0.35)
        self.assertEqual(calculate_buy_fraction(-0.020, -0.010), 0.75)
        self.assertEqual(calculate_buy_fraction(-0.030, -0.010), 1.00)
        self.assertEqual(calculate_buy_fraction(-0.050, -0.010), 1.00)
        self.assertEqual(calculate_buy_fraction(0.000, -0.010), 0.0)

    def test_calculate_position_pnl_pct_uses_average_cost_basis(self):
        self.assertAlmostEqual(calculate_position_pnl_pct(110.0, 100.0), 0.10)
        self.assertAlmostEqual(calculate_position_pnl_pct(95.0, 100.0), -0.05)
        self.assertAlmostEqual(calculate_position_pnl_pct(100.0, 0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
