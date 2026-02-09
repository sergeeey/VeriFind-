import { render, screen, waitFor } from '@testing-library/react'
import { CorridorChart } from '@/components/predictions/CorridorChart'

// Mock fetch globally
global.fetch = jest.fn()

// Mock environment variable
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

// Mock Recharts components
jest.mock('recharts', () => ({
  AreaChart: ({ children }: { children: React.ReactNode }) => <div data-testid="area-chart">{children}</div>,
  Area: () => <div data-testid="area" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="grid" />,
  Tooltip: ({ content }: { content?: any }) => (
    <div data-testid="tooltip">{content ? 'Has content' : 'No content'}</div>
  ),
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  ReferenceLine: () => <div data-testid="reference-line" />,
}))

// Mock ChartContainer
jest.mock('@/components/charts/ChartContainer', () => ({
  ChartContainer: ({ children, title, description }: { children: React.ReactNode; title: string; description?: string }) => (
    <div data-testid="chart-container" data-title={title} data-description={description}>
      {children}
    </div>
  ),
}))

// Mock data
const mockCorridorResponse = {
  corridor_data: [
    {
      target_date: '2024-03-01',
      price_low: 180,
      price_high: 200,
      price_base: 190,
      actual_price: 195,
      is_hit: true,
    },
    {
      target_date: '2024-03-15',
      price_low: 185,
      price_high: 205,
      price_base: 195,
      actual_price: 188,
      is_hit: false,
    },
  ],
}

describe('CorridorChart', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  it('renders chart container with correct title', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockCorridorResponse,
    })

    render(<CorridorChart ticker="AAPL" limit={10} />)

    await waitFor(() => {
      const container = screen.getByTestId('chart-container')
      expect(container).toHaveAttribute('data-title', 'Price Corridor')
    })
  })

  it('fetches corridor data from correct endpoint', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockCorridorResponse,
    })

    render(<CorridorChart ticker="AAPL" limit={10} />)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/predictions/AAPL/corridor?limit=10'
      )
    })
  })

  it('renders Recharts components', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockCorridorResponse,
    })

    render(<CorridorChart ticker="AAPL" limit={10} />)

    await waitFor(() => {
      expect(screen.getByTestId('area-chart')).toBeInTheDocument()
    })

    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    expect(screen.getByTestId('grid')).toBeInTheDocument()
    expect(screen.getByTestId('legend')).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    ;(global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'))

    render(<CorridorChart ticker="AAPL" limit={10} />)

    // Component should show error state
    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })

  it('handles non-ok API response', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      statusText: 'Not Found',
    })

    render(<CorridorChart ticker="INVALID" limit={10} />)

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch corridor data: Not Found/i)).toBeInTheDocument()
    })
  })

  it('renders with empty data', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ corridor_data: [] }),
    })

    render(<CorridorChart ticker="AAPL" limit={10} />)

    // Chart should still render even with empty data
    await waitFor(() => {
      expect(screen.getByTestId('chart-container')).toBeInTheDocument()
    })
  })
})
