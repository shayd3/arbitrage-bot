"""Tests covering Prometheus metrics instrumentation added to executor, scanner engine,
and API clients.  Checks that counters/gauges/histograms change by the expected delta
so tests remain independent of global registry state."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from backend import metrics

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _counter_value(counter, **labels):
    """Return the current float value of a (possibly-labelled) counter."""
    if labels:
        return counter.labels(**labels)._value.get()
    return counter._value.get()


def _gauge_value(gauge):
    return gauge._value.get()


def _histogram_count(histogram, **labels):
    if labels:
        return histogram.labels(**labels)._metrics  # existence check
    return histogram._metrics


# ---------------------------------------------------------------------------
# executor.py — trades_placed_total / trades_rejected_total
# ---------------------------------------------------------------------------


class TestTradesPlacedCounter:
    async def test_increments_on_successful_order(self):
        from backend.execution.executor import executor

        before = _counter_value(metrics.trades_placed_total)

        order = {"order_id": "ord-1"}
        with (
            patch("backend.execution.executor.pre_trade_checks", new=AsyncMock(return_value=None)),
            patch(
                "backend.clients.kalshi.kalshi_client.create_order",
                new=AsyncMock(return_value=order),
            ),
            patch("backend.execution.executor.insert_trade", new=AsyncMock(return_value=42)),
            patch("backend.execution.executor.log_scanner", new=AsyncMock()),
            patch("backend.api.websocket.manager.broadcast", new=AsyncMock()),
        ):
            await executor.execute("KXNBA-LAL", "yes", 10, 80)

        assert _counter_value(metrics.trades_placed_total) == before + 1

    async def test_does_not_increment_on_risk_rejection(self):
        from backend.execution.executor import executor
        from backend.execution.risk import RiskError

        before = _counter_value(metrics.trades_placed_total)

        with patch(
            "backend.execution.executor.pre_trade_checks",
            new=AsyncMock(side_effect=RiskError("insufficient balance")),
        ):
            await executor.execute("KXNBA-LAL", "yes", 10, 80)

        assert _counter_value(metrics.trades_placed_total) == before


class TestTradesRejectedCounter:
    async def _reject(self, error_msg: str):
        from backend.execution.executor import executor
        from backend.execution.risk import RiskError

        with patch(
            "backend.execution.executor.pre_trade_checks",
            new=AsyncMock(side_effect=RiskError(error_msg)),
        ):
            await executor.execute("KXNBA-LAL", "yes", 10, 80)

    async def test_position_size_reason(self):
        before = _counter_value(metrics.trades_rejected_total, reason="position_size")
        await self._reject("Position $240 exceeds 20% of balance ($200)")
        assert _counter_value(metrics.trades_rejected_total, reason="position_size") == before + 1

    async def test_insufficient_balance_reason(self):
        before = _counter_value(metrics.trades_rejected_total, reason="insufficient_balance")
        await self._reject("Insufficient balance: need $80.00, have $5.00")
        assert (
            _counter_value(metrics.trades_rejected_total, reason="insufficient_balance")
            == before + 1
        )

    async def test_daily_loss_limit_reason(self):
        before = _counter_value(metrics.trades_rejected_total, reason="daily_loss_limit")
        await self._reject("Daily loss limit reached: $105.00")
        assert (
            _counter_value(metrics.trades_rejected_total, reason="daily_loss_limit") == before + 1
        )

    async def test_max_positions_reason(self):
        before = _counter_value(metrics.trades_rejected_total, reason="max_positions")
        await self._reject("Max 5 concurrent positions reached")
        assert _counter_value(metrics.trades_rejected_total, reason="max_positions") == before + 1

    async def test_duplicate_reason(self):
        before = _counter_value(metrics.trades_rejected_total, reason="duplicate")
        await self._reject("Already have open position on KXNBA-LAL")
        assert _counter_value(metrics.trades_rejected_total, reason="duplicate") == before + 1

    async def test_invalid_contracts_reason(self):
        before = _counter_value(metrics.trades_rejected_total, reason="invalid_contracts")
        await self._reject("Contracts must be positive")
        assert (
            _counter_value(metrics.trades_rejected_total, reason="invalid_contracts") == before + 1
        )

    async def test_invalid_price_reason(self):
        before = _counter_value(metrics.trades_rejected_total, reason="invalid_price")
        await self._reject("Invalid price 0¢ (must be 1-99)")
        assert _counter_value(metrics.trades_rejected_total, reason="invalid_price") == before + 1

    async def test_other_reason_fallback(self):
        before = _counter_value(metrics.trades_rejected_total, reason="other")
        await self._reject("Something unexpected happened")
        assert _counter_value(metrics.trades_rejected_total, reason="other") == before + 1


# ---------------------------------------------------------------------------
# scanner/engine.py — available_balance gauge (sync_balance)
# ---------------------------------------------------------------------------


class TestSyncBalanceGauge:
    async def test_sets_available_balance_gauge(self):
        from backend.scanner.engine import sync_balance

        with (
            patch(
                "backend.scanner.engine.kalshi_client.get_balance",
                new=AsyncMock(return_value=50000),  # 500 cents → $500
            ),
            patch("backend.scanner.engine.insert_balance", new=AsyncMock()),
        ):
            await sync_balance()

        assert _gauge_value(metrics.available_balance) == pytest.approx(500.0)

    async def test_exception_does_not_raise(self):
        """sync_balance swallows errors; gauge should be unchanged."""
        from backend.scanner.engine import sync_balance

        before = _gauge_value(metrics.available_balance)

        with patch(
            "backend.scanner.engine.kalshi_client.get_balance",
            new=AsyncMock(side_effect=Exception("network error")),
        ):
            await sync_balance()  # should not raise

        assert _gauge_value(metrics.available_balance) == before


# ---------------------------------------------------------------------------
# scanner/engine.py — active_positions / daily_pnl gauges (_update_position_gauges)
# ---------------------------------------------------------------------------


class TestUpdatePositionGauges:
    async def test_active_positions_counts_open_statuses(self):
        from backend.scanner.engine import ScannerEngine

        engine = ScannerEngine()
        with (
            patch("backend.scanner.engine.count_active_positions", new=AsyncMock(return_value=2)),
            patch("backend.scanner.engine.sum_daily_pnl", new=AsyncMock(return_value=0.0)),
        ):
            await engine._update_position_gauges()

        assert _gauge_value(metrics.active_positions) == 2

    async def test_daily_pnl_sums_todays_trades(self):
        from backend.scanner.engine import ScannerEngine

        engine = ScannerEngine()
        with (
            patch("backend.scanner.engine.count_active_positions", new=AsyncMock(return_value=0)),
            patch("backend.scanner.engine.sum_daily_pnl", new=AsyncMock(return_value=15.0)),
        ):
            await engine._update_position_gauges()

        assert _gauge_value(metrics.daily_pnl) == pytest.approx(15.0)

    async def test_none_pnl_excluded_from_daily(self):
        from backend.scanner.engine import ScannerEngine

        engine = ScannerEngine()
        with (
            patch("backend.scanner.engine.count_active_positions", new=AsyncMock(return_value=0)),
            patch("backend.scanner.engine.sum_daily_pnl", new=AsyncMock(return_value=30.0)),
        ):
            await engine._update_position_gauges()

        assert _gauge_value(metrics.daily_pnl) == pytest.approx(30.0)

    async def test_exception_is_swallowed(self):
        from backend.scanner.engine import ScannerEngine

        engine = ScannerEngine()
        with patch(
            "backend.scanner.engine.count_active_positions",
            new=AsyncMock(side_effect=Exception("db error")),
        ):
            await engine._update_position_gauges()  # should not raise


# ---------------------------------------------------------------------------
# scanner/engine.py — scanner_cycles_total counter (_scan)
# ---------------------------------------------------------------------------


class TestScannerCyclesCounter:
    async def test_increments_each_scan(self):
        from backend.scanner.engine import ScannerEngine

        engine = ScannerEngine()
        before = _counter_value(metrics.scanner_cycles_total)

        with (
            patch("backend.scanner.engine.get_config_override", new=AsyncMock(return_value=None)),
            patch("backend.scanner.engine.sync_trades_from_kalshi", new=AsyncMock()),
            patch("backend.scanner.engine.check_settlements", new=AsyncMock()),
            patch("backend.scanner.engine.sync_balance", new=AsyncMock()),
            patch.object(engine, "_update_position_gauges", new=AsyncMock()),
            patch.object(engine, "_fetch_all_markets", new=AsyncMock()),
            patch("backend.scanner.engine.fetch_games", new=AsyncMock(return_value=[])),
            patch("backend.scanner.engine.manager.broadcast", new=AsyncMock()),
        ):
            await engine._scan()

        assert _counter_value(metrics.scanner_cycles_total) == before + 1


# ---------------------------------------------------------------------------
# scanner/engine.py — opportunities_found_total counter (_process_game_markets)
# ---------------------------------------------------------------------------


class TestOpportunitiesCounter:
    async def test_increments_when_opportunity_detected(self):
        from backend.models import Game, GameClock, GameStatus, KalshiMarket, Sport, Team
        from backend.scanner.engine import ScannerEngine

        engine = ScannerEngine()
        before = _counter_value(metrics.opportunities_found_total, sport="nba")

        game = Game(
            id="game-1",
            sport=Sport.NBA,
            home_team=Team(id="1", name="Lakers", abbreviation="LAL", score=110),
            away_team=Team(id="2", name="Celtics", abbreviation="BOS", score=95),
            status=GameStatus.IN_PROGRESS,
            clock=GameClock(
                period=4,
                period_type="regular",
                display_clock="1:30",
                seconds_remaining=90,
            ),
        )
        market = KalshiMarket(
            ticker="KXNBAGAME-LAL",
            title="Lakers Winner?",
            status="open",
            yes_ask=85,
        )

        with (
            patch(
                "backend.scanner.engine.get_sport_config",
                new=AsyncMock(
                    return_value=MagicMock(
                        final_period=4,
                        final_period_window=120,
                        clock_based=True,
                        min_lead=10,
                        regular_periods=4,
                    )
                ),
            ),
            patch("backend.scanner.engine.log_scanner", new=AsyncMock()),
            patch("backend.scanner.engine.manager.broadcast", new=AsyncMock()),
            patch("backend.strategy.evaluator.evaluator.evaluate", new=AsyncMock()),
        ):
            await engine._process_game_markets(game, [market])

        assert _counter_value(metrics.opportunities_found_total, sport="nba") == before + 1

    async def test_no_increment_when_not_in_window(self):
        """Early game: counter should not change."""
        from backend.models import Game, GameClock, GameStatus, KalshiMarket, Sport, Team
        from backend.scanner.engine import ScannerEngine

        engine = ScannerEngine()
        before = _counter_value(metrics.opportunities_found_total, sport="nba")

        game = Game(
            id="game-2",
            sport=Sport.NBA,
            home_team=Team(id="1", name="Lakers", abbreviation="LAL", score=110),
            away_team=Team(id="2", name="Celtics", abbreviation="BOS", score=95),
            status=GameStatus.IN_PROGRESS,
            clock=GameClock(
                period=2,  # early game — not final period
                period_type="regular",
                display_clock="10:00",
                seconds_remaining=600,
            ),
        )
        market = KalshiMarket(
            ticker="KXNBAGAME-LAL", title="Lakers Winner?", status="open", yes_ask=85
        )

        with patch(
            "backend.scanner.engine.get_sport_config",
            new=AsyncMock(
                return_value=MagicMock(
                    final_period=4,
                    final_period_window=120,
                    clock_based=True,
                    min_lead=10,
                    regular_periods=4,
                )
            ),
        ):
            await engine._process_game_markets(game, [market])

        assert _counter_value(metrics.opportunities_found_total, sport="nba") == before


# ---------------------------------------------------------------------------
# clients/espn.py — espn_poll_latency_seconds histogram
# ---------------------------------------------------------------------------


def _histogram_count(metric_name: str, labels: dict) -> float:
    """Read a histogram _count sample from the Prometheus registry."""
    return REGISTRY.get_sample_value(f"{metric_name}_count", labels) or 0.0


class TestEspnLatencyHistogram:
    async def test_histogram_observed_on_successful_fetch(self):
        from backend.clients.espn import fetch_games
        from backend.models import Sport

        before = _histogram_count("espn_poll_latency_seconds", {"sport": "nba"})

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"events": []}

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        with (
            patch(
                "backend.clients.espn.get_sport_config",
                new=AsyncMock(return_value=MagicMock(regular_periods=4)),
            ),
            patch("httpx.AsyncClient") as MockClient,
        ):
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)
            await fetch_games(Sport.NBA)

        assert _histogram_count("espn_poll_latency_seconds", {"sport": "nba"}) == before + 1


# ---------------------------------------------------------------------------
# clients/kalshi.py — kalshi_api_latency_seconds histogram
# ---------------------------------------------------------------------------


class TestKalshiLatencyHistogram:
    async def test_histogram_observed_on_request(self):
        import httpx

        from backend.clients.kalshi import KalshiClient

        client = KalshiClient()
        mock_key = MagicMock()
        mock_key.sign.return_value = b"fakesignature"
        client._private_key = mock_key

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"balance": 50000}

        before = _histogram_count("kalshi_api_latency_seconds", {"endpoint": "portfolio_balance"})

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.request = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http

            await client._request("GET", "/portfolio/balance")

        assert (
            _histogram_count("kalshi_api_latency_seconds", {"endpoint": "portfolio_balance"})
            == before + 1
        )
