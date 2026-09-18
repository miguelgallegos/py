from .backtest import BacktestEngine, Trade
from .brokers import AlpacaBroker, BrokerAdapter, RobinhoodBroker
from .live_trader import LiveTrader, PaperBroker
from .optimizer import optimize_strategy
from .strategies import STRATEGY_REGISTRY
from .strategies.bollinger_strategy import BollingerStrategy
from .strategies.macd_strategy import MacdStrategy
from .strategies.rsi_strategy import RsiStrategy
from .strategies.sma_crossover import SmaCrossoverStrategy
from .trade_manager import JesseTradeManager, PositionPlan

__all__ = [
    "BacktestEngine",
    "Trade",
    "LiveTrader",
    "PaperBroker",
    "BrokerAdapter",
    "RobinhoodBroker",
    "AlpacaBroker",
    "optimize_strategy",
    "SmaCrossoverStrategy",
    "RsiStrategy",
    "MacdStrategy",
    "BollingerStrategy",
    "JesseTradeManager",
    "PositionPlan",
    "STRATEGY_REGISTRY",
]
