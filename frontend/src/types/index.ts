export interface Team {
  id: string
  name: string
  abbreviation: string
  score: number
}

export interface GameClock {
  period: number
  period_type: string
  display_clock: string
  seconds_remaining: number | null
}

export interface Game {
  id: string
  sport: string
  home_team: Team
  away_team: Team
  status: 'scheduled' | 'in_progress' | 'final'
  clock: GameClock | null
  start_time: string | null
  venue: string | null
}

export interface KalshiMarket {
  ticker: string
  title: string
  status: string
  yes_bid: number | null
  yes_ask: number | null
  no_bid: number | null
  no_ask: number | null
  volume: number | null
  open_interest: number | null
  close_time: string | null
}

export interface Trade {
  id: number
  kalshi_order_id: string | null
  ticker: string
  side: 'yes' | 'no'
  contracts: number
  price: number
  status: string
  pnl: number | null
  created_at: string
  settled_at: string | null
  game_id: string | null
}

export interface KalshiPosition {
  ticker: string
  position_fp: string
  market_exposure_dollars: string
  total_traded_dollars: string
  realized_pnl_dollars: string
  fees_paid_dollars: string
}

export interface Balance {
  id?: number
  timestamp?: string
  available: number
  portfolio_value: number
  total: number
  error?: string
}

export interface WsMessage {
  type: string
  data: Record<string, unknown>
}
