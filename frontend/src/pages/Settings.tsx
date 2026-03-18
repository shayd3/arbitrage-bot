import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchStrategy, updateGlobal, updateSport, formatWindow, modeColor, type SportConfig, type GlobalConfig } from '../api/strategy'
import { useGlobalConfigEditor, useSportConfigEditor } from '../hooks/useStrategyEditors'

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-xl font-bold text-white">{value}</div>
    </div>
  )
}

function GlobalEditor({ data, onSave }: { data: GlobalConfig; onSave: (c: Partial<GlobalConfig>) => Promise<void> }) {
  const { editing, setEditing, pct, setPct, positions, setPositions, loss, setLoss, saving, setSaving, buildConfig } =
    useGlobalConfigEditor(data)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(buildConfig())
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  if (!editing) {
    return (
      <button onClick={() => setEditing(true)}
        className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded-lg px-3 py-1.5 hover:border-gray-500 transition-colors">
        Edit
      </button>
    )
  }

  return (
    <div className="flex flex-wrap items-end gap-4 mt-4 p-4 bg-gray-800 border border-gray-700 rounded-xl">
      <div>
        <div className="text-xs text-gray-500 mb-1">Bet % of Balance</div>
        <div className="flex items-center gap-1">
          <input type="number" min="1" max="100" value={pct} onChange={e => setPct(e.target.value)}
            className="w-16 bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-white" />
          <span className="text-gray-400 text-sm">%</span>
        </div>
      </div>
      <div>
        <div className="text-xs text-gray-500 mb-1">Max Positions</div>
        <input type="number" min="1" max="20" value={positions} onChange={e => setPositions(e.target.value)}
          className="w-16 bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-white" />
      </div>
      <div>
        <div className="text-xs text-gray-500 mb-1">Max Daily Loss</div>
        <div className="flex items-center gap-1">
          <span className="text-gray-400 text-sm">$</span>
          <input type="number" min="0" value={loss} onChange={e => setLoss(e.target.value)}
            className="w-20 bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-white" />
        </div>
      </div>
      <div className="flex gap-2">
        <button onClick={handleSave} disabled={saving}
          className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button onClick={() => setEditing(false)}
          className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-600 transition-colors">
          Cancel
        </button>
      </div>
    </div>
  )
}

function SportRow({ config, onSave }: {
  config: SportConfig
  onSave: (sport: string, config: Partial<SportConfig>) => Promise<void>
}) {
  const { editing, setEditing, minLead, setMinLead, windowSecs, setWindowSecs, minPrice, setMinPrice, saving, setSaving, meta, reset, buildConfig } =
    useSportConfigEditor(config)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(config.sport, buildConfig())
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const tdClass = 'py-3 pr-6 text-sm'

  return (
    <tr className="border-b border-gray-800 last:border-0">
      <td className={`${tdClass} font-semibold text-yellow-400`}>{meta.label}</td>
      <td className={`${tdClass} text-gray-300`}>
        {editing ? (
          <div className="flex items-center gap-1">
            <input type="number" value={windowSecs} onChange={e => setWindowSecs(e.target.value)}
              className="w-20 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-white" />
            <span className="text-gray-500 text-xs">s</span>
          </div>
        ) : formatWindow(config.sport, config.final_period_window)}
      </td>
      <td className={tdClass}>
        {editing ? (
          <div className="flex items-center gap-1">
            <input type="number" value={minLead} onChange={e => setMinLead(e.target.value)}
              className="w-16 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-white" />
            <span className="text-gray-500 text-xs">{meta.leadUnit}</span>
          </div>
        ) : <span className="text-yellow-400 font-semibold">{config.min_lead}</span>}
      </td>
      <td className={tdClass}>
        {editing ? (
          <div className="flex items-center gap-1">
            <input type="number" min="1" max="99" value={minPrice} onChange={e => setMinPrice(e.target.value)}
              className="w-16 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-white" />
            <span className="text-gray-500 text-xs">¢</span>
          </div>
        ) : <span className="text-gray-300">{config.min_yes_price}¢</span>}
      </td>
      <td className="py-3 text-right">
        {editing ? (
          <div className="flex gap-2 justify-end">
            <button onClick={handleSave} disabled={saving}
              className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-xs font-medium disabled:opacity-50 transition-colors">
              {saving ? '...' : 'Save'}
            </button>
            <button onClick={reset}
              className="px-3 py-1 bg-gray-700 text-gray-300 rounded text-xs font-medium hover:bg-gray-600 transition-colors">
              Cancel
            </button>
          </div>
        ) : (
          <button onClick={() => setEditing(true)}
            className="px-3 py-1 bg-gray-800 border border-gray-700 text-gray-400 rounded text-xs font-medium hover:text-white hover:border-gray-500 transition-colors">
            Edit
          </button>
        )}
      </td>
    </tr>
  )
}

export default function Settings() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['strategy'],
    queryFn: fetchStrategy,
    refetchInterval: 30000,
  })

  const globalMutation = useMutation({
    mutationFn: updateGlobal,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategy'] }),
  })

  const sportMutation = useMutation({
    mutationFn: ({ sport, config }: { sport: string; config: Partial<SportConfig> }) =>
      updateSport(sport, config),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategy'] }),
  })

  if (isLoading || !data) {
    return <div className="text-gray-500 text-sm">Loading strategy...</div>
  }

  const { global: g, mode, sports } = data

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Strategy</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-gray-400">Global Configuration</h2>
          <GlobalEditor data={g} onSave={(c) => globalMutation.mutateAsync(c)} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Bet % of Balance" value={`${g.max_position_pct}%`} />
          <StatCard label="Max Positions" value={String(g.max_open_positions)} />
          <StatCard label="Max Daily Loss" value={`$${g.max_daily_loss}`} />
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <div className="text-xs text-gray-500 mb-1">Mode</div>
            <div className={`text-xl font-bold uppercase ${modeColor(mode)}`}>{mode}</div>
          </div>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-medium text-gray-400 mb-4">Sport Thresholds</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">Sport</th>
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">End-of-Game</th>
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">Min Lead</th>
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">Min YES Price</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sports.map(s => (
                <SportRow
                  key={s.sport}
                  config={s}
                  onSave={(sport, config) => sportMutation.mutateAsync({ sport, config })}
                />
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs text-gray-600">
          End-of-Game window is in seconds (e.g. 300 = 5:00 remaining). MLB ignores this value and always uses the final inning.
        </p>
      </div>
    </div>
  )
}
