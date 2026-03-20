import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.clients.kalshi import kalshi_client
from backend.config import settings
from backend.db import (
    get_balance_history,
    get_config_override,
    get_latest_balance,
    get_trades,
    set_config_override,
)
from backend.models import Sport

logger = logging.getLogger(__name__)


class SportStrategyBody(BaseModel):
    min_lead: int | None = None
    final_period_window: float | None = None
    min_yes_price: int | None = None
    poll_interval: float | None = None


class GlobalStrategyBody(BaseModel):
    max_position_pct: int | None = None
    max_open_positions: int | None = None
    max_daily_loss: float | None = None
    espn_poll_interval: float | None = None
    kalshi_poll_interval: float | None = None
    kalshi_sync_interval: float | None = None


router = APIRouter(prefix="/api")


@router.get("/health")
async def health():
    return {"status": "ok", "demo": settings.kalshi_use_demo}


@router.get("/games")
async def get_games(sport: str | None = Query(None)):
    from backend.clients.espn import fetch_games
    from backend.scanner.engine import scanner

    games = scanner.games
    if sport:
        try:
            sport_enum = Sport(sport.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown sport: {sport}") from None
        games = [g for g in games if g.sport == sport_enum]
        if not games:
            try:
                games = await fetch_games(sport_enum)
            except Exception as e:
                logger.warning(f"ESPN fallback failed for {sport_enum.value}: {e}")
    return {"games": [g.model_dump(mode="json") for g in games]}


@router.get("/markets")
async def get_markets(status: str = "open", limit: int = 50, series_ticker: str = ""):
    try:
        markets = await kalshi_client.get_markets(
            status=status, limit=limit, series_ticker=series_ticker
        )
        return {"markets": [m.model_dump(mode="json") for m in markets]}
    except Exception as e:
        # Return empty if no API keys configured
        return {"markets": [], "error": str(e)}


@router.get("/markets/{ticker}")
async def get_market(ticker: str):
    market = await kalshi_client.get_market(ticker)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market.model_dump(mode="json")


@router.get("/balance")
async def get_balance():
    try:
        cents = await kalshi_client.get_balance()
        available = int(cents) / 100
        portfolio_value = 0.0
        positions_error = None
        try:
            positions = await kalshi_client.get_positions()
            portfolio_value = sum(
                float(p.get("market_exposure_dollars", 0) or 0) for p in positions
            )
        except Exception as pe:
            logger.warning("Failed to fetch positions for balance: %s", pe)
            positions_error = str(pe)
        result = {
            "available": available,
            "portfolio_value": portfolio_value,
            "total": available + portfolio_value,
        }
        if positions_error:
            result["positions_error"] = positions_error
        return result
    except Exception as e:
        balance = await get_latest_balance()
        return {
            "available": balance["available"] if balance else 0,
            "portfolio_value": balance["portfolio_value"] if balance else 0,
            "total": balance["total"] if balance else 0,
            "error": str(e),
        }


@router.get("/balance/history")
async def get_balance_history_endpoint(limit: int = 100):
    history = await get_balance_history(limit=limit)
    return {"history": history}


@router.get("/trades")
async def get_trades_endpoint(limit: int = 100):
    trades = await get_trades(limit=limit)
    return {"trades": trades}


@router.get("/positions")
async def get_positions():
    try:
        positions = await kalshi_client.get_positions()
        return {"positions": positions}
    except Exception as e:
        return {"positions": [], "error": str(e)}


@router.get("/scanner/status")
async def get_scanner_status():
    from backend.scanner.engine import scanner

    return {
        "running": scanner._running,
        "games_count": len(scanner.games),
        "demo": settings.kalshi_use_demo,
    }


@router.get("/scanner/log")
async def get_scanner_log(limit: int = 50):
    from backend.db import get_db

    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM scanner_log ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return {"logs": [dict(r) for r in rows]}


@router.post("/config/{key}")
async def set_config(key: str, value: str):
    await set_config_override(key, value)
    return {"key": key, "value": value}


@router.get("/config/{key}")
async def get_config(key: str):
    value = await get_config_override(key)
    return {"key": key, "value": value}


@router.get("/strategy")
async def get_strategy():
    import json

    from backend.scanner.sports import SPORT_CONFIGS, get_sport_config

    global_override = await get_config_override("global_risk")
    global_config = {"max_position_pct": 20, "max_open_positions": 5, "max_daily_loss": 100.0}
    if global_override:
        try:
            global_config.update(json.loads(global_override))
        except (json.JSONDecodeError, KeyError):
            pass

    interval_override = await get_config_override("scanner_intervals")
    global_config["espn_poll_interval"] = settings.espn_poll_interval
    global_config["kalshi_poll_interval"] = settings.kalshi_poll_interval
    global_config["kalshi_sync_interval"] = 1800.0
    if interval_override:
        try:
            d = json.loads(interval_override)
            global_config["espn_poll_interval"] = max(
                5.0, float(d.get("espn_poll_interval", settings.espn_poll_interval))
            )
            global_config["kalshi_poll_interval"] = max(
                10.0, float(d.get("kalshi_poll_interval", settings.kalshi_poll_interval))
            )
            global_config["kalshi_sync_interval"] = max(
                30.0, float(d.get("kalshi_sync_interval", 1800.0))
            )
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    sports = []
    for sport in Sport:
        if sport in SPORT_CONFIGS:
            config = await get_sport_config(sport)
            sports.append(
                {
                    "sport": sport.value,
                    "final_period": config.final_period,
                    "final_period_window": config.final_period_window,
                    "min_lead": config.min_lead,
                    "min_yes_price": config.min_yes_price,
                    "poll_interval": config.poll_interval,
                }
            )

    return {"global": global_config, "demo": settings.kalshi_use_demo, "sports": sports}


@router.post("/strategy/global")
async def set_global_strategy(body: GlobalStrategyBody):
    import json

    payload = body.model_dump(exclude_none=True)

    # Persist risk fields separately from interval fields
    risk_keys = {"max_position_pct", "max_open_positions", "max_daily_loss"}
    interval_keys = {"espn_poll_interval", "kalshi_poll_interval", "kalshi_sync_interval"}

    risk_update = {k: v for k, v in payload.items() if k in risk_keys}
    interval_update = {k: v for k, v in payload.items() if k in interval_keys}

    if risk_update:
        existing_json = await get_config_override("global_risk")
        current: dict = {}
        if existing_json:
            try:
                current = json.loads(existing_json)
            except json.JSONDecodeError:
                pass
        current.update(risk_update)
        await set_config_override("global_risk", json.dumps(current))

    if interval_update:
        # Enforce minimum floors before persisting
        if "espn_poll_interval" in interval_update:
            interval_update["espn_poll_interval"] = max(
                5.0, float(interval_update["espn_poll_interval"])
            )
        if "kalshi_poll_interval" in interval_update:
            interval_update["kalshi_poll_interval"] = max(
                10.0, float(interval_update["kalshi_poll_interval"])
            )
        if "kalshi_sync_interval" in interval_update:
            interval_update["kalshi_sync_interval"] = max(
                30.0, float(interval_update["kalshi_sync_interval"])
            )
        existing_json = await get_config_override("scanner_intervals")
        current_intervals: dict = {}
        if existing_json:
            try:
                current_intervals = json.loads(existing_json)
            except json.JSONDecodeError:
                pass
        current_intervals.update(interval_update)
        await set_config_override("scanner_intervals", json.dumps(current_intervals))

    return {"config": payload}


@router.post("/strategy/sport/{sport}")
async def set_sport_strategy(sport: str, body: SportStrategyBody):
    import json

    from backend.scanner.sports import get_sport_config

    try:
        sport_enum = Sport(sport.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown sport: {sport}") from None
    config = await get_sport_config(sport_enum)
    merged = {
        "final_period": config.final_period,
        "final_period_window": config.final_period_window,
        "min_lead": config.min_lead,
        "min_yes_price": config.min_yes_price,
        "poll_interval": config.poll_interval,
    }
    merged.update(body.model_dump(exclude_none=True))
    await set_config_override(f"sport_config_{sport_enum.value}", json.dumps(merged))
    return {"sport": sport, "config": merged}
