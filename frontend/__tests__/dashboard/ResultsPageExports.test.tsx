import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import ResultsPage from '@/app/dashboard/results/[id]/page'

const mockPush = jest.fn()
const mockToast = jest.fn()

jest.mock('next/navigation', () => ({
  useParams: () => ({ id: 'ep-123' }),
  useRouter: () => ({
    push: mockPush,
  }),
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

jest.mock('@/components/results/ResultsHeader', () => ({
  ResultsHeader: () => <div>ResultsHeader</div>,
}))
jest.mock('@/components/results/FactsTable', () => ({
  FactsTable: () => <div>FactsTable</div>,
}))
jest.mock('@/components/results/DebateViewer', () => ({
  DebateViewer: () => <div>DebateViewer</div>,
}))
jest.mock('@/components/results/SynthesisCard', () => ({
  SynthesisCard: () => <div>SynthesisCard</div>,
}))
jest.mock('@/components/results/CodeViewer', () => ({
  CodeViewer: () => <div>CodeViewer</div>,
}))
jest.mock('@/components/results/FactDetailsDialog', () => ({
  FactDetailsDialog: () => <div>FactDetailsDialog</div>,
}))
jest.mock('@/components/charts/ChartContainer', () => ({
  ChartContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
jest.mock('@/components/charts/TimeRangeSelector', () => ({
  TimeRangeSelector: () => <div>TimeRangeSelector</div>,
}))
jest.mock('@/components/charts/CandlestickChart', () => ({
  CandlestickChart: () => <div>CandlestickChart</div>,
}))
jest.mock('@/components/charts/ConfidenceTrendChart', () => ({
  ConfidenceTrendChart: () => <div>ConfidenceTrendChart</div>,
}))
jest.mock('@/components/charts/DebateDistributionChart', () => ({
  DebateDistributionChart: () => <div>DebateDistributionChart</div>,
}))
jest.mock('@/components/charts/ExecutionTimeHistogram', () => ({
  ExecutionTimeHistogram: () => <div>ExecutionTimeHistogram</div>,
}))
jest.mock('@/components/charts/FactTimelineChart', () => ({
  FactTimelineChart: () => <div>FactTimelineChart</div>,
}))
jest.mock('@/components/layout/DisclaimerBanner', () => ({
  DisclaimerFooter: () => <div>DisclaimerFooter</div>,
}))

const { api } = jest.requireMock('@/lib/api') as { api: { getEpisode: jest.Mock } }

describe('ResultsPage report export', () => {
  beforeEach(() => {
    jest.resetAllMocks()
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'
    global.fetch = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/verification/')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            verification_score: 0.82,
            confidence_before: 0.78,
            confidence_after: 0.82,
            confidence_delta: 0.04,
            confidence_rationale: 'Debate improved confidence due to consensus.',
            key_risks: ['Valuation compression'],
            key_opportunities: ['Margin expansion'],
          }),
        })
      }
      return Promise.resolve({
        ok: true,
        blob: async () => new Blob(['report']),
      })
    }) as jest.Mock

    api.getEpisode.mockResolvedValue({
      data: {
        episode_id: 'ep-123',
        query_text: 'AAPL outlook',
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

    global.URL.createObjectURL = jest.fn(() => 'blob:report')
    global.URL.revokeObjectURL = jest.fn()
  })

  it('downloads JSON report from backend report endpoint', async () => {
    const clickMock = jest.fn()
    const anchor = { click: clickMock, href: '', download: '' } as unknown as HTMLAnchorElement
    const originalCreateElement = document.createElement.bind(document)
    const createElementSpy = jest.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      if (tagName === 'a') return anchor
      return originalCreateElement(tagName)
    })

    render(<ResultsPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Report JSON/i })).toBeInTheDocument()
      expect(screen.getByText(/Verification Transparency/i)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Report JSON/i }))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/report/ep-123?format=json')
      expect(anchor.download).toBe('report_ep-123.json')
      expect(clickMock).toHaveBeenCalled()
    })

    createElementSpy.mockRestore()
  })

  it('downloads Markdown report from backend report endpoint', async () => {
    const clickMock = jest.fn()
    const anchor = { click: clickMock, href: '', download: '' } as unknown as HTMLAnchorElement
    const originalCreateElement = document.createElement.bind(document)
    const createElementSpy = jest.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      if (tagName === 'a') return anchor
      return originalCreateElement(tagName)
    })

    render(<ResultsPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Report MD/i })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: /Report MD/i }))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/report/ep-123?format=md')
      expect(anchor.download).toBe('report_ep-123.md')
      expect(clickMock).toHaveBeenCalled()
    })

    createElementSpy.mockRestore()
  })
})
