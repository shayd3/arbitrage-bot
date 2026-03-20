import { describe, it, expect } from 'vitest'
import { matchMarketsForGame } from '../utils/markets'
import type { Game, KalshiMarket } from '../types'

function makeGame(overrides: Partial<Game> = {}): Game {
  return {
    id: 'game-1',
    sport: 'nba',
    status: 'in_progress',
    home_team: { id: 'bos', name: 'Boston Celtics', abbreviation: 'BOS', score: 100 },
    away_team: { id: 'gsw', name: 'Golden State Warriors', abbreviation: 'GS', score: 95 },
    clock: null,
    start_time: null,
    venue: null,
    ...overrides,
  }
}

function makeMarket(ticker: string, status = 'open'): KalshiMarket {
  return {
    ticker,
    title: ticker,
    status,
    yes_bid: 60,
    yes_ask: 62,
    no_bid: 38,
    no_ask: 40,
    volume: 1000,
    open_interest: 50,
    close_time: null,
  }
}

describe('matchMarketsForGame', () => {
  it('matches a market containing both team abbreviations for the correct sport', () => {
    const game = makeGame()
    // GS (ESPN) → GSW (Kalshi NBA mapping), BOS → BOS
    const market = makeMarket('KXNBAGAME-26MAR18GSWBOS-BOS')
    expect(matchMarketsForGame(game, [market])).toHaveLength(1)
  })

  it('filters out markets with status other than open or active', () => {
    const game = makeGame()
    const closed = makeMarket('KXNBAGAME-26MAR18GSWBOS-BOS', 'closed')
    const settled = makeMarket('KXNBAGAME-26MAR18GSWBOS-BOS', 'settled')
    expect(matchMarketsForGame(game, [closed, settled])).toHaveLength(0)
  })

  it('accepts status "active" as well as "open"', () => {
    const game = makeGame()
    const active = makeMarket('KXNBAGAME-26MAR18GSWBOS-BOS', 'active')
    expect(matchMarketsForGame(game, [active])).toHaveLength(1)
  })

  it('filters out markets for a different sport', () => {
    const game = makeGame({ sport: 'nba' })
    const nflMarket = makeMarket('KXNFLGAME-26MAR18SFKC-KC')
    expect(matchMarketsForGame(game, [nflMarket])).toHaveLength(0)
  })

  it('filters out markets missing the home team abbreviation', () => {
    const game = makeGame()
    // Has GSW but not BOS
    const market = makeMarket('KXNBAGAME-26MAR18GSWMIA-MIA')
    expect(matchMarketsForGame(game, [market])).toHaveLength(0)
  })

  it('filters out markets missing the away team abbreviation', () => {
    const game = makeGame()
    // Has BOS but not GSW
    const market = makeMarket('KXNBAGAME-26MAR18MIABOS-BOS')
    expect(matchMarketsForGame(game, [market])).toHaveLength(0)
  })

  it('applies ESPN→Kalshi abbreviation mapping (GS → GSW) when matching', () => {
    const game = makeGame({
      away_team: { id: 'gsw', name: 'Golden State Warriors', abbreviation: 'GS', score: 95 },
    })
    // Ticker uses Kalshi abbreviation GSW, not ESPN abbreviation GS
    const marketWithKalshi = makeMarket('KXNBAGAME-26MAR18GSWBOS-BOS')
    const marketWithEspn = makeMarket('KXNBAGAME-26MAR18GSBOS-BOS')
    const results = matchMarketsForGame(game, [marketWithKalshi, marketWithEspn])
    // Only the Kalshi-style ticker should match
    expect(results).toHaveLength(1)
    expect(results[0].ticker).toBe('KXNBAGAME-26MAR18GSWBOS-BOS')
  })

  it('is case-insensitive on the ticker', () => {
    const game = makeGame()
    const lowerTicker = makeMarket('kxnbagame-26mar18gswbos-bos')
    expect(matchMarketsForGame(game, [lowerTicker])).toHaveLength(1)
  })

  it('returns multiple matching markets for a single game', () => {
    const game = makeGame()
    const m1 = makeMarket('KXNBAGAME-26MAR18GSWBOS-BOS')
    const m2 = makeMarket('KXNBAGAME-26MAR18GSWBOS-GSW')
    expect(matchMarketsForGame(game, [m1, m2])).toHaveLength(2)
  })

  it('returns an empty array when no markets match', () => {
    const game = makeGame()
    expect(matchMarketsForGame(game, [])).toHaveLength(0)
  })

  it('does not match markets from a different game (wrong teams)', () => {
    const game = makeGame() // BOS vs GS
    const otherGame = makeMarket('KXNBAGAME-26MAR18OKCORL-OKC') // OKC vs ORL
    expect(matchMarketsForGame(game, [otherGame])).toHaveLength(0)
  })

  it('correctly maps NHL abbreviations (TB → TBL) when matching', () => {
    const game = makeGame({
      sport: 'nhl',
      home_team: { id: 'bos', name: 'Boston Bruins', abbreviation: 'BOS', score: 3 },
      away_team: { id: 'tbl', name: 'Tampa Bay Lightning', abbreviation: 'TB', score: 2 },
    })
    const market = makeMarket('KXNHLGAME-26MAR18TBLBOS-BOS')
    expect(matchMarketsForGame(game, [market])).toHaveLength(1)
  })
})
