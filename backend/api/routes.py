from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from backend.clients.espn import fetch_all_games, fetch_games
from backend.clients.kalshi import kalshi_client
from backend.db import get_trades, get_latest_balance, get_balance_history, get_config_override, set_config_override
from backend.models import Sport
from backend.config import settings

class SportStrategyBody(BaseModel):
    min_lead: Optional[int] = None
    final_period_window: Optional[float] = None
    min_yes_price: Optional[int] = None
    poll_interval: Optional[float] = None

class GlobalStrategyBody(BaseModel):
    max_position_pct: Optional[int] = None
    max_open_positions: Optional[int] = None
    max_daily_loss: Optional[float] = None

router = APIRouter(prefix="/api")

@router.get("/health")
async def health():
    return {"status": "ok", "mode": settings.bot_mode.value}

@router.get("/games")
async def get_games(sport: Optional[str] = Query(None)):
    if sport:
        try:
            sport_enum = Sport(sport.lower())
            games = await fetch_games(sport_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown sport: {sport}")
    else:
        games = await fetch_all_games()
    return {"games": [g.model_dump(mode="json") for g in games]}

@router.get("/markets")
async def get_markets(status: str = "open", limit: int = 50, series_ticker: str = ""):
    try:
        markets = await kalshi_client.get_markets(status=status, limit=limit, series_ticker=series_ticker)
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
        try:
            positions = await kalshi_client.get_positions()
            portfolio_value = sum(
                float(p.get("market_exposure_dollars", 0) or 0)
                for p in positions
            )
        except Exception:
            portfolio_value = 0.0
        return {"available": available, "portfolio_value": portfolio_value, "total": available + portfolio_value}
    except Exception as e:
        # Surface auth/network errors so the UI can show them
        is_simulated = settings.bot_mode.value != "live"
        balance = await get_latest_balance(is_simulated=is_simulated)
        return {
            "available": balance["available"] if balance else 0,
            "portfolio_value": balance["portfolio_value"] if balance else 0,
            "total": balance["total"] if balance else 0,
            "error": str(e),
        }

@router.get("/balance/history")
async def get_balance_history_endpoint(limit: int = 100):
    history = await get_balance_history(
        is_simulated=(settings.bot_mode.value != "live"),
        limit=limit
    )
    return {"history": history}

@router.get("/trades")
async def get_trades_endpoint(limit: int = 100, simulated: Optional[bool] = None):
    trades = await get_trades(limit=limit, is_simulated=simulated)
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
        "mode": settings.bot_mode.value,
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
    from backend.scanner.sports import SPORT_CONFIGS, get_sport_config
    import json

    global_override = await get_config_override("global_risk")
    global_config = {"max_position_pct": 20, "max_open_positions": 5, "max_daily_loss": 100.0}
    if global_override:
        try:
            global_config.update(json.loads(global_override))
        except (json.JSONDecodeError, KeyError):
            pass

    sports = []
    for sport in Sport:
        if sport in SPORT_CONFIGS:
            config = await get_sport_config(sport)
            sports.append({
                "sport": sport.value,
                "final_period": config.final_period,
                "final_period_window": config.final_period_window,
                "min_lead": config.min_lead,
                "min_yes_price": config.min_yes_price,
                "poll_interval": config.poll_interval,
            })

    return {"global": global_config, "mode": settings.bot_mode.value, "sports": sports}

@router.post("/strategy/global")
async def set_global_strategy(body: GlobalStrategyBody):
    import json
    existing_json = await get_config_override("global_risk")
    current: dict = {}
    if existing_json:
        try:
            current = json.loads(existing_json)
        except json.JSONDecodeError:
            pass
    current.update(body.model_dump(exclude_none=True))
    await set_config_override("global_risk", json.dumps(current))
    return {"config": current}

@router.post("/strategy/sport/{sport}")
async def set_sport_strategy(sport: str, body: SportStrategyBody):
    from backend.scanner.sports import get_sport_config
    import json
    try:
        sport_enum = Sport(sport.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown sport: {sport}")
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
