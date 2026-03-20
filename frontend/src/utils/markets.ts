import type { Game, KalshiMarket } from '../types'
import { toKalshiAbbr } from './teams'

/**
 * Return the subset of markets that correspond to a given game.
 * A market matches when:
 *   - status is 'open' or 'active'
 *   - the ticker starts with the Kalshi series prefix for the sport (e.g. "KXNBA" for NBA)
 *   - both the home and away Kalshi abbreviations appear in the ticker
 */
export function matchMarketsForGame(game: Game, markets: KalshiMarket[]): KalshiMarket[] {
  const sport = game.sport
  const sportUpper = sport.toUpperCase()
  const homeAbbr = toKalshiAbbr(game.home_team.abbreviation, sport)
  const awayAbbr = toKalshiAbbr(game.away_team.abbreviation, sport)
  return markets.filter((m) => {
    if (m.status !== 'open' && m.status !== 'active') return false
    const ticker = m.ticker.toUpperCase()
    if (!ticker.startsWith(`KX${sportUpper}`)) return false
    // Both teams must appear in the ticker (KXNBAGAME format: OKCORL)
    return ticker.includes(homeAbbr) && ticker.includes(awayAbbr)
  })
}
