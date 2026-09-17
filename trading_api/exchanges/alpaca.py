from typing import Any, Dict, Optional

from exchanges.base import ExchangeAdapter


class AlpacaAdapter(ExchangeAdapter):
    def __init__(self, config: Dict[str, Any], test_mode: bool = False):
        super().__init__(config, test_mode)
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.base_url = config.get("base_url", "https://paper-api.alpaca.markets")
        self.trading_client = None
        self.data_client = None

    def _trading_client(self):
        if self.test_mode:
            raise RuntimeError("Alpaca adapter is running in TEST_MODE and no live client is available.")
        if self.trading_client is None:
            try:
                from alpaca.trading.client import TradingClient
            except ImportError as exc:
                raise ImportError("alpaca-py is required for Alpaca integration") from exc

            if not self.api_key or not self.api_secret:
                raise ValueError("Alpaca API key and secret are required for live mode.")
            self.trading_client = TradingClient(
                self.api_key,
                self.api_secret,
                paper=True if "paper" in self.base_url else False,
                base_url=self.base_url,
            )
        return self.trading_client

    def _data_client(self):
        if self.test_mode:
            raise RuntimeError("Alpaca adapter is running in TEST_MODE and no live client is available.")
        if self.data_client is None:
            try:
                from alpaca.data import StockDataClient
            except ImportError as exc:
                raise ImportError("alpaca-py is required for Alpaca integration") from exc

            if not self.api_key or not self.api_secret:
                raise ValueError("Alpaca API key and secret are required for live mode.")
            data_base_url = (
                "https://data.sandbox.alpaca.markets"
                if "paper" in self.base_url
                else "https://data.alpaca.markets"
            )
            self.data_client = StockDataClient(
                key=self.api_key,
                secret=self.api_secret,
                base_url=data_base_url,
            )
        return self.data_client

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
                "exchange": "alpaca",
                "operation": operation,
                "symbol": symbol,
                "order_type": order_type,
                "quantity": quantity,
                "amount_percent": amount_percent,
                "price": price,
                "status": "simulated",
            }

        client = self._trading_client()
        if order_type == "limit" and price is None:
            raise ValueError("'price' is required for limit orders")

        order = client.submit_order(
            symbol=symbol,
            qty=quantity,
            side=operation,
            type=order_type,
            time_in_force="day",
            limit_price=price if order_type == "limit" else None,
        )
        return order.__dict__ if hasattr(order, "__dict__") else order

    def get_portfolio(self) -> Dict[str, Any]:
        if self.test_mode:
            return {
                "exchange": "alpaca",
                "account": {"cash": "10000.00", "portfolio_value": "0.00"},
                "positions": [],
            }

        client = self._trading_client()
        account = client.get_account()
        positions = [position.__dict__ for position in client.list_positions()]
        return {
            "exchange": "alpaca",
            "account": {"cash": account.cash, "portfolio_value": account.portfolio_value},
            "positions": positions,
        }

    def resolve_quantity_for_auto_trade(self, symbol: str, amount_percent: float) -> float:
        if self.test_mode:
            return max(1.0, round(amount_percent / 100 * 10, 6))

        account = self._trading_client().get_account()
        available_cash = float(account.cash)
        data_client = self._data_client()
        bars = data_client.get_latest_trade(symbol)
        trade_price = float(bars.price)
        if trade_price <= 0:
            raise ValueError("Unable to retrieve a valid market price for auto trade")

        quantity = (available_cash * amount_percent / 100.0) / trade_price
        return float(int(quantity)) if quantity >= 1 else float(round(quantity, 6))
