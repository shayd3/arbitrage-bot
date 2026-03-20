from abc import ABC, abstractmethod

from backend.models import Game, KalshiMarket
from backend.scanner.sports import SportConfig


class TradeSignal:
    def __init__(self, should_trade: bool, side: str, price: int, contracts: int, reason: str):
        self.should_trade = should_trade
        self.side = side  # "yes" or "no"
        self.price = price  # cents
        self.contracts = contracts
        self.reason = reason


class Strategy(ABC):
    @abstractmethod
    async def evaluate(
        self, game: Game, market: KalshiMarket, config: SportConfig
    ) -> TradeSignal:
        ...
