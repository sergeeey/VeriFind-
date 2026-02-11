import { render, screen, waitFor } from '@testing-library/react'
import { SystemStatusPanel } from '@/components/dashboard/SystemStatusPanel'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('SystemStatusPanel', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('renders live metrics from health/status/usage endpoints', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.endsWith('/health')) {
        return Promise.resolve({ ok: true, json: async () => ({ status: 'healthy' }) })
      }
      if (url.includes('/api/status-summary')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total_tracked: 2,
            completed: 1,
            failed: 1,
            pending: 0,
            today_count: 2,
            avg_completion_ms: 2000,
          }),
        })
      }
      if (url.includes('/api/usage/summary')) {
        return Promise.resolve({ ok: true, json: async () => ({ usage: { active_consumers: 3 } }) })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<SystemStatusPanel />)

    await waitFor(() => {
      expect(screen.getByText(/API Healthy/i)).toBeInTheDocument()
      expect(screen.getByText(/Tracked Queries/i)).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText(/Active API consumers: 3/i)).toBeInTheDocument()
    })
  })
})
