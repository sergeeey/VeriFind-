'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

type CompareRow = {
  ticker: string
  status: string
  verification_score: number
  answer?: string | null
  error?: string | null
}

type CompareResponse = {
  compare_id: string
  status: string
  provider: string
  tickers: string[]
  leader_ticker?: string | null
  completed_count: number
  failed_count: number
  average_verification_score: number
  results: CompareRow[]
}

export function CompareWorkbench() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [query, setQuery] = useState('Compare Sharpe ratio for {ticker} in 2023')
  const [tickers, setTickers] = useState('AAPL,MSFT,GOOGL')
  const [provider, setProvider] = useState<'deepseek' | 'openai' | 'gemini'>('deepseek')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CompareResponse | null>(null)

  const parsedTickers = useMemo(
    () =>
      tickers
        .split(',')
        .map((value) => value.trim().toUpperCase())
        .filter(Boolean),
    [tickers]
  )

  const runCompare = async () => {
    if (!query.trim() || parsedTickers.length < 2) {
      setError('Provide a query and at least 2 tickers')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const response = await fetch(`${apiBase}/api/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          tickers: parsedTickers,
          provider,
        }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body?.detail || 'Failed to run comparison')
      }
      setResult((await response.json()) as CompareResponse)
    } catch (e: any) {
      setError(String(e?.message || 'Failed to run comparison'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Multi-Ticker Compare</CardTitle>
          <CardDescription>
            Run the same analysis across multiple tickers and compare verification strength.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Compare query" />
          <Input value={tickers} onChange={(e) => setTickers(e.target.value)} placeholder="AAPL,MSFT,GOOGL" />
          <Select value={provider} onValueChange={(v: 'deepseek' | 'openai' | 'gemini') => setProvider(v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="deepseek">deepseek</SelectItem>
              <SelectItem value="openai">openai</SelectItem>
              <SelectItem value="gemini">gemini</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={runCompare} disabled={loading}>
            {loading ? 'Running...' : 'Run Compare'}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Card>
          <CardContent className="pt-6 text-red-500">{error}</CardContent>
        </Card>
      )}

      {result && (
        <>
          <div className="grid gap-4 md:grid-cols-4 text-sm">
            <Card>
              <CardHeader><CardTitle>Overall</CardTitle></CardHeader>
              <CardContent>status: {result.status}</CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Leader</CardTitle></CardHeader>
              <CardContent>{result.leader_ticker || 'N/A'}</CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Completed</CardTitle></CardHeader>
              <CardContent>{result.completed_count}</CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Failed</CardTitle></CardHeader>
              <CardContent>{result.failed_count}</CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Per-Ticker Results</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {result.results.map((row) => (
                <div key={row.ticker} className="rounded border p-2">
                  {row.ticker} | status: {row.status} | score: {row.verification_score ?? 0}
                  {row.answer ? ` | ${row.answer}` : ''}
                  {row.error ? ` | error: ${row.error}` : ''}
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
