from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from brokers import BrokerAdapter, PaperBroker
from trade_manager import ExecutionManager, JesseTradeManager


@dataclass
class TradeExecution:
    symbol: str
    side: str
    qty: float
    entry_price: float
    current_price: float
    status: str = "open"
    partials: list[dict[str, Any]] = field(default_factory=list)


class ExecutionEngine:
    def __init__(self, broker: BrokerAdapter | None = None, trade_manager: JesseTradeManager | None = None):
        self.broker = broker or PaperBroker()
        self.trade_manager = trade_manager or JesseTradeManager()
        self.execution_manager = ExecutionManager(self.trade_manager)
        self.open_positions: dict[str, TradeExecution] = {}

    def open_long(self, symbol: str, qty: float, entry_price: float) -> dict[str, Any]:
        self.broker.place_order(symbol, "BUY", qty, entry_price, "market")
        plan = self.execution_manager.on_entry(entry_price, "LONG")
        self.open_positions[symbol] = TradeExecution(symbol=symbol, side="LONG", qty=qty, entry_price=entry_price, current_price=entry_price)
        self.open_positions[symbol].partials.append({"entry": entry_price, "plan": plan})
        return {"symbol": symbol, "side": "LONG", "qty": qty, "entry_price": entry_price, "plan": plan}

    def handle_bar(self, symbol: str, current_price: float) -> dict[str, Any] | None:
        position = self.open_positions.get(symbol)
        if position is None:
            return None
        position.current_price = current_price
        plan = position.partials[-1]["plan"]
        action = self.execution_manager.on_bar(plan, current_price, position.side)

        if action["action"] == "partial":
            partial_qty = max(position.qty * float(action["ratio"]), 0.0)
            self.broker.place_order(symbol, "SELL", partial_qty, current_price, "limit")
            action["partial_qty"] = partial_qty
            position.partials.append({"tp_level": action.get("level"), "price": current_price, "quantity": partial_qty})
            return action

        if action["action"] == "close":
            self.broker.place_order(symbol, "SELL", position.qty, current_price, "limit")
            position.status = "closed"
            del self.open_positions[symbol]
            return {"symbol": symbol, "side": position.side, "qty": position.qty, "price": current_price, "action": "close"}

        return action
