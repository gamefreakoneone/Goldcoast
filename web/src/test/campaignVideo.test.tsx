import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { ReviewPage } from '../marketing/Review'
import { useRun } from '../marketing/hooks'
import type { Campaign, Run } from '../marketing/types'

vi.mock('../marketing/client', () => ({ api: vi.fn(async () => []), downloadCampaign: vi.fn() }))
vi.mock('../marketing/hooks', () => ({
  useRun: vi.fn(),
  PrivateImage: ({ path, alt }: { path: string; alt: string }) => <img data-path={path} alt={alt}/>,
}))

it('shows the selected campaign-video frame and the agent rationale in Review', () => {
  const run: Run = { id: 'run', kind: 'campaign', mode: 'live', state: 'completed', input: { video_asset_id: 'video' }, checkpoint: {}, counters: {}, created_at: 0, finished_at: 1 }
  const selected = { id: 'boba', category: 'evergreen' as const, title: 'Boba today', angle: 'Feature the new drink', product_name: 'Boba tea', source_ids: [], expires_at: '2099-01-01T00:00:00Z', fit: 9, timeliness: 7, risks: [] }
  const campaign: Campaign = { candidates: [selected], selected, rationale: 'The video clearly features the product.', rejected: [], graph: { sources: [], nodes: [], edges: [], built_at: '2026-09-14T12:00:00Z' }, video_evidence: { asset_id: 'video', title: 'Limited Edition Boba Tea', description: 'A fresh purple boba tea being poured.', subject: 'Boba tea', observations: 'The complete cup is centered on the counter.', search_queries: ['Los Angeles boba today'], uncertainty: 'Flavor is not readable.', best_frame_s: 2.4, frame_reason: 'The cup and toppings are fully visible.', frame_asset_id: 'frame' } }
  vi.mocked(useRun).mockReturnValue({ run, result: campaign, creatives: [], events: [], error: '', reload: vi.fn() })
  render(<ReviewPage id="run" onNew={vi.fn()} onChanged={vi.fn()} />)
  expect(screen.getByRole('heading', { name: 'Limited Edition Boba Tea' })).toBeVisible()
  expect(screen.getByText('2.4 seconds')).toBeVisible()
  expect(screen.getByText('The cup and toppings are fully visible.')).toBeVisible()
  expect(screen.getByRole('img', { name: /Selected frame/ })).toHaveAttribute('data-path', '/runs/run/video-frame')
})
