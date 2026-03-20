from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class GameStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINAL = "final"

class Sport(str, Enum):
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
    seconds_remaining: Optional[float] = None

class Game(BaseModel):
    id: str
    sport: Sport
    home_team: Team
    away_team: Team
    status: GameStatus
    clock: Optional[GameClock] = None
    start_time: Optional[datetime] = None
    venue: Optional[str] = None

class MarketSide(str, Enum):
    YES = "yes"
    NO = "no"

class OrderbookEntry(BaseModel):
    price: int  # cents (0-100)
    quantity: int

class KalshiMarket(BaseModel):
    ticker: str
    title: str
    status: str
    yes_bid: Optional[int] = None  # cents
    yes_ask: Optional[int] = None  # cents
    no_bid: Optional[int] = None
    no_ask: Optional[int] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    close_time: Optional[datetime] = None
    result: Optional[str] = None  # "yes" or "no" after settlement

class TradeStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    SETTLED = "settled"

class Trade(BaseModel):
    id: Optional[int] = None
    kalshi_order_id: Optional[str] = None
    ticker: str
    side: MarketSide
    contracts: int
    price: int  # cents paid
    status: TradeStatus = TradeStatus.PENDING
    pnl: Optional[float] = None
    created_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    game_id: Optional[str] = None

class Balance(BaseModel):
    timestamp: datetime
    available: float  # dollars
    portfolio_value: float
    total: float
