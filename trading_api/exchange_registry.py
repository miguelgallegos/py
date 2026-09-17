from typing import Dict

from config import EXCHANGE_CONFIG, TEST_MODE
from exchanges.alpaca import AlpacaAdapter
from exchanges.kraken import KrakenAdapter
from exchanges.robinhood import RobinhoodAdapter
from exchanges.webull import WebullAdapter


EXCHANGE_ADAPTERS = {
    "robinhood": RobinhoodAdapter,
    "webull": WebullAdapter,
    "kraken": KrakenAdapter,
    "alpaca": AlpacaAdapter,
}


def get_exchange_adapter(exchange_name: str):
    key = exchange_name.strip().lower()
    adapter_class = EXCHANGE_ADAPTERS.get(key)
    if adapter_class is None:
        raise ValueError(f"Exchange '{exchange_name}' is not supported.")
    return adapter_class(EXCHANGE_CONFIG.get(key, {}), test_mode=TEST_MODE)
