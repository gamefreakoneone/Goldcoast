import { eventTypes } from './types'
import type {
  AdBrief, AdStyle, AdWithVerdict, ApprovalDecision, Athlete, Business, ClipInfo,
  DecisionCreate, ExportManifest, MomentView, PipelineEvent, Run, RunCreate,
} from './types'

const base = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')
export const mediaUrl = (path: string) => /^https?:\/\//.test(path) ? path : `${base}${path}`
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : String(error)

async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${base}${path}`, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status}: ${detail || response.statusText}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  clips: () => request<ClipInfo[]>('/clips'),
  runs: () => request<Run[]>('/runs'),
  run: (id: string) => request<Run>(`/runs/${encodeURIComponent(id)}`),
  start: (body: RunCreate) => request<Run>('/runs', body),
  moments: (id: string) => request<MomentView[]>(`/runs/${encodeURIComponent(id)}/moments`),
  briefs: (id: string) => request<AdBrief[]>(`/runs/${encodeURIComponent(id)}/briefs`),
  ads: (id: string) => request<AdWithVerdict[]>(`/runs/${encodeURIComponent(id)}/ads`),
  decide: (id: string, body: DecisionCreate) => request<ApprovalDecision>(`/ads/${encodeURIComponent(id)}/decision`, body),
  export: (id: string) => request<ExportManifest>(`/runs/${encodeURIComponent(id)}/export`),
  athletes: () => request<Athlete[]>('/seed/athletes'),
  businesses: () => request<Business[]>('/seed/businesses'),
  styles: () => request<AdStyle[]>('/seed/ad-styles'),
}

export type Connection = 'connecting' | 'connected' | 'reconnecting' | 'closed'

export function subscribeToRun(
  id: string,
  onEvent: (event: PipelineEvent) => void,
  onConnection: (state: Connection) => void,
  onError: (message: string) => void,
) {
  const source = new EventSource(`${base}/runs/${encodeURIComponent(id)}/events`)
  let lastId = -1
  onConnection('connecting')
  source.onopen = () => onConnection('connected')
  source.onerror = () => onConnection(source.readyState === EventSource.CLOSED ? 'closed' : 'reconnecting')
  for (const type of eventTypes) {
    source.addEventListener(type, (message: MessageEvent<string>) => {
      try {
        const event = JSON.parse(message.data) as PipelineEvent
        if (event.run_id !== id || !eventTypes.includes(event.type) || !/^\d+$/.test(event.id)) {
          throw new Error('Invalid pipeline event')
        }
        if (Number(event.id) <= lastId) return
        lastId = Number(event.id)
        if (event.type === 'run_completed' || event.type === 'run_failed') {
          source.close()
          onConnection('closed')
        }
        onEvent(event)
      } catch (error) {
        source.close()
        onConnection('closed')
        onError(errorMessage(error))
      }
    })
  }
  return () => source.close()
}
