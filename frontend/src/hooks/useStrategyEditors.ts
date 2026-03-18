import { useState, useEffect } from 'react'
import { SPORT_META, type GlobalConfig, type SportConfig } from '../api/strategy'

/**
 * Shared state/logic for editing global risk config.
 * Syncs from props when not actively editing, so background refetches
 * don't clobber in-progress edits but do update the initial values.
 */
export function useGlobalConfigEditor(g: GlobalConfig) {
  const [editing, setEditing] = useState(false)
  const [pct, setPct] = useState(String(g.max_position_pct))
  const [positions, setPositions] = useState(String(g.max_open_positions))
  const [loss, setLoss] = useState(String(g.max_daily_loss))
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!editing) {
      setPct(String(g.max_position_pct))
      setPositions(String(g.max_open_positions))
      setLoss(String(g.max_daily_loss))
    }
  }, [g.max_position_pct, g.max_open_positions, g.max_daily_loss, editing])

  const buildConfig = (): Partial<GlobalConfig> => ({
    max_position_pct: parseInt(pct),
    max_open_positions: parseInt(positions),
    max_daily_loss: parseFloat(loss),
  })

  return { editing, setEditing, pct, setPct, positions, setPositions, loss, setLoss, saving, setSaving, buildConfig }
}

/**
 * Shared state/logic for editing per-sport thresholds.
 * Same sync-when-idle pattern as above.
 */
export function useSportConfigEditor(config: SportConfig) {
  const [editing, setEditing] = useState(false)
  const [minLead, setMinLead] = useState(String(config.min_lead))
  const [windowSecs, setWindowSecs] = useState(String(config.final_period_window))
  const [minPrice, setMinPrice] = useState(String(config.min_yes_price))
  const [saving, setSaving] = useState(false)

  const meta = SPORT_META[config.sport] ?? { label: config.sport.toUpperCase(), leadUnit: 'pts' }

  useEffect(() => {
    if (!editing) {
      setMinLead(String(config.min_lead))
      setWindowSecs(String(config.final_period_window))
      setMinPrice(String(config.min_yes_price))
    }
  }, [config.min_lead, config.final_period_window, config.min_yes_price, editing])

  const reset = () => {
    setMinLead(String(config.min_lead))
    setWindowSecs(String(config.final_period_window))
    setMinPrice(String(config.min_yes_price))
    setEditing(false)
  }

  const buildConfig = (): Partial<SportConfig> => ({
    min_lead: parseInt(minLead),
    final_period_window: parseFloat(windowSecs),
    min_yes_price: parseInt(minPrice),
  })

  return { editing, setEditing, minLead, setMinLead, windowSecs, setWindowSecs, minPrice, setMinPrice, saving, setSaving, meta, reset, buildConfig }
}
