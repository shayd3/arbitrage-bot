import asyncio
import logging
import time
from datetime import datetime
from backend.clients.espn import fetch_games
from backend.clients.kalshi import kalshi_client
from backend.models import Game, GameStatus, KalshiMarket, Sport, Balance
from backend.scanner.matcher import match_markets_to_games
from backend.scanner.sports import get_sport_config, SPORT_SERIES_TICKER
from backend.db import log_scanner, insert_balance
from backend.config import settings
from backend.api.websocket import manager

logger = logging.getLogger(__name__)

async def sync_balance():
    """Fetch Kalshi balance and store in DB so risk checks have current data."""
    try:
        cents = await kalshi_client.get_balance()
        available = int(cents) / 100
        await insert_balance(Balance(
            timestamp=datetime.utcnow(),
            available=available,
            portfolio_value=0.0,
            total=available,
        ))
        logger.info(f"Synced balance: ${available:.2f}")
    except Exception as e:
        logger.warning(f"Failed to sync balance: {e}")

class ScannerEngine:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._games: list[Game] = []
        self._markets: dict[Sport, list[KalshiMarket]] = {}
        self._last_balance_sync: float = 0.0
        self._last_market_fetch: float = 0.0

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
        now = time.monotonic()

        # Throttle balance sync
        if now - self._last_balance_sync >= settings.kalshi_poll_interval:
            await sync_balance()
            self._last_balance_sync = now

        # 1. Fetch Kalshi markets (throttled separately)
        if now - self._last_market_fetch >= settings.kalshi_poll_interval:
            await self._fetch_all_markets()
            self._last_market_fetch = now

        # 2. Determine which sports have open markets
        all_markets: list[KalshiMarket] = []
        sports_with_markets: set[Sport] = set()
        for sport, markets in self._markets.items():
            if markets:
                sports_with_markets.add(sport)
                all_markets.extend(markets)

        # 3. Fetch ESPN scoreboards for sports with open markets, or all sports as fallback
        sports_to_fetch = sports_with_markets if sports_with_markets else set(Sport)
        espn_tasks = {
            sport: fetch_games(sport) for sport in sports_to_fetch
        }
        espn_results = await asyncio.gather(
            *espn_tasks.values(), return_exceptions=True
        )
        all_games: list[Game] = []
        for sport, result in zip(espn_tasks.keys(), espn_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch ESPN {sport.value} games: {result}")
            else:
                all_games.extend(result)

        self._games = all_games

        if not sports_with_markets:
            await manager.broadcast("games_update", {
                "games": [g.model_dump(mode="json") for g in all_games],
                "timestamp": datetime.utcnow().isoformat(),
            })
            return

        # 4. Match markets → games
        in_progress = [g for g in all_games if g.status == GameStatus.IN_PROGRESS]
        pairs = match_markets_to_games(all_markets, in_progress)

        # 5. Group markets by game and process once per game
        markets_by_game: dict[str, tuple[Game, list[KalshiMarket]]] = {}
        for game, market in pairs:
            if game.id not in markets_by_game:
                markets_by_game[game.id] = (game, [])
            markets_by_game[game.id][1].append(market)

        for _, (game, matched_markets) in markets_by_game.items():
            await self._process_game_markets(game, matched_markets)

        # 6. Broadcast all games to dashboard
        await manager.broadcast("games_update", {
            "games": [g.model_dump(mode="json") for g in all_games],
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def _fetch_all_markets(self):
        """Fetch Kalshi game-winner markets for all sports concurrently."""
        async def _fetch_sport(sport: Sport, series_ticker: str):
            try:
                return sport, await kalshi_client.get_markets(
                    status="open", limit=100, series_ticker=series_ticker
                )
            except Exception as e:
                logger.warning(f"Failed to fetch {sport.value} markets: {e}")
                return sport, None

        tasks = [
            _fetch_sport(sport, ticker)
            for sport, ticker in SPORT_SERIES_TICKER.items()
        ]
        results = await asyncio.gather(*tasks)
        for sport, markets in results:
            if markets is not None:
                self._markets[sport] = markets

    async def _process_game_markets(self, game: Game, markets: list[KalshiMarket]):
        """Evaluate a matched game with all its corresponding markets."""
        config = await get_sport_config(game.sport)

        if not game.clock:
            return

        clock = game.clock
        is_final_period = clock.period == config.final_period
        in_time_window = (
            clock.seconds_remaining is not None
            and clock.seconds_remaining <= config.final_period_window
        )

        if not (is_final_period and in_time_window):
            return

        lead = abs(game.home_team.score - game.away_team.score)
        if lead < config.min_lead:
            return

        leading_team = (
            game.home_team if game.home_team.score > game.away_team.score
            else game.away_team
        )

        await log_scanner("info", f"Opportunity detected: {game.id}", {
            "game_id": game.id,
            "home": game.home_team.name,
            "away": game.away_team.name,
            "home_score": game.home_team.score,
            "away_score": game.away_team.score,
            "lead": lead,
            "period": clock.period,
            "clock": clock.display_clock,
            "matched_markets": [m.ticker for m in markets],
        })

        await manager.broadcast("opportunity", {
            "game_id": game.id,
            "leading_team": leading_team.name,
            "lead": lead,
            "clock": clock.display_clock,
            "period": clock.period,
            "markets": [m.model_dump(mode="json") for m in markets],
        })

        from backend.strategy.evaluator import evaluator
        for market in markets:
            await evaluator.evaluate(game, market, config)

    @property
    def games(self) -> list[Game]:
        return self._games

scanner = ScannerEngine()
