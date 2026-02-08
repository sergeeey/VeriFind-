// API Configuration
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'APE 2026'

// Query States
export const QUERY_STATES = {
  PENDING: 'pending',
  PLANNING: 'planning',
  FETCHING: 'fetching',
  EXECUTING: 'executing',
  VALIDATING: 'validating',
  DEBATING: 'debating',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const

export type QueryState = (typeof QUERY_STATES)[keyof typeof QUERY_STATES]

// Pipeline Steps
export const PIPELINE_STEPS = [
  { key: 'planning', label: 'PLAN', description: 'Generating analysis plan' },
  { key: 'fetching', label: 'FETCH', description: 'Fetching market data' },
  { key: 'executing', label: 'VEE', description: 'Running code in sandbox' },
  { key: 'validating', label: 'GATE', description: 'Validating results' },
  { key: 'debating', label: 'DEBATE', description: 'Multi-perspective analysis' },
  { key: 'completed', label: 'DONE', description: 'Analysis complete' },
] as const

// Debate Perspectives
export const PERSPECTIVES = {
  BULL: 'bull',
  BEAR: 'bear',
  NEUTRAL: 'neutral',
} as const

export type Perspective = (typeof PERSPECTIVES)[keyof typeof PERSPECTIVES]

// Confidence Thresholds
export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.8,
  MEDIUM: 0.6,
  LOW: 0.4,
} as const

// Pagination
export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

// Example Queries
export const EXAMPLE_QUERIES = [
  {
    label: 'Moving Average',
    query: 'Calculate the 50-day moving average for AAPL over the last 6 months',
    category: 'simple',
  },
  {
    label: 'Correlation',
    query: 'What is the correlation between SPY and QQQ over the past year?',
    category: 'simple',
  },
  {
    label: 'Volatility',
    query: 'Compare the 30-day volatility of TSLA vs the S&P 500',
    category: 'advanced',
  },
  {
    label: 'Sharpe Ratio',
    query: 'Calculate the Sharpe ratio for MSFT over the last 3 years',
    category: 'advanced',
  },
  {
    label: 'Beta Analysis',
    query: 'What is the beta of NVDA relative to SPY over 2023-2024?',
    category: 'advanced',
  },
  {
    label: 'Drawdown',
    query: 'What was the maximum drawdown for AAPL in 2022?',
    category: 'advanced',
  },
] as const

// Chart Colors
export const CHART_COLORS = {
  primary: 'hsl(221.2 83.2% 53.3%)',
  success: 'hsl(142.1 76.2% 36.3%)',
  warning: 'hsl(38 92% 50%)',
  danger: 'hsl(0 84.2% 60.2%)',
  info: 'hsl(199 89% 48%)',
  muted: 'hsl(215 20.2% 65.1%)',
} as const
