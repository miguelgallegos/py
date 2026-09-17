import unittest
from unittest.mock import patch

from app import app


class TradingApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    @patch("app.execute_trade")
    def test_trade_bad_json(self, mock_execute_trade):
        response = self.client.post("/trade", data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json)
        self.assertEqual(response.json["error"], "JSON body is required")
        mock_execute_trade.assert_not_called()

    @patch("app.execute_trade")
    def test_trade_success(self, mock_execute_trade):
        mock_execute_trade.return_value = {"order_id": "12345"}
        response = self.client.post(
            "/trade",
            json={
                "exchange": "alpaca",
                "operation": "buy",
                "symbol": "AAPL",
                "order_type": "market",
                "quantity": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])
        self.assertEqual(response.json["data"], {"order_id": "12345"})

    @patch("app.get_portfolio")
    def test_portfolio_all_exchanges(self, mock_get_portfolio):
        mock_get_portfolio.return_value = {"alpaca": {"account": {}}, "kraken": {"balances": {}}}
        response = self.client.get("/portfolio")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])
        self.assertEqual(response.json["data"], {"alpaca": {"account": {}}, "kraken": {"balances": {}}})

    @patch("app.get_portfolio")
    def test_portfolio_single_exchange(self, mock_get_portfolio):
        mock_get_portfolio.return_value = {"alpaca": {"account": {}}}
        response = self.client.get("/portfolio?exchange=alpaca")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["success"])
        self.assertEqual(response.json["data"], {"alpaca": {"account": {}}})


if __name__ == "__main__":
    unittest.main()
