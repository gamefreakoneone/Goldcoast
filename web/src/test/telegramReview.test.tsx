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
