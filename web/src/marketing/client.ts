import { accessToken } from './auth'
import type { StudioEvent } from './types'

const base = import.meta.env.VITE_STUDIO_API_BASE || '/api/v2'

export async function authenticatedFetch(path: string, init: RequestInit = {}) {
  const token = await accessToken()
  const headers = new Headers(init.headers)
  headers.set('Authorization', 'Bearer ' + token)
  let response = await fetch(base + path, { ...init, headers })
  if (response.status === 401) {
    headers.set('Authorization', 'Bearer ' + await accessToken(token))
    response = await fetch(base + path, { ...init, headers })
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : Array.isArray(body.detail)
      ? body.detail.map((entry: { msg: string; loc?: string[] }) => entry.msg).join('; ')
      : `Request failed (${response.status}). Please try again.`
    throw new Error(detail)
  }
  return response
}

export async function api<T>(path: string, body?: unknown, method = body === undefined ? 'GET' : 'POST', signal?: AbortSignal) {
  const response = await authenticatedFetch(path, body === undefined ? { signal } : {
    signal,
    method, headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
    body: JSON.stringify(body),
  })
  return response.json() as Promise<T>
}

export function parseEventBlock(block: string): StudioEvent | null {
  const data = block.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
  if (!data) return null
  const value = JSON.parse(data)
  if (typeof value.id !== 'string' || typeof value.type !== 'string' || typeof value.timestamp !== 'number') {
    throw new Error('Invalid workflow event')
  }
  return value as StudioEvent
}

export async function streamEvents(runId: string, onEvent: (event: StudioEvent) => void,
  signal: AbortSignal, after = '-1') {
  const response = await authenticatedFetch(`/runs/${runId}/events`, {
    signal, headers: { 'Last-Event-ID': after },
  })
  if (!response.body) throw new Error('Live updates are unavailable')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (!signal.aborted) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done }).replace(/\r/g, '')
      if (buffer.length > 1_000_000) throw new Error('Workflow event exceeds the display limit')
      let boundary: number
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const event = parseEventBlock(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        if (event) onEvent(event)
      }
      if (done) return
    }
  } finally { await reader.cancel().catch(() => undefined); reader.releaseLock() }
}

export async function downloadCampaign(id: string) {
  const blob = await (await authenticatedFetch(`/runs/${id}/export`)).blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = 'goldcoast-campaign.zip'; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
