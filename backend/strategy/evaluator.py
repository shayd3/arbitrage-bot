import logging

from backend.execution.executor import executor
from backend.models import Game, KalshiMarket
from backend.scanner.sports import SportConfig
from backend.strategy.late_game import late_game_strategy

logger = logging.getLogger(__name__)


class StrategyEvaluator:
    def __init__(self):
        self._strategies = [late_game_strategy]

    async def evaluate(self, game: Game, market: KalshiMarket, config: SportConfig):
        for strategy in self._strategies:
            try:
                signal = await strategy.evaluate(game, market, config)
                if signal.should_trade:
                    logger.info(f"Strategy signal for {market.ticker}: {signal.reason}")
                    await executor.execute(
                        ticker=market.ticker,
                        side=signal.side,
                        contracts=signal.contracts,
                        price=signal.price,
                        game_id=game.id,
                        reason=signal.reason,
                    )
            except Exception as e:
                logger.error(f"Strategy evaluation error: {e}", exc_info=True)


evaluator = StrategyEvaluator()
