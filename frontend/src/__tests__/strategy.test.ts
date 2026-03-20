import { describe, it, expect } from 'vitest'
import { formatWindow } from '../api/strategy'

describe('formatWindow', () => {
  it('always returns "final inning" for MLB regardless of seconds', () => {
    expect(formatWindow('mlb', 0)).toBe('final inning')
    expect(formatWindow('mlb', 120)).toBe('final inning')
    expect(formatWindow('mlb', 9999)).toBe('final inning')
  })

  it('returns "any time" when seconds is 0 for non-MLB sports', () => {
    expect(formatWindow('nba', 0)).toBe('any time')
    expect(formatWindow('nfl', 0)).toBe('any time')
    expect(formatWindow('nhl', 0)).toBe('any time')
  })

  it('formats whole minutes with :00', () => {
    expect(formatWindow('nba', 60)).toBe('1:00 remaining')
    expect(formatWindow('nba', 120)).toBe('2:00 remaining')
    expect(formatWindow('nba', 300)).toBe('5:00 remaining')
  })

  it('formats minutes and seconds with zero-padded seconds', () => {
    expect(formatWindow('nba', 90)).toBe('1:30 remaining')
    expect(formatWindow('nba', 125)).toBe('2:05 remaining')
    expect(formatWindow('nfl', 65)).toBe('1:05 remaining')
  })

  it('formats sub-minute values as 0:SS', () => {
    expect(formatWindow('nba', 45)).toBe('0:45 remaining')
    expect(formatWindow('nba', 5)).toBe('0:05 remaining')
  })

  it('rounds fractional seconds', () => {
    // 90.6s → 1 min, round(30.6) = 31s → "1:31 remaining"
    expect(formatWindow('nba', 90.6)).toBe('1:31 remaining')
  })

  it('works the same for all clock-based sports', () => {
    const result = '4:00 remaining'
    expect(formatWindow('nba', 240)).toBe(result)
    expect(formatWindow('nfl', 240)).toBe(result)
    expect(formatWindow('nhl', 240)).toBe(result)
    expect(formatWindow('wnba', 240)).toBe(result)
    expect(formatWindow('cbb', 240)).toBe(result)
  })
})
