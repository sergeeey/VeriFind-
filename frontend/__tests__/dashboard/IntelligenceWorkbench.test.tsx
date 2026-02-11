import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IntelligenceWorkbench } from '@/components/dashboard/IntelligenceWorkbench'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('IntelligenceWorkbench', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('runs all intelligence endpoints and renders summary cards', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/api/data/chart/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            points: [
              { timestamp: '2026-01-01', close: 100, ema: 99.5, rsi: 55.2 },
              { timestamp: '2026-01-02', close: 101, ema: 100.0, rsi: 57.1 },
            ],
          }),
        })
      }
      if (url.includes('/api/sec/filings/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            filings: [{ form: '10-Q', filing_date: '2026-01-10', filing_url: 'http://sec' }],
          }),
        })
      }
      if (url.includes('/api/sentiment/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            average_sentiment_label: 'positive',
            average_sentiment_score: 0.4,
            items: [{ title: 'AAPL beats earnings', sentiment_label: 'positive', sentiment_score: 1 }],
          }),
        })
      }
      if (url.includes('/api/sensitivity/price')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ sign_flip_detected: true }),
        })
      }
      if (url.includes('/api/educational/explain')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            detected_terms: ['rsi', 'ema'],
            limitations: ['Historical patterns can break under regime changes.'],
          }),
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<IntelligenceWorkbench />)
    fireEvent.click(screen.getByRole('button', { name: /Run Intel/i }))

    await waitFor(() => {
      expect(screen.getByText(/Latest Close:/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/Sign Flip Detected:/i)).toBeInTheDocument()
    expect(screen.getByText(/SEC 10-Q Filings/i)).toBeInTheDocument()
    expect(screen.getByText(/Headline Sentiment/i)).toBeInTheDocument()
    expect(screen.getByText(/Educational Highlights/i)).toBeInTheDocument()
  })
})

