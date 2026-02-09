import { render, screen, waitFor, cleanup } from '@testing-library/react'
import { PredictionDashboard } from '@/components/predictions/PredictionDashboard'

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
  Tooltip: ({ content }: { content?: React.ReactNode }) => <div data-testid="tooltip">{content}</div>,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  ReferenceLine: () => <div data-testid="reference-line" />,
}))

// Mock child components - this prevents actual API calls in children
jest.mock('@/components/predictions/CorridorChart', () => ({
  CorridorChart: ({ ticker }: { ticker: string }) => (
    <div data-testid="corridor-chart" data-ticker={ticker}>Corridor Chart for {ticker || 'none'}</div>
  ),
}))

jest.mock('@/components/predictions/TrackRecordTable', () => ({
  TrackRecordTable: ({ ticker }: { ticker: string }) => (
    <div data-testid="track-record-table" data-ticker={ticker}>Track Record Table for {ticker || 'none'}</div>
  ),
}))

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  AlertCircle: () => <svg data-testid="alert-circle" />,
  TrendingUp: () => <svg data-testid="trending-up" />,
  Target: () => <svg data-testid="target" />,
  AlertTriangle: () => <svg data-testid="alert-triangle" />,
  BarChart3: () => <svg data-testid="bar-chart" />,
}))

// Mock data
const mockTickersResponse = {
  tickers: ['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
}

const mockTrackRecordResponse = {
  track_record: {
    total_predictions: 50,
    completed_predictions: 45,
    pending_predictions: 5,
    hit_rate: 0.68,
    near_rate: 0.24,
    miss_rate: 0.08,
    avg_error_pct: 4.5,
    median_error_pct: 3.2,
  },
}

describe('PredictionDashboard', () => {
  beforeEach(() => {
    jest.resetAllMocks()
    cleanup()
  })

  afterEach(() => {
    cleanup()
    jest.resetAllMocks()
  })

  it('renders dashboard with header and ticker selector', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockTickersResponse,
    })

    render(<PredictionDashboard />)

    // Check header renders
    expect(screen.getByText('Prediction Dashboard')).toBeInTheDocument()
    expect(
      screen.getByText('Track prediction accuracy and performance metrics')
    ).toBeInTheDocument()

    // Wait for tickers to load
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/predictions/tickers'
      )
    })
  })

  it('displays summary cards with metrics', async () => {
    // Mock multiple fetch calls - first for tickers, then for track record
    ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/tickers')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockTickersResponse,
        })
      }
      if (url.includes('/track-record')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockTrackRecordResponse,
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<PredictionDashboard />)

    // Wait for data to load and check summary cards
    await waitFor(() => {
      expect(screen.getByText('Total Predictions')).toBeInTheDocument()
    }, { timeout: 3000 })

    // Check metrics are displayed
    expect(screen.getByText('50')).toBeInTheDocument()
    expect(screen.getByText('HIT Rate')).toBeInTheDocument()
    expect(screen.getByText('68.0%')).toBeInTheDocument()
    expect(screen.getByText('NEAR Rate')).toBeInTheDocument()
    expect(screen.getByText('24.0%')).toBeInTheDocument()
    expect(screen.getByText('MISS Rate')).toBeInTheDocument()
    expect(screen.getByText('8.0%')).toBeInTheDocument()
    expect(screen.getByText('Avg Error')).toBeInTheDocument()
    expect(screen.getByText('4.50%')).toBeInTheDocument()
  })

  it('renders TrackRecordTable component', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockTickersResponse,
    })

    render(<PredictionDashboard />)

    // TrackRecordTable should render (it always renders, even with empty ticker)
    await waitFor(() => {
      expect(screen.getByTestId('track-record-table')).toBeInTheDocument()
    })
  })

  it('displays disclaimer footer', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockTickersResponse,
    })

    render(<PredictionDashboard />)

    // Check disclaimer is rendered
    expect(screen.getByText(/Disclaimer:/i)).toBeInTheDocument()
    expect(
      screen.getByText(/This analysis is for informational and educational purposes only/i)
    ).toBeInTheDocument()
    expect(screen.getByText(/NOT financial advice/i)).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    ;(global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'))

    render(<PredictionDashboard />)

    // Component should still render without crashing
    expect(screen.getByText('Prediction Dashboard')).toBeInTheDocument()
    
    // Disclaimer should still be visible
    expect(screen.getByText(/Disclaimer:/i)).toBeInTheDocument()
  })

  it('fetches tickers from correct API endpoint', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockTickersResponse,
    })

    render(<PredictionDashboard />)

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/predictions/tickers'
      )
    })
  })

  it('fetches track record when ticker is available', async () => {
    // Use mockImplementation to handle multiple calls
    ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/tickers')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockTickersResponse,
        })
      }
      if (url.includes('/track-record')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockTrackRecordResponse,
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<PredictionDashboard />)

    // Wait for at least 2 API calls (tickers + track-record)
    await waitFor(() => {
      expect(global.fetch.mock.calls.length).toBeGreaterThanOrEqual(2)
    }, { timeout: 3000 })

    // Check that track-record endpoint is called
    const trackRecordCall = global.fetch.mock.calls.find(call => 
      call[0] && call[0].includes('/track-record')
    )
    expect(trackRecordCall).toBeTruthy()
  })

  it('shows loading state initially', async () => {
    // Create a delayed promise
    let resolveTickers: (value: any) => void
    const tickersPromise = new Promise((resolve) => {
      resolveTickers = resolve
    })

    ;(global.fetch as jest.Mock).mockImplementation(() => tickersPromise)

    render(<PredictionDashboard />)

    // Loading skeletons should be visible immediately
    const skeletons = screen.getAllByTestId('skeleton')
    expect(skeletons.length).toBeGreaterThan(0)

    // Resolve to complete the test
    resolveTickers!({ ok: true, json: async () => mockTickersResponse })
  })

  it('renders CorridorChart when ticker is selected', async () => {
    // Use mockImplementation to handle multiple calls
    ;(global.fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/tickers')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockTickersResponse,
        })
      }
      if (url.includes('/track-record')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockTrackRecordResponse,
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    })

    render(<PredictionDashboard />)

    // Wait for track record to be fetched (this ensures ticker is selected)
    await waitFor(() => {
      const trackRecordCall = global.fetch.mock.calls.find(call => 
        call[0] && call[0].includes('/track-record')
      )
      expect(trackRecordCall).toBeTruthy()
    }, { timeout: 3000 })

    // Now CorridorChart should be rendered with the selected ticker
    const chart = screen.getByTestId('corridor-chart')
    expect(chart).toBeInTheDocument()
    expect(chart).toHaveAttribute('data-ticker', 'AAPL')
  })
})
