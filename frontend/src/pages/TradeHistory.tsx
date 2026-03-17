import { useState } from 'react'
import { useTrades } from '../api/hooks'
import TradeTable from '../components/TradeTable'

export default function TradeHistory() {
  const [filter, setFilter] = useState<'all' | 'sim' | 'live'>('all')
  const { data, isLoading } = useTrades(
    filter === 'sim' ? true : filter === 'live' ? false : undefined
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Trade History</h1>
        <div className="flex gap-2">
          {(['all', 'sim', 'live'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filter === f
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-gray-200'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <TradeTable trades={data?.trades ?? []} />
        </div>
      )}
    </div>
  )
}
