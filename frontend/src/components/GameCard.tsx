import type { Game, KalshiMarket } from '../types'

interface Props {
  game: Game
  markets: KalshiMarket[]
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

function MarketRow({ market }: { market: KalshiMarket }) {
  // Shorten ticker for display: "KXNBA-LAL-20250317" → "LAL-20250317"
  const shortTicker = market.ticker.replace(/^KX(NBA|NFL|MLB|NHL)-?/i, '')

  return (
    <div className="bg-gray-800/60 rounded-lg px-3 py-2 space-y-1.5">
      <div className="text-xs text-gray-400 font-mono truncate" title={market.ticker}>
        {shortTicker}
      </div>
      <div className="flex items-center gap-3">
        {market.yes_ask != null && (
          <div className="flex flex-col items-center">
            <span className="text-[10px] text-gray-500 uppercase">YES ask</span>
            <span className="text-sm font-semibold text-green-400">{market.yes_ask}¢</span>
          </div>
        )}
        {market.no_ask != null && (
          <div className="flex flex-col items-center">
            <span className="text-[10px] text-gray-500 uppercase">NO ask</span>
            <span className="text-sm font-semibold text-red-400">{market.no_ask}¢</span>
          </div>
        )}
        {market.yes_bid != null && (
          <div className="flex flex-col items-center">
            <span className="text-[10px] text-gray-500 uppercase">YES bid</span>
            <span className="text-sm font-semibold text-green-600">{market.yes_bid}¢</span>
          </div>
        )}
        <div className="ml-auto flex gap-3">
          {market.volume != null && (
            <div className="flex flex-col items-center">
              <span className="text-[10px] text-gray-500 uppercase">Vol</span>
              <span className="text-xs text-gray-300">{market.volume.toLocaleString()}</span>
            </div>
          )}
          {market.open_interest != null && (
            <div className="flex flex-col items-center">
              <span className="text-[10px] text-gray-500 uppercase">OI</span>
              <span className="text-xs text-gray-300">{market.open_interest.toLocaleString()}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function GameCard({ game, markets }: Props) {
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

      {markets.length > 0 && (
        <div className="border-t border-gray-800 pt-3 space-y-2">
          {markets.map(m => (
            <MarketRow key={m.ticker} market={m} />
          ))}
        </div>
      )}

      {markets.length === 0 && game.status === 'in_progress' && (
        <div className="border-t border-gray-800 pt-3">
          <p className="text-xs text-gray-600 italic">No open Kalshi markets found</p>
        </div>
      )}
    </div>
  )
}
