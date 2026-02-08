'use client'

import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import type { ConfidencePoint } from '@/types/charts'
import { formatPercent } from '@/lib/utils'

interface ConfidenceTrendChartProps {
  data: ConfidencePoint[]
  height?: number
}

export function ConfidenceTrendChart({ data, height = 260 }: ConfidenceTrendChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-[260px] items-center justify-center rounded-md border border-dashed">
        <p className="text-sm text-muted-foreground">Нет данных для тренда уверенности</p>
      </div>
    )
  }

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          <YAxis domain={[0, 1]} tickFormatter={(value) => formatPercent(value, 0)} />
          <Tooltip
            formatter={(value: number) => formatPercent(value)}
            labelStyle={{ color: '#0f172a' }}
          />
          <Line
            type="monotone"
            dataKey="confidence"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
