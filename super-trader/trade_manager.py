from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PositionPlan:
    entry_price: float
    stop_loss: float
    tp_levels: tuple[float, ...] = (0.02, 0.04, 0.06)
    sl_levels: tuple[float, ...] = (0.01, 0.02)
    trail_stop_pct: float = 0.01
    size_pct: float = 1.0
    partials_taken: set[int] = field(default_factory=set)


class JesseTradeManager:
    def __init__(self, tp_levels: tuple[float, ...] = (0.02, 0.04, 0.06), sl_levels: tuple[float, ...] = (0.01, 0.02), trail_stop_pct: float = 0.01, partial_exit_ratio: float = 0.5):
        self.tp_levels = tuple(float(v) for v in tp_levels)
        self.sl_levels = tuple(float(v) for v in sl_levels)
        self.trailing_stop_pct = float(trail_stop_pct)
        self.partial_exit_ratio = float(partial_exit_ratio)

    def build_position(self, entry_price: float, side: str = "LONG") -> PositionPlan:
        if side.upper() == "LONG":
            stop = entry_price * (1.0 - self.sl_levels[0])
        else:
            stop = entry_price * (1.0 + self.sl_levels[0])
        return PositionPlan(
            entry_price=float(entry_price),
            stop_loss=float(stop),
            tp_levels=self.tp_levels,
            sl_levels=self.sl_levels,
            trail_stop_pct=self.trailing_stop_pct,
            size_pct=1.0,
        )

    def check_exit(self, plan: PositionPlan, current_price: float, side: str = "LONG") -> dict[str, Any]:
        side = side.upper()
        if side == "LONG":
            if current_price <= plan.stop_loss:
                return {"action": "close", "price": current_price, "reason": "stop_loss"}
            for level_index, tp_level in enumerate(self.tp_levels):
                if level_index in plan.partials_taken:
                    continue
                target = plan.entry_price * (1.0 + tp_level)
                if current_price >= target:
                    plan.partials_taken.add(level_index)
                    return {"action": "partial", "price": current_price, "level": level_index, "ratio": self.partial_exit_ratio, "reason": "take_profit"}
            if self.trailing_stop_pct > 0:
                trailing_stop = current_price * (1.0 - self.trailing_stop_pct)
                plan.stop_loss = max(plan.stop_loss, trailing_stop)
        else:
            if current_price >= plan.stop_loss:
                return {"action": "close", "price": current_price, "reason": "stop_loss"}
            for level_index, tp_level in enumerate(self.tp_levels):
                if level_index in plan.partials_taken:
                    continue
                target = plan.entry_price * (1.0 - tp_level)
                if current_price <= target:
                    plan.partials_taken.add(level_index)
                    return {"action": "partial", "price": current_price, "level": level_index, "ratio": self.partial_exit_ratio, "reason": "take_profit"}
            if self.trailing_stop_pct > 0:
                trailing_stop = current_price * (1.0 + self.trailing_stop_pct)
                plan.stop_loss = min(plan.stop_loss, trailing_stop)

        return {"action": "hold", "price": current_price}


class ExecutionManager:
    def __init__(self, trade_manager: JesseTradeManager | None = None):
        self.trade_manager = trade_manager or JesseTradeManager()

    def on_entry(self, entry_price: float, side: str = "LONG") -> PositionPlan:
        return self.trade_manager.build_position(entry_price, side)

    def on_bar(self, plan: PositionPlan, current_price: float, side: str = "LONG") -> dict[str, Any]:
        return self.trade_manager.check_exit(plan, current_price, side)
