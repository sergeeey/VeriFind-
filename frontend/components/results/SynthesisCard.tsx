'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { getConfidenceColor } from '@/lib/utils'
import type { SynthesisData } from '@/types/results'
import { TrendingUp, AlertTriangle, Lightbulb } from 'lucide-react'

interface SynthesisCardProps {
  synthesis: SynthesisData
}

export function SynthesisCard({ synthesis }: SynthesisCardProps) {
  const confidencePercent = (synthesis.confidence * 100).toFixed(0)
  const confidenceColor = getConfidenceColor(synthesis.confidence)

  return (
    <Card className="border-2">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Final Synthesis</CardTitle>
          <Badge className={confidenceColor}>
            {confidencePercent}% Confidence
          </Badge>
        </div>
        <CardDescription>Aggregated analysis from all perspectives</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Verdict */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">Verdict</h3>
          <p className="rounded-lg border bg-muted/50 p-4 text-sm leading-relaxed">
            {synthesis.verdict}
          </p>
        </div>

        {/* Confidence Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">Overall Confidence</span>
            <span className="text-muted-foreground">{confidencePercent}%</span>
          </div>
          <Progress value={synthesis.confidence * 100} className="h-2" />
        </div>

        {/* Risks */}
        {synthesis.risks && synthesis.risks.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              <h3 className="font-medium">Risks</h3>
            </div>
            <ul className="space-y-2">
              {synthesis.risks.map((risk, index) => (
                <li
                  key={index}
                  className="flex gap-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200"
                >
                  <span className="text-red-500">•</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Opportunities */}
        {synthesis.opportunities && synthesis.opportunities.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-500" />
              <h3 className="font-medium">Opportunities</h3>
            </div>
            <ul className="space-y-2">
              {synthesis.opportunities.map((opportunity, index) => (
                <li
                  key={index}
                  className="flex gap-3 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200"
                >
                  <span className="text-green-500">•</span>
                  <span>{opportunity}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Key Insights Box */}
        <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <div className="flex items-start gap-3">
            <Lightbulb className="h-5 w-5 flex-shrink-0 text-blue-500" />
            <div>
              <p className="font-medium text-blue-900 dark:text-blue-100">Key Takeaway</p>
              <p className="mt-1 text-sm text-blue-800 dark:text-blue-200">
                {synthesis.risks.length > 0 && synthesis.opportunities.length > 0
                  ? `Balanced analysis with ${synthesis.risks.length} risk${synthesis.risks.length > 1 ? 's' : ''} and ${synthesis.opportunities.length} opportunit${synthesis.opportunities.length > 1 ? 'ies' : 'y'} identified.`
                  : synthesis.risks.length > 0
                  ? `Risk-focused analysis with ${synthesis.risks.length} concern${synthesis.risks.length > 1 ? 's' : ''} highlighted.`
                  : synthesis.opportunities.length > 0
                  ? `Opportunity-focused analysis with ${synthesis.opportunities.length} potential benefit${synthesis.opportunities.length > 1 ? 's' : ''} identified.`
                  : 'Analysis complete with verified facts.'}
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
