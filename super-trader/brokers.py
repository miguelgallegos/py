from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrokerAdapter:
    name: str = "paper"
    cash: float = 10000.0
    position_qty: float = 0.0
    avg_price: float = 0.0
    orders: list[dict[str, Any]] = field(default_factory=list)

    def place_order(self, symbol: str, side: str, qty: float, price: float | None = None, order_type: str = "market") -> dict:
        payload = {"symbol": symbol, "side": side, "qty": qty, "price": price, "order_type": order_type, "broker": self.name}
        self.orders.append(payload)
        return payload

    def get_account_status(self) -> dict[str, Any]:
        return {"cash": self.cash, "position_qty": self.position_qty, "avg_price": self.avg_price, "broker": self.name}


@dataclass
class PaperBroker(BrokerAdapter):
    name: str = "paper"

    def place_order(self, symbol: str, side: str, qty: float, price: float | None = None, order_type: str = "market") -> dict:
        if price is None:
            raise ValueError("PaperBroker requires a price for order simulation.")
        if side.upper() == "BUY":
            cost = qty * price
            self.cash -= cost
            self.position_qty += qty
            self.avg_price = ((self.avg_price * max(self.position_qty - qty, 0.0)) + (qty * price)) / max(self.position_qty, 1e-9)
        elif side.upper() == "SELL":
            proceeds = qty * price
            self.cash += proceeds
            self.position_qty -= qty
            if self.position_qty <= 0:
                self.position_qty = 0.0
                self.avg_price = 0.0
        payload = {"symbol": symbol, "side": side, "qty": qty, "price": price, "order_type": order_type, "broker": self.name}
        self.orders.append(payload)
        return payload


@dataclass
class RobinhoodBroker(BrokerAdapter):
    name: str = "robinhood"

    def place_order(self, symbol: str, side: str, qty: float, price: float | None = None, order_type: str = "market") -> dict:
        return super().place_order(symbol, side, qty, price, order_type)


@dataclass
class AlpacaBroker(BrokerAdapter):
    name: str = "alpaca"

    def place_order(self, symbol: str, side: str, qty: float, price: float | None = None, order_type: str = "market") -> dict:
        return super().place_order(symbol, side, qty, price, order_type)
