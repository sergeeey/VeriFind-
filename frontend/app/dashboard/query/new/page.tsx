'use client'

import { QueryBuilder } from '@/components/query/QueryBuilder'

export default function NewQueryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">New Analysis Query</h1>
        <p className="text-muted-foreground">
          Ask APE 2026 to analyze financial data with zero hallucination guarantee
        </p>
      </div>
      <QueryBuilder />
    </div>
  )
}
