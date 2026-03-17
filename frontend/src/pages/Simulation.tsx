import { useTrades, useBalance, useBalanceHistory } from '../api/hooks'
import TradeTable from '../components/TradeTable'
import PnLChart from '../components/PnLChart'

export default function Simulation() {
  const { data: tradesData } = useTrades(true)
  const { data: balance } = useBalance()
  const { data: historyData } = useBalanceHistory()

  const trades = tradesData?.trades ?? []
  const history = historyData?.history ?? []

  const settled = trades.filter((t) => t.pnl != null)
  const wins = settled.filter((t) => (t.pnl ?? 0) > 0).length
  const totalPnl = settled.reduce((sum, t) => sum + (t.pnl ?? 0), 0)
  const winRate = settled.length > 0 ? ((wins / settled.length) * 100).toFixed(1) : '—'

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Simulation</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-sm text-gray-500">Virtual Balance</div>
          <div className="text-2xl font-bold">${(balance?.available ?? 0).toFixed(2)}</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-sm text-gray-500">Total P&L</div>
          <div className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-sm text-gray-500">Win Rate</div>
          <div className="text-2xl font-bold">{winRate}%</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-sm text-gray-500">Total Trades</div>
          <div className="text-2xl font-bold">{settled.length}</div>
        </div>
      </div>

      {history.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-medium text-gray-400 mb-4">P&L Over Time</h2>
          <PnLChart history={history} />
        </div>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-medium text-gray-400 mb-4">Simulated Trades</h2>
        <TradeTable trades={trades} />
      </div>
    </div>
  )
}
