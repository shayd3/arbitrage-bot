// Overrides where ESPN and Kalshi use different team abbreviations.
// Key = ESPN abbreviation, Value = Kalshi abbreviation.
const ESPN_TO_KALSHI: Record<string, string> = {
  WSH: 'WAS', // Washington (ESPN uses WSH, Kalshi uses WAS)
  SA: 'SAS',  // San Antonio Spurs (ESPN uses SA, Kalshi uses SAS)
  NY: 'NYK',  // New York Knicks (ESPN uses NY, Kalshi uses NYK)
  GS: 'GSW',  // Golden State Warriors (ESPN uses GS, Kalshi uses GSW)
  NO: 'NOP',  // New Orleans Pelicans (ESPN uses NO, Kalshi uses NOP)
}

export function toKalshiAbbr(espnAbbr: string): string {
  const upper = espnAbbr.toUpperCase()
  return ESPN_TO_KALSHI[upper] ?? upper
}
