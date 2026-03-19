import asyncio
import logging
import time
from datetime import datetime
from backend.clients.espn import fetch_games
from backend.clients.kalshi import kalshi_client
from backend.models import Game, GameStatus, KalshiMarket, Sport, Balance
from backend.scanner.matcher import match_markets_to_games
from backend.scanner.sports import get_sport_config, SPORT_SERIES_TICKER
from backend.db import log_scanner, insert_balance, get_filled_trades, settle_trade, sync_trade_from_order, get_config_override
from backend.config import settings
from backend.api.websocket import manager

logger = logging.getLogger(__name__)

async def sync_trades_from_kalshi():
    """
    Reconcile local DB against Kalshi's order history.
    Inserts orders missing from the DB (e.g. placed while app was down)
    and updates status on records that have drifted.
    Commits once after processing all orders (batched).
    """
    try:
        orders = await kalshi_client.get_orders(limit=100)
        synced = 0
        for order in orders:
            await sync_trade_from_order(order, commit=False)
            synced += 1
        if synced:
            from backend.db import get_db
            db = await get_db()
            await db.commit()
            logger.debug(f"Synced {synced} orders from Kalshi")
    except Exception as e:
        logger.error(f"Trade sync error: {e}", exc_info=True)

async def check_settlements():
    """
    Check for settled trades using the /portfolio/settlements endpoint.
    One API call builds a ticker→result map; all filled trades are resolved in-memory.
    """
    try:
        trades = await get_filled_trades()
        if not trades:
            return

        settlements = await kalshi_client.get_settlements(limit=200)
        # Build ticker → result map (Kalshi may use market_ticker or ticker)
        settled_map: dict[str, str] = {}
        for s in settlements:
            ticker = s.get("market_ticker") or s.get("ticker", "")
            result = (s.get("market_result") or s.get("result", "")).lower()
            if ticker and result in ("yes", "no"):
                settled_map[ticker] = result

        if not settled_map:
            return

        now = datetime.utcnow()
        for trade in trades:
            result = settled_map.get(trade["ticker"])
            if not result:
                continue

            won = trade["side"] == result
            contracts = trade["contracts"]
            price = trade["price"]  # cents paid

            pnl = contracts * (100 - price) / 100 if won else -(contracts * price) / 100

            await settle_trade(trade["id"], pnl, now)
            logger.info(
                f"Settled trade {trade['id']} ({trade['ticker']}): "
                f"side={trade['side']}, result={result}, pnl=${pnl:.2f}"
            )
            await log_scanner("info", f"Trade {trade['id']} settled", {
                "trade_id": trade["id"],
                "ticker": trade["ticker"],
                "side": trade["side"],
                "result": result,
                "pnl": pnl,
            })
    except Exception as e:
        logger.error(f"Settlement check error: {e}", exc_info=True)

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
        self._last_settlement_check: float = 0.0
        self._last_trade_sync: float = 0.0
        self._espn_interval: float = settings.espn_poll_interval
        self._kalshi_interval: float = settings.kalshi_poll_interval
        self._sync_interval: float = 1800.0  # DB↔Kalshi trade sync, default 30min

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
            await asyncio.sleep(self._espn_interval)

    async def _refresh_intervals(self):
        """Read dynamic scan intervals from the config_overrides table."""
        import json
        val = await get_config_override("scanner_intervals")
        if val:
            try:
                d = json.loads(val)
                self._espn_interval = max(5.0, float(d.get("espn_poll_interval", settings.espn_poll_interval)))
                self._kalshi_interval = max(10.0, float(d.get("kalshi_poll_interval", settings.kalshi_poll_interval)))
                self._sync_interval = max(30.0, float(d.get("kalshi_sync_interval", 1800.0)))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

    async def _scan(self):
        await self._refresh_intervals()
        now = time.monotonic()

        # Sync orders from Kalshi (reconcile DB with remote state)
        if now - self._last_trade_sync >= self._sync_interval:
            await sync_trades_from_kalshi()
            self._last_trade_sync = now

        # Throttle settlement checks
        if now - self._last_settlement_check >= self._kalshi_interval:
            await check_settlements()
            self._last_settlement_check = now

        # Throttle balance sync
        if now - self._last_balance_sync >= self._kalshi_interval:
            await sync_balance()
            self._last_balance_sync = now

        # 1. Fetch Kalshi markets (throttled separately)
        if now - self._last_market_fetch >= self._kalshi_interval:
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
