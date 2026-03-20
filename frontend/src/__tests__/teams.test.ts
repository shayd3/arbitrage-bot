import { describe, it, expect } from 'vitest'
import { toKalshiAbbr } from '../utils/teams'

describe('toKalshiAbbr', () => {
  describe('NBA overrides', () => {
    it('maps WSH → WAS (Washington Wizards)', () => {
      expect(toKalshiAbbr('WSH', 'nba')).toBe('WAS')
    })
    it('maps SA → SAS (San Antonio Spurs)', () => {
      expect(toKalshiAbbr('SA', 'nba')).toBe('SAS')
    })
    it('maps NY → NYK (New York Knicks)', () => {
      expect(toKalshiAbbr('NY', 'nba')).toBe('NYK')
    })
    it('maps GS → GSW (Golden State Warriors)', () => {
      expect(toKalshiAbbr('GS', 'nba')).toBe('GSW')
    })
    it('maps NO → NOP (New Orleans Pelicans)', () => {
      expect(toKalshiAbbr('NO', 'nba')).toBe('NOP')
    })
    it('passes through standard abbreviations unchanged', () => {
      expect(toKalshiAbbr('BOS', 'nba')).toBe('BOS')
      expect(toKalshiAbbr('LAL', 'nba')).toBe('LAL')
      expect(toKalshiAbbr('MIA', 'nba')).toBe('MIA')
    })
  })

  describe('NFL overrides', () => {
    it('maps WSH → WAS (Washington Commanders)', () => {
      expect(toKalshiAbbr('WSH', 'nfl')).toBe('WAS')
    })
    it('does NOT remap NO in NFL (New Orleans Saints stay NO)', () => {
      expect(toKalshiAbbr('NO', 'nfl')).toBe('NO')
    })
    it('passes through standard abbreviations unchanged', () => {
      expect(toKalshiAbbr('KC', 'nfl')).toBe('KC')
      expect(toKalshiAbbr('SF', 'nfl')).toBe('SF')
    })
  })

  describe('NHL overrides', () => {
    it('maps TB → TBL (Tampa Bay Lightning)', () => {
      expect(toKalshiAbbr('TB', 'nhl')).toBe('TBL')
    })
    it('maps SJ → SJS (San Jose Sharks)', () => {
      expect(toKalshiAbbr('SJ', 'nhl')).toBe('SJS')
    })
    it('maps NJ → NJD (New Jersey Devils)', () => {
      expect(toKalshiAbbr('NJ', 'nhl')).toBe('NJD')
    })
    it('passes through standard abbreviations unchanged', () => {
      expect(toKalshiAbbr('BOS', 'nhl')).toBe('BOS')
      expect(toKalshiAbbr('TOR', 'nhl')).toBe('TOR')
    })
  })

  describe('MLB overrides', () => {
    it('maps CWS → CHW (Chicago White Sox)', () => {
      expect(toKalshiAbbr('CWS', 'mlb')).toBe('CHW')
    })
    it('passes through standard abbreviations unchanged', () => {
      expect(toKalshiAbbr('NYY', 'mlb')).toBe('NYY')
      expect(toKalshiAbbr('BOS', 'mlb')).toBe('BOS')
    })
  })

  describe('WNBA overrides', () => {
    it('maps NY → NYL (New York Liberty, not Knicks)', () => {
      expect(toKalshiAbbr('NY', 'wnba')).toBe('NYL')
    })
    it('passes through standard abbreviations unchanged', () => {
      expect(toKalshiAbbr('LAS', 'wnba')).toBe('LAS')
    })
  })

  describe('CBB — no overrides', () => {
    it('passes all abbreviations through as-is', () => {
      expect(toKalshiAbbr('CONN', 'cbb')).toBe('CONN')
      expect(toKalshiAbbr('KU', 'cbb')).toBe('KU')
    })
  })

  describe('input normalization', () => {
    it('accepts lowercase ESPN abbreviations and applies override', () => {
      expect(toKalshiAbbr('gs', 'nba')).toBe('GSW')
      expect(toKalshiAbbr('wsh', 'nfl')).toBe('WAS')
    })
    it('accepts mixed-case input', () => {
      expect(toKalshiAbbr('Gs', 'nba')).toBe('GSW')
    })
    it('returns uppercase when no override exists for a lowercase input', () => {
      expect(toKalshiAbbr('bos', 'nba')).toBe('BOS')
    })
    it('returns uppercase for unknown sport', () => {
      expect(toKalshiAbbr('abc', 'unknown')).toBe('ABC')
    })
  })

  describe('cross-sport isolation', () => {
    it('NY maps to NYK in NBA but NYL in WNBA', () => {
      expect(toKalshiAbbr('NY', 'nba')).toBe('NYK')
      expect(toKalshiAbbr('NY', 'wnba')).toBe('NYL')
    })
    it('WSH maps to WAS in both NBA and NFL', () => {
      expect(toKalshiAbbr('WSH', 'nba')).toBe('WAS')
      expect(toKalshiAbbr('WSH', 'nfl')).toBe('WAS')
    })
    it('NO maps to NOP in NBA but stays NO in NFL', () => {
      expect(toKalshiAbbr('NO', 'nba')).toBe('NOP')
      expect(toKalshiAbbr('NO', 'nfl')).toBe('NO')
    })
  })
})
