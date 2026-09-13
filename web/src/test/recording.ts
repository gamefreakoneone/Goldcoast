import raw from './fixtures/events.jsonl?raw'
import type { AdWithVerdict, JudgedAd, PipelineEvent, Run } from '../api/types'

function enrich(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(enrich)
  if (!value || typeof value !== 'object') return value
  const record = value as Record<string, unknown>
  const result = Object.fromEntries(Object.entries(record).map(([key, item]) => [key, enrich(item)]))
  if ('image_path' in record) {
    result.image_url = `/media/${record.run_id}/${String(record.image_path).replaceAll('\\', '/').split(`/${record.run_id}/`)[1]}`
  }
  if ('best_frame_path' in record) {
    result.best_frame_url = record.best_frame_path ? `/media/${record.run_id}/frames/${record.id}.png` : null
    result.clip_url = `/clips/${String(record.clip_path).replaceAll('\\', '/').split('/').at(-1)}`
  }
  return result
}
export const events = raw.trim().split(/\r?\n/).map((line) => enrich(JSON.parse(line)) as PipelineEvent)
export const recordedRun = events.at(-1)!.payload as unknown as Run
export const recordedAds: AdWithVerdict[] = events.filter((event) => event.type === 'ad_final').map((event) => {
  const final = event.payload as unknown as JudgedAd
  return {
    ...final.final_ad, verdict: final.final_verdict, decision: null, errors: final.errors,
    attempts: final.attempts.map(([ad, verdict]) => ({ ad, verdict, is_final: ad.id === final.final_ad.id })),
  }
})

export class MockEventSource {
  static CLOSED = 2
  static instances: MockEventSource[] = []
  readyState = 0
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  listeners = new Map<string, (event: MessageEvent<string>) => void>()
  constructor(public url: string) { MockEventSource.instances.push(this) }
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) { this.listeners.set(type, listener) }
  emit(event: PipelineEvent) {
    this.listeners.get(event.type)?.(new MessageEvent(event.type, { data: JSON.stringify(event), lastEventId: event.id }))
  }
  close() { this.readyState = MockEventSource.CLOSED }
}
