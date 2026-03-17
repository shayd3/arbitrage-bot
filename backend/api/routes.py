from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from backend.clients.espn import fetch_all_games, fetch_games
from backend.clients.kalshi import kalshi_client
from backend.db import get_trades, get_latest_balance, get_balance_history
from backend.models import Sport
from backend.config import settings

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
async def get_markets(status: str = "open", limit: int = 50):
    try:
        markets = await kalshi_client.get_markets(status=status, limit=limit)
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
        return {"available": available, "portfolio_value": 0, "total": available}
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
    from backend.db import set_config_override
    await set_config_override(key, value)
    return {"key": key, "value": value}

@router.get("/config/{key}")
async def get_config(key: str):
    from backend.db import get_config_override
    value = await get_config_override(key)
    return {"key": key, "value": value}
