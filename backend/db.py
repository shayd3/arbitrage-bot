import aiosqlite
import asyncio
from datetime import datetime
from pathlib import Path
from backend.config import settings
from backend.models import Trade, Balance, TradeStatus, MarketSide

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS markets (
    ticker TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    yes_bid INTEGER,
    yes_ask INTEGER,
    no_bid INTEGER,
    no_ask INTEGER,
    volume INTEGER,
    open_interest INTEGER,
    close_time TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kalshi_order_id TEXT,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    contracts INTEGER NOT NULL,
    price INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    pnl REAL,
    created_at TEXT NOT NULL,
    settled_at TEXT,
    game_id TEXT
);

CREATE TABLE IF NOT EXISTS balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    available REAL NOT NULL,
    portfolio_value REAL NOT NULL,
    total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS game_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS config_overrides (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scanner_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    data_json TEXT,
    created_at TEXT NOT NULL
);
"""

_db: aiosqlite.Connection | None = None

async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(settings.database_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _db.executescript(CREATE_TABLES)
        await _db.commit()
    return _db

async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None

async def insert_trade(trade: Trade) -> int:
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO trades (kalshi_order_id, ticker, side, contracts, price, status, pnl, created_at, game_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (trade.kalshi_order_id, trade.ticker, trade.side.value, trade.contracts,
         trade.price, trade.status.value, trade.pnl,
         (trade.created_at or datetime.utcnow()).isoformat(), trade.game_id)
    )
    await db.commit()
    return cursor.lastrowid

async def get_trades(limit: int = 100) -> list[dict]:
    db = await get_db()
    # Filter out legacy simulated rows (pre-migration rows with no real Kalshi order ID)
    cursor = await db.execute(
        "SELECT * FROM trades WHERE kalshi_order_id IS NOT NULL ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]

async def insert_balance(balance: Balance):
    db = await get_db()
    await db.execute(
        """INSERT INTO balances (timestamp, available, portfolio_value, total)
           VALUES (?, ?, ?, ?)""",
        (balance.timestamp.isoformat(), balance.available, balance.portfolio_value, balance.total)
    )
    await db.commit()

async def get_latest_balance() -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM balances ORDER BY timestamp DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    return dict(row) if row else None

async def get_balance_history(limit: int = 100) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM balances ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]

async def log_scanner(level: str, message: str, data: dict | None = None):
    import json
    db = await get_db()
    await db.execute(
        "INSERT INTO scanner_log (level, message, data_json, created_at) VALUES (?, ?, ?, ?)",
        (level, message, json.dumps(data) if data else None, datetime.utcnow().isoformat())
    )
    await db.commit()

async def get_config_override(key: str) -> str | None:
    db = await get_db()
    cursor = await db.execute("SELECT value FROM config_overrides WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row[0] if row else None

async def set_config_override(key: str, value: str):
    db = await get_db()
    await db.execute(
        """INSERT INTO config_overrides (key, value, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
        (key, value, datetime.utcnow().isoformat())
    )
    await db.commit()
