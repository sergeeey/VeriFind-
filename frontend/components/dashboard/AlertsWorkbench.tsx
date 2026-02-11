'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

type AlertRow = {
  id: string
  ticker: string
  condition: 'above' | 'below'
  target_price: number
  is_active: boolean
  last_notified_at?: string | null
}

type CheckRow = {
  id: string
  ticker: string
  condition: 'above' | 'below'
  target_price: number
  current_price: number | null
  triggered: boolean
}

export function AlertsWorkbench() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [ticker, setTicker] = useState('AAPL')
  const [condition, setCondition] = useState<'above' | 'below'>('above')
  const [targetPrice, setTargetPrice] = useState('200')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [alerts, setAlerts] = useState<AlertRow[]>([])
  const [checkRows, setCheckRows] = useState<CheckRow[]>([])
  const [checkMeta, setCheckMeta] = useState<{ total: number; triggered: number; notifications: number } | null>(null)

  const formatTimestamp = (value?: string | null) => {
    if (!value) return 'never'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return 'invalid'
    return date.toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const loadAlerts = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/api/alerts`)
      if (!response.ok) throw new Error('Failed to load alerts')
      setAlerts(await response.json())
    } catch {
      setError('Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }

  const createAlert = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/api/alerts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ticker.trim().toUpperCase(),
          condition,
          target_price: Number(targetPrice),
        }),
      })
      if (!response.ok) throw new Error('Failed to create alert')
      await loadAlerts()
    } catch {
      setError('Failed to create alert')
    } finally {
      setLoading(false)
    }
  }

  const deleteAlert = async (id: string) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/api/alerts/${id}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('Failed to delete alert')
      await loadAlerts()
    } catch {
      setError('Failed to delete alert')
    } finally {
      setLoading(false)
    }
  }

  const checkNow = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/api/alerts/check-now`, { method: 'POST' })
      if (!response.ok) throw new Error('Failed to check alerts')
      const json = await response.json()
      setCheckRows(json.rows || [])
      setCheckMeta({
        total: json.total_checked || 0,
        triggered: json.triggered_count || 0,
        notifications: json.notifications_sent || 0,
      })
      await loadAlerts()
    } catch {
      setError('Failed to check alerts')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Price Alerts</CardTitle>
          <CardDescription>Create price thresholds and run on-demand checks.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <Input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="Ticker" />
          <Select value={condition} onValueChange={(v: 'above' | 'below') => setCondition(v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="above">above</SelectItem>
              <SelectItem value="below">below</SelectItem>
            </SelectContent>
          </Select>
          <Input value={targetPrice} onChange={(e) => setTargetPrice(e.target.value)} placeholder="Target price" />
          <div className="flex gap-2">
            <Button onClick={createAlert} disabled={loading}>Create</Button>
            <Button onClick={loadAlerts} variant="outline" disabled={loading}>Refresh</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active Alerts</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {alerts.length === 0 && <div>No alerts loaded</div>}
          {alerts.map((row) => (
            <div key={row.id} className="flex items-center justify-between rounded border p-2">
              <div>
                {row.ticker} {row.condition} {row.target_price}
                <div className="text-xs text-muted-foreground">
                  last notification: {formatTimestamp(row.last_notified_at)}
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={() => deleteAlert(row.id)} disabled={loading}>
                Delete
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Check Now</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <Button onClick={checkNow} disabled={loading}>Run Check</Button>
          {checkMeta && (
            <div className="rounded border p-2">
              checked: {checkMeta.total} | triggered: {checkMeta.triggered} | notifications: {checkMeta.notifications}
            </div>
          )}
          {checkRows.map((row) => (
            <div key={row.id} className="rounded border p-2">
              {row.ticker} {row.condition} {row.target_price} | current: {row.current_price ?? 'N/A'} | triggered: {row.triggered ? 'YES' : 'NO'}
            </div>
          ))}
        </CardContent>
      </Card>

      {error && (
        <Card>
          <CardContent className="pt-6 text-red-500">{error}</CardContent>
        </Card>
      )}
    </div>
  )
}
