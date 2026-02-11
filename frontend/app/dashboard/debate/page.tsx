'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { MultiLLMDebateView, type MultiLLMDebateData } from '@/components/debate/MultiLLMDebateView'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Sparkles, AlertCircle } from 'lucide-react'
import apiClient from '@/lib/api'

export default function DebatePage() {
  const [query, setQuery] = useState('')
  const [context, setContext] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<MultiLLMDebateData | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!query.trim()) {
      setError('Please enter a query')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      // Parse context if provided
      let contextObj = {}
      if (context.trim()) {
        try {
          contextObj = JSON.parse(context)
        } catch {
          setError('Context must be valid JSON')
          setLoading(false)
          return
        }
      }

      // Call Multi-LLM Debate API
      const response = await apiClient.post('/api/analyze-debate', {
        query: query.trim(),
        context: contextObj
      })

      setResult(response.data)
    } catch (err: any) {
      console.error('Debate error:', err)

      if (err.response?.status === 501) {
        setError('Multi-LLM Debate requires additional packages. Please check server logs.')
      } else if (err.response?.status === 500) {
        setError(err.response?.data?.detail || 'API keys not configured. Set DEEPSEEK_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY.')
      } else {
        setError(err.message || 'Failed to run debate analysis')
      }
    } finally {
      setLoading(false)
    }
  }

  const exampleQueries = [
    {
      query: 'Should I buy Tesla stock?',
      context: '{"ticker": "TSLA", "current_price": 250.00, "52w_high": 299.00}'
    },
    {
      query: 'Is Apple overvalued at current price?',
      context: '{"ticker": "AAPL", "current_price": 185.00, "pe_ratio": 28.5}'
    },
    {
      query: 'Should I invest in Microsoft for long-term growth?',
      context: '{"ticker": "MSFT", "current_price": 420.00, "market_cap": "3.1T"}'
    }
  ]

  const loadExample = (example: typeof exampleQueries[0]) => {
    setQuery(example.query)
    setContext(example.context)
    setError(null)
    setResult(null)
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Sparkles className="h-8 w-8 text-yellow-500" />
        <div>
          <h1 className="text-3xl font-bold">Multi-LLM Debate</h1>
          <p className="text-muted-foreground">
            Get Bull, Bear, and Arbiter perspectives from 3 LLM providers
          </p>
        </div>
      </div>

      {/* Query Form */}
      <Card>
        <CardHeader>
          <CardTitle>Run Debate Analysis</CardTitle>
          <CardDescription>
            Enter your financial query and optional context. Three LLMs will analyze in parallel.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Query Input */}
            <div className="space-y-2">
              <Label htmlFor="query">Query *</Label>
              <Textarea
                id="query"
                placeholder="Example: Should I buy Tesla stock?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={3}
                className="resize-none"
              />
            </div>

            {/* Context Input */}
            <div className="space-y-2">
              <Label htmlFor="context">
                Context (JSON, optional)
              </Label>
              <Textarea
                id="context"
                placeholder='{"ticker": "TSLA", "current_price": 250.00}'
                value={context}
                onChange={(e) => setContext(e.target.value)}
                rows={3}
                className="font-mono text-sm resize-none"
              />
              <p className="text-xs text-muted-foreground">
                Provide additional data as JSON (ticker, price, metrics, etc.)
              </p>
            </div>

            {/* Example Queries */}
            <div className="space-y-2">
              <Label>Quick Examples:</Label>
              <div className="flex flex-wrap gap-2">
                {exampleQueries.map((example, idx) => (
                  <Button
                    key={idx}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => loadExample(example)}
                  >
                    {example.query}
                  </Button>
                ))}
              </div>
            </div>

            {/* Submit Button */}
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Running debate (3-4s)...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Run Multi-LLM Debate
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Results */}
      {result && <MultiLLMDebateView data={result} />}

      {/* Info Card */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-lg">How Multi-LLM Debate Works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div className="space-y-1">
            <p className="font-medium text-foreground">1. Parallel Execution (3-4 seconds)</p>
            <p>Bull (DeepSeek) and Bear (Claude) agents run simultaneously, then Arbiter (GPT-4) synthesizes.</p>
          </div>
          <div className="space-y-1">
            <p className="font-medium text-foreground">2. Three Perspectives</p>
            <ul className="list-disc list-inside space-y-1 pl-4">
              <li><strong>Bull:</strong> Optimistic analysis focusing on growth and opportunities</li>
              <li><strong>Bear:</strong> Skeptical analysis focusing on risks and concerns</li>
              <li><strong>Arbiter:</strong> Balanced synthesis with BUY/HOLD/SELL recommendation</li>
            </ul>
          </div>
          <div className="space-y-1">
            <p className="font-medium text-foreground">3. Cost & Speed</p>
            <p>~$0.002 per query • 3x faster than sequential • No hallucinations (fact-based analysis)</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
