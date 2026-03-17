import type { Game, KalshiMarket } from '../types'

interface Props {
  game: Game
  market?: KalshiMarket
}

function ScoreBadge({ score, isLeading }: { score: number; isLeading: boolean }) {
  return (
    <span className={`text-2xl font-bold ${isLeading ? 'text-white' : 'text-gray-400'}`}>
      {score}
    </span>
  )
}

function ClockBadge({ game }: { game: Game }) {
  if (game.status === 'scheduled') {
    return (
      <span className="text-xs text-gray-500">
        {game.start_time ? new Date(game.start_time).toLocaleTimeString() : 'TBD'}
      </span>
    )
  }
  if (game.status === 'final') {
    return <span className="text-xs font-semibold text-gray-400">FINAL</span>
  }
  if (game.clock) {
    const { period, display_clock, period_type } = game.clock
    const periodLabel = period_type === 'overtime' ? `OT${period - 4}` : `Q${period}`
    return (
      <span className="text-xs font-semibold text-yellow-400">
        {display_clock} {periodLabel}
      </span>
    )
  }
  return null
}

export default function GameCard({ game, market }: Props) {
  const homeLeading = game.home_team.score > game.away_team.score
  const awayLeading = game.away_team.score > game.home_team.score

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 uppercase tracking-wide">{game.sport}</span>
        <ClockBadge game={game} />
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 text-center">
          <div className="text-sm text-gray-400">{game.away_team.abbreviation}</div>
          <ScoreBadge score={game.away_team.score} isLeading={awayLeading} />
        </div>
        <div className="text-gray-600 font-bold">@</div>
        <div className="flex-1 text-center">
          <div className="text-sm text-gray-400">{game.home_team.abbreviation}</div>
          <ScoreBadge score={game.home_team.score} isLeading={homeLeading} />
        </div>
      </div>

      {market && (
        <div className="border-t border-gray-800 pt-3">
          <div className="text-xs text-gray-500 mb-1 truncate">{market.ticker}</div>
          <div className="flex gap-3 text-xs">
            {market.yes_bid != null && (
              <span className="text-green-400">YES bid: {market.yes_bid}¢</span>
            )}
            {market.yes_ask != null && (
              <span className="text-red-400">YES ask: {market.yes_ask}¢</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
