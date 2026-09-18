from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class Signal:
    action: str
    reason: str = ""
    confidence: float = 0.0


class Strategy:
    name = "base"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
