export interface SportConfig {
  sport: string
  final_period: number
  final_period_window: number
  min_lead: number
  min_yes_price: number
  poll_interval: number
}

export interface GlobalConfig {
  max_position_pct: number
  max_open_positions: number
  max_daily_loss: number
  espn_poll_interval: number
  kalshi_poll_interval: number
  kalshi_sync_interval: number
}

export interface StrategyData {
  global: GlobalConfig
  demo: boolean
  sports: SportConfig[]
}

export async function fetchStrategy(): Promise<StrategyData> {
  const res = await fetch('/api/strategy')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function updateGlobal(config: Partial<GlobalConfig>): Promise<void> {
  const res = await fetch('/api/strategy/global', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function updateSport(sport: string, config: Partial<SportConfig>): Promise<void> {
  const res = await fetch(`/api/strategy/sport/${sport}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export const SPORT_META: Record<string, { label: string; leadUnit: string }> = {
  nba: { label: 'NBA', leadUnit: 'pts' },
  nfl: { label: 'NFL', leadUnit: 'pts' },
  nhl: { label: 'NHL', leadUnit: 'goals' },
  mlb: { label: 'MLB', leadUnit: 'runs' },
}

export function formatWindow(sport: string, seconds: number): string {
  if (sport === 'mlb') return 'final inning'
  if (seconds === 0) return 'any time'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return secs > 0
    ? `${mins}:${String(secs).padStart(2, '0')} remaining`
    : `${mins}:00 remaining`
}
