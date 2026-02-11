'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type UsageConsumer = {
  consumer: string
  requests_current_window: number
  requests_total: number
  last_seen: string | null
}

type UsageSnapshot = {
  enforcement_enabled: boolean
  window_hours: number
  default_limit: number
  active_consumers: number
  consumers: UsageConsumer[]
}

type BreakerStats = {
  name: string
  state: string
  failure_count: number
  success_count?: number
  total_calls: number
  total_failures?: number
  total_successes?: number
  failure_rate: number
  time_until_retry?: number
}

type BreakerHealth = {
  initialized: boolean
  provider: string | null
  message?: string
  breakers: Record<string, BreakerStats>
}

const initialSnapshot: UsageSnapshot = {
  enforcement_enabled: false,
  window_hours: 1,
  default_limit: 0,
  active_consumers: 0,
  consumers: [],
}

export function UsageWorkbench() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<UsageSnapshot>(initialSnapshot)
  const [breakerHealth, setBreakerHealth] = useState<BreakerHealth>({
    initialized: false,
    provider: null,
    breakers: {},
  })

  const loadUsage = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/api/usage/summary`)
      if (!response.ok) throw new Error('Failed to load usage summary')
      const json = await response.json()
      setSnapshot(json.usage || initialSnapshot)

      const breakerResponse = await fetch(`${apiBase}/api/health/circuit-breakers`)
      if (breakerResponse.ok) {
        const breakerJson = await breakerResponse.json()
        setBreakerHealth({
          initialized: Boolean(breakerJson.initialized),
          provider: breakerJson.provider || null,
          message: breakerJson.message,
          breakers: breakerJson.breakers || {},
        })
      }
    } catch {
      setError('Failed to load usage summary')
    } finally {
      setLoading(false)
    }
  }, [apiBase])

  useEffect(() => {
    loadUsage()
  }, [loadUsage])

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>API Usage Dashboard</CardTitle>
          <CardDescription>
            Rate-limit usage, active consumers and enforcement status.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button onClick={loadUsage} variant="outline" disabled={loading}>Refresh</Button>
          </div>

          <div className="grid gap-3 md:grid-cols-4 text-sm">
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Enforcement</div>
              <div className="font-semibold">{snapshot.enforcement_enabled ? 'ON' : 'OFF'}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Window (hours)</div>
              <div className="font-semibold">{snapshot.window_hours}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Default Limit</div>
              <div className="font-semibold">{snapshot.default_limit}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Active Consumers</div>
              <div className="font-semibold">{snapshot.active_consumers}</div>
            </div>
          </div>

          <div className="space-y-2 text-sm">
            {snapshot.consumers.length === 0 && (
              <div className="rounded border p-3">No usage records</div>
            )}
            {snapshot.consumers.map((row) => (
              <div key={row.consumer} className="rounded border p-3">
                <div className="font-medium">{row.consumer}</div>
                <div className="text-muted-foreground">
                  window: {row.requests_current_window} | total: {row.requests_total} | last seen: {row.last_seen || 'N/A'}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Circuit Breakers</CardTitle>
          <CardDescription>
            Runtime breaker state for market data and debate dependencies.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {!breakerHealth.initialized && (
            <div className="rounded border p-3">
              {breakerHealth.message || 'Orchestrator not initialized'}
            </div>
          )}
          {breakerHealth.initialized && Object.keys(breakerHealth.breakers).length === 0 && (
            <div className="rounded border p-3">No breaker stats available</div>
          )}
          {Object.entries(breakerHealth.breakers).map(([key, stats]) => (
            <div key={key} className="rounded border p-3">
              <div className="font-medium">
                {stats.name} ({breakerHealth.provider || 'unknown'})
              </div>
              <div className="text-muted-foreground">
                state: {stats.state} | calls: {stats.total_calls} | failures: {stats.failure_count} | failure rate: {(stats.failure_rate * 100).toFixed(1)}%
              </div>
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
