'use client'

import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { ChartContainer } from '@/components/charts/ChartContainer'
import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent } from '@/components/ui/card'
import { AlertCircle } from 'lucide-react'
import type { CorridorData, CorridorResponse } from '@/types/predictions'

interface CorridorChartProps {
  ticker: string
  limit?: number
}

interface ChartDataPoint {
  date: string
  price_low: number
  price_high: number
  price_base: number
  actual_price?: number
  is_hit?: boolean
}

export function CorridorChart({ ticker, limit = 10 }: CorridorChartProps) {
  const [data, setData] = useState<ChartDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/predictions/${ticker}/corridor?limit=${limit}`
        )

        if (!response.ok) {
          throw new Error(`Failed to fetch corridor data: ${response.statusText}`)
        }

        const json: CorridorResponse = await response.json()

        // Transform data for Recharts
        const chartData: ChartDataPoint[] = json.corridor_data.map((item: CorridorData) => ({
          date: new Date(item.target_date).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
          }),
          price_low: item.price_low,
          price_high: item.price_high,
          price_base: item.price_base,
          actual_price: item.actual_price,
          is_hit: item.is_hit,
        }))

        // Reverse to show oldest first (left to right)
        setData(chartData.reverse())
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    if (ticker) {
      fetchData()
    }
  }, [ticker, limit])

  if (loading) {
    return (
      <ChartContainer title="Price Corridor" description="Predicted vs actual price ranges">
        <Skeleton className="h-[400px] w-full" />
      </ChartContainer>
    )
  }

  if (error) {
    return (
      <ChartContainer title="Price Corridor" description="Predicted vs actual price ranges">
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-4 w-4" />
              <p className="text-sm">{error}</p>
            </div>
          </CardContent>
        </Card>
      </ChartContainer>
    )
  }

  if (data.length === 0) {
    return (
      <ChartContainer title="Price Corridor" description="Predicted vs actual price ranges">
        <div className="flex h-[400px] items-center justify-center text-muted-foreground">
          No prediction data available for {ticker}
        </div>
      </ChartContainer>
    )
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null

    const data = payload[0].payload
    const isEvaluated = data.actual_price !== undefined

    return (
      <div className="rounded-lg border bg-background p-3 shadow-md">
        <p className="mb-2 font-semibold">{data.date}</p>
        <div className="space-y-1 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">High:</span>
            <span className="font-mono">${data.price_high.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Base:</span>
            <span className="font-mono">${data.price_base.toFixed(2)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Low:</span>
            <span className="font-mono">${data.price_low.toFixed(2)}</span>
          </div>
          {isEvaluated && (
            <>
              <div className="my-1 border-t" />
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Actual:</span>
                <span
                  className={`font-mono font-semibold ${
                    data.is_hit
                      ? 'text-green-600'
                      : data.actual_price >= data.price_low * 0.95 &&
                        data.actual_price <= data.price_high * 1.05
                      ? 'text-yellow-600'
                      : 'text-red-600'
                  }`}
                >
                  ${data.actual_price.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Status:</span>
                <span
                  className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
                    data.is_hit
                      ? 'bg-green-100 text-green-800'
                      : data.actual_price >= data.price_low * 0.95 &&
                        data.actual_price <= data.price_high * 1.05
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {data.is_hit
                    ? 'HIT'
                    : data.actual_price >= data.price_low * 0.95 &&
                      data.actual_price <= data.price_high * 1.05
                    ? 'NEAR'
                    : 'MISS'}
                </span>
              </div>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <ChartContainer
      title="Price Corridor"
      description={`Prediction corridors vs actual prices for ${ticker}`}
    >
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="corridorGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickLine={{ stroke: '#888' }}
            className="text-muted-foreground"
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickLine={{ stroke: '#888' }}
            tickFormatter={(value) => `$${value}`}
            className="text-muted-foreground"
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '14px', paddingTop: '10px' }} />

          {/* Price corridor (shaded area) */}
          <Area
            type="monotone"
            dataKey="price_high"
            stroke="#3b82f6"
            fill="url(#corridorGradient)"
            name="Upper Bound"
          />
          <Area
            type="monotone"
            dataKey="price_low"
            stroke="#3b82f6"
            fill="url(#corridorGradient)"
            name="Lower Bound"
          />

          {/* Base prediction line */}
          <ReferenceLine
            y={data.length > 0 ? data[0].price_base : 0}
            stroke="#6366f1"
            strokeDasharray="5 5"
            label={{ value: 'Base', position: 'right', fill: '#6366f1' }}
          />

          {/* Actual price line (if available) */}
          {data.some((d) => d.actual_price !== undefined) && (
            <Area
              type="monotone"
              dataKey="actual_price"
              stroke="#10b981"
              strokeWidth={2}
              fill="none"
              name="Actual Price"
              connectNulls
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </ChartContainer>
  )
}
