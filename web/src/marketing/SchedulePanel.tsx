import { useEffect, useState } from 'react'
import { api } from './client'
import { Notice } from './ui'
import type { Resource } from './types'

interface Schedule { enabled: boolean; hour: number; goal: string; last_local_date?: string | null; last_job_id?: string | null; last_error?: string | null }
const empty: Schedule = { enabled: false, hour: 9, goal: 'Bring more neighbors in today' }

export function SchedulePanel({ timezone }: { timezone: string }) {
  const [row, setRow] = useState<Resource<Schedule> | null>(null)
  const [form, setForm] = useState<Schedule>(empty)
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  useEffect(() => {
    let active = true
    api<Resource<Schedule> | null>('/schedule').then(value => {
      if (active) { setRow(value); setForm(value?.data ?? empty); setLoaded(true) }
    }).catch(reason => { if (active) setError(String(reason)) })
    return () => { active = false }
  }, [])
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try {
      const next = await api<Resource<Schedule>>('/schedule', { version: row?.version ?? 0, schedule: { enabled: form.enabled, hour: form.hour, goal: form.goal } }, 'PUT')
      setRow(next); setForm(next.data); setNotice(next.data.enabled ? 'Daily schedule enabled.' : 'Daily schedule disabled.')
    } catch (reason) { setError(String(reason)) } finally { setBusy(false) }
  }
  return <form className="panel owner-controls" onSubmit={save}><h2>A daily head start</h2><p className="small muted">Optional. One live campaign per day, at or after your chosen hour in {timezone}. Uses your live allowance and the same shared limits. Business and brand must be confirmed; the owner can pause all live work.</p>
    {error && <Notice>{error}</Notice>}{notice && <Notice tone="success">{notice}</Notice>}
    <label className="checkbox"><input disabled={!loaded || busy} type="checkbox" checked={form.enabled} onChange={e => setForm({ ...form, enabled: e.target.checked })}/>Automatically start my daily workflow</label>
    <div className="form-grid"><label>Local start hour<select disabled={!loaded || busy} value={form.hour} onChange={e => setForm({ ...form, hour: Number(e.target.value) })}>{Array.from({ length: 24 }, (_, hour) => <option key={hour} value={hour}>{String(hour).padStart(2, '0')}:00</option>)}</select></label><label>Daily campaign goal<input disabled={!loaded || busy} required maxLength={1500} value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })}/></label></div>
    <div className="form-footer"><button className="primary" disabled={!loaded || busy}>{busy ? 'Saving…' : 'Save daily schedule'}</button><span className="small muted">{row?.data.last_local_date ? `Last scheduled: ${row.data.last_local_date}` : 'Manual start is the default.'}</span></div>{row?.data.last_error && <p className="small muted">{row.data.last_error}</p>}
  </form>
}
