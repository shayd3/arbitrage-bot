import { describe, it, expect } from 'vitest'
import { computeOutcomePnL, computePnL } from '../utils/pnl'
import type { Game, KalshiMarket, KalshiPosition, Trade } from '../types'

// ─── Fixtures ─────────────────────────────────────────────────────────────────

function makeGame(overrides: Partial<Game> = {}): Game {
  return {
    id: 'game-1',
    sport: 'nba',
    status: 'final',
    home_team: { id: 'bos', name: 'Boston Celtics', abbreviation: 'BOS', score: 110 },
    away_team: { id: 'gsw', name: 'Golden State Warriors', abbreviation: 'GS', score: 98 },
    clock: null,
    start_time: null,
    venue: null,
    ...overrides,
  }
}

function makeTrade(overrides: Partial<Trade> = {}): Trade {
  return {
    id: 1,
    kalshi_order_id: 'order-abc',
    ticker: 'KXNBAGAME-26MAR18GSWBOS-BOS',
    side: 'yes',
    contracts: 10,
    price: 75, // cents
    status: 'filled',
    pnl: null,
    created_at: '2024-03-18T20:00:00Z',
    settled_at: null,
    game_id: 'game-1',
    ...overrides,
  }
}

function makeMarket(overrides: Partial<KalshiMarket> = {}): KalshiMarket {
  return {
    ticker: 'KXNBAGAME-26MAR18GSWBOS-BOS',
    title: 'NBA: GSW vs BOS',
    status: 'active',
    yes_bid: 80,
    yes_ask: 82,
    no_bid: 18,
    no_ask: 20,
    volume: 5000,
    open_interest: 200,
    close_time: null,
    ...overrides,
  }
}

function makePosition(overrides: Partial<KalshiPosition> = {}): KalshiPosition {
  return {
    ticker: 'KXNBAGAME-26MAR18GSWBOS-BOS',
    position_fp: '10',
    market_exposure_dollars: '8.50',
    total_traded_dollars: '7.50',
    realized_pnl_dollars: '0',
    fees_paid_dollars: '0.05',
    ...overrides,
  }
}

// ─── computeOutcomePnL ────────────────────────────────────────────────────────

describe('computeOutcomePnL', () => {
  it('returns null when game is not final', () => {
    expect(computeOutcomePnL(makeTrade(), makeGame({ status: 'in_progress' }))).toBeNull()
    expect(computeOutcomePnL(makeTrade(), makeGame({ status: 'scheduled' }))).toBeNull()
  })

  it('YES bet wins: profit = contracts × (100 - price) / 100', () => {
    // BOS ticker, BOS wins (home 110 vs away 98), side=yes → win
    // 10 contracts @ 75¢: profit = 10 * 25 / 100 = $2.50
    const result = computeOutcomePnL(makeTrade({ side: 'yes' }), makeGame())
    expect(result).toBeCloseTo(2.5)
  })

  it('YES bet loses: loss = -(contracts × price) / 100', () => {
    // BOS ticker, BOS loses, side=yes → loss
    // 10 contracts @ 75¢: loss = -(10 * 75 / 100) = -$7.50
    const game = makeGame({
      home_team: { id: 'bos', name: 'Boston Celtics', abbreviation: 'BOS', score: 90 },
      away_team: { id: 'gsw', name: 'Golden State Warriors', abbreviation: 'GS', score: 110 },
    })
    const result = computeOutcomePnL(makeTrade({ side: 'yes' }), game)
    expect(result).toBeCloseTo(-7.5)
  })

  it('NO bet wins when YES team loses: profit = contracts × (100 - price) / 100', () => {
    // BOS ticker, BOS loses, side=no → win
    const game = makeGame({
      home_team: { id: 'bos', name: 'Boston Celtics', abbreviation: 'BOS', score: 90 },
      away_team: { id: 'gsw', name: 'Golden State Warriors', abbreviation: 'GS', score: 110 },
    })
    const result = computeOutcomePnL(makeTrade({ side: 'no' }), game)
    expect(result).toBeCloseTo(2.5)
  })

  it('NO bet loses when YES team wins: loss = -(contracts × price) / 100', () => {
    // BOS ticker, BOS wins, side=no → loss
    const result = computeOutcomePnL(makeTrade({ side: 'no' }), makeGame())
    expect(result).toBeCloseTo(-7.5)
  })

  it('applies ESPN→Kalshi abbreviation mapping when resolving the YES team', () => {
    // GS (ESPN) maps to GSW (Kalshi) in NBA
    // Ticker ends in GSW, home team abbr is GS (ESPN raw)
    const trade = makeTrade({ ticker: 'KXNBAGAME-26MAR18GSWBOS-GSW' })
    const game = makeGame({
      home_team: { id: 'gsw', name: 'Golden State Warriors', abbreviation: 'GS', score: 110 },
      away_team: { id: 'bos', name: 'Boston Celtics', abbreviation: 'BOS', score: 98 },
    })
    // GSW YES bet wins (home wins) → 10 × 25 / 100 = $2.50
    expect(computeOutcomePnL(trade, game)).toBeCloseTo(2.5)
  })

  it('returns null when the YES team in the ticker does not match either team', () => {
    // Ticker says DEN but neither team is Denver
    const trade = makeTrade({ ticker: 'KXNBAGAME-26MAR18GSWBOS-DEN' })
    expect(computeOutcomePnL(trade, makeGame())).toBeNull()
  })

  it('handles away-team YES ticker correctly', () => {
    // Ticker: GSW is away team, YES on GS (ESPN) → GSW
    const trade = makeTrade({ ticker: 'KXNBAGAME-26MAR18GSWBOS-GSW', side: 'yes' })
    const game = makeGame({
      home_team: { id: 'bos', name: 'Boston Celtics', abbreviation: 'BOS', score: 110 },
      away_team: { id: 'gsw', name: 'Golden State Warriors', abbreviation: 'GS', score: 98 },
    })
    // GSW away team lost → YES bet loses → -(10 * 75 / 100) = -$7.50
    expect(computeOutcomePnL(trade, game)).toBeCloseTo(-7.5)
  })

  it('correctly parses multi-segment tickers to extract the YES team', () => {
    // Ticker: "KXNBAGAME-26MAR18GSWBOS-BOS" → split by '-' → last segment = "BOS"
    const trade = makeTrade({ ticker: 'KXNBAGAME-26MAR18GSWBOS-BOS' })
    expect(computeOutcomePnL(trade, makeGame())).not.toBeNull()
  })
})

// ─── computePnL ───────────────────────────────────────────────────────────────

describe('computePnL', () => {
  it('priority 1: returns trade.pnl directly when it is already populated', () => {
    const trade = makeTrade({ pnl: 3.14 })
    // Even though game is final and an outcome could be computed, pnl takes precedence
    expect(computePnL(trade, makeGame(), [], makePosition())).toBe(3.14)
  })

  it('priority 1: returns 0 when trade.pnl is explicitly 0', () => {
    const trade = makeTrade({ pnl: 0 })
    expect(computePnL(trade, makeGame(), [])).toBe(0)
  })

  it('priority 2: computes from final game outcome when trade.pnl is null', () => {
    const trade = makeTrade({ pnl: null, side: 'yes' })
    // BOS wins → YES bet wins → $2.50
    const result = computePnL(trade, makeGame(), [])
    expect(result).toBeCloseTo(2.5)
  })

  it('priority 3: uses Kalshi position data for in-progress games', () => {
    const trade = makeTrade({ pnl: null })
    const game = makeGame({ status: 'in_progress' })
    const position = makePosition({
      market_exposure_dollars: '8.50',
      total_traded_dollars: '7.50',
    })
    // 8.50 - 7.50 = $1.00 unrealised gain
    expect(computePnL(trade, game, [], position)).toBeCloseTo(1.0)
  })

  it('priority 3: handles negative unrealised P&L from position data', () => {
    const trade = makeTrade({ pnl: null })
    const game = makeGame({ status: 'in_progress' })
    const position = makePosition({
      market_exposure_dollars: '5.00',
      total_traded_dollars: '7.50',
    })
    expect(computePnL(trade, game, [], position)).toBeCloseTo(-2.5)
  })

  it('priority 3: skips invalid position strings and falls through to market price', () => {
    const trade = makeTrade({ pnl: null })
    const game = makeGame({ status: 'in_progress' })
    const position = makePosition({
      market_exposure_dollars: 'N/A',
      total_traded_dollars: '7.50',
    })
    const market = makeMarket({ yes_bid: 80 })
    // Falls through to priority 4: (80 - 75) * 10 / 100 = $0.50
    expect(computePnL(trade, game, [market], position)).toBeCloseTo(0.5)
  })

  it('priority 4: estimates P&L from live YES bid price', () => {
    const trade = makeTrade({ pnl: null, side: 'yes' })
    const game = makeGame({ status: 'in_progress' })
    const market = makeMarket({ yes_bid: 85 })
    // (85 - 75) * 10 / 100 = $1.00
    expect(computePnL(trade, game, [market])).toBeCloseTo(1.0)
  })

  it('priority 4: estimates P&L from live NO bid price for a NO trade', () => {
    const trade = makeTrade({ pnl: null, side: 'no', price: 25 })
    const game = makeGame({ status: 'in_progress' })
    const market = makeMarket({ no_bid: 30 })
    // (30 - 25) * 10 / 100 = $0.50
    expect(computePnL(trade, game, [market])).toBeCloseTo(0.5)
  })

  it('priority 4: returns negative when current bid is below entry price', () => {
    const trade = makeTrade({ pnl: null, side: 'yes', price: 75 })
    const game = makeGame({ status: 'in_progress' })
    const market = makeMarket({ yes_bid: 60 })
    // (60 - 75) * 10 / 100 = -$1.50
    expect(computePnL(trade, game, [market])).toBeCloseTo(-1.5)
  })

  it('returns null when no P&L source is available', () => {
    const trade = makeTrade({ pnl: null })
    const game = makeGame({ status: 'in_progress' })
    // No position, no matching market
    expect(computePnL(trade, game, [])).toBeNull()
  })

  it('returns null when market exists but bid is null', () => {
    const trade = makeTrade({ pnl: null, side: 'yes' })
    const game = makeGame({ status: 'in_progress' })
    const market = makeMarket({ yes_bid: null })
    expect(computePnL(trade, game, [market])).toBeNull()
  })

  it('matches market by ticker for priority 4', () => {
    const trade = makeTrade({ pnl: null, ticker: 'KXNBAGAME-26MAR18GSWBOS-BOS' })
    const game = makeGame({ status: 'in_progress' })
    const wrongMarket = makeMarket({ ticker: 'KXNBAGAME-26MAR18OKCORL-OKC', yes_bid: 99 })
    const rightMarket = makeMarket({ ticker: 'KXNBAGAME-26MAR18GSWBOS-BOS', yes_bid: 80 })
    // (80 - 75) * 10 / 100 = $0.50, ignores wrongMarket
    expect(computePnL(trade, game, [wrongMarket, rightMarket])).toBeCloseTo(0.5)
  })
})
