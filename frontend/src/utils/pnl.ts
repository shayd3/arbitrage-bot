import type { Game, KalshiMarket, KalshiPosition, Trade } from '../types'
import { toKalshiAbbr } from './teams'

/**
 * Compute P&L from actual game outcome for a settled/final game.
 * Extracts the YES team from the ticker (last dash-segment) and determines
 * whether the bet won based on the final score.
 *
 * Returns null if the game isn't final or the ticker can't be matched.
 */
export function computeOutcomePnL(trade: Trade, game: Game): number | null {
  if (game.status !== 'final') return null
  // Extract YES team abbreviation from ticker: "KXNBAGAME-26MAR18GSWBOS-BOS" → "BOS"
  const parts = trade.ticker.split('-')
  const yesTeam = parts[parts.length - 1].toUpperCase()

  let yesTeamWon: boolean
  if (yesTeam === toKalshiAbbr(game.home_team.abbreviation, game.sport)) {
    yesTeamWon = game.home_team.score > game.away_team.score
  } else if (yesTeam === toKalshiAbbr(game.away_team.abbreviation, game.sport)) {
    yesTeamWon = game.away_team.score > game.home_team.score
  } else {
    return null
  }

  const betWon = trade.side === 'yes' ? yesTeamWon : !yesTeamWon
  return betWon
    ? (trade.contracts * (100 - trade.price)) / 100
    : -(trade.contracts * trade.price) / 100
}

/**
 * Compute current P&L for a trade using a priority cascade:
 * 1. trade.pnl if already settled and populated by the backend
 * 2. Outcome P&L computed from the final score (game is final)
 * 3. Kalshi position data (market_exposure - cost basis)
 * 4. Live market bid vs entry price estimate
 *
 * Returns null if no P&L can be determined.
 */
export function computePnL(
  trade: Trade,
  game: Game,
  markets: KalshiMarket[],
  position?: KalshiPosition,
): number | null {
  if (trade.pnl != null) return trade.pnl
  // For final games, compute from actual game outcome
  const outcomePnL = computeOutcomePnL(trade, game)
  if (outcomePnL != null) return outcomePnL
  // Use Kalshi's reported values when available (most accurate for in-progress)
  if (position?.market_exposure_dollars != null && position?.total_traded_dollars != null) {
    const marketValue = parseFloat(position.market_exposure_dollars)
    const cost = parseFloat(position.total_traded_dollars)
    if (!isNaN(marketValue) && !isNaN(cost)) return marketValue - cost
  }
  const market = markets.find((m) => m.ticker === trade.ticker)
  if (!market) return null
  const currentValue = trade.side === 'yes' ? market.yes_bid : market.no_bid
  if (currentValue == null) return null
  return ((currentValue - trade.price) * trade.contracts) / 100
}
