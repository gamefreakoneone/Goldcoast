import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ReviewPage } from '../marketing/Review'
import { useRun } from '../marketing/hooks'
import type { Campaign, CreativeView } from '../marketing/types'

vi.mock('../marketing/client', () => ({ api: vi.fn(), downloadCampaign: vi.fn() }))
vi.mock('../marketing/hooks', () => ({ useRun: vi.fn(), PrivateImage: () => null }))

it('shows the recorded weather signal and provider in campaign thinking', async () => {
  const source = { id: 'weather', url: 'https://api.open-meteo.com/v1/forecast', title: 'Open-Meteo forecast', text: 'Los Angeles: high 34°C, clear sky.', provider: 'weather', retrieved_at: '2026-09-13T12:00:00Z', expires_at: '2026-09-14T06:59:59Z', content_hash: 'hash' }
  const selected = { id: 'heat', title: 'Cool down', angle: 'An iced latte', product_name: 'Latte', category: 'local' as const, source_ids: ['weather'], expires_at: source.expires_at, fit: 9, timeliness: 9, risks: [] }
  const campaign: Campaign = { candidates: [selected], selected, rationale: 'A hot afternoon', rejected: [], graph: { sources: [source], nodes: [], edges: [], built_at: source.retrieved_at }, local_signals: { available: true, reason: '', summary: [source.text], sources: [source], claims: [] } }
  vi.mocked(useRun).mockReturnValue({ run: { id: 'run', kind: 'campaign', mode: 'live', state: 'completed', input: {}, checkpoint: {}, counters: {}, created_at: 0, finished_at: 1 }, result: campaign, creatives: [], events: [], error: '', reload: vi.fn() })
  const creative: CreativeView = { id: 'ad', version: 1, passed: true, stale: false, data: { job_id: 'run', business_id: 'b', brand_id: 'k', format: 'landscape', attempt: 1, width: 1920, height: 1080, sha256: 'hash', brief: { headline: 'Cool down', subheading: 'Take a pause', cta: 'Visit', product_name: 'Latte', offer_text: '', image_prompt: 'Cold latte' }, verdict: { factuality: 8, brand_fidelity: 8, visual_quality: 8, legibility: 8, critical_issues: [], feedback: 'Good', detected_text: 'Latte' }, expires_at: '2099-01-01T00:00:00Z', decision: 'pending', decision_note: '', decided_at: null, replay: false } }
  const state = vi.mocked(useRun).getMockImplementation()!('run')
  vi.mocked(useRun).mockReturnValue({ ...state, creatives: [creative] })
  const view = render(<ReviewPage id="run" onNew={vi.fn()} onChanged={vi.fn()} />)
  await userEvent.click(screen.getByRole('button', { name: 'The thinking' }))
  expect(screen.getByText("Today's signals")).toBeVisible()
  expect(screen.getAllByText(source.text)[0]).toBeVisible()
  await userEvent.click(screen.getByText('All source material'))
  expect(screen.getByText(/Open-Meteo weather/)).toBeVisible()
  expect(screen.getByText(/Weather influence was not recorded/)).toBeVisible()
  creative.data.brief.weather_influence = { influenced: true, rationale: 'A cold latte and cooling imagery suit the warm afternoon.' }
  view.rerender(<ReviewPage id="run" onNew={vi.fn()} onChanged={vi.fn()} />)
  expect(screen.getByText(/A cold latte and cooling imagery/)).toBeVisible()
})
