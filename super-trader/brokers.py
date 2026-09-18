from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BrokerAdapter:
    name: str = "paper"

    def place_order(self, symbol: str, side: str, qty: float, price: float | None = None, order_type: str = "market") -> dict:
        return {"symbol": symbol, "side": side, "qty": qty, "price": price, "order_type": order_type, "broker": self.name}


@dataclass
class RobinhoodBroker(BrokerAdapter):
    name: str = "robinhood"

    def place_order(self, symbol: str, side: str, qty: float, price: float | None = None, order_type: str = "market") -> dict:
        return {"symbol": symbol, "side": side, "qty": qty, "price": price, "order_type": order_type, "broker": "robinhood"}


@dataclass
class AlpacaBroker(BrokerAdapter):
    name: str = "alpaca"

    def place_order(self, symbol: str, side: str, qty: float, price: float | None = None, order_type: str = "market") -> dict:
        return {"symbol": symbol, "side": side, "qty": qty, "price": price, "order_type": order_type, "broker": "alpaca"}
