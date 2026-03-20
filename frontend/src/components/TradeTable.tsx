import type { Trade } from '../types'
import { parseUTCDate } from '../utils/time'

interface Props {
  trades: Trade[]
}

const statusColor: Record<string, string> = {
  pending: 'text-yellow-400',
  filled: 'text-blue-400',
  cancelled: 'text-gray-500',
  settled: 'text-green-400',
}

export default function TradeTable({ trades }: Props) {
  if (trades.length === 0) {
    return <p className="text-gray-500 text-sm text-center py-8">No trades yet.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-gray-800">
            <th className="pb-2 font-medium">Ticker</th>
            <th className="pb-2 font-medium">Side</th>
            <th className="pb-2 font-medium">Contracts</th>
            <th className="pb-2 font-medium">Price</th>
            <th className="pb-2 font-medium">Status</th>
            <th className="pb-2 font-medium">P&L</th>
            <th className="pb-2 font-medium">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {trades.map((trade) => (
            <tr key={trade.id} className="text-gray-300">
              <td className="py-2 font-mono text-xs">{trade.ticker}</td>
              <td className="py-2">
                <span className={`font-semibold ${trade.side === 'yes' ? 'text-green-400' : 'text-red-400'}`}>
                  {trade.side.toUpperCase()}
                </span>
              </td>
              <td className="py-2">{trade.contracts}</td>
              <td className="py-2">{trade.price}¢</td>
              <td className={`py-2 ${statusColor[trade.status] ?? 'text-gray-400'}`}>{trade.status}</td>
              <td className="py-2">
                {trade.pnl != null ? (
                  <span className={trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                  </span>
                ) : '—'}
              </td>
              <td className="py-2 text-gray-500">
                {parseUTCDate(trade.created_at).toLocaleTimeString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
