import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdCard } from '../components/AdCard'
import { galleryAds, groupAds } from '../components/AdGallery'
import { initialState, runReducer } from '../state/runStore'
import { events, recordedAds } from './recording'

describe('gallery', () => {
  it('keeps three separate brief pairs in each business', () => {
    const groups = groupAds(recordedAds)
    expect(groups.size).toBe(2)
    for (const briefs of groups.values()) {
      expect(briefs.size).toBe(3)
      for (const pair of briefs.values()) expect(pair.map((ad) => ad.format)).toEqual(['landscape', 'portrait'])
    }
  })
  it('shows only judged work, then replaces it with the final selection', () => {
    const generatedIndex = events.findIndex((event) => event.type === 'ad_generated')
    let state = events.slice(0, generatedIndex + 1).reduce(runReducer, initialState)
    expect(galleryAds(state)).toHaveLength(0)
    state = runReducer(state, events[generatedIndex + 1])
    expect(galleryAds(state)).toHaveLength(1)
    state = events.reduce(runReducer, initialState)
    expect(galleryAds(state)).toHaveLength(12)
  })
  it('shows failed scores, history, errors and keeps decisions unchanged on HTTP failure', async () => {
    const onDecision = vi.fn().mockRejectedValue(new Error('503: try again'))
    const ad = { ...recordedAds[1], verdict: { ...recordedAds[1].verdict, passed: false }, errors: ['Generation failed once'] }
    render(<AdCard ad={ad} isFinal onDecision={onDecision} />)
    expect(screen.getAllByText('Fail').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByText(/Attempt history/))
    expect(screen.getByText('Generation failed once')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }))
    fireEvent.change(screen.getByLabelText('Rejection reason'), { target: { value: 'Check the logo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('503: try again'))
    expect(onDecision).toHaveBeenCalledWith(ad.id, 'rejected', 'Check the logo')
    expect(screen.getByRole('status')).toHaveTextContent('Awaiting human review')
    expect(screen.getByRole('button', { name: 'Approve' })).toBeEnabled()
  })
  it('disables approval until the selection is final and provides a missing-media path', () => {
    render(<AdCard ad={recordedAds[0]} isFinal={false} onDecision={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled()
    fireEvent.error(screen.getByAltText('landscape discovery ad'))
    expect(screen.getByText(recordedAds[0].image_path)).toBeVisible()
  })
  it('recovers a transient missing image and stops retrying a persistent failure', () => {
    vi.useFakeTimers()
    try {
      render(<AdCard ad={recordedAds[0]} isFinal onDecision={vi.fn()} />)
      for (let attempt = 0; attempt < 2; attempt++) {
        fireEvent.error(screen.getByAltText('landscape discovery ad'))
        expect(screen.getByText(recordedAds[0].image_path)).toBeVisible()
        act(() => vi.advanceTimersByTime(750))
        expect(screen.getByAltText('landscape discovery ad')).toBeInTheDocument()
      }
      fireEvent.error(screen.getByAltText('landscape discovery ad'))
      act(() => vi.advanceTimersByTime(5000))
      expect(screen.getByText(recordedAds[0].image_path)).toBeVisible()
      expect(screen.queryByAltText('landscape discovery ad')).not.toBeInTheDocument()
    } finally { vi.useRealTimers() }
  })
})
