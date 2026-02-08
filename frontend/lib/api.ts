import axios, { AxiosInstance } from 'axios'

const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor - add API key
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const apiKey = localStorage.getItem('api_key')
      if (apiKey) {
        config.headers['X-API-Key'] = apiKey
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login on 401
      if (typeof window !== 'undefined') {
        localStorage.removeItem('api_key')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient

// API methods
export const api = {
  // Health check
  health: () => apiClient.get('/health'),

  // Query endpoints
  submitQuery: (query: string, priority?: string) =>
    apiClient.post('/query', { query, priority }),

  getStatus: (queryId: string) => apiClient.get(`/status/${queryId}`),

  // Episode endpoints
  getEpisode: (episodeId: string) => apiClient.get(`/episodes/${episodeId}`),

  // Facts endpoints
  getFacts: (params?: {
    page?: number
    limit?: number
    episode_id?: string
    ticker?: string
  }) => apiClient.get('/facts', { params }),

  // Stats
  getStats: () => apiClient.get('/stats'),
}

// Types for API responses
export interface QueryResponse {
  query_id: string
  status: string
  message: string
}

export interface QueryStatus {
  query_id: string
  state: 'pending' | 'planning' | 'fetching' | 'executing' | 'validating' | 'completed' | 'failed'
  query_text: string
  current_node?: string
  progress: number
  error?: string
  episode_id?: string
  created_at: string
  updated_at: string
}

export interface VerifiedFact {
  fact_id: string
  query_id: string
  extracted_values: Record<string, number>
  code_hash: string
  execution_time_ms: number
  memory_used_mb: number
  created_at: string
  confidence_score?: number
  source_code?: string
}

export interface Episode {
  episode_id: string
  query_text: string
  state: string
  verified_facts: VerifiedFact[]
  debate_reports?: DebateReport[]
  synthesis?: Synthesis
  created_at: string
  completed_at?: string
}

export interface DebateReport {
  perspective: 'bull' | 'bear' | 'neutral'
  arguments: Argument[]
  verdict: string
}

export interface Argument {
  claim: string
  evidence: string[]
  strength: 'strong' | 'moderate' | 'weak'
}

export interface Synthesis {
  verdict: string
  confidence: number
  risks: string[]
  opportunities: string[]
}
