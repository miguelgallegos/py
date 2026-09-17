import uuid
from typing import Any, Dict, Optional

from webull.data.common.category import Category
from exchanges.base import ExchangeAdapter


class WebullAdapter(ExchangeAdapter):
    def __init__(self, config: Dict[str, Any], test_mode: bool = False):
        super().__init__(config, test_mode)
        self.app_key = config.get("app_key")
        self.app_secret = config.get("app_secret")
        self.region = config.get("region", "us").lower()
        self.account_id = config.get("account_id")
        self.api_endpoint = config.get("api_endpoint")
        self.token_dir = config.get("token_dir")
        self.api_client = None
        self.trade_client = None
        self.data_client = None

    def _api_client(self):
        if self.test_mode:
            raise RuntimeError("Webull adapter is running in TEST_MODE and no live client is available.")
        if self.api_client is None:
            try:
                from webull.core.client import ApiClient
            except ImportError as exc:
                raise ImportError("webull-openapi-python-sdk is required for Webull integration") from exc

            if not self.app_key or not self.app_secret:
                raise ValueError("Webull APP key and secret are required for live mode.")

            self.api_client = ApiClient(self.app_key, self.app_secret, self.region)
            if self.api_endpoint:
                self.api_client.add_endpoint(self.region, self.api_endpoint)
            if self.token_dir:
                self.api_client.set_token_dir(self.token_dir)
        return self.api_client

    def _trade_client(self):
        if self.trade_client is None:
            from webull.trade.trade_client import TradeClient

            self.trade_client = TradeClient(self._api_client())
        return self.trade_client

    def _data_client(self):
        if self.data_client is None:
            from webull.data.data_client import DataClient

            self.data_client = DataClient(self._api_client())
        return self.data_client

    def _resolve_account_id(self) -> str:
        if self.account_id:
            return self.account_id

        response = self._trade_client().account_v2.get_account_list()
        if not hasattr(response, "json"):
            raise ValueError("Unable to retrieve Webull account list")

        data = response.json()
        accounts = data.get("data") or data.get("accounts") or []
        if isinstance(accounts, dict):
            accounts = [accounts]
        if not accounts:
            raise ValueError("No Webull account ID found; set WEBULL_ACCOUNT_ID in .env")

        return accounts[0].get("accountId") or accounts[0].get("account_id")

    def _market_for_region(self) -> str:
        return "HK" if self.region == "hk" else "US"

    def _build_order_payload(
        self,
        operation: str,
        symbol: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        payload = {
            "client_order_id": uuid.uuid4().hex,
            "symbol": symbol,
            "instrument_type": "EQUITY",
            "market": self._market_for_region(),
            "order_type": order_type.upper(),
            "quantity": str(quantity),
            "side": operation.upper(),
            "time_in_force": "DAY",
            "entrust_type": "QTY",
            "support_trading_session": "CORE",
        }
        if order_type.lower() == "limit":
            if price is None:
                raise ValueError("'price' is required for limit orders")
            payload["limit_price"] = str(price)

        return payload

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
                "exchange": "webull",
                "operation": operation,
                "symbol": symbol,
                "order_type": order_type,
                "quantity": quantity,
                "amount_percent": amount_percent,
                "price": price,
                "status": "simulated",
            }

        account_id = self._resolve_account_id()
        trade_client = self._trade_client()
        order_payload = self._build_order_payload(operation, symbol, order_type, quantity, price)
        response = trade_client.order_v2.place_order(account_id, [order_payload])

        return response.json() if hasattr(response, "json") else response

    def get_portfolio(self) -> Dict[str, Any]:
        if self.test_mode:
            return {
                "exchange": "webull",
                "account": {"cash": "1000.00"},
                "positions": [{"symbol": "TSLA", "quantity": "1.0", "market_value": "250.00"}],
            }

        account_id = self._resolve_account_id()
        trade_client = self._trade_client()
        balance_response = trade_client.account_v2.get_account_balance(account_id)
        positions_response = trade_client.account_v2.get_account_position(account_id)

        return {
            "exchange": "webull",
            "account": balance_response.json() if hasattr(balance_response, "json") else balance_response,
            "positions": positions_response.json() if hasattr(positions_response, "json") else positions_response,
        }

    def resolve_quantity_for_auto_trade(self, symbol: str, amount_percent: float) -> float:
        if self.test_mode:
            return max(1.0, round(amount_percent / 100 * 5, 6))

        account_id = self._resolve_account_id()
        balance_response = self._trade_client().account_v2.get_account_balance(account_id)
        if not hasattr(balance_response, "json"):
            raise ValueError("Unable to resolve Webull account balance")

        balance_data = balance_response.json()
        balance = balance_data.get("data") or balance_data
        cash_amount = float(balance.get("available_balance") or balance.get("cash") or balance.get("availableCash") or 0.0)
        if cash_amount <= 0:
            raise ValueError("Unable to resolve Webull cash balance for auto trade")

        data_client = self._data_client()
        snapshot_response = data_client.market_data.get_snapshot(symbol, Category.EQUITY)
        if not hasattr(snapshot_response, "json"):
            raise ValueError("Unable to resolve Webull quote data")

        snapshot_data = snapshot_response.json()
        records = snapshot_data.get("data") or snapshot_data
        price = 0.0
        if isinstance(records, list) and records:
            record = records[0]
            price = float(record.get("last_price") or record.get("last_price_usd") or record.get("price") or 0.0)
        elif isinstance(records, dict):
            price = float(records.get("last_price") or records.get("last_price_usd") or records.get("price") or 0.0)

        if price <= 0:
            raise ValueError("Unable to retrieve a valid market price for auto trade")

        quantity = (cash_amount * amount_percent / 100.0) / price
        return float(int(quantity)) if quantity >= 1 else float(round(quantity, 6))
