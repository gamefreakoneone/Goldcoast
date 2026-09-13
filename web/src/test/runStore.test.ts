import { describe, expect, it } from 'vitest'
import { finalAds, initialState, runReducer } from '../state/runStore'
import { events, recordedAds } from './recording'

describe('recorded event reducer', () => {
  it('retains all moments, briefs, attempts, verdicts and final selections', () => {
    const state = events.reduce(runReducer, initialState)
    expect(state.status).toBe('completed')
    expect(state.moments.map((moment) => moment.best_frame_s)).toEqual([122.5, 41, 91.5])
    expect(Object.keys(state.briefs)).toHaveLength(6)
    expect(Object.keys(state.generatedById)).toHaveLength(17)
    expect(Object.keys(state.verdictsByAd)).toHaveLength(17)
    expect(state.timeline).toHaveLength(93)
    expect(finalAds(state).map((ad) => ad.id)).toEqual(recordedAds.map((ad) => ad.id))
    expect(finalAds(state).every((ad) => ad.verdict.passed)).toBe(true)
    expect(finalAds(state).flatMap((ad) => ad.attempts)).toHaveLength(17)
  })
  it('ignores duplicate, stale and other-run events after reconnect', () => {
    const state = events.slice(0, 15).reduce(runReducer, initialState)
    expect(runReducer(state, events[14])).toBe(state)
    expect(runReducer(state, events[0])).toBe(state)
    expect(runReducer(state, { ...events[15], run_id: 'other-run' })).toBe(state)
  })
  it('retains ads and failure reasons after a failed run', () => {
    const state = events.slice(0, -1).reduce(runReducer, initialState)
    const failures = [{ stage: 'judge', message: 'Recorded failure', moment_id: null, brief_id: null, format: null }]
    const failed = runReducer(state, { ...events.at(-1)!, type: 'run_failed', payload: { failures, reason: 'Recorded failure' } })
    expect(failed.status).toBe('failed')
    expect(failed.failures).toEqual(failures)
    expect(finalAds(failed)).toHaveLength(12)
  })
  it('never admits a final without a matching verdict', () => {
    const event = events.find((item) => item.type === 'ad_final')!
    const state = runReducer(initialState, { ...event, payload: { ...event.payload, final_verdict: null } })
    expect(finalAds(state)).toEqual([])
  })
})
