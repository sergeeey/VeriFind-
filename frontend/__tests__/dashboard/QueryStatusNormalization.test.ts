import { normalizeQueryStatusPayload } from '@/lib/query-status'

describe('normalizeQueryStatusPayload', () => {
  it('maps backend processing + node to frontend state and percent progress', () => {
    const normalized = normalizeQueryStatusPayload(
      {
        query_id: 'q1',
        status: 'processing',
        current_node: 'PLAN',
        progress: 0.2,
      },
      'fallback'
    )

    expect(normalized.query_id).toBe('q1')
    expect(normalized.state).toBe('planning')
    expect(normalized.progress).toBe(20)
  })

  it('maps backend completed status and clamps progress', () => {
    const normalized = normalizeQueryStatusPayload(
      {
        query_id: 'q2',
        status: 'completed',
        progress: 150,
      },
      'fallback'
    )

    expect(normalized.state).toBe('completed')
    expect(normalized.progress).toBe(100)
  })
})
