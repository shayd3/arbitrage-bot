import aiosqlite
import asyncio
from datetime import datetime, timezone
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
         (trade.created_at or datetime.now(timezone.utc)).isoformat(), trade.game_id)
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

async def sync_trade_from_order(order: dict, *, commit: bool = True):
    """
    Upsert a trade record from a raw Kalshi order dict.
    - Inserts if the kalshi_order_id is not yet in the DB.
    - Updates status if it has changed (e.g. pending → filled).
    game_id will be null for orders not captured at placement time.
    Set commit=False to batch multiple calls and commit externally.
    """
    order_id = order.get("order_id")
    if not order_id:
        return

    ticker = order.get("ticker", "")
    side = order.get("side", "")  # "yes" or "no"
    contracts = order.get("filled_count") or order.get("count") or 0
    # Price paid in cents: yes_price if side=yes; for NO orders derive from yes_price
    # (Kalshi API always sends yes_price; NO orders are placed at 100 - yes_price)
    if side == "yes":
        price = round(float(order.get("yes_price") or order.get("yes_bid") or 0))
    else:
        no_price = order.get("no_price") or order.get("no_bid")
        if no_price:
            price = round(float(no_price))
        else:
            yes_price = float(order.get("yes_price") or order.get("yes_bid") or 0)
            price = round(100 - yes_price) if yes_price else 0

    kalshi_status = order.get("status", "")
    if kalshi_status == "filled":
        status = "filled"
    elif kalshi_status in ("canceled", "cancelled"):
        status = "cancelled"
    else:
        status = "pending"

    created_time = order.get("created_time") or datetime.now(timezone.utc).isoformat()

    db = await get_db()
    existing = await db.execute(
        "SELECT id, status FROM trades WHERE kalshi_order_id = ?", (order_id,)
    )
    row = await existing.fetchone()

    if row is None:
        # New order not in DB — insert it
        if contracts > 0 and ticker:
            await db.execute(
                """INSERT INTO trades (kalshi_order_id, ticker, side, contracts, price, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_id, ticker, side, contracts, price, status, created_time)
            )
    else:
        # Update status if it has advanced (avoid going backwards)
        STATUS_RANK = {"pending": 0, "filled": 1, "settled": 2, "cancelled": 1}
        current_rank = STATUS_RANK.get(row["status"], 0)
        new_rank = STATUS_RANK.get(status, 0)
        if new_rank > current_rank:
            await db.execute(
                "UPDATE trades SET status = ? WHERE id = ?",
                (status, row["id"])
            )

    if commit:
        await db.commit()

async def get_filled_trades() -> list[dict]:
    """Return all trades with status='filled' — candidates for settlement checking."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM trades WHERE status = 'filled'"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]

async def settle_trade(trade_id: int, pnl: float, settled_at: datetime):
    """Mark a trade as settled with its P&L."""
    db = await get_db()
    await db.execute(
        "UPDATE trades SET status = 'settled', pnl = ?, settled_at = ? WHERE id = ?",
        (pnl, settled_at.isoformat(), trade_id)
    )
    await db.commit()

async def log_scanner(level: str, message: str, data: dict | None = None):
    import json
    db = await get_db()
    await db.execute(
        "INSERT INTO scanner_log (level, message, data_json, created_at) VALUES (?, ?, ?, ?)",
        (level, message, json.dumps(data) if data else None, datetime.now(timezone.utc).isoformat())
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
        (key, value, datetime.now(timezone.utc).isoformat())
    )
    await db.commit()
