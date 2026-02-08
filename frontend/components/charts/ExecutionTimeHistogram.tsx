'use client'

import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from 'recharts'
import type { ExecutionTimePoint } from '@/types/charts'

interface ExecutionTimeHistogramProps {
  data: ExecutionTimePoint[]
  height?: number
}

// Color gradient based on bucket (faster = green, slower = orange/red)
function getBucketColor(index: number, total: number): string {
  const ratio = index / (total - 1)
  if (ratio < 0.33) return '#22c55e' // Green - fast
  if (ratio < 0.66) return '#f59e0b' // Amber - medium
  return '#ef4444' // Red - slow
}

export function ExecutionTimeHistogram({ data, height = 280 }: ExecutionTimeHistogramProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-md border border-dashed">
        <p className="text-sm text-muted-foreground">Нет данных по времени выполнения</p>
      </div>
    )
  }

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 10, right: 20, left: 0, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
          <XAxis
            dataKey="bucket"
            tick={{ fontSize: 11 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            label={{ value: 'Count', angle: -90, position: 'insideLeft', fontSize: 12 }}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value: number) => [`${value} facts`, 'Count']}
            labelStyle={{ color: '#0f172a', fontWeight: 600 }}
            contentStyle={{
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
            }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={getBucketColor(index, data.length)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
