// Prediction Dashboard Types for APE 2026 Frontend

export interface Prediction {
  id: string
  created_at: string
  ticker: string
  exchange: string
  horizon_days: number
  target_date: string

  // Price corridor
  price_at_creation: number
  price_low: number
  price_base: number
  price_high: number

  // Metadata
  reasoning: Record<string, any>
  verification_score: number
  model_used: string
  pipeline_cost: number

  // Actual results (nullable until target_date)
  actual_price?: number
  actual_date?: string
  accuracy_band?: 'HIT' | 'NEAR' | 'MISS'
  error_pct?: number
  error_direction?: 'OVER' | 'UNDER' | 'EXACT'

  // Calibration
  was_calibrated: boolean
  calibration_adj?: number
}

export interface CorridorData {
  ticker: string
  prediction_date: string
  target_date: string

  price_at_creation: number
  price_low: number
  price_base: number
  price_high: number

  actual_price?: number
  is_hit?: boolean
}

export interface TrackRecord {
  total_predictions: number
  completed_predictions: number
  pending_predictions: number

  // Accuracy metrics
  hit_rate: number
  near_rate: number
  miss_rate: number

  // Error metrics
  avg_error_pct: number
  median_error_pct: number

  // By ticker
  by_ticker: Record<string, TickerStats>

  // Recent predictions
  recent_accuracy: number
}

export interface TickerStats {
  total: number
  completed: number
  hit_rate: number
  avg_error: number
}

export interface LatestPredictionResponse {
  prediction: Prediction | null
  disclaimer: string
}

export interface PredictionHistoryResponse {
  ticker: string
  total: number
  predictions: Prediction[]
  disclaimer: string
}

export interface CorridorResponse {
  ticker: string
  corridor_data: CorridorData[]
  disclaimer: string
}

export interface TrackRecordResponse {
  track_record: TrackRecord
  disclaimer: string
}

export interface TickersResponse {
  tickers: string[]
  total: number
  disclaimer: string
}

export interface CheckActualsResponse {
  total_checked: number
  successful: number
  failed: number
  results: Array<{
    success: boolean
    prediction_id: string
    ticker?: string
    target_date?: string
    actual_price?: number
    accuracy_band?: string
    error_pct?: number
    message: string
  }>
  disclaimer: string
}
