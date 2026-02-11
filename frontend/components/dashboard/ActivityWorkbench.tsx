'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

type StatusRow = {
  query_id: string
  query_text?: string | null
  status: string
  state: string
  progress: number
  updated_at: string
  metadata?: Record<string, unknown>
}

export function ActivityWorkbench() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<StatusRow[]>([])
  const [queryFilter, setQueryFilter] = useState('')
  const [stateFilter, setStateFilter] = useState<'all' | 'pending' | 'completed' | 'failed'>('all')

  const loadActivity = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ limit: '30' })
      if (queryFilter.trim()) params.set('query', queryFilter.trim())
      if (stateFilter !== 'all') params.set('state', stateFilter)
      const response = await fetch(`${apiBase}/api/status?${params.toString()}`)
      if (!response.ok) throw new Error('Failed to load activity')
      const json = (await response.json()) as StatusRow[]
      setRows(json || [])
    } catch {
      setError('Failed to load activity')
    } finally {
      setLoading(false)
    }
  }, [apiBase, queryFilter, stateFilter])

  useEffect(() => {
    loadActivity()
  }, [loadActivity])

  const completedCount = useMemo(() => rows.filter((r) => r.state === 'completed').length, [rows])
  const failedCount = useMemo(() => rows.filter((r) => r.state === 'failed').length, [rows])

  const progressLabel = (value: number) => {
    if (value <= 1) return `${Math.round(value * 100)}%`
    return `${Math.round(value)}%`
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Activity</CardTitle>
          <CardDescription>Recent query pipeline executions and statuses.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2 md:grid-cols-4">
            <Input
              value={queryFilter}
              onChange={(e) => setQueryFilter(e.target.value)}
              placeholder="Filter by query text"
            />
            <Select value={stateFilter} onValueChange={(v: 'all' | 'pending' | 'completed' | 'failed') => setStateFilter(v)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">all</SelectItem>
                <SelectItem value="pending">pending</SelectItem>
                <SelectItem value="completed">completed</SelectItem>
                <SelectItem value="failed">failed</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={loadActivity} variant="outline" disabled={loading}>
              Refresh
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-3 text-sm">
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Total</div>
              <div className="font-semibold">{rows.length}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Completed</div>
              <div className="font-semibold">{completedCount}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-muted-foreground">Failed</div>
              <div className="font-semibold">{failedCount}</div>
            </div>
          </div>

          <div className="space-y-2 text-sm">
            {rows.length === 0 && <div className="rounded border p-3">No activity yet</div>}
            {rows.map((row) => {
              const episodeId = String((row.metadata?.episode_id as string | undefined) || '')
              return (
                <div key={row.query_id} className="rounded border p-3">
                  <div className="font-medium">{row.query_text || row.query_id}</div>
                  <div className="text-muted-foreground">
                    state: {row.state} | progress: {progressLabel(row.progress)} | lang: {String((row.metadata?.detected_language as string | undefined) || 'N/A')} | updated: {row.updated_at}
                  </div>
                  <div className="mt-2 flex gap-2">
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/dashboard/query/${row.query_id}`}>Open Status</Link>
                    </Button>
                    {row.state === 'completed' && episodeId && (
                      <Button asChild size="sm">
                        <Link href={`/dashboard/results/${episodeId}`}>Open Results</Link>
                      </Button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
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
