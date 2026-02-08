'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { DebatePerspective } from '@/types/results'
import { TrendingUp, TrendingDown, Minus, CheckCircle2, AlertCircle } from 'lucide-react'

interface DebateViewerProps {
  debates: DebatePerspective[]
}

export function DebateViewer({ debates }: DebateViewerProps) {
  const getPerspectiveIcon = (perspective: string) => {
    switch (perspective) {
      case 'bull':
        return <TrendingUp className="h-5 w-5 text-green-500" />
      case 'bear':
        return <TrendingDown className="h-5 w-5 text-red-500" />
      case 'neutral':
        return <Minus className="h-5 w-5 text-gray-500" />
      default:
        return null
    }
  }

  const getPerspectiveBadge = (perspective: string) => {
    switch (perspective) {
      case 'bull':
        return <Badge className="bg-green-500">Bull</Badge>
      case 'bear':
        return <Badge className="bg-red-500">Bear</Badge>
      case 'neutral':
        return <Badge variant="secondary">Neutral</Badge>
      default:
        return <Badge>{perspective}</Badge>
    }
  }

  const getStrengthIcon = (strength: string) => {
    switch (strength) {
      case 'strong':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case 'moderate':
        return <CheckCircle2 className="h-4 w-4 text-yellow-500" />
      case 'weak':
        return <AlertCircle className="h-4 w-4 text-gray-500" />
      default:
        return null
    }
  }

  if (!debates || debates.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Debate Analysis</CardTitle>
          <CardDescription>No debate reports available</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Debate Analysis</CardTitle>
        <CardDescription>Multi-perspective analysis from Bull, Bear, and Neutral agents</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {debates.map((debate, index) => (
          <div key={index} className="space-y-4">
            {/* Perspective Header */}
            <div className="flex items-center gap-3">
              {getPerspectiveIcon(debate.perspective)}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold capitalize">{debate.perspective} Perspective</h3>
                  {getPerspectiveBadge(debate.perspective)}
                </div>
              </div>
            </div>

            {/* Arguments */}
            {debate.arguments && debate.arguments.length > 0 && (
              <div className="space-y-3 pl-8">
                <p className="text-sm font-medium text-muted-foreground">Arguments:</p>
                {debate.arguments.map((arg, argIndex) => (
                  <div
                    key={argIndex}
                    className="rounded-lg border bg-muted/50 p-4 space-y-2"
                  >
                    {/* Claim */}
                    <div className="flex items-start gap-2">
                      {getStrengthIcon(arg.strength)}
                      <div className="flex-1">
                        <p className="font-medium">{arg.claim}</p>
                        <Badge variant="outline" className="mt-1 text-xs">
                          {arg.strength}
                        </Badge>
                      </div>
                    </div>

                    {/* Evidence */}
                    {arg.evidence && arg.evidence.length > 0 && (
                      <div className="mt-2 space-y-1 pl-6">
                        <p className="text-xs font-medium text-muted-foreground">Evidence:</p>
                        <ul className="list-disc space-y-1 pl-4 text-sm">
                          {arg.evidence.map((evidence, evidenceIndex) => (
                            <li key={evidenceIndex} className="text-muted-foreground">
                              {evidence}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Verdict */}
            <div className="rounded-lg border-2 bg-background p-4 pl-8">
              <p className="text-sm font-medium text-muted-foreground mb-2">Verdict:</p>
              <p className="text-sm leading-relaxed">{debate.verdict}</p>
            </div>

            {/* Divider */}
            {index < debates.length - 1 && <div className="border-t" />}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
