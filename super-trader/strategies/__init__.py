from .bollinger_strategy import BollingerStrategy
from .macd_sma_strategy import MacdSmaStrategy
from .macd_strategy import MacdStrategy
from .rsi_strategy import RsiStrategy
from .sma_crossover import SmaCrossoverStrategy

STRATEGY_REGISTRY = {
    "sma_crossover": SmaCrossoverStrategy,
    "rsi": RsiStrategy,
    "macd": MacdStrategy,
    "macd_sma": MacdSmaStrategy,
    "bollinger": BollingerStrategy,
}

__all__ = [
    "SmaCrossoverStrategy",
    "RsiStrategy",
    "MacdStrategy",
    "MacdSmaStrategy",
    "BollingerStrategy",
    "STRATEGY_REGISTRY",
]
