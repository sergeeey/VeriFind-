import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { UsageWorkbench } from '@/components/dashboard/UsageWorkbench'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('UsageWorkbench', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('loads and displays usage summary', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.endsWith('/api/usage/summary')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            usage: {
              enforcement_enabled: true,
              window_hours: 1,
              default_limit: 100,
              active_consumers: 1,
              consumers: [
                {
                  consumer: 'key:abcd...1234',
                  requests_current_window: 12,
                  requests_total: 50,
                  last_seen: '2026-02-11T12:00:00Z',
                },
              ],
            },
          }),
        })
      }
      if (url.endsWith('/api/health/circuit-breakers')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            initialized: true,
            provider: 'deepseek',
            breakers: {
              market_data_fetch: {
                name: 'market_data_fetch',
                state: 'closed',
                failure_count: 0,
                total_calls: 10,
                failure_rate: 0,
              },
            },
          }),
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<UsageWorkbench />)

    await waitFor(() => {
      expect(screen.getByText(/API Usage Dashboard/i)).toBeInTheDocument()
      expect(screen.getByText('ON')).toBeInTheDocument()
      expect(screen.getByText('key:abcd...1234')).toBeInTheDocument()
      expect(screen.getByText(/Circuit Breakers/i)).toBeInTheDocument()
      expect(screen.getByText(/market_data_fetch/i)).toBeInTheDocument()
    })
  })

  it('allows manual refresh', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.endsWith('/api/usage/summary')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            usage: {
              enforcement_enabled: false,
              window_hours: 1,
              default_limit: 100,
              active_consumers: 0,
              consumers: [],
            },
          }),
        })
      }
      if (url.endsWith('/api/health/circuit-breakers')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            initialized: false,
            provider: null,
            message: 'Orchestrator not initialized',
            breakers: {},
          }),
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<UsageWorkbench />)

    const refreshButton = await screen.findByRole('button', { name: /Refresh/i })
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/usage/summary')
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/health/circuit-breakers')
      expect(refreshButton).not.toBeDisabled()
    })

    fireEvent.click(refreshButton)

    await waitFor(() => {
      expect((global.fetch as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2)
    })
  })
})
