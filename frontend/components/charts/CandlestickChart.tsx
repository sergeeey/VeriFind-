'use client'

import { useEffect, useRef } from 'react'
import { createChart, type IChartApi, type CandlestickData, type SeriesMarker, type UTCTimestamp } from 'lightweight-charts'
import type { CandlestickPoint, ChartMarker } from '@/types/charts'

interface CandlestickChartProps {
  data: CandlestickPoint[]
  markers?: ChartMarker[]
  height?: number
}

function toCandlestickData(points: CandlestickPoint[]): CandlestickData[] {
  return points.map((point) => ({
    time: point.time as UTCTimestamp,
    open: point.open,
    high: point.high,
    low: point.low,
    close: point.close,
  }))
}

function toMarkers(markers: ChartMarker[]): SeriesMarker<UTCTimestamp>[] {
  return markers.map((marker) => ({
    time: marker.time as UTCTimestamp,
    position: marker.position,
    color: marker.color,
    shape: marker.shape,
    text: marker.text,
  }))
}

export function CandlestickChart({ data, markers = [], height = 320 }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(148,163,184,0.1)' },
        horzLines: { color: 'rgba(148,163,184,0.1)' },
      },
      rightPriceScale: {
        borderColor: 'rgba(148,163,184,0.3)',
      },
      timeScale: {
        borderColor: 'rgba(148,163,184,0.3)',
      },
    })

    const series = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      borderVisible: false,
    })

    series.setData(toCandlestickData(data))
    if (markers.length > 0) {
      series.setMarkers(toMarkers(markers))
    }

    chartRef.current = chart

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width })
      }
    })

    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
    }
  }, [data, markers, height])

  if (data.length === 0) {
    return (
      <div className="flex h-[320px] items-center justify-center rounded-md border border-dashed">
        <p className="text-sm text-muted-foreground">Нет данных OHLC для свечного графика</p>
      </div>
    )
  }

  return <div ref={containerRef} className="w-full" />
}
