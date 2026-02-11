'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

type ChartPoint = {
  timestamp: string
  close: number
  ema?: number | null
  rsi?: number | null
}

type FilingRow = {
  form: string
  filing_date: string
  filing_url?: string | null
}

type SentimentRow = {
  title: string
  sentiment_label: string
  sentiment_score: number
}

export function IntelligenceWorkbench() {
  const [ticker, setTicker] = useState('AAPL')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [chartPoints, setChartPoints] = useState<ChartPoint[]>([])
  const [filings, setFilings] = useState<FilingRow[]>([])
  const [sentiment, setSentiment] = useState<{ label: string; score: number; items: SentimentRow[] } | null>(null)
  const [sensitivityFlip, setSensitivityFlip] = useState<boolean | null>(null)
  const [education, setEducation] = useState<{ terms: string[]; limitations: string[] } | null>(null)

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const latest = useMemo(() => {
    if (!chartPoints.length) return null
    const last = chartPoints[chartPoints.length - 1]
    return {
      close: last.close,
      ema: last.ema,
      rsi: last.rsi,
    }
  }, [chartPoints])

  const runIntel = async () => {
    const token = ticker.trim().toUpperCase()
    if (!token) return
    setLoading(true)
    setError(null)

    try {
      const [chartRes, secRes, sentRes, sensRes, eduRes] = await Promise.all([
        fetch(`${apiBase}/api/data/chart/${token}?period=3mo&interval=1d`),
        fetch(`${apiBase}/api/sec/filings/${token}?form=10-Q&limit=3`),
        fetch(`${apiBase}/api/sentiment/${token}?limit=5`),
        fetch(`${apiBase}/api/sensitivity/price`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ticker: token,
            position_size: 10,
            variation_pct: 15,
            steps: 7,
          }),
        }),
        fetch(`${apiBase}/api/educational/explain`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: `Analyze ${token} RSI EMA volatility beta and sharpe ratio.`,
          }),
        }),
      ])

      const [chartJson, secJson, sentJson, sensJson, eduJson] = await Promise.all([
        chartRes.ok ? chartRes.json() : Promise.resolve(null),
        secRes.ok ? secRes.json() : Promise.resolve(null),
        sentRes.ok ? sentRes.json() : Promise.resolve(null),
        sensRes.ok ? sensRes.json() : Promise.resolve(null),
        eduRes.ok ? eduRes.json() : Promise.resolve(null),
      ])

      setChartPoints(chartJson?.points || [])
      setFilings((secJson?.filings || []) as FilingRow[])
      setSentiment(
        sentJson
          ? {
              label: sentJson.average_sentiment_label,
              score: sentJson.average_sentiment_score,
              items: (sentJson.items || []) as SentimentRow[],
            }
          : null
      )
      setSensitivityFlip(Boolean(sensJson?.sign_flip_detected))
      setEducation(
        eduJson
          ? {
              terms: eduJson.detected_terms || [],
              limitations: eduJson.limitations || [],
            }
          : null
      )
    } catch (e) {
      setError('Failed to run intelligence workbench')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Intelligence Workbench</CardTitle>
          <CardDescription>
            Unified dashboard for Chart, SEC filings, Sentiment, Sensitivity and Educational guidance.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row">
          <Input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="Ticker (e.g. AAPL)" />
          <Button onClick={runIntel} disabled={loading}>
            {loading ? 'Running...' : 'Run Intel'}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Card>
          <CardContent className="pt-6 text-red-500">{error}</CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Market Snapshot</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Latest Close: {latest ? latest.close : 'N/A'}</div>
            <div>EMA: {latest?.ema ?? 'N/A'}</div>
            <div>RSI: {latest?.rsi ?? 'N/A'}</div>
            <div>Points: {chartPoints.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sensitivity Signal</CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            Sign Flip Detected: {sensitivityFlip === null ? 'N/A' : sensitivityFlip ? 'YES' : 'NO'}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>SEC 10-Q Filings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {filings.length === 0 && <div>No filings loaded</div>}
            {filings.map((row, idx) => (
              <div key={`${row.filing_date}-${idx}`} className="rounded border p-2">
                <div>{row.form} • {row.filing_date}</div>
                {row.filing_url && (
                  <a className="text-blue-500 underline" href={row.filing_url} target="_blank" rel="noreferrer">
                    Open filing
                  </a>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Headline Sentiment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Average: {sentiment ? `${sentiment.label} (${sentiment.score})` : 'N/A'}</div>
            {(sentiment?.items || []).slice(0, 3).map((item, idx) => (
              <div key={idx} className="rounded border p-2">
                <div className="font-medium">{item.sentiment_label} ({item.sentiment_score})</div>
                <div className="text-muted-foreground">{item.title}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Educational Highlights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div>Detected terms: {(education?.terms || []).join(', ') || 'N/A'}</div>
          {(education?.limitations || []).slice(0, 3).map((line, idx) => (
            <div key={idx} className="rounded border p-2">{line}</div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

