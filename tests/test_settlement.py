"""Tests for settlement detection in backend/scanner/engine.py."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.scanner.engine import check_settlements


def make_trade(id=1, ticker="KXNBA-LAL", side="yes", contracts=100, price=85):
    return {"id": id, "ticker": ticker, "side": side, "contracts": contracts, "price": price}


def make_settlement(ticker="KXNBA-LAL", result="yes"):
    return {"market_ticker": ticker, "market_result": result}


# ---------------------------------------------------------------------------
# Early-exit cases
# ---------------------------------------------------------------------------


class TestCheckSettlementsEarlyExit:
    async def test_no_filled_trades_skips_api_call(self):
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=[])),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements", new=AsyncMock()
            ) as mock_api,
        ):
            await check_settlements()
        mock_api.assert_not_called()

    async def test_no_settlements_returned_settles_nothing(self):
        trades = [make_trade()]
        settle_mock = AsyncMock()
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=trades)),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements",
                new=AsyncMock(return_value=[]),
            ),
            patch("backend.scanner.engine.settle_trade", new=settle_mock),
        ):
            await check_settlements()
        settle_mock.assert_not_called()

    async def test_settlement_result_empty_string_skipped(self):
        trades = [make_trade()]
        settle_mock = AsyncMock()
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=trades)),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements",
                new=AsyncMock(return_value=[{"market_ticker": "KXNBA-LAL", "market_result": ""}]),
            ),
            patch("backend.scanner.engine.settle_trade", new=settle_mock),
        ):
            await check_settlements()
        settle_mock.assert_not_called()


# ---------------------------------------------------------------------------
# P&L calculation — YES side
# ---------------------------------------------------------------------------


class TestSettlementPnlYesSide:
    async def _run(self, trade, settlement):
        settle_mock = AsyncMock()
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=[trade])),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements",
                new=AsyncMock(return_value=[settlement]),
            ),
            patch("backend.scanner.engine.settle_trade", new=settle_mock),
            patch("backend.scanner.engine.log_scanner", new=AsyncMock()),
        ):
            await check_settlements()
        return settle_mock

    async def test_yes_side_wins(self):
        # 100 contracts @ 85¢, result=yes → profit = 100 * (100-85)/100 = $15.00
        mock = await self._run(
            make_trade(side="yes", contracts=100, price=85),
            make_settlement(result="yes"),
        )
        mock.assert_called_once()
        _, pnl, _ = mock.call_args[0]
        assert pnl == pytest.approx(15.0)

    async def test_yes_side_loses(self):
        # 100 contracts @ 85¢, result=no → loss = -(100 * 85/100) = -$85.00
        mock = await self._run(
            make_trade(side="yes", contracts=100, price=85),
            make_settlement(result="no"),
        )
        mock.assert_called_once()
        _, pnl, _ = mock.call_args[0]
        assert pnl == pytest.approx(-85.0)


# ---------------------------------------------------------------------------
# P&L calculation — NO side
# ---------------------------------------------------------------------------


class TestSettlementPnlNoSide:
    async def _run(self, trade, settlement):
        settle_mock = AsyncMock()
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=[trade])),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements",
                new=AsyncMock(return_value=[settlement]),
            ),
            patch("backend.scanner.engine.settle_trade", new=settle_mock),
            patch("backend.scanner.engine.log_scanner", new=AsyncMock()),
        ):
            await check_settlements()
        return settle_mock

    async def test_no_side_wins(self):
        # 90 contracts @ 87¢, result=no → profit = 90 * (100-87)/100 = $11.70
        mock = await self._run(
            make_trade(side="no", contracts=90, price=87),
            make_settlement(result="no"),
        )
        mock.assert_called_once()
        _, pnl, _ = mock.call_args[0]
        assert pnl == pytest.approx(11.7)

    async def test_no_side_loses(self):
        # 90 contracts @ 87¢, result=yes → loss = -(90 * 87/100) = -$78.30
        mock = await self._run(
            make_trade(side="no", contracts=90, price=87),
            make_settlement(result="yes"),
        )
        mock.assert_called_once()
        _, pnl, _ = mock.call_args[0]
        assert pnl == pytest.approx(-78.3)


# ---------------------------------------------------------------------------
# Ticker matching
# ---------------------------------------------------------------------------


class TestSettlementMatching:
    async def test_unmatched_ticker_not_settled(self):
        trades = [make_trade(ticker="KXNBA-LAL")]
        settle_mock = AsyncMock()
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=trades)),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements",
                new=AsyncMock(
                    return_value=[
                        make_settlement(ticker="KXNBA-BOS", result="yes"),
                    ]
                ),
            ),
            patch("backend.scanner.engine.settle_trade", new=settle_mock),
        ):
            await check_settlements()
        settle_mock.assert_not_called()

    async def test_multiple_trades_same_ticker_all_settled(self):
        trades = [
            make_trade(id=1, ticker="KXNBA-LAL", side="yes", contracts=10, price=85),
            make_trade(id=2, ticker="KXNBA-LAL", side="yes", contracts=20, price=80),
        ]
        settle_mock = AsyncMock()
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=trades)),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements",
                new=AsyncMock(
                    return_value=[
                        make_settlement(ticker="KXNBA-LAL", result="yes"),
                    ]
                ),
            ),
            patch("backend.scanner.engine.settle_trade", new=settle_mock),
            patch("backend.scanner.engine.log_scanner", new=AsyncMock()),
        ):
            await check_settlements()
        assert settle_mock.call_count == 2

    async def test_alternate_field_names_ticker_and_result(self):
        """Kalshi may return 'ticker'/'result' instead of 'market_ticker'/'market_result'."""
        trades = [make_trade(ticker="KXNBA-LAL", side="yes", contracts=10, price=80)]
        settle_mock = AsyncMock()
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=trades)),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements",
                new=AsyncMock(
                    return_value=[
                        {"ticker": "KXNBA-LAL", "result": "yes"},
                    ]
                ),
            ),
            patch("backend.scanner.engine.settle_trade", new=settle_mock),
            patch("backend.scanner.engine.log_scanner", new=AsyncMock()),
        ):
            await check_settlements()
        settle_mock.assert_called_once()

    async def test_result_case_insensitive(self):
        """Result values from Kalshi should be lowercased before comparison."""
        trades = [make_trade(side="yes")]
        settle_mock = AsyncMock()
        with (
            patch("backend.scanner.engine.get_filled_trades", new=AsyncMock(return_value=trades)),
            patch(
                "backend.scanner.engine.kalshi_client.get_settlements",
                new=AsyncMock(
                    return_value=[
                        {"market_ticker": "KXNBA-LAL", "market_result": "Yes"},
                    ]
                ),
            ),
            patch("backend.scanner.engine.settle_trade", new=settle_mock),
            patch("backend.scanner.engine.log_scanner", new=AsyncMock()),
        ):
            await check_settlements()
        settle_mock.assert_called_once()
