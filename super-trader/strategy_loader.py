from __future__ import annotations

import json
from pathlib import Path

from strategies import STRATEGY_REGISTRY


def load_strategy_registry(path: str | Path = "strategy_registry.json") -> dict:
    registry_path = Path(path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Strategy registry not found: {registry_path}")
    with registry_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload.get("strategies", {})


def resolve_strategy(name: str, config: dict | None = None) -> object:
    config = config or {}
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy '{name}'. Available: {sorted(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name](config)
