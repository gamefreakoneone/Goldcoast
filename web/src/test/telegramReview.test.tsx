import { act, render, renderHook, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useRun } from '../marketing/hooks'
import { ReviewPage } from '../marketing/Review'
import { api, streamEvents } from '../marketing/client'
import type { CreativeView, Run } from '../marketing/types'

vi.mock('../marketing/client', () => ({ api: vi.fn(), streamEvents: vi.fn(async () => undefined), authenticatedFetch: vi.fn(async () => new Response(new Blob())), downloadCampaign: vi.fn() }))
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks() })
const run: Run = { id: 'run', kind: 'campaign', mode: 'live', state: 'completed', input: { creative_type: 'product' }, checkpoint: {}, counters: {}, created_at: 0, finished_at: 1 }
const creative: CreativeView = { id: 'creative', version: 2, passed: true, stale: false, data: { job_id: 'run', business_id: 'b', brand_id: 'k', format: 'post', attempt: 1, width: 1080, height: 1440, sha256: 'hash', brief: { headline: 'Coffee time', subheading: 'Take a pause', cta: 'Visit', product_name: 'Latte', offer_text: '', image_prompt: 'Latte' }, verdict: { factuality: 9, brand_fidelity: 8, visual_quality: 8, legibility: 9, critical_issues: [], feedback: 'Good', detected_text: 'Coffee' }, expires_at: '2099-01-01T00:00:00Z', decision: 'approved', decision_note: '', decided_at: '2026-09-13T12:00:00Z', decided_via: 'telegram', replay: false } }

it('refreshes phone decisions and notification events after completion, then stops on unmount', async () => {
  vi.useFakeTimers()
  let reviewed = false
  vi.mocked(api).mockImplementation(async path => path.endsWith('/creatives') ? (reviewed ? [creative] : []) : path.endsWith('/result') ? null : run)
  vi.mocked(streamEvents).mockImplementation(async (_id, emit) => { if (reviewed) emit({ id: '1', type: 'notification_sent', timestamp: 1, payload: { creative_id: 'creative', message_id: 42 } }) })
  const hook = renderHook(() => useRun('run'))
  await act(async () => { await Promise.resolve() })
  expect(hook.result.current.creatives).toHaveLength(0)
  reviewed = true
  await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
  expect(hook.result.current.creatives[0].data.decided_via).toBe('telegram')
  expect(hook.result.current.events.map(e => e.type)).toContain('notification_sent')
  hook.unmount()
  const calls = vi.mocked(api).mock.calls.length
  await act(async () => { await vi.advanceTimersByTimeAsync(6000) })
  expect(vi.mocked(api).mock.calls).toHaveLength(calls)
})

it('labels a phone decision in Review', async () => {
  vi.mocked(api).mockImplementation(async path => path.endsWith('/creatives') ? [creative] : path.endsWith('/result') ? null : run)
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() }))
  render(<ReviewPage id="run" onChanged={vi.fn()} onNew={vi.fn()} />)
  expect(await screen.findByText('Decided on Telegram')).toBeVisible()
  expect(screen.getByRole('button', { name: 'Approved' })).toBeDisabled()
})

it('links the latest phone revision without replacing the original ad', async () => {
  const family = [
    { id: 'run', parent_id: null, state: 'completed', created_at: 0, started_via: 'studio' },
    { id: 'revision', parent_id: 'run', state: 'completed', created_at: 1, started_via: 'telegram' },
  ]
  vi.mocked(api).mockImplementation(async path => path.endsWith('/revisions') ? family : path.endsWith('/creatives') ? [creative] : path.endsWith('/result') ? null : run)
  render(<ReviewPage id="run" onChanged={vi.fn()} onNew={vi.fn()} />)
  expect(await screen.findByRole('link', { name: 'View latest revision' })).toHaveAttribute('href', '#/review/revision')
  expect(screen.getByRole('link', { name: /Original.*Viewing/ })).toHaveAttribute('href', '#/review/run')
  expect(screen.getByRole('link', { name: /Revision 1.*Via phone/ })).toBeVisible()
  expect(await screen.findByRole('button', { name: 'Approved' })).toBeDisabled()
})

it('shows revision feedback and criterion-specific judge reasons', async () => {
  const revised = { ...run, started_via: 'telegram' as const, input: { ...run.input, owner_feedback: 'Use warmer light', regenerate_from: 'parent' } }
  const judged = structuredClone(creative)
  judged.data.verdict.rubric_version = '2026-09-v1'
  judged.data.verdict.score_reasons = { factuality: 'The cold brew matches its reference.', brand_fidelity: 'The correct logo appears.', visual_quality: 'The cup edge is distorted.', legibility: 'The CTA has clear contrast.' }
  vi.mocked(api).mockImplementation(async path => path.endsWith('/revisions') ? [] : path.endsWith('/creatives') ? [judged] : path.endsWith('/result') ? null : revised)
  render(<ReviewPage id="run" onChanged={vi.fn()} onNew={vi.fn()} />)
  expect(await screen.findByText('Use warmer light')).toBeVisible()
  expect(screen.getByText('Via phone')).toBeVisible()
  screen.getByText(/Why these scores.*2026-09-v1/).click()
  expect(screen.getByText('The cup edge is distorted.')).toBeVisible()
})
