import { useEffect, useState } from 'react'
import { authenticatedFetch, api, streamEvents } from './client'
import type { Campaign, CreativeView, Run, StudioEvent, Brand } from './types'
import { terminal } from './types'

export function PrivateImage({ path, alt, className = '' }: { path: string; alt: string; className?: string }) {
  const [source, setSource] = useState('')
  const [error, setError] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    let url = ''
    setSource(''); setError(false)
    authenticatedFetch(path, { signal: controller.signal }).then(r => r.blob()).then(blob => {
      if (controller.signal.aborted) return
      url = URL.createObjectURL(blob); setSource(url)
    }).catch(() => { if (!controller.signal.aborted) setError(true) })
    return () => { controller.abort(); if (url) URL.revokeObjectURL(url) }
  }, [path])
  return source ? <img src={source} alt={alt} className={className} />
    : <div className={`media-placeholder ${className}`} role="status">{error ? 'Image unavailable' : 'Loading image…'}</div>
}

export function useRun(id: string | null) {
  const [run, setRun] = useState<Run | null>(null)
  const [result, setResult] = useState<Campaign | Brand | null>(null)
  const [creatives, setCreatives] = useState<CreativeView[]>([])
  const [events, setEvents] = useState<StudioEvent[]>([])
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    setRun(null); setResult(null); setCreatives([]); setEvents([]); setError('')
  }, [id])
  useEffect(() => {
    if (!id) return
    let active = true
    let timer: ReturnType<typeof setTimeout>
    const load = async () => {
      try {
        const [next, output, images] = await Promise.all([
          api<Run>(`/runs/${id}`), api<Campaign | Brand | null>(`/runs/${id}/result`),
          api<CreativeView[]>(`/runs/${id}/creatives`),
        ])
        if (!active) return
        setRun(next); setResult(output); setCreatives(images); setError('')
        if (!terminal(next)) timer = setTimeout(load, 2000)
      } catch (reason) {
        if (active) { setError(String(reason instanceof Error ? reason.message : reason)); timer = setTimeout(load, 4000) }
      }
    }
    void load()
    return () => { active = false; clearTimeout(timer) }
  }, [id, revision])
  useEffect(() => {
    if (!id) return
    const controller = new AbortController()
    let cursor = '-1'
    let timer: ReturnType<typeof setTimeout>
    const connect = async () => {
      try {
        await streamEvents(id, event => {
          cursor = event.id
          setEvents(previous => previous.some(e => e.id === event.id) ? previous : [...previous, event].slice(-500))
          if (event.type.startsWith('run_')) setRevision(value => value + 1)
        }, controller.signal, cursor)
        if (!controller.signal.aborted) {
          const next = await api<Run>(`/runs/${id}`)
          if (!terminal(next)) timer = setTimeout(connect, 1000)
        }
      } catch { if (!controller.signal.aborted) timer = setTimeout(connect, 2500) }
    }
    void connect()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [id])
  return { run, result, creatives, events, error, reload: () => setRevision(value => value + 1) }
}

