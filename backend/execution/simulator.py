import logging
from datetime import datetime
from backend.db import (
    insert_trade, get_latest_balance, insert_balance, get_trades
)
from backend.models import Trade, Balance, TradeStatus, MarketSide

logger = logging.getLogger(__name__)

STARTING_BALANCE = 1000.0  # Virtual $1000

class Simulator:
    async def ensure_balance(self):
        """Initialize virtual balance if not set."""
        balance = await get_latest_balance(is_simulated=True)
        if balance is None:
            await insert_balance(Balance(
                timestamp=datetime.utcnow(),
                available=STARTING_BALANCE,
                portfolio_value=0.0,
                total=STARTING_BALANCE,
                is_simulated=True,
            ))

    async def place_order(
        self, ticker: str, side: str, contracts: int, price: int, game_id: str | None = None
    ) -> Trade:
        await self.ensure_balance()

        balance = await get_latest_balance(is_simulated=True)
        cost = (contracts * price) / 100  # dollars

        new_available = (balance["available"] if balance else STARTING_BALANCE) - cost

        trade = Trade(
            ticker=ticker,
            side=MarketSide(side),
            contracts=contracts,
            price=price,
            status=TradeStatus.FILLED,
            is_simulated=True,
            created_at=datetime.utcnow(),
            game_id=game_id,
        )
        trade_id = await insert_trade(trade)
        trade.id = trade_id

        # Update simulated balance
        open_trades = await get_trades(limit=500, is_simulated=True)
        portfolio_value = sum(
            (t["contracts"] * t["price"]) / 100
            for t in open_trades
            if t["status"] == "filled" and t["pnl"] is None
        )

        await insert_balance(Balance(
            timestamp=datetime.utcnow(),
            available=new_available,
            portfolio_value=portfolio_value,
            total=new_available + portfolio_value,
            is_simulated=True,
        ))

        logger.info(
            f"[SIM] Bought {contracts}x {ticker} {side.upper()} @ {price}¢ | "
            f"Cost: ${cost:.2f} | Balance: ${new_available:.2f}"
        )
        return trade

    async def settle_trade(self, trade_id: int, won: bool):
        """Settle a simulated trade. won=True means YES settled at $1."""
        from backend.db import get_db
        db = await get_db()

        # Fetch trade
        cursor = await db.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = await cursor.fetchone()
        if not row:
            return

        trade = dict(row)
        contracts = trade["contracts"]
        price = trade["price"]
        side = trade["side"]

        # P&L calculation
        cost = (contracts * price) / 100
        if (side == "yes" and won) or (side == "no" and not won):
            pnl = contracts - cost  # Won: each contract pays $1
        else:
            pnl = -cost  # Lost everything

        await db.execute(
            """UPDATE trades SET status = 'settled', pnl = ?, settled_at = ? WHERE id = ?""",
            (pnl, datetime.utcnow().isoformat(), trade_id)
        )
        await db.commit()

        # Update balance (return winnings)
        balance = await get_latest_balance(is_simulated=True)
        proceeds = contracts if won else 0
        new_available = (balance["available"] if balance else 0) + proceeds

        open_trades = await get_trades(limit=500, is_simulated=True)
        portfolio_value = sum(
            (t["contracts"] * t["price"]) / 100
            for t in open_trades
            if t["status"] == "filled" and t["pnl"] is None and t["id"] != trade_id
        )

        await insert_balance(Balance(
            timestamp=datetime.utcnow(),
            available=new_available,
            portfolio_value=portfolio_value,
            total=new_available + portfolio_value,
            is_simulated=True,
        ))

        logger.info(f"[SIM] Settled trade {trade_id}: P&L ${pnl:.2f}")

simulator = Simulator()
