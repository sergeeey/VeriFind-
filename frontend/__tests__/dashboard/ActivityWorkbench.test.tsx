import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ActivityWorkbench } from '@/components/dashboard/ActivityWorkbench'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('ActivityWorkbench', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('loads status rows and renders summary counters', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [
        {
          query_id: 'q1',
          query_text: 'Analyze AAPL',
          state: 'completed',
          status: 'completed',
          progress: 1,
          updated_at: '2026-02-11T10:00:00Z',
          metadata: { episode_id: 'q1' },
        },
        {
          query_id: 'q2',
          query_text: 'Analyze TSLA',
          state: 'failed',
          status: 'failed',
          progress: 0.2,
          updated_at: '2026-02-11T10:01:00Z',
          metadata: {},
        },
      ],
    })

    render(<ActivityWorkbench />)

    await waitFor(() => {
      expect(screen.getByText(/Total/i)).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
      expect(screen.getByText('Analyze AAPL')).toBeInTheDocument()
      expect(screen.getAllByText(/Open Status/i).length).toBe(2)
      expect(screen.getByText(/Open Results/i)).toBeInTheDocument()
    })
  })

  it('supports manual refresh', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    render(<ActivityWorkbench />)
    const refresh = await screen.findByRole('button', { name: /Refresh/i })
    await waitFor(() => {
      expect(refresh).not.toBeDisabled()
    })
    fireEvent.click(refresh)

    await waitFor(() => {
      expect((global.fetch as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('applies query filter in status request', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [],
    })

    render(<ActivityWorkbench />)
    const input = await screen.findByPlaceholderText(/Filter by query text/i)
    fireEvent.change(input, { target: { value: 'aapl' } })

    await waitFor(() => {
      const urls = (global.fetch as jest.Mock).mock.calls.map((call) => String(call[0]))
      expect(urls.some((url) => url.includes('/api/status?') && url.includes('query=aapl'))).toBeTruthy()
    })
  })
})
