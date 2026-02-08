// Results Types for APE 2026 Frontend

import type { VerifiedFact, DebateReport, Synthesis } from '@/lib/api'

export interface Episode {
  episode_id: string
  query_text: string
  state: string
  verified_facts: VerifiedFact[]
  debate_reports?: DebateReport[]
  synthesis?: Synthesis
  created_at: string
  completed_at?: string
  duration_ms?: number
}

export interface FactsTableRow {
  fact_id: string
  extracted_values: Record<string, number>
  code_hash: string
  execution_time_ms: number
  memory_used_mb: number
  confidence_score: number
  created_at: string
  source_code?: string
}

export interface DebateArgument {
  claim: string
  evidence: string[]
  strength: 'strong' | 'moderate' | 'weak'
}

export interface DebatePerspective {
  perspective: 'bull' | 'bear' | 'neutral'
  arguments: DebateArgument[]
  verdict: string
}

export interface SynthesisData {
  verdict: string
  confidence: number
  risks: string[]
  opportunities: string[]
}

export type ExportFormat = 'json' | 'csv'

export interface ExportOptions {
  format: ExportFormat
  includeCode: boolean
  includeDebate: boolean
}

export type SortDirection = 'asc' | 'desc'

export interface TableSortConfig {
  key: keyof FactsTableRow
  direction: SortDirection
}

export interface PaginationConfig {
  page: number
  pageSize: number
  total: number
}
