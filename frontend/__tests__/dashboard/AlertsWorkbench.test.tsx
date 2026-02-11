import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AlertsWorkbench } from '@/components/dashboard/AlertsWorkbench'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('AlertsWorkbench', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('creates, loads and checks alerts', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith('/api/alerts') && (!options || options.method === undefined)) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 'a1',
              ticker: 'AAPL',
              condition: 'above',
              target_price: 200,
              is_active: true,
              last_notified_at: '2026-02-11T10:30:00Z',
            },
          ],
        })
      }
      if (url.endsWith('/api/alerts') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: async () => ({ id: 'a1' }),
        })
      }
      if (url.endsWith('/api/alerts/check-now')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total_checked: 1,
            triggered_count: 1,
            notifications_sent: 1,
            rows: [
              { id: 'a1', ticker: 'AAPL', condition: 'above', target_price: 200, current_price: 210, triggered: true },
            ],
          }),
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<AlertsWorkbench />)

    fireEvent.click(screen.getByRole('button', { name: /Refresh/i }))
    await waitFor(() => {
      expect(screen.getByText(/AAPL above 200/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/last notification:/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /^Create$/i }))
    await waitFor(() => {
      expect((global.fetch as jest.Mock).mock.calls.some((call) => call[0].includes('/api/alerts'))).toBeTruthy()
    })

    fireEvent.click(screen.getByRole('button', { name: /Run Check/i }))
    await waitFor(() => {
      expect(screen.getByText(/notifications: 1/i)).toBeInTheDocument()
    })
  })
})
