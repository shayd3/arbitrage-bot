/**
 * Parse a timestamp string as UTC, appending 'Z' if no timezone designator is present.
 * This handles legacy DB records that were stored without timezone info.
 */
export function parseUTCDate(s: string): Date {
  const hasTimezone = s.endsWith('Z') || /[+-]\d{2}:?\d{2}$/.test(s)
  return new Date(hasTimezone ? s : s + 'Z')
}
