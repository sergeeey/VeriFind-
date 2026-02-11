'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { QueryStatus } from '@/components/query/QueryStatus'
import { QueryHistory } from '@/components/query/QueryHistory'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { Skeleton } from '@/components/ui/skeleton'
import { useWebSocket } from '@/components/providers/WebSocketProvider'
import { api } from '@/lib/api'
import { QUERY_STATES } from '@/lib/constants'
import type { QueryStatus as QueryStatusType } from '@/types/query'
import { normalizeQueryStatusPayload } from '@/lib/query-status'
import { CheckCircle2, ExternalLink } from 'lucide-react'

export default function QueryStatusPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const { subscribe, connected } = useWebSocket()

  const queryId = params?.id as string

  const [status, setStatus] = useState<QueryStatusType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch initial status
  useEffect(() => {
    if (!queryId) return

    const fetchStatus = async () => {
      try {
        const response = await api.getStatus(queryId)
        setStatus(normalizeQueryStatusPayload(response.data, queryId))
        setError(null)
      } catch (err: any) {
        console.error('Failed to fetch status:', err)
        setError(err.response?.data?.message || 'Failed to load query status')
        toast({
          title: 'Error',
          description: 'Failed to load query status',
          variant: 'destructive',
        })
      } finally {
        setLoading(false)
      }
    }

    fetchStatus()
  }, [queryId, toast])

  // Subscribe to WebSocket updates
  useEffect(() => {
    if (!queryId) return

    console.log(`[QueryStatusPage] Subscribing to updates for ${queryId}`)

    const unsubscribe = subscribe(queryId, (data) => {
      console.log(`[QueryStatusPage] Received update:`, data)
      setStatus((prev) => ({
        ...normalizeQueryStatusPayload(prev || {}, queryId),
        ...normalizeQueryStatusPayload(data || {}, queryId),
      }))
    })

    return unsubscribe
  }, [queryId, subscribe])

  // Polling fallback when WebSocket is not connected
  useEffect(() => {
    if (!queryId || connected) return

    console.log('[QueryStatusPage] WebSocket not connected, using polling fallback')

    const interval = setInterval(async () => {
      try {
        const response = await api.getStatus(queryId)
        setStatus(normalizeQueryStatusPayload(response.data, queryId))
      } catch (err) {
        console.error('Polling failed:', err)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [queryId, connected])

  const handleViewResults = () => {
    if (status?.episode_id) {
      router.push(`/dashboard/results/${status.episode_id}`)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-64" />
          <Skeleton className="mt-2 h-4 w-96" />
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Skeleton className="h-96" />
          </div>
          <div>
            <Skeleton className="h-64" />
          </div>
        </div>
      </div>
    )
  }

  if (error || !status) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Error</CardTitle>
            <CardDescription>{error || 'Query not found'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push('/dashboard/query/new')}>Submit New Query</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Query Status</h1>
          <p className="text-muted-foreground">Real-time execution tracking</p>
        </div>
        {!connected && (
          <div className="text-sm text-muted-foreground">
            WebSocket disconnected - using polling
          </div>
        )}
      </div>

      {/* Results Ready Card */}
      {status.state === QUERY_STATES.COMPLETED && status.episode_id && (
        <Card className="border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-700 dark:text-green-300">
              <CheckCircle2 className="h-5 w-5" />
              Results Ready
            </CardTitle>
            <CardDescription className="text-green-600 dark:text-green-400">
              Your analysis is complete and ready to view
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleViewResults} variant="default">
              <ExternalLink className="mr-2 h-4 w-4" />
              View Results
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Query Status (Main) */}
        <div className="lg:col-span-2">
          <QueryStatus status={status} />
        </div>

        {/* Query History (Sidebar) */}
        <div>
          <QueryHistory />
        </div>
      </div>
    </div>
  )
}
