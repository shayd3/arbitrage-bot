import { useBalance, useBalanceHistory, useTrades } from '../api/hooks'
import PnLChart from '../components/PnLChart'
import TradeTable from '../components/TradeTable'

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const { data: balance } = useBalance()
  const { data: historyData } = useBalanceHistory()
  const { data: tradesData } = useTrades()

  const trades = tradesData?.trades ?? []
  const history = historyData?.history ?? []

  const settledTrades = trades.filter((t) => t.pnl != null)
  const totalPnl = settledTrades.reduce((sum, t) => sum + (t.pnl ?? 0), 0)

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {balance?.error && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-sm text-red-300">
          <span className="font-semibold">Kalshi API error:</span> {balance.error}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Available Balance"
          value={`$${(balance?.available ?? 0).toFixed(2)}`}
        />
        <StatCard
          label="Portfolio Value"
          value={`$${(balance?.portfolio_value ?? 0).toFixed(2)}`}
        />
        <StatCard
          label="Total P&L"
          value={`${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`}
          sub={`${settledTrades.length} settled trades`}
        />
        <StatCard
          label="Open Positions"
          value={String(trades.filter((t) => t.status === 'filled').length)}
        />
      </div>

      {history.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-sm font-medium text-gray-400 mb-4">Balance History</h2>
          <PnLChart history={history} />
        </div>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-medium text-gray-400 mb-4">Recent Trades</h2>
        <TradeTable trades={trades.slice(0, 10)} />
      </div>
    </div>
  )
}
