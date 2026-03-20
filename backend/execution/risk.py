import logging
from datetime import date

from backend.db import get_latest_balance, get_trades

logger = logging.getLogger(__name__)

# Risk limits
MAX_POSITION_PCT = 0.20  # 20% of available balance per trade
MAX_OPEN_POSITIONS = 5  # max concurrent positions
MAX_DAILY_LOSS_DOLLARS = 100.0


class RiskError(Exception):
    pass


async def _get_risk_params() -> dict:
    """Return risk params, applying any DB overrides from the strategy page."""
    import json

    from backend.db import get_config_override

    params = {
        "max_position_pct": MAX_POSITION_PCT,
        "max_open_positions": MAX_OPEN_POSITIONS,
        "max_daily_loss": MAX_DAILY_LOSS_DOLLARS,
    }
    override_json = await get_config_override("global_risk")
    if override_json:
        try:
            overrides = json.loads(override_json)
            if "max_position_pct" in overrides:
                params["max_position_pct"] = overrides["max_position_pct"] / 100.0
            if "max_open_positions" in overrides:
                params["max_open_positions"] = int(overrides["max_open_positions"])
            if "max_daily_loss" in overrides:
                params["max_daily_loss"] = float(overrides["max_daily_loss"])
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    return params


async def get_max_position_dollars() -> float:
    """Return max dollars allowed for a single trade."""
    params = await _get_risk_params()
    balance = await get_latest_balance()
    available = balance["available"] if balance else 0.0
    return available * params["max_position_pct"]


async def pre_trade_checks(
    ticker: str,
    side: str,
    contracts: int,
    price: int,
    game_id: str | None = None,
):
    """Raise RiskError if trade should not proceed."""
    params = await _get_risk_params()

    if contracts <= 0:
        raise RiskError("Contracts must be positive")
    if not (1 <= price <= 99):
        raise RiskError(f"Invalid price {price}¢ (must be 1-99)")

    # Balance + position size check
    balance = await get_latest_balance()
    available = balance["available"] if balance else 0.0
    cost = (contracts * price) / 100  # dollars
    max_cost = available * params["max_position_pct"]
    if cost > max_cost:
        raise RiskError(
            f"Position ${cost:.2f} exceeds {params['max_position_pct'] * 100:.0f}% of balance (${max_cost:.2f})"
        )
    if available < cost:
        raise RiskError(f"Insufficient balance: need ${cost:.2f}, have ${available:.2f}")

    # Daily loss limit
    trades = await get_trades(limit=500)
    today = date.today().isoformat()
    today_trades = [t for t in trades if t["created_at"].startswith(today)]
    daily_loss = sum(t["pnl"] for t in today_trades if t["pnl"] is not None and t["pnl"] < 0)
    if abs(daily_loss) >= params["max_daily_loss"]:
        raise RiskError(f"Daily loss limit reached: ${abs(daily_loss):.2f}")

    # Max concurrent open positions
    open_positions = [t for t in trades if t["status"] in ("pending", "filled")]
    if len(open_positions) >= params["max_open_positions"]:
        raise RiskError(f"Max {params['max_open_positions']} concurrent positions reached")

    # No duplicate ticker
    open_tickers = {t["ticker"] for t in open_positions}
    if ticker in open_tickers:
        raise RiskError(f"Already have open position on {ticker}")

    # No duplicate event (game_id) — one bet per game
    if game_id:
        open_game_ids = {t["game_id"] for t in open_positions if t["game_id"]}
        if game_id in open_game_ids:
            raise RiskError(f"Already have open position on game {game_id}")
