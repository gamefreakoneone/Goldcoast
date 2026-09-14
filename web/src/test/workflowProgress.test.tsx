import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Feed, WorkflowProgress } from '../marketing/Feed'
import { useRun } from '../marketing/hooks'
import { api } from '../marketing/client'

vi.mock('../marketing/client', () => ({ api: vi.fn() }))

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


it('shows the recorded provider failure on Your Feed without starting paid discovery', async () => {
  const run = { id: 'feed-job', kind: 'feed' as const, mode: 'live' as const, state: 'failed' as const, input: {}, checkpoint: {}, counters: {}, created_at: 0, finished_at: 1 }
  vi.mocked(api).mockResolvedValue(run)
  vi.mocked(useRun).mockReturnValue({ run, events: [{ id: 'error', timestamp: 0, type: 'workflow_error', payload: { error: 'ClientError', message: 'The AI provider rejected the analysis request. Check the model configuration before retrying.' } }], result: null, creatives: [], error: '', reload: vi.fn() })
  render(<Feed usage={{ live_enabled: true, campaign_remaining: 2, brand_remaining: 2, feed_remaining: 9, active_job: null, global_campaign_remaining: 2, global_brand_remaining: 2 }} onUse={vi.fn()} onRefresh={vi.fn()} />)
  expect(await screen.findByText(/AI provider rejected the analysis request/)).toBeVisible()
  expect(vi.mocked(api).mock.calls.every(([path, body]) => path === '/feed' && body === undefined)).toBe(true)
})
