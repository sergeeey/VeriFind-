'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatDuration, formatDateTime } from '@/lib/utils'
import type { Episode } from '@/types/results'
import { Calendar, Clock, CheckCircle2, AlertCircle } from 'lucide-react'

interface ResultsHeaderProps {
  episode: Episode
}

export function ResultsHeader({ episode }: ResultsHeaderProps) {
  const getStateBadge = () => {
    switch (episode.state) {
      case 'completed':
        return (
          <Badge className="bg-green-500">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            Completed
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="destructive">
            <AlertCircle className="mr-1 h-3 w-3" />
            Failed
          </Badge>
        )
      default:
        return <Badge variant="outline">{episode.state}</Badge>
    }
  }

  const duration = episode.duration_ms
    ? `${(episode.duration_ms / 1000).toFixed(2)}s`
    : episode.completed_at
    ? formatDuration(
        new Date(episode.completed_at).getTime() - new Date(episode.created_at).getTime()
      )
    : 'N/A'

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription className="max-w-3xl">{episode.query_text}</CardDescription>
          </div>
          {getStateBadge()}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-4">
          {/* Episode ID */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Episode ID</p>
            <code className="block rounded bg-muted px-2 py-1 text-xs">
              {episode.episode_id}
            </code>
          </div>

          {/* Created At */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Created</p>
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span>{formatDateTime(new Date(episode.created_at))}</span>
            </div>
          </div>

          {/* Duration */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Duration</p>
            <div className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span>{duration}</span>
            </div>
          </div>

          {/* Facts Count */}
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">Verified Facts</p>
            <div className="text-2xl font-bold">{episode.verified_facts.length}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
