import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WorkflowProgress } from '../marketing/Feed'
import { useRun } from '../marketing/hooks'

vi.mock('../marketing/hooks', () => ({ useRun: vi.fn() }))

describe('failed workflow progress', () => {
  it.each(['pending', 'failed'])('shows a %s stage as failed for a terminal run', state => {
    vi.mocked(useRun).mockReturnValue({ run: { id: 'test', kind: 'campaign', mode: 'live', input: {}, counters: {}, created_at: 0, finished_at: 1, state: 'failed', checkpoint: {
      chief_plan: { state: 'completed' }, local_scout: { state },
    } }, events: [{ id: 'e', timestamp: 0, type: 'workflow_error', payload: {
      error: 'ValidationError', message: 'Invalid JSON: EOF input_value=private provider output',
    } }], error: '', result: null, creatives: [], reload: vi.fn() })
    render(<WorkflowProgress id="test" />)
    expect(screen.getByText('Completed')).toBeVisible()
    expect(screen.getByText('Failed')).toBeVisible()
    expect(screen.queryByText('In progress')).not.toBeInTheDocument()
    expect(screen.getByText(/agent returned an incomplete or invalid response/)).toBeVisible()
    expect(screen.queryByText(/private provider output/)).not.toBeInTheDocument()
  })
})
