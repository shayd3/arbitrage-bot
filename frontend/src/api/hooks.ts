import { useQuery } from '@tanstack/react-query'
import type { Game, KalshiMarket, Trade, Balance } from '../types'

const API_BASE = '/api'

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function useGames(sport?: string) {
  return useQuery({
    queryKey: ['games', sport],
    queryFn: () => fetchJson<{ games: Game[] }>(
      sport ? `${API_BASE}/games?sport=${sport}` : `${API_BASE}/games`
    ),
    refetchInterval: 10000,
  })
}

export function useMarkets() {
  return useQuery({
    queryKey: ['markets'],
    queryFn: () => fetchJson<{ markets: KalshiMarket[] }>(`${API_BASE}/markets`),
    refetchInterval: 15000,
  })
}

export function useTrades(simulated?: boolean) {
  return useQuery({
    queryKey: ['trades', simulated],
    queryFn: () => {
      const url = simulated !== undefined
        ? `${API_BASE}/trades?simulated=${simulated}`
        : `${API_BASE}/trades`
      return fetchJson<{ trades: Trade[] }>(url)
    },
    refetchInterval: 5000,
  })
}

export function useBalance() {
  return useQuery({
    queryKey: ['balance'],
    queryFn: () => fetchJson<Balance>(`${API_BASE}/balance`),
    refetchInterval: 10000,
  })
}

export function useBalanceHistory() {
  return useQuery({
    queryKey: ['balance-history'],
    queryFn: () => fetchJson<{ history: Balance[] }>(`${API_BASE}/balance/history`),
    refetchInterval: 30000,
  })
}
