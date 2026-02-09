'use client'

import { useEffect, useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { AlertCircle, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { formatDate } from '@/lib/utils'
import type { Prediction, PredictionHistoryResponse } from '@/types/predictions'

interface TrackRecordTableProps {
  ticker?: string
}

type SortKey = 'created_at' | 'target_date' | 'error_pct' | 'accuracy_band'
type SortDirection = 'asc' | 'desc'

interface SortConfig {
  key: SortKey
  direction: SortDirection
}

export function TrackRecordTable({ ticker }: TrackRecordTableProps) {
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: 'created_at',
    direction: 'desc',
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)

        let url = `${process.env.NEXT_PUBLIC_API_URL}/api/predictions`

        if (ticker) {
          url += `/${ticker}/history?limit=50&include_pending=false`
        } else {
          // Fetch all completed predictions from multiple tickers
          // For now, we'll fetch AAPL as default
          url += `/AAPL/history?limit=50&include_pending=false`
        }

        const response = await fetch(url)

        if (!response.ok) {
          throw new Error(`Failed to fetch predictions: ${response.statusText}`)
        }

        const json: PredictionHistoryResponse = await response.json()
        setPredictions(json.predictions.filter((p) => p.actual_price !== undefined))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [ticker])

  const handleSort = (key: SortKey) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }

  const getSortIcon = (key: SortKey) => {
    if (sortConfig.key !== key) {
      return <ArrowUpDown className="ml-2 h-4 w-4" />
    }
    return sortConfig.direction === 'asc' ? (
      <ArrowUp className="ml-2 h-4 w-4" />
    ) : (
      <ArrowDown className="ml-2 h-4 w-4" />
    )
  }

  const sortedPredictions = [...predictions].sort((a, b) => {
    const { key, direction } = sortConfig
    let aValue: any
    let bValue: any

    switch (key) {
      case 'created_at':
        aValue = new Date(a.created_at).getTime()
        bValue = new Date(b.created_at).getTime()
        break
      case 'target_date':
        aValue = new Date(a.target_date).getTime()
        bValue = new Date(b.target_date).getTime()
        break
      case 'error_pct':
        aValue = Math.abs(a.error_pct ?? 0)
        bValue = Math.abs(b.error_pct ?? 0)
        break
      case 'accuracy_band':
        const bandOrder = { HIT: 0, NEAR: 1, MISS: 2 }
        aValue = bandOrder[a.accuracy_band ?? 'MISS']
        bValue = bandOrder[b.accuracy_band ?? 'MISS']
        break
      default:
        return 0
    }

    if (direction === 'asc') {
      return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
    } else {
      return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
    }
  })

  const getAccuracyBadge = (band?: 'HIT' | 'NEAR' | 'MISS') => {
    if (!band) return null

    const variants = {
      HIT: 'bg-green-100 text-green-800 border-green-200',
      NEAR: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      MISS: 'bg-red-100 text-red-800 border-red-200',
    }

    return (
      <Badge className={`${variants[band]} border font-semibold`} variant="outline">
        {band}
      </Badge>
    )
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Track Record</CardTitle>
          <CardDescription>Loading prediction history...</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[400px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Track Record</CardTitle>
          <CardDescription>Prediction accuracy history</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 rounded-lg border border-destructive bg-destructive/10 p-4 text-destructive">
            <AlertCircle className="h-4 w-4" />
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (predictions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Track Record</CardTitle>
          <CardDescription>No completed predictions available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            No completed predictions found
            {ticker && ` for ${ticker}`}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Track Record ({predictions.length})</CardTitle>
        <CardDescription>
          Prediction accuracy history {ticker ? `for ${ticker}` : 'across all tickers'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('created_at')}
                    className="h-8 p-0 hover:bg-transparent"
                  >
                    Date
                    {getSortIcon('created_at')}
                  </Button>
                </TableHead>
                <TableHead>Ticker</TableHead>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('target_date')}
                    className="h-8 p-0 hover:bg-transparent"
                  >
                    Target Date
                    {getSortIcon('target_date')}
                  </Button>
                </TableHead>
                <TableHead>Predicted Range</TableHead>
                <TableHead>Actual</TableHead>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('accuracy_band')}
                    className="h-8 p-0 hover:bg-transparent"
                  >
                    Band
                    {getSortIcon('accuracy_band')}
                  </Button>
                </TableHead>
                <TableHead>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleSort('error_pct')}
                    className="h-8 p-0 hover:bg-transparent"
                  >
                    Error %
                    {getSortIcon('error_pct')}
                  </Button>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedPredictions.map((prediction) => (
                <TableRow key={prediction.id}>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(prediction.created_at)}
                  </TableCell>
                  <TableCell>
                    <span className="font-mono font-semibold">{prediction.ticker}</span>
                  </TableCell>
                  <TableCell className="text-sm">
                    {new Date(prediction.target_date).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </TableCell>
                  <TableCell>
                    <div className="space-y-0.5 text-sm">
                      <div className="font-mono">
                        ${prediction.price_low.toFixed(2)} - ${prediction.price_high.toFixed(2)}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Base: ${prediction.price_base.toFixed(2)}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono font-semibold">
                      ${prediction.actual_price?.toFixed(2) ?? 'N/A'}
                    </span>
                  </TableCell>
                  <TableCell>{getAccuracyBadge(prediction.accuracy_band)}</TableCell>
                  <TableCell>
                    <span
                      className={`font-mono text-sm ${
                        Math.abs(prediction.error_pct ?? 0) < 5
                          ? 'text-green-600'
                          : Math.abs(prediction.error_pct ?? 0) < 10
                          ? 'text-yellow-600'
                          : 'text-red-600'
                      }`}
                    >
                      {prediction.error_pct !== undefined
                        ? `${prediction.error_pct > 0 ? '+' : ''}${prediction.error_pct.toFixed(2)}%`
                        : 'N/A'}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
