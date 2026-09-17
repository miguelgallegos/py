from typing import Any, Dict, List, Optional

from exchange_registry import get_exchange_adapter
from config import EXCHANGE_CONFIG


def get_portfolio(exchange_name: Optional[str] = None) -> Dict[str, Any]:
    if exchange_name:
        adapter = get_exchange_adapter(exchange_name)
        return {exchange_name.lower(): adapter.get_portfolio()}

    results: Dict[str, Any] = {}
    for name in EXCHANGE_CONFIG.keys():
        try:
            adapter = get_exchange_adapter(name)
            results[name] = adapter.get_portfolio()
        except Exception as exc:
            results[name] = {"error": str(exc)}
    return results
