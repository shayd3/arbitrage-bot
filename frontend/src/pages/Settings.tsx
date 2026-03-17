import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

async function fetchConfig(key: string) {
  const res = await fetch(`/api/config/${key}`)
  return res.json()
}

async function setConfig(key: string, value: string) {
  const res = await fetch(`/api/config/${key}?value=${encodeURIComponent(value)}`, { method: 'POST' })
  return res.json()
}

function ConfigRow({ label, configKey, defaultValue }: { label: string; configKey: string; defaultValue: string }) {
  const { data } = useQuery({
    queryKey: ['config', configKey],
    queryFn: () => fetchConfig(configKey),
  })
  const [value, setValue] = useState('')
  const mutation = useMutation({ mutationFn: (v: string) => setConfig(configKey, v) })

  const current = data?.value ?? defaultValue

  return (
    <div className="flex items-center gap-4 py-3 border-b border-gray-800">
      <div className="flex-1">
        <div className="text-sm font-medium text-gray-200">{label}</div>
        <div className="text-xs text-gray-500">Current: {current}</div>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={current}
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 w-32"
      />
      <button
        onClick={() => { mutation.mutate(value); setValue('') }}
        disabled={!value || mutation.isPending}
        className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm font-medium disabled:opacity-50"
      >
        Save
      </button>
    </div>
  )
}

export default function Settings() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-sm font-medium text-gray-400 mb-4">NBA Thresholds</h2>
        <ConfigRow label="Min YES Price (¢)" configKey="min_yes_price_nba" defaultValue="88" />
        <ConfigRow label="Min Lead (pts)" configKey="min_lead_nba" defaultValue="15" />
        <ConfigRow label="Final Period Window (s)" configKey="final_period_window_nba" defaultValue="300" />
      </div>
    </div>
  )
}
