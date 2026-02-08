'use client'

import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts'
import type { DebateSlice } from '@/types/charts'

const COLORS = ['#22c55e', '#f97316', '#0ea5e9']

interface DebateDistributionChartProps {
  data: DebateSlice[]
  height?: number
}

export function DebateDistributionChart({ data, height = 260 }: DebateDistributionChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-[260px] items-center justify-center rounded-md border border-dashed">
        <p className="text-sm text-muted-foreground">Нет данных по дебатам</p>
      </div>
    )
  }

  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={45}
            outerRadius={80}
            paddingAngle={4}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend verticalAlign="bottom" height={36} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
