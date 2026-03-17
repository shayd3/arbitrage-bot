import { useState } from 'react'
import { useGames, useMarkets } from '../api/hooks'
import GameCard from '../components/GameCard'
import type { KalshiMarket } from '../types'

export default function LiveGames() {
  const [sport, setSport] = useState<string>('nba')
  const { data: gamesData, isLoading } = useGames(sport)
  const { data: marketsData } = useMarkets()

  const games = gamesData?.games ?? []
  const markets = marketsData?.markets ?? []

  // Try to match game to market by team abbreviation in ticker
  function findMarket(_gameId: string): KalshiMarket | undefined {
    // This will be improved with proper matching in Phase 2
    return markets.find((m) =>
      m.ticker.toLowerCase().includes('nba') &&
      m.status === 'open'
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Live Games</h1>
        <select
          value={sport}
          onChange={(e) => setSport(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
        >
          <option value="nba">NBA</option>
          <option value="nfl">NFL</option>
          <option value="mlb">MLB</option>
          <option value="nhl">NHL</option>
        </select>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading games...</p>
      ) : games.length === 0 ? (
        <p className="text-gray-500">No games found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {games.map((game) => (
            <GameCard key={game.id} game={game} market={findMarket(game.id)} />
          ))}
        </div>
      )}
    </div>
  )
}
