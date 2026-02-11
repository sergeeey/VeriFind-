'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

type ScenarioRow = {
  shock_pct: number
  scenario_price: number
  pnl: number
  return_pct: number
  sign_flip: boolean
}

type SensitivityResponse = {
  ticker: string
  base_price: number
  position_size: number
  variation_pct: number
  steps: number
  scenarios: ScenarioRow[]
  sign_flip_detected: boolean
}

export function SensitivityWorkbench() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [ticker, setTicker] = useState('AAPL')
  const [positionSize, setPositionSize] = useState('10')
  const [basePrice, setBasePrice] = useState('')
  const [variationPct, setVariationPct] = useState('20')
  const [steps, setSteps] = useState('9')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<SensitivityResponse | null>(null)

  const extremes = useMemo(() => {
    if (!result || result.scenarios.length === 0) return null
    const sorted = [...result.scenarios].sort((a, b) => a.shock_pct - b.shock_pct)
    return {
      worst: sorted[0],
      best: sorted[sorted.length - 1],
    }
  }, [result])

  const runSensitivity = async () => {
    const token = ticker.trim().toUpperCase()
    if (!token) return

    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const payload: Record<string, unknown> = {
        ticker: token,
        position_size: Number(positionSize),
        variation_pct: Number(variationPct),
        steps: Number(steps),
      }
      if (basePrice.trim()) {
        payload.base_price = Number(basePrice)
      }

      const response = await fetch(`${apiBase}/api/sensitivity/price`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) throw new Error('Failed to run sensitivity analysis')
      const json = (await response.json()) as SensitivityResponse
      setResult(json)
    } catch {
      setError('Failed to run sensitivity analysis')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Sensitivity Workbench</CardTitle>
          <CardDescription>
            Price shock sweep with PnL and sign-flip detection.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-6">
          <Input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="Ticker" />
          <Input value={positionSize} onChange={(e) => setPositionSize(e.target.value)} placeholder="Position size" />
          <Input value={basePrice} onChange={(e) => setBasePrice(e.target.value)} placeholder="Base price (optional)" />
          <Input value={variationPct} onChange={(e) => setVariationPct(e.target.value)} placeholder="Variation %" />
          <Input value={steps} onChange={(e) => setSteps(e.target.value)} placeholder="Steps" />
          <Button onClick={runSensitivity} disabled={loading}>
            {loading ? 'Running...' : 'Run Sweep'}
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
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Base</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                <div>Ticker: {result.ticker}</div>
                <div>Base Price: {result.base_price}</div>
                <div>Position: {result.position_size}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Risk/Reward</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                <div>Worst PnL: {extremes?.worst.pnl ?? 'N/A'}</div>
                <div>Best PnL: {extremes?.best.pnl ?? 'N/A'}</div>
                <div>Sign Flip: {result.sign_flip_detected ? 'YES' : 'NO'}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Sweep</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                <div>Range: +/-{result.variation_pct}%</div>
                <div>Steps: {result.steps}</div>
                <div>Scenarios: {result.scenarios.length}</div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Scenario Grid</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {result.scenarios.map((row, idx) => (
                <div key={`${row.shock_pct}-${idx}`} className="rounded border p-2">
                  shock: {row.shock_pct}% | price: {row.scenario_price} | pnl: {row.pnl} | return: {row.return_pct}%
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
