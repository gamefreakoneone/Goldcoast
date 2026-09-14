import { act, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useVisiblePolling } from '../marketing/polling'

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

it('polls idle pages, coalesces focus, aborts hidden requests and stops on unmount', async () => {
  vi.useFakeTimers()
  let visibility = 'visible'
  vi.spyOn(document, 'visibilityState', 'get').mockImplementation(() => visibility as DocumentVisibilityState)
  let resolve: (() => void) | undefined
  const signals: AbortSignal[] = []
  const load = vi.fn((signal: AbortSignal) => { signals.push(signal); return new Promise<void>(done => { resolve = done }) })
  const hook = renderHook(() => useVisiblePolling(load))
  expect(load).toHaveBeenCalledTimes(1)
  await act(async () => { window.dispatchEvent(new Event('focus')); await vi.advanceTimersByTimeAsync(6000) })
  expect(load).toHaveBeenCalledTimes(1)
  await act(async () => { resolve!(); await Promise.resolve() })
  expect(load).toHaveBeenCalledTimes(2)
  await act(async () => { visibility = 'hidden'; document.dispatchEvent(new Event('visibilitychange')); resolve!(); await vi.advanceTimersByTimeAsync(6000) })
  expect(signals[1].aborted).toBe(true)
  expect(load).toHaveBeenCalledTimes(2)
  await act(async () => { visibility = 'visible'; document.dispatchEvent(new Event('visibilitychange')); resolve!(); await Promise.resolve() })
  expect(load).toHaveBeenCalledTimes(3)
  await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
  expect(load).toHaveBeenCalledTimes(4)
  hook.unmount()
  expect(signals[3].aborted).toBe(true)
  await act(async () => { resolve!(); await vi.advanceTimersByTimeAsync(6000) })
  expect(load).toHaveBeenCalledTimes(4)
})
