import type { Game, KalshiMarket, Trade, KalshiPosition } from '../types'
import { parseUTCDate } from '../utils/time'
import { computePnL } from '../utils/pnl'

interface Props {
  game: Game
  markets: KalshiMarket[]
  trades?: Trade[]
  positionsByTicker?: Map<string, KalshiPosition>
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
        {game.start_time ? parseUTCDate(game.start_time).toLocaleTimeString() : 'TBD'}
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
  // Shorten ticker for display: "KXNBAGAME-26MAR17OKCORL-OKC" → "26MAR17OKCORL-OKC"
  const shortTicker = market.ticker.replace(/^KX(NBA|NFL|MLB|NHL)(GAME)?-?/i, '')

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


function TradeRow({ trade, game, markets, position }: { trade: Trade; game: Game; markets: KalshiMarket[]; position?: KalshiPosition }) {
  const pnlDollars = computePnL(trade, game, markets, position)
  const sideColor = trade.side === 'yes' ? 'text-green-400' : 'text-red-400'

  return (
    <div className="flex items-center justify-between text-xs">
      <div className="flex items-center gap-2">
        <span className={`font-semibold uppercase ${sideColor}`}>{trade.side}</span>
        <span className="text-gray-300">{trade.contracts}x @ {trade.price}¢</span>
        <span className="text-gray-600">{trade.status}</span>
      </div>
      {pnlDollars != null && (
        <span className={`font-semibold ${pnlDollars >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {pnlDollars >= 0 ? '+' : ''}{pnlDollars.toFixed(2)}
        </span>
      )}
    </div>
  )
}

function TradeStrip({ trades, game, markets, positionsByTicker }: { trades: Trade[]; game: Game; markets: KalshiMarket[]; positionsByTicker?: Map<string, KalshiPosition> }) {
  return (
    <div className="border-t border-yellow-500/30 pt-2 space-y-1.5">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] font-semibold uppercase text-yellow-400 tracking-wide">Active Trade{trades.length !== 1 ? 's' : ''}</span>
        {trades.map(t => {
          const shortTicker = t.ticker.replace(/^KX(NBA|NFL|MLB|NHL)(GAME)?-?/i, '')
          return (
            <span key={t.id} className="text-[10px] font-mono text-yellow-400/70 bg-yellow-500/10 px-1.5 py-0.5 rounded">
              {shortTicker}
            </span>
          )
        })}
      </div>
      {trades.map(t => (
        <TradeRow key={t.id} trade={t} game={game} markets={markets} position={positionsByTicker?.get(t.ticker)} />
      ))}
    </div>
  )
}

export default function GameCard({ game, markets, trades, positionsByTicker }: Props) {
  const homeLeading = game.home_team.score > game.away_team.score
  const awayLeading = game.away_team.score > game.home_team.score

  return (
    <div className={`bg-gray-900 border rounded-xl p-4 space-y-3 ${trades?.length ? 'border-yellow-500/60 active-trade-card' : 'border-gray-800'}`}>
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

      {trades && trades.length > 0 && (
        <TradeStrip trades={trades} game={game} markets={markets} positionsByTicker={positionsByTicker} />
      )}

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
