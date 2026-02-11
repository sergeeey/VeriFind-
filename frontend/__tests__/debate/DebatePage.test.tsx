import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DebatePage from '@/app/dashboard/debate/page'
import apiClient from '@/lib/api'

// Mock apiClient
jest.mock('@/lib/api', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}))

// Mock MultiLLMDebateView component
jest.mock('@/components/debate/MultiLLMDebateView', () => ({
  MultiLLMDebateView: ({ data }: any) => (
    <div data-testid="debate-view">
      <div>Recommendation: {data.synthesis.recommendation}</div>
      <div>Bull: {data.perspectives.bull.analysis}</div>
      <div>Bear: {data.perspectives.bear.analysis}</div>
      <div>Arbiter: {data.perspectives.arbiter.analysis}</div>
    </div>
  ),
}))

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  Sparkles: () => <svg data-testid="sparkles-icon" />,
  Loader2: () => <svg data-testid="loader-icon" />,
  AlertCircle: () => <svg data-testid="alert-icon" />,
}))

// Mock debate API response
const mockDebateResponse = {
  perspectives: {
    bull: {
      analysis: 'Strong bullish case with growth potential.',
      confidence: 0.75,
      key_points: ['Growth', 'Momentum'],
      provider: 'deepseek',
    },
    bear: {
      analysis: 'Significant bearish concerns about risks.',
      confidence: 0.65,
      key_points: ['Risks', 'Valuation'],
      provider: 'anthropic',
    },
    arbiter: {
      analysis: 'Balanced view with moderate recommendation.',
      confidence: 0.70,
      key_points: ['Balance', 'Caution'],
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

describe('DebatePage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders the page header', () => {
    render(<DebatePage />)

    expect(screen.getByText('Multi-LLM Debate')).toBeInTheDocument()
    expect(screen.getByText(/Get Bull, Bear, and Arbiter perspectives/)).toBeInTheDocument()
  })

  it('renders query form with all fields', () => {
    render(<DebatePage />)

    expect(screen.getByLabelText(/Query/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Context/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Run Multi-LLM Debate/i })).toBeInTheDocument()
  })

  it('renders example query buttons', () => {
    render(<DebatePage />)

    expect(screen.getByText(/Should I buy Tesla stock?/)).toBeInTheDocument()
    expect(screen.getByText(/Is Apple overvalued/)).toBeInTheDocument()
    expect(screen.getByText(/Should I invest in Microsoft/)).toBeInTheDocument()
  })

  it('loads example query when button clicked', async () => {
    const user = userEvent.setup()
    render(<DebatePage />)

    const exampleButton = screen.getByText(/Should I buy Tesla stock?/)
    await user.click(exampleButton)

    const queryInput = screen.getByLabelText(/Query/) as HTMLTextAreaElement
    expect(queryInput.value).toContain('Tesla')

    const contextInput = screen.getByLabelText(/Context/) as HTMLTextAreaElement
    expect(contextInput.value).toContain('TSLA')
  })

  it('shows error when submitting empty query', async () => {
    const user = userEvent.setup()
    render(<DebatePage />)

    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Please enter a query')).toBeInTheDocument()
    })

    // API should not be called
    expect(apiClient.post).not.toHaveBeenCalled()
  })

  it('shows error when context is invalid JSON', async () => {
    const user = userEvent.setup()
    render(<DebatePage />)

    // Fill query
    const queryInput = screen.getByLabelText(/Query/)
    await user.type(queryInput, 'Should I buy Tesla?')

    // Fill invalid JSON context using fireEvent to avoid curly brace issues
    const contextInput = screen.getByLabelText(/Context/)
    fireEvent.change(contextInput, { target: { value: '{invalid json}' } })

    // Submit
    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Context must be valid JSON')).toBeInTheDocument()
    })

    // API should not be called
    expect(apiClient.post).not.toHaveBeenCalled()
  })

  it('successfully submits debate query and displays results', async () => {
    const user = userEvent.setup()
    ;(apiClient.post as jest.Mock).mockResolvedValue({ data: mockDebateResponse })

    render(<DebatePage />)

    // Fill query
    const queryInput = screen.getByLabelText(/Query/)
    await user.type(queryInput, 'Should I buy Tesla stock?')

    // Submit
    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    // Should call API
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/analyze-debate', {
        query: 'Should I buy Tesla stock?',
        context: {},
      })
    })

    // Should display results
    await waitFor(() => {
      expect(screen.getByTestId('debate-view')).toBeInTheDocument()
      expect(screen.getByText('Recommendation: HOLD')).toBeInTheDocument()
      expect(screen.getByText(/Strong bullish case/)).toBeInTheDocument()
      expect(screen.getByText(/Significant bearish concerns/)).toBeInTheDocument()
    })
  })

  it('submits with context JSON', async () => {
    const user = userEvent.setup()
    ;(apiClient.post as jest.Mock).mockResolvedValue({ data: mockDebateResponse })

    render(<DebatePage />)

    // Fill query
    const queryInput = screen.getByLabelText(/Query/)
    await user.type(queryInput, 'Test query')

    // Fill valid JSON context using fireEvent to avoid curly brace issues
    const contextInput = screen.getByLabelText(/Context/)
    fireEvent.change(contextInput, { target: { value: '{"ticker": "TSLA", "price": 250.00}' } })

    // Submit
    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/analyze-debate', {
        query: 'Test query',
        context: { ticker: 'TSLA', price: 250.0 },
      })
    })
  })

  it('handles 501 error (missing packages)', async () => {
    const user = userEvent.setup()
    ;(apiClient.post as jest.Mock).mockRejectedValue({
      response: {
        status: 501,
        data: { detail: 'Missing packages' },
      },
    })

    render(<DebatePage />)

    // Fill and submit
    const queryInput = screen.getByLabelText(/Query/)
    await user.type(queryInput, 'Test query')

    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    // Should show error
    await waitFor(() => {
      expect(screen.getByText(/requires additional packages/)).toBeInTheDocument()
    })
  })

  it('handles 500 error (missing API keys)', async () => {
    const user = userEvent.setup()
    ;(apiClient.post as jest.Mock).mockRejectedValue({
      response: {
        status: 500,
        data: { detail: 'DEEPSEEK_API_KEY not found' },
      },
    })

    render(<DebatePage />)

    // Fill and submit
    const queryInput = screen.getByLabelText(/Query/)
    await user.type(queryInput, 'Test query')

    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    // Should show API key error
    await waitFor(() => {
      expect(screen.getByText(/DEEPSEEK_API_KEY not found/)).toBeInTheDocument()
    })
  })

  it('handles generic error', async () => {
    const user = userEvent.setup()
    ;(apiClient.post as jest.Mock).mockRejectedValue({
      message: 'Network error',
    })

    render(<DebatePage />)

    // Fill and submit
    const queryInput = screen.getByLabelText(/Query/)
    await user.type(queryInput, 'Test query')

    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    // Should show generic error
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument()
    })
  })

  it('disables submit button while loading', async () => {
    const user = userEvent.setup()
    ;(apiClient.post as jest.Mock).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: mockDebateResponse }), 100))
    )

    render(<DebatePage />)

    // Fill query
    const queryInput = screen.getByLabelText(/Query/)
    await user.type(queryInput, 'Test query')

    // Submit
    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    // Button should be disabled while loading
    await waitFor(() => {
      expect(submitButton).toBeDisabled()
    })

    // Wait for completion
    await waitFor(() => {
      expect(screen.getByTestId('debate-view')).toBeInTheDocument()
    })

    // Button should be enabled again
    expect(submitButton).not.toBeDisabled()
  })

  it('renders info section explaining how it works', () => {
    render(<DebatePage />)

    expect(screen.getByText('How Multi-LLM Debate Works')).toBeInTheDocument()
    expect(screen.getByText(/Parallel Execution/)).toBeInTheDocument()
    expect(screen.getByText(/Three Perspectives/)).toBeInTheDocument()
    expect(screen.getByText(/Cost & Speed/)).toBeInTheDocument()
  })

  it('clears results when new query is submitted', async () => {
    const user = userEvent.setup()
    ;(apiClient.post as jest.Mock).mockResolvedValue({ data: mockDebateResponse })

    render(<DebatePage />)

    // First submission
    const queryInput = screen.getByLabelText(/Query/)
    await user.type(queryInput, 'First query')

    const submitButton = screen.getByRole('button', { name: /Run Multi-LLM Debate/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByTestId('debate-view')).toBeInTheDocument()
    })

    // Clear and submit again
    await user.clear(queryInput)
    await user.type(queryInput, 'Second query')
    await user.click(submitButton)

    // Should call API again with new query
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/analyze-debate', {
        query: 'Second query',
        context: {},
      })
    })

    // Results should be displayed again
    await waitFor(() => {
      expect(screen.getByTestId('debate-view')).toBeInTheDocument()
    })
  })
})
