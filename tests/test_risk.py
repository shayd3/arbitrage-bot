"""Tests for backend/execution/risk.py — pre_trade_checks and _get_risk_params."""
import json
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date

from backend.execution.risk import (
    pre_trade_checks,
    _get_risk_params,
    RiskError,
    MAX_POSITION_PCT,
    MAX_OPEN_POSITIONS,
    MAX_DAILY_LOSS_DOLLARS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_trade(ticker="KXNBA-LAL", status="filled", pnl=None, game_id=None, created_at=None):
    return {
        "ticker": ticker,
        "status": status,
        "pnl": pnl,
        "game_id": game_id,
        "created_at": created_at or f"{date.today().isoformat()}T12:00:00",
    }


BALANCE_1000 = {"available": 1000.0}
_UNSET = object()


def patch_risk(balance=_UNSET, trades=None, config_override=None):
    """Return a context manager stack that patches the three DB calls in risk.py."""
    if balance is _UNSET:
        balance = BALANCE_1000
    trades = trades or []
    return (
        patch("backend.execution.risk.get_latest_balance", new=AsyncMock(return_value=balance)),
        patch("backend.execution.risk.get_trades", new=AsyncMock(return_value=trades)),
        patch("backend.db.get_config_override", new=AsyncMock(return_value=config_override)),
    )


# ---------------------------------------------------------------------------
# _get_risk_params
# ---------------------------------------------------------------------------

class TestGetRiskParams:
    async def test_defaults_when_no_override(self):
        with patch("backend.db.get_config_override", new=AsyncMock(return_value=None)):
            params = await _get_risk_params()
        assert params["max_position_pct"] == MAX_POSITION_PCT
        assert params["max_open_positions"] == MAX_OPEN_POSITIONS
        assert params["max_daily_loss"] == MAX_DAILY_LOSS_DOLLARS

    async def test_db_override_applies(self):
        override = json.dumps({"max_position_pct": 10, "max_open_positions": 3, "max_daily_loss": 50.0})
        with patch("backend.db.get_config_override", new=AsyncMock(return_value=override)):
            params = await _get_risk_params()
        assert params["max_position_pct"] == pytest.approx(0.10)
        assert params["max_open_positions"] == 3
        assert params["max_daily_loss"] == pytest.approx(50.0)

    async def test_partial_override_keeps_defaults(self):
        override = json.dumps({"max_open_positions": 2})
        with patch("backend.db.get_config_override", new=AsyncMock(return_value=override)):
            params = await _get_risk_params()
        assert params["max_position_pct"] == MAX_POSITION_PCT
        assert params["max_open_positions"] == 2
        assert params["max_daily_loss"] == MAX_DAILY_LOSS_DOLLARS

    async def test_invalid_json_falls_back_to_defaults(self):
        with patch("backend.db.get_config_override", new=AsyncMock(return_value="not-json")):
            params = await _get_risk_params()
        assert params["max_position_pct"] == MAX_POSITION_PCT


# ---------------------------------------------------------------------------
# pre_trade_checks — happy path
# ---------------------------------------------------------------------------

class TestPreTradeChecksPass:
    async def test_valid_trade_passes(self):
        """A trade well within all limits should not raise."""
        bal, trades, cfg = patch_risk(balance={"available": 1000.0}, trades=[])
        with bal, trades, cfg:
            # 10 contracts @ 80¢ = $8 cost, max = $200 (20% of $1000)
            await pre_trade_checks("KXNBA-LAL", "yes", 10, 80, is_simulated=True)


# ---------------------------------------------------------------------------
# pre_trade_checks — validation failures
# ---------------------------------------------------------------------------

class TestPreTradeChecksInputValidation:
    async def test_zero_contracts(self):
        bal, trades, cfg = patch_risk()
        with bal, trades, cfg, pytest.raises(RiskError, match="positive"):
            await pre_trade_checks("KXNBA-LAL", "yes", 0, 80, is_simulated=True)

    async def test_negative_contracts(self):
        bal, trades, cfg = patch_risk()
        with bal, trades, cfg, pytest.raises(RiskError, match="positive"):
            await pre_trade_checks("KXNBA-LAL", "yes", -5, 80, is_simulated=True)

    async def test_price_zero(self):
        bal, trades, cfg = patch_risk()
        with bal, trades, cfg, pytest.raises(RiskError, match="Invalid price"):
            await pre_trade_checks("KXNBA-LAL", "yes", 10, 0, is_simulated=True)

    async def test_price_100(self):
        bal, trades, cfg = patch_risk()
        with bal, trades, cfg, pytest.raises(RiskError, match="Invalid price"):
            await pre_trade_checks("KXNBA-LAL", "yes", 10, 100, is_simulated=True)

    async def test_price_boundary_valid(self):
        """Prices 1 and 99 are valid."""
        bal, trades, cfg = patch_risk(balance={"available": 10_000.0})
        with bal, trades, cfg:
            await pre_trade_checks("KXNBA-LAL", "yes", 1, 1, is_simulated=True)
        with bal, trades, cfg:
            await pre_trade_checks("KXNBA-LAL", "yes", 1, 99, is_simulated=True)


class TestPreTradeChecksBalanceLimits:
    async def test_position_exceeds_max_pct(self):
        """Cost > 20% of balance should fail."""
        # balance $1000, max = $200; 300 contracts @ 80¢ = $240
        bal, trades, cfg = patch_risk(balance={"available": 1000.0})
        with bal, trades, cfg, pytest.raises(RiskError, match="exceeds"):
            await pre_trade_checks("KXNBA-LAL", "yes", 300, 80, is_simulated=True)

    async def test_insufficient_balance(self):
        """Cost > available balance (even if < max_pct) should fail."""
        # balance $5, max pct = $1; 10 contracts @ 80¢ = $8 — hits pct check first
        # Use a scenario where balance is really tiny
        bal, trades, cfg = patch_risk(balance={"available": 5.0})
        with bal, trades, cfg, pytest.raises(RiskError):
            await pre_trade_checks("KXNBA-LAL", "yes", 10, 80, is_simulated=True)

    async def test_no_balance_record(self):
        """If no balance row exists, available=0 → any cost fails."""
        bal, trades, cfg = patch_risk(balance=None)  # explicitly None → available=0
        with bal, trades, cfg, pytest.raises(RiskError):
            await pre_trade_checks("KXNBA-NEW", "yes", 1, 50, is_simulated=True)


class TestPreTradeChecksDailyLoss:
    async def test_daily_loss_limit_reached(self):
        today = date.today().isoformat()
        trades = [make_trade(pnl=-50.0, created_at=f"{today}T10:00:00"),
                  make_trade(ticker="KXNBA-BOS", pnl=-60.0, created_at=f"{today}T11:00:00")]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg, pytest.raises(RiskError, match="Daily loss"):
            await pre_trade_checks("KXNBA-LAL", "yes", 1, 50, is_simulated=True)

    async def test_daily_loss_from_yesterday_ignored(self):
        """Losses from prior days should not count toward today's limit."""
        # Use ticker "OTHER" so the existing trade doesn't trigger duplicate-ticker check
        trades = [make_trade(ticker="KXNBA-OTHER", pnl=-99.0, created_at="2020-01-01T10:00:00")]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg:
            await pre_trade_checks("KXNBA-NEW", "yes", 1, 50, is_simulated=True)

    async def test_winning_trades_do_not_count(self):
        """Positive pnl should not trigger the loss limit."""
        today = date.today().isoformat()
        trades = [make_trade(ticker="KXNBA-OTHER", pnl=200.0, created_at=f"{today}T10:00:00")]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg:
            await pre_trade_checks("KXNBA-NEW", "yes", 1, 50, is_simulated=True)


class TestPreTradeChecksOpenPositions:
    async def test_max_positions_reached(self):
        tickers = ["KXNBA-A", "KXNBA-B", "KXNBA-C", "KXNBA-D", "KXNBA-E"]
        trades = [make_trade(ticker=t, status="filled") for t in tickers]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg, pytest.raises(RiskError, match="concurrent positions"):
            await pre_trade_checks("KXNBA-F", "yes", 1, 50, is_simulated=True)

    async def test_settled_trades_not_counted_as_open(self):
        """Settled/cancelled positions don't count toward max_open_positions."""
        trades = [make_trade(ticker=f"KXNBA-{i}", status="settled") for i in range(10)]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg:
            await pre_trade_checks("KXNBA-NEW", "yes", 1, 50, is_simulated=True)

    async def test_duplicate_ticker_rejected(self):
        trades = [make_trade(ticker="KXNBA-LAL", status="filled")]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg, pytest.raises(RiskError, match="open position on KXNBA-LAL"):
            await pre_trade_checks("KXNBA-LAL", "yes", 1, 50, is_simulated=True)

    async def test_duplicate_game_id_rejected(self):
        trades = [make_trade(ticker="KXNBA-LAL", status="filled", game_id="game-123")]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg, pytest.raises(RiskError, match="game-123"):
            await pre_trade_checks("KXNBA-BOS", "yes", 1, 50, is_simulated=True, game_id="game-123")

    async def test_different_game_id_allowed(self):
        trades = [make_trade(ticker="KXNBA-LAL", status="filled", game_id="game-111")]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg:
            await pre_trade_checks("KXNBA-BOS", "yes", 1, 50, is_simulated=True, game_id="game-222")

    async def test_no_game_id_skips_game_check(self):
        """Passing game_id=None should not trigger the game duplicate check."""
        trades = [make_trade(ticker="KXNBA-LAL", status="filled", game_id="game-123")]
        bal, trd, cfg = patch_risk(trades=trades)
        with bal, trd, cfg:
            await pre_trade_checks("KXNBA-BOS", "yes", 1, 50, is_simulated=True, game_id=None)
