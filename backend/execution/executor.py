import logging
from backend.config import settings, BotMode
from backend.execution.risk import pre_trade_checks, RiskError
from backend.db import insert_trade, log_scanner
from backend.models import Trade, TradeStatus, MarketSide
from datetime import datetime

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
        mode = settings.bot_mode
        is_simulated = mode != BotMode.LIVE

        logger.info(f"[{mode.value.upper()}] Execute: {side.upper()} {contracts}x {ticker} @ {price}¢")

        try:
            await pre_trade_checks(ticker, side, contracts, price, is_simulated=is_simulated, game_id=game_id)
        except RiskError as e:
            logger.warning(f"Risk check failed: {e}")
            await log_scanner("warning", f"Risk check failed for {ticker}: {e}")
            return

        if mode == BotMode.DRY_RUN:
            await log_scanner("info", f"DRY RUN: Would buy {contracts}x {ticker} {side.upper()} @ {price}¢", {
                "ticker": ticker, "side": side, "contracts": contracts, "price": price, "reason": reason
            })
            logger.info(f"[DRY RUN] {side.upper()} {contracts}x {ticker} @ {price}¢ | {reason}")

        elif mode == BotMode.SIMULATION:
            from backend.execution.simulator import simulator
            trade = await simulator.place_order(ticker, side, contracts, price, game_id)
            await log_scanner("info", f"SIM trade placed: {trade.id}", {
                "trade_id": trade.id, "ticker": ticker, "side": side,
                "contracts": contracts, "price": price, "reason": reason,
            })
            from backend.api.websocket import manager
            await manager.broadcast("trade", {
                "id": trade.id,
                "ticker": ticker,
                "side": side,
                "contracts": contracts,
                "price": price,
                "is_simulated": True,
                "reason": reason,
            })

        elif mode == BotMode.LIVE:
            await self._place_live_order(ticker, side, contracts, price, game_id, reason)

    async def _place_live_order(
        self, ticker: str, side: str, contracts: int, price: int,
        game_id: str | None, reason: str
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
                is_simulated=False,
                created_at=datetime.utcnow(),
                game_id=game_id,
            )
            trade_id = await insert_trade(trade)

            await log_scanner("info", f"LIVE order placed: {order_id}", {
                "trade_id": trade_id, "order_id": order_id, "ticker": ticker,
                "side": side, "contracts": contracts, "price": price, "reason": reason,
            })

            from backend.api.websocket import manager
            await manager.broadcast("trade", {
                "id": trade_id,
                "order_id": order_id,
                "ticker": ticker,
                "side": side,
                "contracts": contracts,
                "price": price,
                "is_simulated": False,
                "reason": reason,
            })

            logger.info(f"[LIVE] Order placed: {order_id} | {side.upper()} {contracts}x {ticker} @ {price}¢")
        except Exception as e:
            logger.error(f"Failed to place live order: {e}", exc_info=True)
            await log_scanner("error", f"Live order failed for {ticker}: {e}")

executor = Executor()
