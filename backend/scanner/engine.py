import asyncio
import logging
from datetime import datetime
from backend.clients.espn import fetch_all_games
from backend.clients.kalshi import kalshi_client
from backend.models import Game, GameStatus, Sport
from backend.scanner.matcher import match_game_to_markets
from backend.scanner.sports import get_sport_config
from backend.db import log_scanner
from backend.config import settings
from backend.api.websocket import manager

logger = logging.getLogger(__name__)

class ScannerEngine:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._games: list[Game] = []
        self._markets: list = []

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
        # Fetch live games
        games = await fetch_all_games()
        self._games = games

        in_progress = [g for g in games if g.status == GameStatus.IN_PROGRESS]

        if not in_progress:
            return

        # Fetch markets (less frequently, cache between cycles)
        try:
            self._markets = await kalshi_client.get_markets(status="open", limit=200)
        except Exception as e:
            logger.warning(f"Failed to fetch markets: {e}")
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
        matches = match_game_to_markets(game, self._markets)
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
