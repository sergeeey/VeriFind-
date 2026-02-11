'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { TrendingUp, TrendingDown, Scale, CircleDollarSign, Clock, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

// Types
export interface AgentPerspective {
  analysis: string
  confidence: number // 0.0-1.0
  key_points: string[]
  provider: string
  recommendation?: 'BUY' | 'HOLD' | 'SELL'
}

export interface MultiLLMDebateData {
  perspectives: {
    bull: AgentPerspective
    bear: AgentPerspective
    arbiter: AgentPerspective
  }
  synthesis: {
    recommendation: 'BUY' | 'HOLD' | 'SELL'
    overall_confidence: number
    risk_reward_ratio: string
  }
  metadata: {
    cost_usd: number
    latency_ms: number
    timestamp: number
  }
}

interface MultiLLMDebateViewProps {
  data: MultiLLMDebateData
}

export function MultiLLMDebateView({ data }: MultiLLMDebateViewProps) {
  const { perspectives, synthesis, metadata } = data

  // Get recommendation color
  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'BUY':
        return 'bg-green-500 text-white'
      case 'SELL':
        return 'bg-red-500 text-white'
      case 'HOLD':
        return 'bg-yellow-500 text-white'
      default:
        return 'bg-gray-500 text-white'
    }
  }

  // Get provider badge color
  const getProviderColor = (provider: string) => {
    switch (provider.toLowerCase()) {
      case 'deepseek':
        return 'bg-blue-500 text-white'
      case 'anthropic':
        return 'bg-orange-500 text-white'
      case 'openai':
        return 'bg-purple-500 text-white'
      default:
        return 'bg-gray-500 text-white'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header Card with Synthesis */}
      <Card className="border-2">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-yellow-500" />
                Multi-LLM Debate Analysis
              </CardTitle>
              <CardDescription>
                Parallel Bull/Bear/Arbiter perspectives from 3 LLM providers
              </CardDescription>
            </div>
            <Badge className={cn('text-lg px-4 py-2', getRecommendationColor(synthesis.recommendation))}>
              {synthesis.recommendation}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Overall Confidence */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Overall Confidence</span>
              <span className="text-muted-foreground">
                {(synthesis.overall_confidence * 100).toFixed(1)}%
              </span>
            </div>
            <Progress value={synthesis.overall_confidence * 100} className="h-2" />
          </div>

          {/* Risk/Reward Ratio */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-muted">
            <div className="flex items-center gap-2">
              <Scale className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Risk/Reward Ratio</span>
            </div>
            <Badge variant="outline">{synthesis.risk_reward_ratio}</Badge>
          </div>

          {/* Metadata */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t">
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{(metadata.latency_ms / 1000).toFixed(1)}s</span>
            </div>
            <div className="flex items-center gap-1">
              <CircleDollarSign className="h-3 w-3" />
              <span>${metadata.cost_usd.toFixed(4)}</span>
            </div>
            <div className="flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              <span>3 LLMs in parallel</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Perspectives Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Bull Perspective */}
        <Card className="border-green-500/50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-500" />
              <CardTitle className="text-lg">Bull</CardTitle>
            </div>
            <CardDescription>Optimistic Analysis</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Provider Badge */}
            <Badge className={getProviderColor(perspectives.bull.provider)}>
              {perspectives.bull.provider}
            </Badge>

            {/* Confidence */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-medium">
                  {(perspectives.bull.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <Progress value={perspectives.bull.confidence * 100} className="h-1.5" />
            </div>

            {/* Analysis */}
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground font-medium">Analysis:</p>
              <p className="text-sm leading-relaxed">{perspectives.bull.analysis}</p>
            </div>

            {/* Key Points */}
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground font-medium">Key Points:</p>
              <ul className="space-y-1 text-sm">
                {perspectives.bull.key_points.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-green-500 mt-1">•</span>
                    <span className="flex-1">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Bear Perspective */}
        <Card className="border-red-500/50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-5 w-5 text-red-500" />
              <CardTitle className="text-lg">Bear</CardTitle>
            </div>
            <CardDescription>Skeptical Analysis</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Provider Badge */}
            <Badge className={getProviderColor(perspectives.bear.provider)}>
              {perspectives.bear.provider}
            </Badge>

            {/* Confidence */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-medium">
                  {(perspectives.bear.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <Progress value={perspectives.bear.confidence * 100} className="h-1.5" />
            </div>

            {/* Analysis */}
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground font-medium">Analysis:</p>
              <p className="text-sm leading-relaxed">{perspectives.bear.analysis}</p>
            </div>

            {/* Key Points */}
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground font-medium">Key Points:</p>
              <ul className="space-y-1 text-sm">
                {perspectives.bear.key_points.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-red-500 mt-1">•</span>
                    <span className="flex-1">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Arbiter Perspective */}
        <Card className="border-purple-500/50">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5 text-purple-500" />
              <CardTitle className="text-lg">Arbiter</CardTitle>
            </div>
            <CardDescription>Balanced Synthesis</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Provider Badge */}
            <Badge className={getProviderColor(perspectives.arbiter.provider)}>
              {perspectives.arbiter.provider}
            </Badge>

            {/* Confidence */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Confidence</span>
                <span className="font-medium">
                  {(perspectives.arbiter.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <Progress value={perspectives.arbiter.confidence * 100} className="h-1.5" />
            </div>

            {/* Recommendation */}
            {perspectives.arbiter.recommendation && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-purple-500/10">
                <span className="text-sm font-medium">Recommendation:</span>
                <Badge className={cn('text-sm', getRecommendationColor(perspectives.arbiter.recommendation))}>
                  {perspectives.arbiter.recommendation}
                </Badge>
              </div>
            )}

            {/* Analysis */}
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground font-medium">Analysis:</p>
              <p className="text-sm leading-relaxed">{perspectives.arbiter.analysis}</p>
            </div>

            {/* Key Points */}
            <div className="space-y-2">
              <p className="text-xs text-muted-foreground font-medium">Key Points:</p>
              <ul className="space-y-1 text-sm">
                {perspectives.arbiter.key_points.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-purple-500 mt-1">•</span>
                    <span className="flex-1">{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Info Footer */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <p className="text-xs text-muted-foreground">
            <strong>How it works:</strong> Three LLM providers analyze your query in parallel.
            DeepSeek provides the bullish view, Claude provides the bearish view, and GPT-4
            synthesizes both into a balanced recommendation. Total cost: ${metadata.cost_usd.toFixed(4)} per analysis.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
