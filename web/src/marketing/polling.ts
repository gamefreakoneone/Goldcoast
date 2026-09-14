import { useEffect } from 'react'

export function useVisiblePolling(load: (signal: AbortSignal) => Promise<void>, enabled = true) {
  useEffect(() => {
    if (!enabled) return
    let active = true
    let busy = false
    let pending = false
    let timer: ReturnType<typeof setTimeout> | undefined
    let controller: AbortController | undefined
    const run = async () => {
      clearTimeout(timer)
      if (!active || document.visibilityState !== 'visible') return
      if (busy) { pending = true; return }
      busy = true
      pending = false
      controller = new AbortController()
      try { await load(controller.signal).catch(() => undefined) }
      finally {
        busy = false
        if (active && document.visibilityState === 'visible') {
          if (pending) void run()
          else timer = setTimeout(() => void run(), 3000)
        }
      }
    }
    const wake = () => {
      clearTimeout(timer)
      if (document.visibilityState === 'visible') void run()
      else { pending = false; controller?.abort() }
    }
    void run()
    window.addEventListener('focus', wake)
    document.addEventListener('visibilitychange', wake)
    return () => {
      active = false
      clearTimeout(timer)
      controller?.abort()
      window.removeEventListener('focus', wake)
      document.removeEventListener('visibilitychange', wake)
    }
  }, [load, enabled])
}
