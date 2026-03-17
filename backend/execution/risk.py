import logging
from datetime import datetime, date
from backend.db import get_trades, get_latest_balance
from backend.config import settings, BotMode

logger = logging.getLogger(__name__)

# Risk limits
MAX_POSITION_PCT = 0.20        # 20% of available balance per trade
MAX_OPEN_POSITIONS = 5         # max concurrent positions
MAX_DAILY_LOSS_DOLLARS = 100.0

class RiskError(Exception):
    pass

async def get_max_position_dollars(is_simulated: bool) -> float:
    """Return max dollars allowed for a single trade (20% of available balance)."""
    balance = await get_latest_balance(is_simulated=is_simulated)
    available = balance["available"] if balance else 0.0
    return available * MAX_POSITION_PCT

async def pre_trade_checks(
    ticker: str, side: str, contracts: int, price: int,
    is_simulated: bool, game_id: str | None = None,
):
    """Raise RiskError if trade should not proceed."""

    if contracts <= 0:
        raise RiskError("Contracts must be positive")
    if not (1 <= price <= 99):
        raise RiskError(f"Invalid price {price}¢ (must be 1-99)")

    # Balance + 20% position size check
    balance = await get_latest_balance(is_simulated=is_simulated)
    available = balance["available"] if balance else 0.0
    cost = (contracts * price) / 100  # dollars
    max_cost = available * MAX_POSITION_PCT
    if cost > max_cost:
        raise RiskError(
            f"Position ${cost:.2f} exceeds 20% of balance (${max_cost:.2f})"
        )
    if available < cost:
        raise RiskError(f"Insufficient balance: need ${cost:.2f}, have ${available:.2f}")

    # Daily loss limit
    trades = await get_trades(limit=500, is_simulated=is_simulated)
    today = date.today().isoformat()
    today_trades = [t for t in trades if t["created_at"].startswith(today)]
    daily_loss = sum(t["pnl"] for t in today_trades if t["pnl"] is not None and t["pnl"] < 0)
    if abs(daily_loss) >= MAX_DAILY_LOSS_DOLLARS:
        raise RiskError(f"Daily loss limit reached: ${abs(daily_loss):.2f}")

    # Max 5 concurrent open positions
    open_positions = [t for t in trades if t["status"] in ("pending", "filled")]
    if len(open_positions) >= MAX_OPEN_POSITIONS:
        raise RiskError(f"Max {MAX_OPEN_POSITIONS} concurrent positions reached")

    # No duplicate ticker
    open_tickers = {t["ticker"] for t in open_positions}
    if ticker in open_tickers:
        raise RiskError(f"Already have open position on {ticker}")

    # No duplicate event (game_id) — one bet per game
    if game_id:
        open_game_ids = {t["game_id"] for t in open_positions if t["game_id"]}
        if game_id in open_game_ids:
            raise RiskError(f"Already have open position on game {game_id}")
