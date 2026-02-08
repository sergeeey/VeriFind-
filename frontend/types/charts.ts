// Chart Types for APE 2026 Frontend

export type TimeRange = '1D' | '1W' | '1M' | '3M' | '1Y' | 'ALL'

export interface CandlestickPoint {
  time: number // UNIX timestamp in seconds
  open: number
  high: number
  low: number
  close: number
}

export interface ChartMarker {
  time: number // UNIX timestamp in seconds
  position: 'aboveBar' | 'belowBar' | 'inBar'
  color: string
  shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown'
  text?: string
}

export interface ConfidencePoint {
  time: string
  confidence: number
}

export interface ExecutionTimePoint {
  bucket: string
  count: number
}

export interface TimelinePoint {
  date: string
  count: number
}

export interface DebateSlice {
  name: string
  value: number
  fill: string
}

// Component Props Types
export interface TimeRangeSelectorProps {
  selected: TimeRange
  onChange: (range: TimeRange) => void
  className?: string
}

export interface ChartContainerProps {
  title: string
  description?: string
  children: React.ReactNode
  className?: string
  actions?: React.ReactNode
}

export interface CandlestickChartProps {
  data: CandlestickPoint[]
  markers?: ChartMarker[]
  height?: number
  className?: string
}

export interface ConfidenceTrendChartProps {
  data: ConfidencePoint[]
  height?: number
  showMovingAverage?: boolean
  className?: string
}

export interface DebateDistributionChartProps {
  data: DebateSlice[]
  height?: number
  className?: string
}

export interface ExecutionTimeHistogramProps {
  data: ExecutionTimePoint[]
  height?: number
  className?: string
}

export interface FactTimelineChartProps {
  data: TimelinePoint[]
  height?: number
  markers?: ChartMarker[]
  className?: string
}
