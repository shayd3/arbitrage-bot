import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useGames, useMarkets, useTrades, usePositions } from '../api/hooks'
import GameCard from '../components/GameCard'
import type { Game, KalshiMarket, Trade } from '../types'
import { fetchStrategy, updateGlobal, updateSport, formatWindow, type SportConfig, type GlobalConfig } from '../api/strategy'
import { useGlobalConfigEditor, useSportConfigEditor } from '../hooks/useStrategyEditors'
import { toKalshiAbbr } from '../utils/teams'

// ─── Shared primitives ────────────────────────────────────────────────────────

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500">{label}</span>
      <span className="text-sm font-semibold text-white">{value}</span>
    </div>
  )
}

function Field({ label, unit, unitBefore, children }: {
  label: string; unit?: string; unitBefore?: boolean; children: React.ReactNode
}) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="flex items-center gap-1">
        {unitBefore && unit && <span className="text-gray-400 text-sm">{unit}</span>}
        {children}
        {!unitBefore && unit && <span className="text-gray-400 text-sm">{unit}</span>}
      </div>
    </div>
  )
}

// ─── Global config bar ────────────────────────────────────────────────────────

function GlobalConfigBar({ g, demo, onSave }: {
  g: GlobalConfig
  demo: boolean
  onSave: (c: Partial<GlobalConfig>) => Promise<void>
}) {
  const { editing, setEditing, pct, setPct, positions, setPositions, loss, setLoss, saving, setSaving, buildConfig } =
    useGlobalConfigEditor(g)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(buildConfig())
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <Chip label="Bet / trade" value={`${g.max_position_pct}%`} />
        <Chip label="Max positions" value={String(g.max_open_positions)} />
        <Chip label="Daily loss limit" value={`$${g.max_daily_loss}`} />
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Env</span>
          <span className={`text-sm font-bold uppercase ${demo ? 'text-yellow-400' : 'text-green-400'}`}>{demo ? 'demo' : 'live'}</span>
        </div>

        <div className="ml-auto">
          {editing ? (
            <div className="flex flex-wrap items-end gap-3">
              <Field label="Bet %" unit="%">
                <input type="number" min="1" max="100" value={pct} onChange={e => setPct(e.target.value)}
                  className="w-14 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white" />
              </Field>
              <Field label="Max positions">
                <input type="number" min="1" max="20" value={positions} onChange={e => setPositions(e.target.value)}
                  className="w-14 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white" />
              </Field>
              <Field label="Max daily loss" unit="$" unitBefore>
                <input type="number" min="0" value={loss} onChange={e => setLoss(e.target.value)}
                  className="w-20 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white" />
              </Field>
              <button onClick={handleSave} disabled={saving}
                className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
                {saving ? '...' : 'Save'}
              </button>
              <button onClick={() => setEditing(false)}
                className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-600 transition-colors">
                Cancel
              </button>
            </div>
          ) : (
            <button onClick={() => setEditing(true)}
              className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded-lg px-3 py-1.5 hover:border-gray-500 transition-colors">
              Edit global
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Per-sport config strip ───────────────────────────────────────────────────

function SportConfigStrip({ config, onSave }: {
  config: SportConfig
  onSave: (sport: string, c: Partial<SportConfig>) => Promise<void>
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

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
      {editing ? (
        <>
          <Field label={`Min lead (${meta.leadUnit})`}>
            <input type="number" value={minLead} onChange={e => setMinLead(e.target.value)}
              className="w-16 bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-white" />
          </Field>
          <Field label="Window (seconds)">
            <input type="number" value={windowSecs} onChange={e => setWindowSecs(e.target.value)}
              className="w-20 bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-white" />
          </Field>
          <Field label="Min YES price" unit="¢">
            <input type="number" min="1" max="99" value={minPrice} onChange={e => setMinPrice(e.target.value)}
              className="w-16 bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-white" />
          </Field>
          <div className="flex gap-2 ml-auto">
            <button onClick={handleSave} disabled={saving}
              className="px-3 py-1 bg-green-600 hover:bg-green-500 text-white rounded text-xs font-medium disabled:opacity-50 transition-colors">
              {saving ? '...' : 'Save'}
            </button>
            <button onClick={reset}
              className="px-3 py-1 bg-gray-700 text-gray-300 rounded text-xs font-medium hover:bg-gray-600 transition-colors">
              Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <Chip label="Min lead" value={`${config.min_lead} ${meta.leadUnit}`} />
          <Chip label="End-of-game" value={formatWindow(config.sport, config.final_period_window)} />
          <Chip label="Min YES" value={`${config.min_yes_price}¢`} />
          <button onClick={() => setEditing(true)}
            className="ml-auto text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded px-2.5 py-1 hover:border-gray-500 transition-colors">
            Edit thresholds
          </button>
        </>
      )}
    </div>
  )
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'nba', label: 'NBA' },
  { id: 'nfl', label: 'NFL' },
  { id: 'mlb', label: 'MLB' },
  { id: 'nhl', label: 'NHL' },
]

const SPORT_SERIES_TICKERS: Record<string, string> = {
  nba: 'KXNBAGAME',
  nfl: 'KXNFLGAME',
  mlb: 'KXMLBGAME',
  nhl: 'KXNHLGAME',
}

function matchMarketsForGame(game: Game, markets: KalshiMarket[]): KalshiMarket[] {
  const sport = game.sport.toUpperCase()
  const homeAbbr = toKalshiAbbr(game.home_team.abbreviation)
  const awayAbbr = toKalshiAbbr(game.away_team.abbreviation)
  return markets.filter(m => {
    if (m.status !== 'open' && m.status !== 'active') return false
    const ticker = m.ticker.toUpperCase()
    if (!ticker.includes(sport)) return false
    // Both teams must appear in the ticker (KXNBAGAME format: OKCORL)
    return ticker.includes(homeAbbr) && ticker.includes(awayAbbr)
  })
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LiveGames() {
  const [activeTab, setActiveTab] = useState('nba')
  const qc = useQueryClient()

  const { data: strategy, isLoading: strategyLoading } = useQuery({
    queryKey: ['strategy'],
    queryFn: fetchStrategy,
    refetchInterval: 30000,
  })

  const { data: gamesData, isLoading: gamesLoading } = useGames(activeTab)
  const { data: marketsData } = useMarkets(SPORT_SERIES_TICKERS[activeTab])
  const { data: tradesData } = useTrades()
  const { data: positionsData } = usePositions()

  const positionsByTicker = new Map(
    (positionsData?.positions ?? []).map(p => [p.ticker, p])
  )

  const tradesByGame = (tradesData?.trades ?? []).reduce((map, trade) => {
    if (!trade.game_id) return map
    if (trade.status !== 'pending' && trade.status !== 'filled') return map
    const list = map.get(trade.game_id) ?? []
    list.push(trade)
    map.set(trade.game_id, list)
    return map
  }, new Map<string, Trade[]>())

  const globalMutation = useMutation({
    mutationFn: updateGlobal,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategy'] }),
  })

  const sportMutation = useMutation({
    mutationFn: ({ sport, config }: { sport: string; config: Partial<SportConfig> }) =>
      updateSport(sport, config),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['strategy'] }),
  })

  const games = gamesData?.games ?? []
  const markets = marketsData?.markets ?? []
  const activeSportConfig = strategy?.sports.find(s => s.sport === activeTab)

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">Live Games</h1>

      {strategy && !strategyLoading && (
        <GlobalConfigBar
          g={strategy.global}
          demo={strategy.demo}
          onSave={(c) => globalMutation.mutateAsync(c)}
        />
      )}

      <div>
        <div className="flex border-b border-gray-800">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-2.5 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-white border-b-2 border-yellow-400 -mb-px'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="pt-4 space-y-4">
          {activeSportConfig && (
            <SportConfigStrip
              config={activeSportConfig}
              onSave={(sport, config) => sportMutation.mutateAsync({ sport, config })}
            />
          )}

          {gamesLoading ? (
            <p className="text-gray-500 text-sm">Loading games...</p>
          ) : games.length === 0 ? (
            <p className="text-gray-500 text-sm">No {activeTab.toUpperCase()} games right now.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {games.map(game => (
                <GameCard key={game.id} game={game} markets={matchMarketsForGame(game, markets)} trades={tradesByGame.get(game.id)} positionsByTicker={positionsByTicker} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
