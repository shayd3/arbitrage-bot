import logging

from backend.db import get_config_override
from backend.models import Game, GameStatus, KalshiMarket
from backend.scanner.matcher import (
    espn_abbrev_to_kalshi,
    outcome_team_from_ticker,
    team_to_kalshi_abbrev,
)
from backend.scanner.sports import SportConfig
from backend.strategy.base import Strategy, TradeSignal

logger = logging.getLogger(__name__)


class LateGameStrategy(Strategy):
    """
    Buy YES on the leading team when:
    - Final period, within time window
    - Lead exceeds threshold
    - YES price is above minimum (high probability = high price)
    - Price allows at least 12¢ spread to $1 settlement
    """

    async def evaluate(self, game: Game, market: KalshiMarket, config: SportConfig) -> TradeSignal:
        # Runtime config overrides
        min_yes_price = await self._get_min_yes_price(config)

        if game.status != GameStatus.IN_PROGRESS:
            return TradeSignal(False, "yes", 0, 0, "Game not in progress")

        if not game.clock:
            return TradeSignal(False, "yes", 0, 0, "No clock data")

        clock = game.clock
        home_score = game.home_team.score
        away_score = game.away_team.score
        lead = abs(home_score - away_score)

        if lead < config.min_lead:
            return TradeSignal(False, "yes", 0, 0, f"Lead {lead} < min {config.min_lead}")

        if home_score > away_score:
            leading_team = game.home_team
        elif away_score > home_score:
            leading_team = game.away_team
        else:
            return TradeSignal(False, "yes", 0, 0, "Game is tied")

        yes_ask = market.yes_ask
        no_ask = market.no_ask

        if yes_ask is None:
            return TradeSignal(False, "yes", 0, 0, "No YES ask price")

        # Determine which team YES refers to on this market by parsing the ticker suffix.
        # e.g. KXNBAGAME-26MAR25SASMEM-SAS → YES = SAS wins
        outcome_abbrev = outcome_team_from_ticker(market.ticker)
        leading_kalshi = team_to_kalshi_abbrev(leading_team.name, game.sport)
        if leading_kalshi is None:
            leading_kalshi = espn_abbrev_to_kalshi(leading_team.abbreviation, game.sport)

        if outcome_abbrev and leading_kalshi:
            if outcome_abbrev == leading_kalshi.upper():
                side = "yes"
                price = yes_ask
            else:
                side = "no"
                price = no_ask if no_ask is not None else (100 - yes_ask)
        else:
            # Fallback: ticker unparseable, use legacy home=YES assumption
            logger.warning(
                "Could not parse outcome team from ticker %s, falling back to home=YES",
                market.ticker,
            )
            if home_score > away_score:
                side = "yes"
                price = yes_ask
            else:
                side = "no"
                price = no_ask if no_ask is not None else (100 - yes_ask)

        if price < min_yes_price:
            return TradeSignal(False, side, price, 0, f"Price {price}¢ < min {min_yes_price}¢")

        # Max profit is (100 - price) cents per contract
        # Min acceptable spread: 12¢
        spread = 100 - price
        if spread < 12:
            return TradeSignal(False, side, price, 0, f"Spread {spread}¢ < 12¢ minimum")

        # Size position to 20% of available balance
        from backend.execution.risk import get_max_position_dollars

        max_dollars = await get_max_position_dollars()
        contracts = self._size_position(price, max_dollars)

        reason = (
            f"Lead={lead}, Period={clock.period}, Clock={clock.display_clock}, "
            f"Price={price}¢, Spread={spread}¢"
        )
        logger.info(
            f"Trade signal: {side.upper()} {contracts}x {market.ticker} @ {price}¢ | {reason}"
        )

        return TradeSignal(True, side, price, contracts, reason)

    async def _get_min_yes_price(self, config: SportConfig) -> int:

        override = await get_config_override(f"min_yes_price_{config.sport.value}")
        if override:
            try:
                return int(override)
            except ValueError:
                pass
        return config.min_yes_price

    def _size_position(self, price: int, max_dollars: float) -> int:
        """Size to spend at most max_dollars (20% of balance) on this trade."""
        if price <= 0 or max_dollars <= 0:
            return 0
        # contracts * (price/100) = dollars spent
        contracts = int((max_dollars * 100) / price)
        return max(1, contracts)


late_game_strategy = LateGameStrategy()
