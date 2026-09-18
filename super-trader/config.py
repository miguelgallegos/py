from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class StrategyConfig:
    name: str = "sma_crossover"
    fast_window: int = 10
    slow_window: int = 30
    position_size: float = 1.0
    tp_levels: tuple[float, ...] = (0.02, 0.04, 0.06)
    sl_levels: tuple[float, ...] = (0.01, 0.02)
    risk_per_trade: float = 0.01
    allow_short: bool = False
    commission: float = 0.0
    indicator_params: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, values: dict) -> "StrategyConfig":
        return cls(
            name=values.get("name", "sma_crossover"),
            fast_window=int(values.get("fast_window", 10)),
            slow_window=int(values.get("slow_window", 30)),
            position_size=float(values.get("position_size", 1.0)),
            tp_levels=tuple(float(v) for v in values.get("tp_levels", (0.02, 0.04, 0.06))),
            sl_levels=tuple(float(v) for v in values.get("sl_levels", (0.01, 0.02))),
            risk_per_trade=float(values.get("risk_per_trade", 0.01)),
            allow_short=bool(values.get("allow_short", False)),
            commission=float(values.get("commission", 0.0)),
            indicator_params=dict(values.get("indicator_params", {})),
        )
