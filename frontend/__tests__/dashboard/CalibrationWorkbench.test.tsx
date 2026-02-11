import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { CalibrationWorkbench } from '@/components/dashboard/CalibrationWorkbench'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('CalibrationWorkbench', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('loads and renders calibration summary', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        calibration_period: '30 days',
        total_evaluated: 120,
        expected_calibration_error: 0.0832,
        brier_score: 0.1456,
        calibration_curve: [
          { confidence_bin: '0.7-0.8', predicted_prob: 0.75, actual_accuracy: 0.69, count: 20 },
        ],
        recommendations: [
          { confidence_bin: '0.7-0.8', gap: 0.06, direction: 'overconfident', recommendation: 'Reduce confidence' },
        ],
        status: 'ok',
        min_required_samples: 10,
        ticker: 'AAPL',
      }),
    })

    render(<CalibrationWorkbench />)
    fireEvent.change(screen.getByPlaceholderText('Ticker (optional)'), { target: { value: 'aapl' } })
    fireEvent.click(screen.getByRole('button', { name: /Run Calibration/i }))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/predictions/calibration?days=30&min_samples=10&ticker=AAPL'
      )
      expect(screen.getByText(/Calibration Curve/i)).toBeInTheDocument()
      expect(screen.getByText(/Expected Calibration Error/i)).toBeInTheDocument()
      expect(screen.getByText(/0.0832/i)).toBeInTheDocument()
      expect(screen.getByText(/0.7-0.8 \| overconfident \| gap: 0.060/i)).toBeInTheDocument()
    })
  })

  it('renders error on api failure', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 500 })

    render(<CalibrationWorkbench />)
    fireEvent.click(screen.getByRole('button', { name: /Run Calibration/i }))

    await waitFor(() => {
      expect(screen.getByText(/Failed to load calibration metrics/i)).toBeInTheDocument()
    })
  })
})
