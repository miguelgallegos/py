from typing import Any, Dict, Optional

from exchanges.base import ExchangeAdapter


class KrakenAdapter(ExchangeAdapter):
    def __init__(self, config: Dict[str, Any], test_mode: bool = False):
        super().__init__(config, test_mode)
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.client = None

    def _client(self):
        if self.test_mode:
            raise RuntimeError("Kraken adapter is running in TEST_MODE and no live client is available.")
        if self.client is None:
            try:
                import krakenex
            except ImportError as exc:
                raise ImportError("krakenex is required for Kraken integration") from exc

            if not self.api_key or not self.api_secret:
                raise ValueError("Kraken API key and secret are required for live mode.")
            self.client = krakenex.API(key=self.api_key, secret=self.api_secret)
        return self.client

    def place_order(
        self,
        operation: str,
        symbol: str,
        order_type: str,
        quantity: Optional[float] = None,
        amount_percent: Optional[float] = None,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        if self.test_mode:
            return {
                "exchange": "kraken",
                "operation": operation,
                "symbol": symbol,
                "order_type": order_type,
                "quantity": quantity,
                "amount_percent": amount_percent,
                "price": price,
                "status": "simulated",
            }

        client = self._client()
        if order_type == "limit" and price is None:
            raise ValueError("'price' is required for limit orders")

        pair = symbol.upper()
        payload = {
            "pair": pair,
            "type": operation,
            "ordertype": order_type,
            "volume": str(quantity),
        }
        if order_type == "limit":
            payload["price"] = str(price)

        return client.query_private("AddOrder", payload)

    def get_portfolio(self) -> Dict[str, Any]:
        if self.test_mode:
            return {
                "exchange": "kraken",
                "balances": {"ZUSD": "1000.00", "XXBT": "0.05"},
            }

        client = self._client()
        balances = client.query_private("Balance")
        return {"exchange": "kraken", "balances": balances.get("result", balances)}

    def resolve_quantity_for_auto_trade(self, symbol: str, amount_percent: float) -> float:
        if self.test_mode:
            return max(1.0, round(amount_percent / 100 * 5, 6))

        client = self._client()
        balances = client.query_private("Balance").get("result", {})
        fiat_balance = 0.0
        for key, value in balances.items():
            if key in {"ZUSD", "USDT", "USDC", "ZEUR"}:
                fiat_balance = float(value)
                break

        if fiat_balance <= 0.0:
            raise ValueError("No supported fiat balance found for auto trade")

        ticker = client.query_public("Ticker", {"pair": symbol.upper()})
        price = float(next(iter(ticker.get("result", {}).values()))["c"][0])
        quantity = (fiat_balance * amount_percent / 100.0) / price
        return float(int(quantity)) if quantity >= 1 else float(round(quantity, 6))
