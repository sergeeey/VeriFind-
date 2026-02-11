import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { SensitivityWorkbench } from '@/components/dashboard/SensitivityWorkbench'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('SensitivityWorkbench', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('runs sweep and renders scenario results', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({
        ticker: 'AAPL',
        base_price: 100,
        position_size: 10,
        variation_pct: 20,
        steps: 5,
        sign_flip_detected: true,
        scenarios: [
          { shock_pct: -20, scenario_price: 80, pnl: -200, return_pct: -20, sign_flip: false },
          { shock_pct: 0, scenario_price: 100, pnl: 0, return_pct: 0, sign_flip: false },
          { shock_pct: 20, scenario_price: 120, pnl: 200, return_pct: 20, sign_flip: true },
        ],
      }),
    })

    render(<SensitivityWorkbench />)
    fireEvent.click(screen.getByRole('button', { name: /Run Sweep/i }))

    await waitFor(() => {
      expect(screen.getByText(/Scenario Grid/i)).toBeInTheDocument()
      expect(screen.getByText(/Sign Flip: YES/i)).toBeInTheDocument()
      expect(screen.getByText(/shock: -20%/i)).toBeInTheDocument()
    })
  })
})
