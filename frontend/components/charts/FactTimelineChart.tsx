'use client'

import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts'
import type { TimelinePoint } from '@/types/charts'

interface FactTimelineChartProps {
  data: TimelinePoint[]
  height?: number
  markers?: Array<{ time: number; fact_id: string; confidence: number }>
}

export function FactTimelineChart({ data, height = 280, markers = [] }: FactTimelineChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center rounded-md border border-dashed">
        <p className="text-sm text-muted-foreground">Нет данных для timeline фактов</p>
      </div>
    )
  }

  return (
    <div className="h-[280px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 20, left: 0, bottom: 20 }}
        >
          <defs>
            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            label={{ value: 'Verified Facts', angle: -90, position: 'insideLeft', fontSize: 12 }}
            tick={{ fontSize: 12 }}
            allowDecimals={false}
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
          <Legend
            verticalAlign="top"
            height={36}
            iconType="circle"
            wrapperStyle={{ fontSize: '12px' }}
          />
          <Area
            type="monotone"
            dataKey="count"
            name="Verified Facts"
            stroke="#3b82f6"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorCount)"
            animationDuration={800}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Markers for verified facts */}
      {markers.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {markers.slice(0, 5).map((marker, idx) => (
            <div
              key={idx}
              className="flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-700"
              title={`Fact ${marker.fact_id} - Confidence: ${(marker.confidence * 100).toFixed(0)}%`}
            >
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              <span className="font-medium">{new Date(marker.time * 1000).toLocaleDateString()}</span>
            </div>
          ))}
          {markers.length > 5 && (
            <div className="flex items-center px-2 py-1 text-xs text-muted-foreground">
              +{markers.length - 5} more
            </div>
          )}
        </div>
      )}
    </div>
  )
}
