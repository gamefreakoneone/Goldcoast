import { describe, expect, it, vi } from 'vitest'
import { parseEventBlock, streamEvents } from '../marketing/client'

vi.mock('../marketing/auth', () => ({ accessToken: vi.fn(async () => 'fixture-access') }))

describe('authenticated studio events', () => {
  it('ignores heartbeats and validates event envelopes', () => {
    expect(parseEventBlock(': heartbeat')).toBeNull()
    expect(parseEventBlock('id: 2\ndata: {"id":"2","type":"stage_completed","timestamp":1,"payload":{}}')?.id).toBe('2')
    expect(() => parseEventBlock('data: {"id":2}')).toThrow('Invalid workflow event')
  })
  it('handles split UTF-8 chunks and carries auth and resume cursor', async () => {
    const text = 'id: 4\ndata: {"id":"4","type":"stage_completed","timestamp":1,"payload":{"text":"café"}}\n\n'
    const bytes = new TextEncoder().encode(text)
    const stream = new ReadableStream<Uint8Array>({ start(controller) {
      for (let i = 0; i < bytes.length; i += 3) controller.enqueue(bytes.slice(i, i + 3))
      controller.close()
    } })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(stream))
    const events: string[] = []
    await streamEvents('run', event => events.push(String(event.payload.text)), new AbortController().signal, '3')
    expect(events).toEqual(['café'])
    const headers = new Headers(fetchMock.mock.calls[0][1]?.headers)
    expect(headers.get('Authorization')).toBe('Bearer fixture-access')
    expect(headers.get('Last-Event-ID')).toBe('3')
  })
})
