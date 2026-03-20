from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class GameStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINAL = "final"


class Sport(StrEnum):
    NBA = "nba"
    NFL = "nfl"
    MLB = "mlb"
    NHL = "nhl"
    WNBA = "wnba"
    CBB = "cbb"


class Team(BaseModel):
    id: str
    name: str
    abbreviation: str
    score: int = 0


class GameClock(BaseModel):
    period: int
    period_type: str  # "regular", "overtime"
    display_clock: str  # e.g. "4:32"
    seconds_remaining: float | None = None


class Game(BaseModel):
    id: str
    sport: Sport
    home_team: Team
    away_team: Team
    status: GameStatus
    clock: GameClock | None = None
    start_time: datetime | None = None
    venue: str | None = None


class MarketSide(StrEnum):
    YES = "yes"
    NO = "no"


class OrderbookEntry(BaseModel):
    price: int  # cents (0-100)
    quantity: int


class KalshiMarket(BaseModel):
    ticker: str
    title: str
    status: str
    yes_bid: int | None = None  # cents
    yes_ask: int | None = None  # cents
    no_bid: int | None = None
    no_ask: int | None = None
    volume: int | None = None
    open_interest: int | None = None
    close_time: datetime | None = None
    result: str | None = None  # "yes" or "no" after settlement


class TradeStatus(StrEnum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    SETTLED = "settled"


class Trade(BaseModel):
    id: int | None = None
    kalshi_order_id: str | None = None
    ticker: str
    side: MarketSide
    contracts: int
    price: int  # cents paid
    status: TradeStatus = TradeStatus.PENDING
    pnl: float | None = None
    created_at: datetime | None = None
    settled_at: datetime | None = None
    game_id: str | None = None


class Balance(BaseModel):
    timestamp: datetime
    available: float  # dollars
    portfolio_value: float
    total: float
