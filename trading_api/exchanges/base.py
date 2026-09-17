from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ExchangeAdapter(ABC):
    def __init__(self, config: Dict[str, Any], test_mode: bool = False):
        self.config = config
        self.test_mode = test_mode

    @abstractmethod
    def place_order(
        self,
        operation: str,
        symbol: str,
        order_type: str,
        quantity: Optional[float] = None,
        amount_percent: Optional[float] = None,
        price: Optional[float] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_portfolio(self) -> Dict[str, Any]:
        raise NotImplementedError

    def resolve_quantity_for_auto_trade(
        self, symbol: str, amount_percent: float
    ) -> float:
        raise NotImplementedError("Auto-trade quantity resolution is not implemented.")
