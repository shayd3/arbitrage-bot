import asyncio
import logging
from datetime import datetime
from backend.clients.espn import fetch_all_games
from backend.clients.kalshi import kalshi_client
from backend.models import Game, GameStatus, Sport, Balance
from backend.scanner.matcher import match_game_to_markets
from backend.scanner.sports import get_sport_config, SPORT_SERIES_TICKER
from backend.db import log_scanner, insert_balance
from backend.config import settings, BotMode
from backend.api.websocket import manager
from datetime import datetime

async def sync_live_balance():
    """Fetch real Kalshi balance and store in DB so risk checks have current data."""
    try:
        cents = await kalshi_client.get_balance()
        available = int(cents) / 100
        await insert_balance(Balance(
            timestamp=datetime.utcnow(),
            available=available,
            portfolio_value=0.0,
            total=available,
            is_simulated=False,
        ))
        logger.info(f"Synced live balance: ${available:.2f}")
    except Exception as e:
        logger.warning(f"Failed to sync live balance: {e}")

logger = logging.getLogger(__name__)

class ScannerEngine:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._games: list[Game] = []
        self._markets: dict[Sport, list] = {}  # per-sport game winner markets

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scanner engine started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scanner engine stopped")

    async def _run_loop(self):
        while self._running:
            try:
                await self._scan()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Scanner error: {e}", exc_info=True)
                await log_scanner("error", f"Scanner loop error: {e}")
            await asyncio.sleep(settings.espn_poll_interval)

    async def _scan(self):
        # Keep live balance in sync so risk checks have current data
        if settings.bot_mode == BotMode.LIVE:
            await sync_live_balance()

        # Fetch live games
        games = await fetch_all_games()
        self._games = games

        in_progress = [g for g in games if g.status == GameStatus.IN_PROGRESS]

        if not in_progress:
            return

        # Fetch game winner markets per sport in play
        sports_in_play = {g.sport for g in in_progress}
        for sport in sports_in_play:
            series_ticker = SPORT_SERIES_TICKER.get(sport)
            if not series_ticker:
                continue
            try:
                self._markets[sport] = await kalshi_client.get_markets(
                    status="open", limit=100, series_ticker=series_ticker
                )
            except Exception as e:
                logger.warning(f"Failed to fetch {sport} markets: {e}")
                # Continue with cached markets

        for game in in_progress:
            await self._process_game(game)

        # Broadcast game updates to dashboard
        await manager.broadcast("games_update", {
            "games": [g.model_dump(mode="json") for g in games],
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def _process_game(self, game: Game):
        config = await get_sport_config(game.sport)

        # Check if we're in the critical window
        if not game.clock:
            return

        clock = game.clock
        is_final_period = clock.period == config.final_period
        in_time_window = (
            clock.seconds_remaining is not None and
            clock.seconds_remaining <= config.final_period_window
        )

        if not (is_final_period and in_time_window):
            return

        lead = abs(game.home_team.score - game.away_team.score)
        if lead < config.min_lead:
            return

        # Find matching Kalshi markets
        sport_markets = self._markets.get(game.sport, [])
        matches = match_game_to_markets(game, sport_markets)
        if not matches:
            return

        leading_team = game.home_team if game.home_team.score > game.away_team.score else game.away_team

        await log_scanner("info", f"Opportunity detected: {game.id}", {
            "game_id": game.id,
            "home": game.home_team.name,
            "away": game.away_team.name,
            "home_score": game.home_team.score,
            "away_score": game.away_team.score,
            "lead": lead,
            "period": clock.period,
            "clock": clock.display_clock,
            "matched_markets": [m.ticker for m in matches],
        })

        await manager.broadcast("opportunity", {
            "game_id": game.id,
            "leading_team": leading_team.name,
            "lead": lead,
            "clock": clock.display_clock,
            "period": clock.period,
            "markets": [m.model_dump(mode="json") for m in matches],
        })

        # Dispatch to strategy evaluator
        from backend.strategy.evaluator import evaluator
        for market in matches:
            await evaluator.evaluate(game, market, config)

    @property
    def games(self) -> list[Game]:
        return self._games

scanner = ScannerEngine()
