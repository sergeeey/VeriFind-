'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { AlertCircle, TrendingUp, Target, AlertTriangle, BarChart3 } from 'lucide-react'
import { CorridorChart } from './CorridorChart'
import { TrackRecordTable } from './TrackRecordTable'
import { formatPercent } from '@/lib/utils'
import type { TrackRecordResponse, TickersResponse } from '@/types/predictions'

const DISCLAIMER = (
  <div className="mt-6 rounded-lg border bg-muted/50 p-4">
    <p className="text-sm text-muted-foreground">
      <strong>Disclaimer:</strong> This analysis is for informational and educational purposes only.
      NOT financial advice. NOT a recommendation to buy or sell securities. Past performance does not
      guarantee future results. Always consult a licensed financial advisor before making investment
      decisions.
    </p>
  </div>
)

export function PredictionDashboard() {
  const [selectedTicker, setSelectedTicker] = useState<string>('')
  const [tickers, setTickers] = useState<string[]>([])
  const [trackRecord, setTrackRecord] = useState<TrackRecordResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch available tickers
  useEffect(() => {
    const fetchTickers = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/predictions/tickers`)

        if (!response.ok) {
          throw new Error('Failed to fetch tickers')
        }

        const json: TickersResponse = await response.json()
        setTickers(json.tickers)

        if (json.tickers.length > 0) {
          setSelectedTicker((prev) => prev || json.tickers[0])
        }
      } catch (err) {
        console.error('Error fetching tickers:', err)
      }
    }

    fetchTickers()
  }, [])

  // Fetch track record
  useEffect(() => {
    const fetchTrackRecord = async () => {
      try {
        setLoading(true)
        setError(null)

        const url = selectedTicker
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/predictions/track-record?ticker=${selectedTicker}`
          : `${process.env.NEXT_PUBLIC_API_URL}/api/predictions/track-record`

        const response = await fetch(url)

        if (!response.ok) {
          throw new Error('Failed to fetch track record')
        }

        const json: TrackRecordResponse = await response.json()
        setTrackRecord(json)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    if (selectedTicker) {
      fetchTrackRecord()
    }
  }, [selectedTicker])

  const StatCard = ({
    title,
    value,
    icon: Icon,
    trend,
    color = 'text-foreground',
  }: {
    title: string
    value: string | number
    icon: any
    trend?: string
    color?: string
  }) => (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className={`h-4 w-4 ${color}`} />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${color}`}>{value}</div>
        {trend && <p className="text-xs text-muted-foreground">{trend}</p>}
      </CardContent>
    </Card>
  )

  if (error) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center gap-2 rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
          <AlertCircle className="h-4 w-4" />
          <p className="text-sm">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Prediction Dashboard</h1>
          <p className="text-muted-foreground">
            Track prediction accuracy and performance metrics
          </p>
        </div>

        {/* Ticker Selector */}
        <Select value={selectedTicker} onValueChange={setSelectedTicker}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Select ticker..." />
          </SelectTrigger>
          <SelectContent>
            {tickers?.length === 0 ? (
              <SelectItem value="loading" disabled>
                Loading tickers...
              </SelectItem>
            ) : (
              tickers?.map((ticker) => (
                <SelectItem key={ticker} value={ticker}>
                  {ticker}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
      </div>

      {/* Summary Cards */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : trackRecord ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <StatCard
            title="Total Predictions"
            value={trackRecord.track_record.total_predictions}
            icon={BarChart3}
            trend={`${trackRecord.track_record.completed_predictions} completed, ${trackRecord.track_record.pending_predictions} pending`}
          />
          <StatCard
            title="HIT Rate"
            value={formatPercent(trackRecord.track_record.hit_rate, 1)}
            icon={Target}
            color="text-green-600"
            trend="Within price corridor"
          />
          <StatCard
            title="NEAR Rate"
            value={formatPercent(trackRecord.track_record.near_rate, 1)}
            icon={TrendingUp}
            color="text-yellow-600"
            trend="Close to corridor (±5%)"
          />
          <StatCard
            title="MISS Rate"
            value={formatPercent(trackRecord.track_record.miss_rate, 1)}
            icon={AlertTriangle}
            color="text-red-600"
            trend="Outside corridor (>5%)"
          />
          <StatCard
            title="Avg Error"
            value={`${trackRecord.track_record.avg_error_pct.toFixed(2)}%`}
            icon={BarChart3}
            trend={`Median: ${trackRecord.track_record.median_error_pct.toFixed(2)}%`}
          />
        </div>
      ) : null}

      {/* Corridor Chart */}
      {selectedTicker && <CorridorChart ticker={selectedTicker} limit={10} />}

      {/* Track Record Table */}
      <TrackRecordTable ticker={selectedTicker} />

      {/* Disclaimer */}
      {DISCLAIMER}
    </div>
  )
}
