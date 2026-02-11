import { render, screen } from '@testing-library/react'
import { MultiLLMDebateView, type MultiLLMDebateData } from '@/components/debate/MultiLLMDebateView'

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  TrendingUp: () => <svg data-testid="trending-up-icon" />,
  TrendingDown: () => <svg data-testid="trending-down-icon" />,
  Scale: () => <svg data-testid="scale-icon" />,
  CircleDollarSign: () => <svg data-testid="dollar-icon" />,
  Clock: () => <svg data-testid="clock-icon" />,
  Sparkles: () => <svg data-testid="sparkles-icon" />,
}))

// Mock data
const mockDebateData: MultiLLMDebateData = {
  perspectives: {
    bull: {
      analysis: 'Strong growth potential with positive market momentum and increasing revenue.',
      confidence: 0.75,
      key_points: [
        'Revenue growth 25% YoY',
        'Strong market position',
        'Positive technical indicators',
      ],
      provider: 'deepseek',
    },
    bear: {
      analysis: 'Significant risks including high valuation and regulatory concerns.',
      confidence: 0.65,
      key_points: [
        'P/E ratio above industry average',
        'Regulatory headwinds',
        'Market volatility increasing',
      ],
      provider: 'anthropic',
    },
    arbiter: {
      analysis: 'Balanced view considering both growth potential and material risks.',
      confidence: 0.70,
      key_points: [
        'Growth potential exists but risks are material',
        'Valuation reasonable at current price',
        'Market conditions uncertain',
      ],
      provider: 'openai',
      recommendation: 'HOLD',
    },
  },
  synthesis: {
    recommendation: 'HOLD',
    overall_confidence: 0.70,
    risk_reward_ratio: '55/45',
  },
  metadata: {
    cost_usd: 0.002,
    latency_ms: 3500,
    timestamp: 1739287654,
  },
}

describe('MultiLLMDebateView', () => {
  it('renders the main header with debate title', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText('Multi-LLM Debate Analysis')).toBeInTheDocument()
    expect(screen.getByText(/Parallel Bull\/Bear\/Arbiter perspectives/)).toBeInTheDocument()
  })

  it('displays the final recommendation badge', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    const badges = screen.getAllByText('HOLD')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows overall confidence score', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText('Overall Confidence')).toBeInTheDocument()
    expect(screen.getByText('70.0%')).toBeInTheDocument()
  })

  it('displays risk/reward ratio', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText('Risk/Reward Ratio')).toBeInTheDocument()
    expect(screen.getByText('55/45')).toBeInTheDocument()
  })

  it('shows metadata (latency and cost)', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    // Latency: 3500ms = 3.5s
    expect(screen.getByText('3.5s')).toBeInTheDocument()

    // Cost: $0.0020
    expect(screen.getByText('$0.0020')).toBeInTheDocument()
  })

  it('renders all three perspective cards (Bull, Bear, Arbiter)', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText('Bull')).toBeInTheDocument()
    expect(screen.getByText('Bear')).toBeInTheDocument()
    expect(screen.getByText('Arbiter')).toBeInTheDocument()
  })

  it('displays bull perspective content', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText('Optimistic Analysis')).toBeInTheDocument()
    expect(screen.getByText(/Strong growth potential/)).toBeInTheDocument()
    expect(screen.getByText('Revenue growth 25% YoY')).toBeInTheDocument()
  })

  it('displays bear perspective content', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText('Skeptical Analysis')).toBeInTheDocument()
    expect(screen.getByText(/Significant risks/)).toBeInTheDocument()
    expect(screen.getByText('P/E ratio above industry average')).toBeInTheDocument()
  })

  it('displays arbiter perspective content with recommendation', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText('Balanced Synthesis')).toBeInTheDocument()
    expect(screen.getByText(/Balanced view considering/)).toBeInTheDocument()
    expect(screen.getByText('Growth potential exists but risks are material')).toBeInTheDocument()

    // Arbiter should have recommendation displayed
    const holdBadges = screen.getAllByText('HOLD')
    expect(holdBadges.length).toBeGreaterThan(1) // Both in header and arbiter card
  })

  it('displays provider badges for each perspective', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText('deepseek')).toBeInTheDocument()
    expect(screen.getByText('anthropic')).toBeInTheDocument()
    expect(screen.getByText('openai')).toBeInTheDocument()
  })

  it('shows confidence scores for all perspectives', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    // Bull: 75%, Bear: 65%, Arbiter: 70%
    expect(screen.getByText('75%')).toBeInTheDocument()
    expect(screen.getByText('65%')).toBeInTheDocument()
    // 70% appears twice (overall + arbiter)
    const seventyPercent = screen.getAllByText('70%')
    expect(seventyPercent.length).toBeGreaterThanOrEqual(1)
  })

  it('displays all key points for each perspective', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    // Bull key points
    expect(screen.getByText('Revenue growth 25% YoY')).toBeInTheDocument()
    expect(screen.getByText('Strong market position')).toBeInTheDocument()

    // Bear key points
    expect(screen.getByText('Regulatory headwinds')).toBeInTheDocument()

    // Arbiter key points
    expect(screen.getByText('Valuation reasonable at current price')).toBeInTheDocument()
  })

  it('renders info footer explaining how it works', () => {
    render(<MultiLLMDebateView data={mockDebateData} />)

    expect(screen.getByText(/How it works:/)).toBeInTheDocument()
    expect(screen.getByText(/Three LLM providers analyze/)).toBeInTheDocument()
  })

  it('renders with BUY recommendation', () => {
    const buyData: MultiLLMDebateData = {
      ...mockDebateData,
      perspectives: {
        ...mockDebateData.perspectives,
        arbiter: {
          ...mockDebateData.perspectives.arbiter,
          recommendation: 'BUY',
        },
      },
      synthesis: {
        ...mockDebateData.synthesis,
        recommendation: 'BUY',
      },
    }

    render(<MultiLLMDebateView data={buyData} />)

    const buyBadges = screen.getAllByText('BUY')
    expect(buyBadges.length).toBeGreaterThan(0)
  })

  it('renders with SELL recommendation', () => {
    const sellData: MultiLLMDebateData = {
      ...mockDebateData,
      perspectives: {
        ...mockDebateData.perspectives,
        arbiter: {
          ...mockDebateData.perspectives.arbiter,
          recommendation: 'SELL',
        },
      },
      synthesis: {
        ...mockDebateData.synthesis,
        recommendation: 'SELL',
      },
    }

    render(<MultiLLMDebateView data={sellData} />)

    const sellBadges = screen.getAllByText('SELL')
    expect(sellBadges.length).toBeGreaterThan(0)
  })

  it('handles low confidence scores', () => {
    const lowConfidenceData: MultiLLMDebateData = {
      ...mockDebateData,
      perspectives: {
        ...mockDebateData.perspectives,
        bull: {
          ...mockDebateData.perspectives.bull,
          confidence: 0.30,
        },
      },
      synthesis: {
        ...mockDebateData.synthesis,
        overall_confidence: 0.35,
      },
    }

    render(<MultiLLMDebateView data={lowConfidenceData} />)

    expect(screen.getByText('30%')).toBeInTheDocument()
    expect(screen.getByText('35.0%')).toBeInTheDocument()
  })

  it('handles high cost and latency', () => {
    const slowData: MultiLLMDebateData = {
      ...mockDebateData,
      metadata: {
        cost_usd: 0.05,
        latency_ms: 12500,
        timestamp: Date.now(),
      },
    }

    render(<MultiLLMDebateView data={slowData} />)

    expect(screen.getByText('12.5s')).toBeInTheDocument()
    expect(screen.getByText('$0.0500')).toBeInTheDocument()
  })
})
