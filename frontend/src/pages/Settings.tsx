import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

interface SportConfig {
  sport: string
  final_period: number
  final_period_window: number
  min_lead: number
  min_yes_price: number
  poll_interval: number
}

interface GlobalConfig {
  max_position_pct: number
  max_open_positions: number
  max_daily_loss: number
}

interface StrategyData {
  global: GlobalConfig
  mode: string
  sports: SportConfig[]
}

async function fetchStrategy(): Promise<StrategyData> {
  const res = await fetch('/api/strategy')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

async function updateGlobal(config: Partial<GlobalConfig>) {
  const res = await fetch('/api/strategy/global', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

async function updateSport(sport: string, config: Partial<SportConfig>) {
  const res = await fetch(`/api/strategy/sport/${sport}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

const SPORT_META: Record<string, { label: string; periodLabel: string; leadUnit: string }> = {
  nba: { label: 'NBA', periodLabel: 'Q4', leadUnit: 'pts' },
  nfl: { label: 'NFL', periodLabel: 'Q4', leadUnit: 'pts' },
  nhl: { label: 'NHL', periodLabel: 'P3', leadUnit: 'goals' },
  mlb: { label: 'MLB', periodLabel: 'Inning 9', leadUnit: 'runs' },
}

function formatWindow(sport: string, seconds: number): string {
  if (sport === 'mlb') return 'final inning'
  if (seconds === 0) return 'any time'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return secs > 0 ? `${mins}:${String(secs).padStart(2, '0')} remaining` : `${mins}:00 remaining`
}

function modeColor(mode: string) {
  if (mode === 'live') return 'text-green-400'
  if (mode === 'simulation') return 'text-yellow-400'
  return 'text-gray-400'
}

function StatCard({ label, value, dim }: { label: string; value: string; dim?: string }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-xl font-bold text-white">
        {value}
        {dim && <span className="text-sm text-gray-400 ml-1">{dim}</span>}
      </div>
    </div>
  )
}

function GlobalEditor({ data, onSave }: { data: GlobalConfig; onSave: (c: Partial<GlobalConfig>) => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [pct, setPct] = useState(String(data.max_position_pct))
  const [positions, setPositions] = useState(String(data.max_open_positions))
  const [loss, setLoss] = useState(String(data.max_daily_loss))
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave({
        max_position_pct: parseInt(pct),
        max_open_positions: parseInt(positions),
        max_daily_loss: parseFloat(loss),
      })
      setOpen(false)
    } finally {
      setSaving(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded-lg px-3 py-1.5 hover:border-gray-500 transition-colors"
      >
        Edit
      </button>
    )
  }

  return (
    <div className="flex flex-wrap items-end gap-4 mt-4 p-4 bg-gray-800 border border-gray-700 rounded-xl">
      <div>
        <div className="text-xs text-gray-500 mb-1">Bet % of Balance</div>
        <div className="flex items-center gap-1">
          <input
            type="number" min="1" max="100" value={pct} onChange={e => setPct(e.target.value)}
            className="w-16 bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-white"
          />
          <span className="text-gray-400 text-sm">%</span>
        </div>
      </div>
      <div>
        <div className="text-xs text-gray-500 mb-1">Max Positions</div>
        <input
          type="number" min="1" max="20" value={positions} onChange={e => setPositions(e.target.value)}
          className="w-16 bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-white"
        />
      </div>
      <div>
        <div className="text-xs text-gray-500 mb-1">Max Daily Loss</div>
        <div className="flex items-center gap-1">
          <span className="text-gray-400 text-sm">$</span>
          <input
            type="number" min="0" value={loss} onChange={e => setLoss(e.target.value)}
            className="w-20 bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-white"
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleSave} disabled={saving}
          className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button
          onClick={() => setOpen(false)}
          className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-600 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}

function SportRow({ config, onSave }: { config: SportConfig; onSave: (sport: string, u: Partial<SportConfig>) => Promise<void> }) {
  const [editing, setEditing] = useState(false)
  const [minLead, setMinLead] = useState(String(config.min_lead))
  const [windowSecs, setWindowSecs] = useState(String(config.final_period_window))
  const [minPrice, setMinPrice] = useState(String(config.min_yes_price))
  const [saving, setSaving] = useState(false)

  const meta = SPORT_META[config.sport] ?? { label: config.sport.toUpperCase(), periodLabel: `P${config.final_period}`, leadUnit: 'pts' }

  const reset = () => {
    setMinLead(String(config.min_lead))
    setWindowSecs(String(config.final_period_window))
    setMinPrice(String(config.min_yes_price))
    setEditing(false)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(config.sport, {
        min_lead: parseInt(minLead),
        final_period_window: parseFloat(windowSecs),
        min_yes_price: parseInt(minPrice),
      })
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const tdClass = 'py-3 pr-6 text-sm'

  return (
    <tr className="border-b border-gray-800 last:border-0">
      <td className={`${tdClass} font-semibold text-yellow-400`}>{meta.label}</td>
      <td className={`${tdClass} text-gray-400`}>{meta.periodLabel}</td>
      <td className={`${tdClass} text-gray-300`}>
        {editing ? (
          <div className="flex items-center gap-1">
            <input
              type="number" value={windowSecs} onChange={e => setWindowSecs(e.target.value)}
              className="w-20 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-white"
            />
            <span className="text-gray-500 text-xs">s</span>
          </div>
        ) : (
          formatWindow(config.sport, config.final_period_window)
        )}
      </td>
      <td className={`${tdClass}`}>
        {editing ? (
          <div className="flex items-center gap-1">
            <input
              type="number" value={minLead} onChange={e => setMinLead(e.target.value)}
              className="w-16 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-white"
            />
            <span className="text-gray-500 text-xs">{meta.leadUnit}</span>
          </div>
        ) : (
          <span className="text-yellow-400 font-semibold">{config.min_lead}</span>
        )}
      </td>
      <td className={`${tdClass}`}>
        {editing ? (
          <div className="flex items-center gap-1">
            <input
              type="number" min="1" max="99" value={minPrice} onChange={e => setMinPrice(e.target.value)}
              className="w-16 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs text-white"
            />
            <span className="text-gray-500 text-xs">¢</span>
          </div>
        ) : (
          <span className="text-gray-300">{config.min_yes_price}¢</span>
        )}
      </td>
      <td className="py-3 text-right">
        {editing ? (
          <div className="flex gap-2 justify-end">
            <button
              onClick={handleSave} disabled={saving}
              className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-xs font-medium disabled:opacity-50 transition-colors"
            >
              {saving ? '...' : 'Save'}
            </button>
            <button
              onClick={reset}
              className="px-3 py-1 bg-gray-700 text-gray-300 rounded text-xs font-medium hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className="px-3 py-1 bg-gray-800 border border-gray-700 text-gray-400 rounded text-xs font-medium hover:text-white hover:border-gray-500 transition-colors"
          >
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

      {/* Global config */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-gray-400">Global Configuration</h2>
          <GlobalEditor
            data={g}
            onSave={(config) => globalMutation.mutateAsync(config)}
          />
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

      {/* Per-sport thresholds */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-medium text-gray-400 mb-4">Sport Thresholds</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">Sport</th>
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">Final Period</th>
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">End-of-Game</th>
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">Min Lead</th>
                <th className="pb-3 pr-6 text-xs font-semibold text-gray-500 uppercase tracking-wide">Min YES Price</th>
                <th className="pb-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide"></th>
              </tr>
            </thead>
            <tbody>
              {sports.map((s) => (
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
          End-of-Game is entered in seconds (e.g. 300 = 5:00 remaining). MLB uses final inning regardless of seconds value.
        </p>
      </div>
    </div>
  )
}
