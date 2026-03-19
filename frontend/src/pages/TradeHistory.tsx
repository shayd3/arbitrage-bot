import { useTrades } from '../api/hooks'
import TradeTable from '../components/TradeTable'

export default function TradeHistory() {
  const { data, isLoading } = useTrades()

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Trade History</h1>

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
