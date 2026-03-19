import { useQuery } from '@tanstack/react-query'
import type { Game, KalshiMarket, Trade, Balance, KalshiPosition } from '../types'

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

export function useMarkets(seriesTicker?: string) {
  return useQuery({
    queryKey: ['markets', seriesTicker],
    queryFn: () => {
      const params = new URLSearchParams({ limit: '100' })
      if (seriesTicker) params.set('series_ticker', seriesTicker)
      return fetchJson<{ markets: KalshiMarket[] }>(`${API_BASE}/markets?${params}`)
    },
    refetchInterval: 15000,
  })
}

export function useTrades() {
  return useQuery({
    queryKey: ['trades'],
    queryFn: () => fetchJson<{ trades: Trade[] }>(`${API_BASE}/trades`),
    refetchInterval: 5000,
  })
}

export function usePositions() {
  return useQuery({
    queryKey: ['positions'],
    queryFn: () => fetchJson<{ positions: KalshiPosition[] }>(`${API_BASE}/positions`),
    refetchInterval: 15000,
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
