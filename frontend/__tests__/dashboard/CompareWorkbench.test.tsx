import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CompareWorkbench } from '@/components/dashboard/CompareWorkbench'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('CompareWorkbench', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('runs compare and renders leader/results', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        compare_id: 'cmp-1',
        status: 'completed',
        provider: 'deepseek',
        tickers: ['AAPL', 'MSFT'],
        leader_ticker: 'AAPL',
        completed_count: 2,
        failed_count: 0,
        average_verification_score: 0.79,
        results: [
          { ticker: 'AAPL', status: 'completed', verification_score: 0.81, answer: 'Result for AAPL' },
          { ticker: 'MSFT', status: 'completed', verification_score: 0.77, answer: 'Result for MSFT' },
        ],
      }),
    })

    render(<CompareWorkbench />)
    fireEvent.click(screen.getByRole('button', { name: /Run Compare/i }))

    await waitFor(() => {
      expect(screen.getByText(/Multi-Ticker Compare/i)).toBeInTheDocument()
      expect(screen.getByText(/Leader/i)).toBeInTheDocument()
      expect(screen.getByText('AAPL')).toBeInTheDocument()
      expect(screen.getByText(/Per-Ticker Results/i)).toBeInTheDocument()
      expect(screen.getByText(/MSFT \| status: completed/i)).toBeInTheDocument()
    })
  })
})
