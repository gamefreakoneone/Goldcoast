import { useEffect, useState } from 'react'
import { api, authenticatedFetch } from './client'
import { useRun } from './hooks'
import { Notice } from './ui'
import type { Asset, Resource, Run, Usage } from './types'

export interface Transcript { asset_id: string; segments: { id: string; start: number; end: number; text: string; clear: boolean }[]; quotes: { id: string; segment_id: string; text: string }[]; attribution: string; reviewed: boolean; approved_quote_ids: string[] }

function SourceVideo({ id }: { id: string }) {
  const [url, setUrl] = useState('')
  const [failed, setFailed] = useState(false)
  useEffect(() => { let live = true; let value = ''; authenticatedFetch(`/assets/${id}/content`).then(r => r.blob()).then(blob => { value = URL.createObjectURL(blob); if (live) setUrl(value); else URL.revokeObjectURL(value) }).catch(() => { if (live) setFailed(true) }); return () => { live = false; if (value) URL.revokeObjectURL(value) } }, [id])
  return url ? <video controls src={url} className="testimonial-video"/> : <p>{failed ? 'Source video unavailable. Reload before reviewing quotes.' : 'Loading source video...'}</p>
}

function TranscriptEditor({ row, reload }: { row: Resource<Transcript>; reload: () => Promise<void> }) {
  const [draft, setDraft] = useState(row.data)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const save = async () => { setBusy(true); setError(''); try { await api(`/testimonials/${row.id}`, { version: row.version, transcript: draft }, 'PUT'); await reload() } catch (e) { setError(String(e)) } finally { setBusy(false) } }
  return <article className="transcript-editor"><h3>Review the source and excerpts</h3><SourceVideo id={draft.asset_id}/>{draft.segments.map((segment, i) => <label key={segment.id}>{segment.start.toFixed(1)}s - {segment.end.toFixed(1)}s {segment.clear ? '' : '(unclear - not eligible for quotes)'}<textarea value={segment.text} onChange={e => setDraft({ ...draft, reviewed: false, approved_quote_ids: [], segments: draft.segments.map((s, n) => n === i ? { ...s, text: e.target.value } : s) })}/></label>)}
    <label>Customer-approved attribution<input maxLength={100} value={draft.attribution} onChange={e => setDraft({ ...draft, attribution: e.target.value })} placeholder="Name or approved anonymous attribution"/></label>
    {draft.quotes.map((quote, i) => <div key={quote.id}><label>Exact quote<textarea maxLength={220} value={quote.text} onChange={e => setDraft({ ...draft, reviewed: false, approved_quote_ids: [], quotes: draft.quotes.map((q, n) => n === i ? { ...q, text: e.target.value } : q) })}/></label><label className="checkbox"><input type="checkbox" checked={draft.approved_quote_ids.includes(quote.id)} onChange={e => setDraft({ ...draft, approved_quote_ids: e.target.checked ? [...draft.approved_quote_ids, quote.id] : draft.approved_quote_ids.filter(id => id !== quote.id) })}/>Permit this excerpt in marketing</label></div>)}
    <label className="checkbox"><input type="checkbox" checked={draft.reviewed} onChange={e => setDraft({ ...draft, reviewed: e.target.checked, approved_quote_ids: e.target.checked ? draft.approved_quote_ids : [] })}/>I checked the transcript against the video and have permission to use the selected quotes and attribution.</label>
    {error && <Notice>{error}</Notice>}<button type="button" className="primary" disabled={busy} onClick={() => void save()}>Save testimonial review</button>
  </article>
}

export function Testimonials({ assets, usage, onSaved }: { assets: Resource<Asset>[]; usage: Usage; onSaved: () => Promise<void> }) {
  const [rows, setRows] = useState<Resource<Transcript>[]>([])
  const [jobId, setJobId] = useState<string | null>(null)
  const [selected, setSelected] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const run = useRun(jobId)
  const reload = async () => { setRows(await api('/testimonials')); await onSaved() }
  useEffect(() => { let live = true; api<Resource<Transcript>[]>('/testimonials').then(value => { if (live) setRows(value) }).catch(e => { if (live) setError(String(e)) }); return () => { live = false } }, [run.run?.state])
  const videos = assets.filter(a => a.data.role === 'testimonial')
  const analyze = async () => { setBusy(true); setError(''); try { const job = await api<Run>('/testimonials/analyze', { asset_id: selected || videos[0]?.id }); setJobId(job.id); await onSaved() } catch (e) { setError(String(e)) } finally { setBusy(false) } }
  return <section className="panel testimonial-panel"><h2>Customer voices</h2><p>Upload a testimonial video above, then review its words before making a quote post.</p>{error && <Notice>{error}</Notice>}
    <label>Testimonial video<select value={selected || videos[0]?.id || ''} onChange={e => setSelected(e.target.value)}>{!videos.length && <option value="">Upload a testimonial video first</option>}{videos.map(a => <option key={a.id} value={a.id}>{a.data.filename}</option>)}</select></label>
    <button type="button" className="primary" disabled={busy || !videos.length || !usage.live_enabled || (usage.testimonial_remaining ?? 0) < 1 || Boolean(usage.active_job)} onClick={() => void analyze()}>Transcribe and propose quotes</button><p className="small muted">Uses 1 testimonial analysis · {usage.testimonial_remaining ?? 0} left</p>
    {run.run && <p role="status">Testimonial analysis: {run.run.state}</p>}{run.events.filter(e => e.type === 'workflow_error').map(e => <Notice key={e.id}>{String(e.payload.message)}</Notice>)}
    {rows.map(row => <TranscriptEditor key={`${row.id}-${row.version}`} row={row} reload={reload}/>)}</section>
}

export function QuotePicker({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [rows, setRows] = useState<Resource<Transcript>[]>([])
  useEffect(() => { api<Resource<Transcript>[]>('/testimonials').then(setRows).catch(() => setRows([])) }, [])
  return <label>Reviewed testimonial quote<select value={value} onChange={e => onChange(e.target.value)}><option value="">Choose an approved excerpt</option>{rows.filter(r => r.data.reviewed).flatMap(r => r.data.quotes.filter(q => r.data.approved_quote_ids.includes(q.id)).map(q => <option key={`${r.id}:${q.id}`} value={`${r.id}:${q.id}`}>{q.text} - {r.data.attribution}</option>))}</select><span className="small muted">Manage reviewed excerpts in Brand library.</span></label>
}
