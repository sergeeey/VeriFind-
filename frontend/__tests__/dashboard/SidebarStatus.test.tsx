import { render, screen, waitFor } from '@testing-library/react'
import { Sidebar } from '@/components/layout/Sidebar'

global.fetch = jest.fn()
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

describe('Sidebar status block', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('loads health and query counts from backend', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.endsWith('/health')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ status: 'healthy' }),
        })
      }
      if (url.includes('/api/status-summary')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ today_count: 2 }),
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<Sidebar />)

    await waitFor(() => {
      expect(screen.getByText('Healthy')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })
})
