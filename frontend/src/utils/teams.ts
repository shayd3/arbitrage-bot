// Overrides where ESPN and Kalshi use different team abbreviations.
// Scoped per sport to avoid cross-sport collisions (e.g., "NY" → NYK in NBA but NYL in WNBA).
const ESPN_TO_KALSHI: Record<string, Record<string, string>> = {
  nba: {
    WSH: 'WAS', // Washington Wizards
    SA: 'SAS',  // San Antonio Spurs
    NY: 'NYK',  // New York Knicks
    GS: 'GSW',  // Golden State Warriors
    NO: 'NOP',  // New Orleans Pelicans
  },
  nfl: {
    WSH: 'WAS', // Washington Commanders
    // NO stays NO for NFL (New Orleans Saints)
  },
  nhl: {
    TB: 'TBL',  // Tampa Bay Lightning
    SJ: 'SJS',  // San Jose Sharks
    NJ: 'NJD',  // New Jersey Devils
  },
  mlb: {
    CWS: 'CHW', // Chicago White Sox
  },
  wnba: {
    // WNBA abbreviations; NY → NYL for New York Liberty
    NY: 'NYL',
  },
  cbb: {},
}

export function toKalshiAbbr(espnAbbr: string, sport: string): string {
  const upper = espnAbbr.toUpperCase()
  const sportMap = ESPN_TO_KALSHI[sport.toLowerCase()]
  if (sportMap && upper in sportMap) {
    return sportMap[upper]
  }
  return upper
}
