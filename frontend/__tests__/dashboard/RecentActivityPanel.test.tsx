import { render, screen, waitFor } from '@testing-library/react'
import { RecentActivityPanel } from '@/components/dashboard/RecentActivityPanel'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('RecentActivityPanel', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('renders live recent items from status endpoint', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => [
        {
          query_id: 'q1',
          query_text: 'Analyze AAPL',
          state: 'completed',
          updated_at: '2026-02-11T10:00:00Z',
          metadata: { episode_id: 'q1' },
        },
      ],
    })

    render(<RecentActivityPanel />)

    await waitFor(() => {
      expect(screen.getByText(/Recent Activity/i)).toBeInTheDocument()
      expect(screen.getByText('Analyze AAPL')).toBeInTheDocument()
      expect(screen.getByText(/View/i)).toBeInTheDocument()
    })
  })
})
