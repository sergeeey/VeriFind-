'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type ActivityRow = {
  query_id: string
  query_text?: string | null
  state: string
  updated_at: string
  metadata?: Record<string, unknown>
}

export function RecentActivityPanel() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [rows, setRows] = useState<ActivityRow[]>([])

  useEffect(() => {
    const load = async () => {
      try {
        const response = await fetch(`${apiBase}/api/status?limit=3`)
        if (!response.ok) return
        const json = (await response.json()) as ActivityRow[]
        setRows(json || [])
      } catch {
        // best-effort panel; keep silent
      }
    }
    load()
  }, [apiBase])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Your latest analysis queries</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {rows.length === 0 && <div className="rounded border p-3 text-sm">No recent activity</div>}
          {rows.map((row) => {
            const episodeId = String((row.metadata?.episode_id as string | undefined) || '')
            const target = row.state === 'completed' && episodeId
              ? `/dashboard/results/${episodeId}`
              : `/dashboard/query/${row.query_id}`
            return (
              <div key={row.query_id} className="flex items-center justify-between p-3 rounded-lg border">
                <div>
                  <p className="font-medium">{row.query_text || row.query_id}</p>
                  <p className="text-sm text-muted-foreground">{row.updated_at} • {row.state}</p>
                </div>
                <Button asChild variant="outline" size="sm">
                  <Link href={target}>View</Link>
                </Button>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
