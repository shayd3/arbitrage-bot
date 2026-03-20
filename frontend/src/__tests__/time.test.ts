import { describe, it, expect } from 'vitest'
import { parseUTCDate } from '../utils/time'

describe('parseUTCDate', () => {
  it('parses a string already suffixed with Z as UTC', () => {
    const d = parseUTCDate('2024-03-15T20:30:00Z')
    expect(d.getUTCFullYear()).toBe(2024)
    expect(d.getUTCMonth()).toBe(2) // 0-indexed
    expect(d.getUTCDate()).toBe(15)
    expect(d.getUTCHours()).toBe(20)
    expect(d.getUTCMinutes()).toBe(30)
  })

  it('appends Z to a bare datetime string (legacy DB format) so it is treated as UTC', () => {
    const withZ = parseUTCDate('2024-03-15T20:30:00Z')
    const withoutZ = parseUTCDate('2024-03-15T20:30:00')
    // Both should represent the same instant
    expect(withoutZ.getTime()).toBe(withZ.getTime())
  })

  it('does not double-append Z when Z is already present', () => {
    const d = parseUTCDate('2024-01-01T00:00:00Z')
    expect(d.getTime()).toBe(new Date('2024-01-01T00:00:00Z').getTime())
  })

  it('recognises a positive UTC offset and does not append Z', () => {
    const d = parseUTCDate('2024-06-01T12:00:00+05:30')
    // 12:00 +05:30 = 06:30 UTC
    expect(d.getUTCHours()).toBe(6)
    expect(d.getUTCMinutes()).toBe(30)
  })

  it('recognises a negative UTC offset and does not append Z', () => {
    const d = parseUTCDate('2024-06-01T12:00:00-04:00')
    // 12:00 -04:00 = 16:00 UTC
    expect(d.getUTCHours()).toBe(16)
  })

  it('returns a valid Date object', () => {
    const d = parseUTCDate('2024-11-05T03:15:00')
    expect(d).toBeInstanceOf(Date)
    expect(isNaN(d.getTime())).toBe(false)
  })

  it('preserves milliseconds when present', () => {
    const d = parseUTCDate('2024-03-15T20:30:00.123')
    expect(d.getUTCMilliseconds()).toBe(123)
  })
})
