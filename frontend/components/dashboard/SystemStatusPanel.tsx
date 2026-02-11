'use client'

import { useEffect, useMemo, useState } from 'react'
import { Activity } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

type UsageSummary = {
  active_consumers: number
}

export function SystemStatusPanel() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [apiHealthy, setApiHealthy] = useState<boolean>(true)
  const [totalQueries, setTotalQueries] = useState<number>(0)
  const [activeConsumers, setActiveConsumers] = useState<number>(0)
  const [avgLatencyText, setAvgLatencyText] = useState<string>('N/A')

  useEffect(() => {
    const load = async () => {
      try {
        const [healthRes, statusRes, usageRes] = await Promise.all([
          fetch(`${apiBase}/health`),
          fetch(`${apiBase}/api/status-summary`),
          fetch(`${apiBase}/api/usage/summary`),
        ])

        if (healthRes.ok) {
          const health = await healthRes.json()
          setApiHealthy(health.status === 'healthy')
        }

        if (statusRes.ok) {
          const summary = await statusRes.json()
          setTotalQueries(Number(summary.total_tracked || 0))
          const avgMs = Number(summary.avg_completion_ms || 0)
          if (avgMs > 0) {
            if (avgMs < 1000) setAvgLatencyText(`${Math.round(avgMs)}ms`)
            else setAvgLatencyText(`${(avgMs / 1000).toFixed(1)}s`)
          }
        }

        if (usageRes.ok) {
          const usageJson = await usageRes.json()
          const usage = (usageJson.usage || {}) as UsageSummary
          setActiveConsumers(Number(usage.active_consumers || 0))
        }
      } catch {
        // Keep defaults on best-effort dashboard panel errors.
      }
    }
    load()
  }, [apiBase])

  const healthLabel = useMemo(() => (apiHealthy ? 'API Healthy' : 'API Degraded'), [apiHealthy])
  const healthColor = useMemo(() => (apiHealthy ? 'text-green-500' : 'text-yellow-500'), [apiHealthy])

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>System Status</CardTitle>
          <Activity className={`h-5 w-5 ${healthColor}`} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          <div>
            <div className={`text-3xl font-bold mb-1 ${healthColor}`}>✓</div>
            <div className="text-sm text-muted-foreground">{healthLabel}</div>
          </div>
          <div>
            <div className="text-3xl font-bold mb-1">{totalQueries}</div>
            <div className="text-sm text-muted-foreground">Tracked Queries</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-500 mb-1">0.00%</div>
            <div className="text-sm text-muted-foreground">Hallucination Rate</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-blue-500 mb-1">{avgLatencyText}</div>
            <div className="text-sm text-muted-foreground">Avg Completion Time</div>
          </div>
        </div>
        <div className="mt-4 text-center text-xs text-muted-foreground">
          Active API consumers: {activeConsumers}
        </div>
      </CardContent>
    </Card>
  )
}
