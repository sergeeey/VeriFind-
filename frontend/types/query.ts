// Query Types for APE 2026 Frontend

export type QueryState =
  | 'pending'
  | 'planning'
  | 'fetching'
  | 'executing'
  | 'validating'
  | 'debating'
  | 'completed'
  | 'failed'

export interface QueryStatus {
  query_id: string
  state: QueryState
  query_text: string
  current_node?: string
  progress: number
  error?: string
  episode_id?: string
  created_at: string
  updated_at: string
}

export interface QuerySubmitResponse {
  query_id: string
  status: string
  message: string
}

export interface QueryHistoryItem {
  id: string
  text: string
  time: string
  status: QueryState
}

export interface WebSocketMessage {
  type: 'query_update' | 'query_complete' | 'query_error' | 'status' | 'complete' | 'error' | 'subscribed' | 'unsubscribed' | 'pong'
  query_id?: string
  data?: Partial<QueryStatus>
  status?: string
  progress?: number
  current_step?: string
  error?: string
  result_summary?: Record<string, unknown>
}

export interface PipelineStep {
  key: string
  label: string
  description: string
  status: 'pending' | 'active' | 'completed' | 'failed'
}
