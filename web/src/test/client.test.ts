import { describe, expect, it, vi } from 'vitest'
import { subscribeToRun } from '../api/client'
import { events, MockEventSource, recordedRun } from './recording'

describe('EventSource lifecycle', () => {
  it('keeps the native source for Last-Event-ID reconnects, deduplicates, and closes at terminal', () => {
    MockEventSource.instances = []
    vi.stubGlobal('EventSource', MockEventSource)
    const onEvent = vi.fn(), onConnection = vi.fn(), onError = vi.fn()
    subscribeToRun(recordedRun.id, onEvent, onConnection, onError)
    const source = MockEventSource.instances[0]
    source.onopen?.()
    source.emit(events[0])
    source.onerror?.()
    expect(onConnection).toHaveBeenLastCalledWith('reconnecting')
    source.onopen?.()
    source.emit(events[0])
    source.emit(events[1])
    expect(onEvent).toHaveBeenCalledTimes(2)
    expect(MockEventSource.instances).toHaveLength(1)
    source.emit(events.at(-1)!)
    expect(source.readyState).toBe(MockEventSource.CLOSED)
    expect(onConnection).toHaveBeenLastCalledWith('closed')
    expect(onError).not.toHaveBeenCalled()
  })
  it('closes failed streams and cleans up on unmount', () => {
    vi.stubGlobal('EventSource', MockEventSource)
    const dispose = subscribeToRun(recordedRun.id, vi.fn(), vi.fn(), vi.fn())
    const source = MockEventSource.instances.at(-1)!
    source.emit({ ...events.at(-1)!, type: 'run_failed' })
    expect(source.readyState).toBe(MockEventSource.CLOSED)
    dispose()
    expect(source.readyState).toBe(MockEventSource.CLOSED)
  })
})
