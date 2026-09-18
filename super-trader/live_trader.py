from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PaperBroker:
    cash: float = 10000.0
    position: float = 0.0
    avg_price: float = 0.0

    def buy(self, price: float, qty: float) -> None:
        self.cash -= price * qty
        self.position += qty
        self.avg_price = (self.avg_price * (self.position - qty) + price * qty) / max(self.position, 1e-9)

    def sell(self, price: float, qty: float) -> None:
        self.cash += price * qty
        self.position -= qty
        if self.position <= 0:
            self.position = 0.0
            self.avg_price = 0.0


class LiveTrader:
    def __init__(self, strategy_name: str = "sma_crossover"):
        self.strategy_name = strategy_name

    def evaluate_signal(self, df: Any, strategy: Any) -> dict[str, Any]:
        signals = strategy.generate_signals(df)
        last = signals.iloc[-1]
        return {
            "signal": int(last.get("signal", 0)),
            "close": float(last["Close"]),
            "fast_sma": float(last.get("fast_sma", 0.0)),
            "slow_sma": float(last.get("slow_sma", 0.0)),
        }
