import logging
from datetime import UTC, datetime

from backend.db import insert_trade, log_scanner
from backend.execution.risk import RiskError, pre_trade_checks
from backend.metrics import trades_placed_total, trades_rejected_total
from backend.models import MarketSide, Trade, TradeStatus

logger = logging.getLogger(__name__)


class Executor:
    async def execute(
        self,
        ticker: str,
        side: str,
        contracts: int,
        price: int,
        game_id: str | None = None,
        reason: str = "",
    ):
        logger.info(f"Execute: {side.upper()} {contracts}x {ticker} @ {price}¢")

        try:
            await pre_trade_checks(ticker, side, contracts, price, game_id=game_id)
        except RiskError as e:
            logger.warning(f"Risk check failed: {e}")
            await log_scanner("warning", f"Risk check failed for {ticker}: {e}")
            msg = str(e).lower()
            if "exceeds" in msg and "position" in msg:
                reason = "position_size"
            elif "insufficient" in msg:
                reason = "insufficient_balance"
            elif "daily loss" in msg:
                reason = "daily_loss_limit"
            elif "max" in msg and "positions" in msg:
                reason = "max_positions"
            elif "already" in msg or "duplicate" in msg:
                reason = "duplicate"
            elif "contracts" in msg:
                reason = "invalid_contracts"
            elif "price" in msg:
                reason = "invalid_price"
            else:
                reason = "other"
            trades_rejected_total.labels(reason=reason).inc()
            return

        await self._place_live_order(ticker, side, contracts, price, game_id, reason)

    async def _place_live_order(
        self, ticker: str, side: str, contracts: int, price: int, game_id: str | None, reason: str
    ):
        from backend.clients.kalshi import kalshi_client

        try:
            order = await kalshi_client.create_order(ticker, side, contracts, price)
            order_id = order.get("order_id") or order.get("id")

            trade = Trade(
                kalshi_order_id=order_id,
                ticker=ticker,
                side=MarketSide(side),
                contracts=contracts,
                price=price,
                status=TradeStatus.FILLED,
                created_at=datetime.now(UTC),
                game_id=game_id,
            )
            trade_id = await insert_trade(trade)
            if trade_id is None:
                logger.error("insert_trade returned None; skipping broadcast")
                return

            await log_scanner(
                "info",
                f"Order placed: {order_id}",
                {
                    "trade_id": trade_id,
                    "order_id": order_id,
                    "ticker": ticker,
                    "side": side,
                    "contracts": contracts,
                    "price": price,
                    "reason": reason,
                },
            )

            from backend.api.websocket import manager

            await manager.broadcast(
                "trade",
                {
                    "id": trade_id,
                    "order_id": order_id,
                    "ticker": ticker,
                    "side": side,
                    "contracts": contracts,
                    "price": price,
                    "reason": reason,
                },
            )

            trades_placed_total.inc()
            logger.info(
                f"Order placed: {order_id} | {side.upper()} {contracts}x {ticker} @ {price}¢"
            )
        except Exception as e:
            logger.error(f"Failed to place order: {e}", exc_info=True)
            await log_scanner("error", f"Order failed for {ticker}: {e}")


executor = Executor()
