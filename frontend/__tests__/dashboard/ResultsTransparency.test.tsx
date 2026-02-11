import { render, screen, waitFor } from '@testing-library/react'
import ResultsPage from '@/app/dashboard/results/[id]/page'

const mockToast = jest.fn()

jest.mock('next/navigation', () => ({
  useParams: () => ({ id: 'ep-900' }),
  useRouter: () => ({ push: jest.fn() }),
}))

jest.mock('@/lib/api', () => ({
  api: {
    getEpisode: jest.fn(),
  },
}))

jest.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}))

jest.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TabsContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({ children }: { children: React.ReactNode }) => <button>{children}</button>,
}))

jest.mock('@/components/results/ResultsHeader', () => ({ ResultsHeader: () => <div>ResultsHeader</div> }))
jest.mock('@/components/results/FactsTable', () => ({ FactsTable: () => <div>FactsTable</div> }))
jest.mock('@/components/results/DebateViewer', () => ({ DebateViewer: () => <div>DebateViewer</div> }))
jest.mock('@/components/results/SynthesisCard', () => ({ SynthesisCard: () => <div>SynthesisCard</div> }))
jest.mock('@/components/results/CodeViewer', () => ({ CodeViewer: () => <div>CodeViewer</div> }))
jest.mock('@/components/results/FactDetailsDialog', () => ({ FactDetailsDialog: () => <div>FactDetailsDialog</div> }))
jest.mock('@/components/charts/ChartContainer', () => ({ ChartContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }))
jest.mock('@/components/charts/TimeRangeSelector', () => ({ TimeRangeSelector: () => <div>TimeRangeSelector</div> }))
jest.mock('@/components/charts/CandlestickChart', () => ({ CandlestickChart: () => <div>CandlestickChart</div> }))
jest.mock('@/components/charts/ConfidenceTrendChart', () => ({ ConfidenceTrendChart: () => <div>ConfidenceTrendChart</div> }))
jest.mock('@/components/charts/DebateDistributionChart', () => ({ DebateDistributionChart: () => <div>DebateDistributionChart</div> }))
jest.mock('@/components/charts/ExecutionTimeHistogram', () => ({ ExecutionTimeHistogram: () => <div>ExecutionTimeHistogram</div> }))
jest.mock('@/components/charts/FactTimelineChart', () => ({ FactTimelineChart: () => <div>FactTimelineChart</div> }))
jest.mock('@/components/layout/DisclaimerBanner', () => ({ DisclaimerFooter: () => <div>DisclaimerFooter</div> }))

const { api } = jest.requireMock('@/lib/api') as { api: { getEpisode: jest.Mock } }

describe('ResultsPage verification transparency', () => {
  beforeEach(() => {
    jest.resetAllMocks()
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

    api.getEpisode.mockResolvedValue({
      data: {
        episode_id: 'ep-900',
        query_text: 'Analyze MSFT',
        state: 'completed',
        created_at: '2026-02-11T00:00:00Z',
        completed_at: '2026-02-11T00:01:00Z',
        verified_facts: [
          {
            fact_id: 'f1',
            extracted_values: { close: 201.1 },
            execution_time_ms: 30,
            memory_used_mb: 12,
            created_at: '2026-02-11T00:00:30Z',
            confidence_score: 0.91,
          },
        ],
        debate_reports: [],
      },
    })

    global.fetch = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/verification/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            verification_score: 0.82,
            confidence_before: 0.78,
            confidence_after: 0.82,
            confidence_delta: 0.04,
            confidence_rationale: 'Consensus improved confidence.',
            key_risks: ['Valuation compression'],
            key_opportunities: ['Margin expansion'],
          }),
        })
      }
      return Promise.resolve({ ok: false, status: 404 })
    }) as jest.Mock
  })

  it('renders transparency block with rationale and risk/opportunity lists', async () => {
    render(<ResultsPage />)

    await waitFor(() => {
      expect(screen.getByText(/Verification Transparency/i)).toBeInTheDocument()
      expect(screen.getByText(/Consensus improved confidence/i)).toBeInTheDocument()
      expect(screen.getByText(/risks:/i)).toBeInTheDocument()
      expect(screen.getByText(/opportunities:/i)).toBeInTheDocument()
    })
  })
})
