'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

type CalibrationPoint = {
  confidence_bin: string
  predicted_prob: number
  actual_accuracy: number
  count: number
}

type CalibrationRecommendation = {
  confidence_bin: string
  gap: number
  direction: string
  recommendation: string
}

type CalibrationResponse = {
  calibration_period: string
  total_evaluated: number
  expected_calibration_error: number
  brier_score: number
  calibration_curve: CalibrationPoint[]
  recommendations: CalibrationRecommendation[]
  status: string
  min_required_samples: number
  ticker: string | null
}

export function CalibrationWorkbench() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [days, setDays] = useState('30')
  const [ticker, setTicker] = useState('')
  const [minSamples, setMinSamples] = useState('10')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CalibrationResponse | null>(null)

  const loadCalibration = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const params = new URLSearchParams({
        days: String(Number(days) || 30),
        min_samples: String(Number(minSamples) || 10),
      })
      const safeTicker = ticker.trim().toUpperCase()
      if (safeTicker) params.set('ticker', safeTicker)

      const response = await fetch(`${apiBase}/api/predictions/calibration?${params.toString()}`)
      if (!response.ok) throw new Error('Failed to load calibration metrics')
      setResult((await response.json()) as CalibrationResponse)
    } catch {
      setError('Failed to load calibration metrics')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Calibration Workbench</CardTitle>
          <CardDescription>
            Confidence calibration diagnostics (ECE, Brier score, reliability bins).
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <Input value={days} onChange={(e) => setDays(e.target.value)} placeholder="Days" />
          <Input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="Ticker (optional)" />
          <Input value={minSamples} onChange={(e) => setMinSamples(e.target.value)} placeholder="Min samples" />
          <Button onClick={loadCalibration} disabled={loading}>
            {loading ? 'Loading...' : 'Run Calibration'}
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
              <CardHeader>
                <CardTitle>Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-semibold">{result.status}</div>
                <div className="text-muted-foreground">{result.calibration_period}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Samples</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-semibold">{result.total_evaluated}</div>
                <div className="text-muted-foreground">Min required: {result.min_required_samples}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>ECE</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-semibold">{result.expected_calibration_error.toFixed(4)}</div>
                <div className="text-muted-foreground">Expected Calibration Error</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Brier Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-semibold">{result.brier_score.toFixed(4)}</div>
                <div className="text-muted-foreground">{result.ticker || 'All tickers'}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Calibration Curve</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {result.calibration_curve.length === 0 && (
                <div className="rounded border p-3">No calibration points available</div>
              )}
              {result.calibration_curve.map((row) => (
                <div key={row.confidence_bin} className="rounded border p-3">
                  bin: {row.confidence_bin} | predicted: {row.predicted_prob.toFixed(3)} | actual: {row.actual_accuracy.toFixed(3)} | count: {row.count}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recommendations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {result.recommendations.length === 0 && (
                <div className="rounded border p-3">No recommendation hints</div>
              )}
              {result.recommendations.map((rec, idx) => (
                <div key={`${rec.confidence_bin}-${idx}`} className="rounded border p-3">
                  {rec.confidence_bin} | {rec.direction} | gap: {rec.gap.toFixed(3)} | {rec.recommendation}
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
