from typing import Any, Dict, Optional

from exchanges.base import ExchangeAdapter


class RobinhoodAdapter(ExchangeAdapter):
    def __init__(self, config: Dict[str, Any], test_mode: bool = False):
        super().__init__(config, test_mode)
        self.username = config.get("username")
        self.password = config.get("password")
        self.two_factor_method = config.get("two_factor_method", "sms")
        self.logged_in = False

    def _login(self):
        if self.test_mode:
            return
        if self.logged_in:
            return

        try:
            import robin_stocks.robinhood as rh
        except ImportError as exc:
            raise ImportError("robin_stocks is required for Robinhood integration") from exc

        if not self.username or not self.password:
            raise ValueError("Robinhood username and password are required for live mode.")

        rh.login(self.username, self.password, store_session=False, mfa_code=None, device_token=None)
        self.logged_in = True

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
                "exchange": "robinhood",
                "operation": operation,
                "symbol": symbol,
                "order_type": order_type,
                "quantity": quantity,
                "amount_percent": amount_percent,
                "price": price,
                "status": "simulated",
            }

        self._login()
        import robin_stocks.robinhood as rh

        if order_type == "market":
            if operation == "buy":
                order = rh.order_buy_market(symbol, quantity)
            else:
                order = rh.order_sell_market(symbol, quantity)
        else:
            if price is None:
                raise ValueError("'price' is required for limit orders")
            if operation == "buy":
                order = rh.order_buy_limit(symbol, quantity, price)
            else:
                order = rh.order_sell_limit(symbol, quantity, price)

        return order

    def get_portfolio(self) -> Dict[str, Any]:
        if self.test_mode:
            return {
                "exchange": "robinhood",
                "holdings": [{"symbol": "AAPL", "quantity": "1.0", "average_buy_price": "170.00"}],
            }

        self._login()
        import robin_stocks.robinhood as rh

        holdings = rh.build_holdings()
        return {"exchange": "robinhood", "holdings": holdings}

    def resolve_quantity_for_auto_trade(self, symbol: str, amount_percent: float) -> float:
        if self.test_mode:
            return max(1.0, round(amount_percent / 100 * 5, 6))

        self._login()
        import robin_stocks.robinhood as rh

        account = rh.load_account_profile()
        buying_power = float(account.get("buying_power", 0.0))
        price_data = rh.stocks.get_latest_price(symbol)
        price = float(price_data[0]) if price_data else 0.0
        if buying_power <= 0 or price <= 0:
            raise ValueError("Unable to resolve quantity for auto trade")

        quantity = (buying_power * amount_percent / 100.0) / price
        return float(int(quantity)) if quantity >= 1 else float(round(quantity, 6))
