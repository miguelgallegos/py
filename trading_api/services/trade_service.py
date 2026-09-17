from typing import Any, Dict, Optional

from exchange_registry import get_exchange_adapter
from config import DEFAULT_AUTO_TRADE_PERCENT

VALID_OPERATIONS = {"buy", "sell"}
VALID_ORDER_TYPES = {"market", "limit"}


def parse_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def execute_trade(payload: Dict[str, Any]) -> Dict[str, Any]:
    exchange_name = payload.get("exchange")
    if not exchange_name:
        raise ValueError("'exchange' is required")

    operation = str(payload.get("operation", "")).strip().lower()
    if operation not in VALID_OPERATIONS:
        raise ValueError("'operation' must be 'buy' or 'sell'")

    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("'symbol' is required")

    order_type = str(payload.get("order_type", "")).strip().lower()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError("'order_type' must be 'market' or 'limit'")

    quantity = payload.get("quantity")
    amount_percent = payload.get("amount_percent")
    auto_trade = parse_boolean(payload.get("auto_trade"))

    if auto_trade:
        if amount_percent is None:
            amount_percent = DEFAULT_AUTO_TRADE_PERCENT
        if quantity is not None:
            raise ValueError("Provide either 'quantity' or 'auto_trade', not both")

    adapter = get_exchange_adapter(exchange_name)

    if auto_trade:
        resolved_quantity = adapter.resolve_quantity_for_auto_trade(symbol, float(amount_percent))
        if resolved_quantity <= 0:
            raise ValueError("Unable to resolve an auto-trade quantity for the requested asset")
        quantity = resolved_quantity

    if quantity is None:
        raise ValueError("'quantity' is required when auto_trade is not true")

    try:
        quantity_value = float(quantity)
    except (TypeError, ValueError):
        raise ValueError("'quantity' must be a number")

    if quantity_value <= 0:
        raise ValueError("'quantity' must be greater than zero")

    price = payload.get("price")
    if price is not None:
        try:
            price = float(price)
        except (TypeError, ValueError):
            raise ValueError("'price' must be a number when provided")

    return adapter.place_order(
        operation=operation,
        symbol=symbol,
        order_type=order_type,
        quantity=quantity_value,
        amount_percent=float(amount_percent) if amount_percent is not None else None,
        price=price,
    )
