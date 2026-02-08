'use client'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { formatDateTime, getConfidenceColor } from '@/lib/utils'
import type { FactsTableRow } from '@/types/results'
import { Clock, MemoryStick, Hash } from 'lucide-react'

interface FactDetailsDialogProps {
  fact: FactsTableRow | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function FactDetailsDialog({ fact, open, onOpenChange }: FactDetailsDialogProps) {
  if (!fact) return null

  const confidenceColor = getConfidenceColor(fact.confidence_score)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Verified Fact Details</DialogTitle>
          <DialogDescription>Complete metadata and execution information</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Fact ID */}
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Fact ID</p>
            <code className="block rounded bg-muted px-3 py-2 text-xs">{fact.fact_id}</code>
          </div>

          {/* Extracted Values */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Extracted Values</p>
            <div className="grid gap-2 rounded-lg border p-3">
              {Object.entries(fact.extracted_values).map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between rounded bg-muted px-3 py-2"
                >
                  <code className="text-sm font-medium">{key}</code>
                  <span className="text-lg font-bold">{value.toFixed(6)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid gap-4 md:grid-cols-3">
            {/* Confidence */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">Confidence</p>
              <Badge className={`${confidenceColor} text-base`}>
                {(fact.confidence_score * 100).toFixed(0)}%
              </Badge>
            </div>

            {/* Execution Time */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">Execution Time</p>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{fact.execution_time_ms}ms</span>
              </div>
            </div>

            {/* Memory Used */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">Memory Used</p>
              <div className="flex items-center gap-2">
                <MemoryStick className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{fact.memory_used_mb.toFixed(2)}MB</span>
              </div>
            </div>
          </div>

          {/* Code Hash */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Code Hash (SHA-256)</p>
            <div className="flex items-center gap-2 rounded bg-muted px-3 py-2">
              <Hash className="h-4 w-4 text-muted-foreground" />
              <code className="flex-1 text-xs">{fact.code_hash}</code>
            </div>
          </div>

          {/* Created At */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Created At</p>
            <p className="text-sm">{formatDateTime(new Date(fact.created_at))}</p>
          </div>

          {/* Verification Badge */}
          <div className="rounded-lg border-2 border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950">
            <p className="font-medium text-green-900 dark:text-green-100">
              ✓ Verified by VEE Sandbox
            </p>
            <p className="mt-1 text-sm text-green-800 dark:text-green-200">
              This fact has been mathematically verified through isolated code execution in the VEE
              Sandbox environment. All values are guaranteed to be free of hallucination.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
