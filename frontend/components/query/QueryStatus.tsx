'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { PIPELINE_STEPS, QUERY_STATES } from '@/lib/constants'
import { formatDuration, getConfidenceColor } from '@/lib/utils'
import type { QueryStatus as QueryStatusType } from '@/types/query'
import {
  CheckCircle2,
  Circle,
  Loader2,
  XCircle,
  Clock,
  Code,
  Database,
  Shield,
  MessageSquare,
  AlertCircle,
} from 'lucide-react'

interface QueryStatusProps {
  status: QueryStatusType
}

export function QueryStatus({ status }: QueryStatusProps) {
  const getStateColor = (state: string): string => {
    switch (state) {
      case QUERY_STATES.COMPLETED:
        return 'bg-green-500'
      case QUERY_STATES.FAILED:
        return 'bg-red-500'
      case QUERY_STATES.PENDING:
        return 'bg-gray-500'
      default:
        return 'bg-blue-500'
    }
  }

  const getStateLabel = (state: string): string => {
    return state.toUpperCase()
  }

  const getStepIcon = (stepKey: string, stepStatus: 'pending' | 'active' | 'completed' | 'failed') => {
    if (stepStatus === 'completed') {
      return <CheckCircle2 className="h-5 w-5 text-green-500" />
    }
    if (stepStatus === 'failed') {
      return <XCircle className="h-5 w-5 text-red-500" />
    }
    if (stepStatus === 'active') {
      return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
    }

    // Icon based on step type
    switch (stepKey) {
      case 'planning':
        return <Code className="h-5 w-5 text-muted-foreground" />
      case 'fetching':
        return <Database className="h-5 w-5 text-muted-foreground" />
      case 'executing':
        return <Circle className="h-5 w-5 text-muted-foreground" />
      case 'validating':
        return <Shield className="h-5 w-5 text-muted-foreground" />
      case 'debating':
        return <MessageSquare className="h-5 w-5 text-muted-foreground" />
      default:
        return <Circle className="h-5 w-5 text-muted-foreground" />
    }
  }

  const getStepStatus = (stepKey: string): 'pending' | 'active' | 'completed' | 'failed' => {
    if (status.state === QUERY_STATES.FAILED) {
      // If query failed, check if this step was the current one
      if (status.current_node === stepKey) return 'failed'
      // Steps before current are completed
      const stepIndex = PIPELINE_STEPS.findIndex((s) => s.key === stepKey)
      const currentIndex = PIPELINE_STEPS.findIndex((s) => s.key === status.current_node)
      return stepIndex < currentIndex ? 'completed' : 'pending'
    }

    if (status.state === QUERY_STATES.COMPLETED) {
      return 'completed'
    }

    // Active query
    const stepIndex = PIPELINE_STEPS.findIndex((s) => s.key === stepKey)
    const currentIndex = PIPELINE_STEPS.findIndex((s) => s.key === status.state)

    if (stepIndex < currentIndex) return 'completed'
    if (stepIndex === currentIndex) return 'active'
    return 'pending'
  }

  const duration = status.created_at
    ? formatDuration(
        new Date(status.updated_at || Date.now()).getTime() - new Date(status.created_at).getTime()
      )
    : '0s'

  return (
    <div className="space-y-6">
      {/* Query Info Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle>Query Status</CardTitle>
              <CardDescription className="max-w-2xl">{status.query_text}</CardDescription>
            </div>
            <Badge className={getStateColor(status.state)}>{getStateLabel(status.state)}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Metadata */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Duration:</span>
              <span className="font-medium">{duration}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Query ID:</span>
              <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{status.query_id}</code>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">{status.progress}%</span>
            </div>
            <Progress value={status.progress} className="h-2" />
          </div>

          {/* Error Message */}
          {status.error && (
            <div className="flex gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <div>
                <p className="font-medium">Error occurred</p>
                <p className="mt-1">{status.error}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pipeline Visualization */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Status</CardTitle>
          <CardDescription>Real-time execution tracking</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {PIPELINE_STEPS.map((step, index) => {
              const stepStatus = getStepStatus(step.key)
              const isLast = index === PIPELINE_STEPS.length - 1

              return (
                <div key={step.key} className="relative">
                  <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className="relative flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border-2 bg-background">
                      {getStepIcon(step.key, stepStatus)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 pt-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{step.label}</p>
                        {stepStatus === 'active' && (
                          <Badge variant="outline" className="text-xs">
                            In Progress
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{step.description}</p>
                    </div>
                  </div>

                  {/* Connector Line */}
                  {!isLast && (
                    <div
                      className={`absolute left-5 top-10 h-10 w-0.5 ${
                        stepStatus === 'completed' ? 'bg-green-500' : 'bg-muted'
                      }`}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
