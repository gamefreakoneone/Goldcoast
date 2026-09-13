import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import App from '../App'
import type { ApprovalDecision, ClipInfo } from '../api/types'
import { events, MockEventSource, recordedAds, recordedRun } from './recording'

it('replays the recorded API events, renders every judged final, seeks, reviews, and exports', async () => {
  let ads = structuredClone(recordedAds)
  const clip: ClipInfo = {
    file: 'gymnastics_simone.mp4', clip_path: 'sample_clips/gymnastics_simone.mp4', clip_url: '/clips/gymnastics_simone.mp4',
    available: true, sport: 'gymnastics', athlete_id: 'simone-biles', analyzed: true, analyzed_by: 'gemini', analyzed_at: null, notes: '', moments: [],
  }
  MockEventSource.instances = []
  vi.stubGlobal('EventSource', MockEventSource)
  const fetchMock = vi.fn(async (input: string, init?: RequestInit) => {
    let value: unknown
    if (input === '/clips') value = [clip]
    else if (input === '/runs') value = init ? { ...recordedRun, status: 'running', replay: true } : [recordedRun]
    else if (input.startsWith('/seed/')) value = []
    else if (input.endsWith('/ads')) value = ads
    else if (input.endsWith('/decision')) {
      const adId = input.split('/')[2]
      const decision: ApprovalDecision = { ...JSON.parse(String(init?.body)), ad_id: adId, decided_at: '2026-09-13T00:00:00Z' }
      ads = ads.map((ad) => ad.id === adId ? { ...ad, decision } : ad)
      value = decision
    } else if (input.endsWith('/export')) value = {
      run_id: recordedRun.id, exported_at: '2026-09-13T00:00:00Z',
      ads: ads.filter((ad) => ad.decision?.decision === 'approved').map((ad) => ({
        ad_id: ad.id, brief_id: ad.brief_id, business_id: ad.business_id, format: ad.format,
        path: `approved/${ad.id}.png`, image_url: `/media/${recordedRun.id}/approved/${ad.id}.png`, decision: ad.decision,
      })),
    }
    else throw new Error(`Unexpected request ${input}`)
    return new Response(JSON.stringify(value), { status: init && input === '/runs' ? 201 : 200 })
  })
  vi.stubGlobal('fetch', fetchMock)
  const user = userEvent.setup()
  render(<App />)
  const start = await screen.findByRole('button', { name: 'Start replay' })
  await waitFor(() => expect(start).toBeEnabled())
  await user.click(start)
  await waitFor(() => expect(MockEventSource.instances).toHaveLength(1))
  expect(JSON.parse(fetchMock.mock.calls.find(([url, init]) => url === '/runs' && init)![1]!.body as string)).toEqual({
    clip_path: clip.clip_path, replay: true, replay_from: recordedRun.id,
  })
  const source = MockEventSource.instances[0]
  act(() => { for (const event of events) source.emit(event) })
  await waitFor(() => expect(document.querySelectorAll('[data-final="true"]')).toHaveLength(12))
  for (const expected of recordedAds) {
    const card = document.querySelector(`[data-ad-id="${expected.id}"]`) as HTMLElement
    expect(card).toBeInTheDocument()
    expect(within(card).getAllByText('Pass').length).toBeGreaterThan(0)
    for (const label of ['Image quality', 'Style adherence', 'Business accuracy', 'Format compliance', 'Brand safety', 'Overall']) {
      expect(within(card).getAllByText(label).length).toBeGreaterThan(0)
    }
    expect(within(card).getByRole('button', { name: 'Approve' })).toBeEnabled()
  }
  expect(document.querySelectorAll('[data-brief-id]')).toHaveLength(6)
  expect(document.querySelectorAll('[data-event-type]')).toHaveLength(93)
  expect(source.readyState).toBe(MockEventSource.CLOSED)
  const player = screen.getByLabelText('Olympics clip') as HTMLVideoElement
  fireEvent.loadedMetadata(player)
  expect(player.currentTime).toBe(122.5)
  expect(screen.getByAltText('Best frame at 122.5s')).toHaveAttribute('src', expect.stringContaining('/frames/'))
  const card = document.querySelector(`[data-ad-id="${recordedAds[0].id}"]`) as HTMLElement
  await user.click(within(card).getByRole('button', { name: 'Approve' }))
  await waitFor(() => expect(within(card).getByRole('status')).toHaveTextContent('Approved by demo'))
  await user.click(screen.getByRole('button', { name: 'Export approved' }))
  expect(await screen.findByText('Exported 1 approved files')).toBeVisible()
  expect(screen.getByRole('link', { name: `${recordedAds[0].id}.png` })).toHaveAttribute('href', expect.stringContaining('/approved/'))
  await user.click(within(card).getByRole('button', { name: 'Reject' }))
  await user.type(within(card).getByLabelText('Rejection reason'), 'Review the logo')
  await user.click(within(card).getByRole('button', { name: 'Confirm rejection' }))
  await waitFor(() => expect(within(card).getByRole('status')).toHaveTextContent('Rejected by demo'))
  expect(within(card).getByText('Reason: Review the logo')).toBeVisible()
  expect(screen.queryByText('Exported 1 approved files')).not.toBeInTheDocument()
  expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/ads'))).toHaveLength(3)
})
