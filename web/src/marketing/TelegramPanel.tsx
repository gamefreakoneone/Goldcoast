import { useEffect, useState } from 'react'
import { api } from './client'
import { Notice } from './ui'
import type { NotificationConnection, TelegramLink } from './types'

export function TelegramPanel() {
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [connection, setConnection] = useState<NotificationConnection | null>(null)
  const [pending, setPending] = useState<(TelegramLink & { expires: number }) | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadAttempt, setLoadAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    Promise.all([api<{ configured: boolean }>('/notifications/config'), api<NotificationConnection | null>('/notifications')])
      .then(([config, value]) => { if (active) { setConfigured(config.configured); setConnection(value) } })
      .catch(reason => { if (active) setError(reason.message === 'Not Found' ? 'The running API does not have the Telegram routes. Restart the Goldcoast API and worker, then retry.' : String(reason.message ?? reason)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [loadAttempt])
  useEffect(() => {
    if (!pending) return
    let active = true
    let loading = false
    const timer = setInterval(async () => {
      if (Date.now() >= pending.expires) { setPending(null); setError('This link expired. Connect again.'); return }
      if (loading) return
      loading = true
      try {
        const value = await api<NotificationConnection | null>('/notifications')
        if (active && value) { setConnection(value); setPending(null); setError('') }
      } catch (reason) { if (active) setError(reason instanceof Error ? reason.message : String(reason)) }
      finally { loading = false }
    }, 3000)
    return () => { active = false; clearInterval(timer) }
  }, [pending])
  const act = async (action: 'connect' | 'disconnect' | 'toggle') => {
    setBusy(true); setError('')
    try {
      if (action === 'connect') {
        const link = await api<TelegramLink>('/notifications/telegram/link', {})
        setPending({ ...link, expires: Date.now() + 600_000 })
      } else if (action === 'disconnect') {
        await api('/notifications/telegram', {}, 'DELETE')
        setConnection(null); setPending(null)
      } else if (connection) {
        setConnection(await api<NotificationConnection>('/notifications', { enabled: !connection.enabled }, 'PUT'))
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) }
    finally { setBusy(false) }
  }
  return <section className="panel"><h2>Telegram approvals</h2>
    <p role="status">{loading ? 'Loading Telegram settings...' : configured === null ? 'Telegram settings unavailable' : !configured ? 'Not configured' : connection ? `Connected as ${connection.chat_title}` : 'Not connected'}</p>
    <p>Receive finished creatives on your phone. Approve, reject, or request changes. Nothing is published.</p>
    {error && <Notice>{error}</Notice>}
    {!loading && configured === null && <button className="secondary" onClick={() => setLoadAttempt(value => value + 1)}>Retry Telegram settings</button>}
    {configured && !connection && <button className="primary" disabled={busy} onClick={() => void act('connect')}>{pending ? 'Create a new link' : 'Connect Telegram'}</button>}
    {configured && pending && <div><p><a className="primary" href={pending.deep_link} target="_blank" rel="noreferrer">Open Telegram</a></p><p>Or send this message to the bot: <code>/start {pending.code}</code></p><small>Link expires in 10 minutes. Waiting for connection…</small></div>}
    {configured && connection && <div><label><input type="checkbox" checked={connection.enabled} disabled={busy} onChange={() => void act('toggle')}/>Enable Telegram approvals</label><button className="secondary" disabled={busy} onClick={() => void act('disconnect')}>Disconnect Telegram</button></div>}
  </section>
}
