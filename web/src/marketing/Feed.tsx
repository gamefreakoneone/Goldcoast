import { useEffect, useState } from 'react'
import { api } from './client'
import { useRun } from './hooks'
import { Notice, PageHeading, Status } from './ui'
import type { Candidate, FeedResult, Run, Usage } from './types'

export type IdeaSelection = { jobId: string; idea: Candidate }

const stageTitle = (name: string) => ({ chief_plan: 'Understanding your brief', recent_search: 'Checking recent news', upcoming_search: 'Finding upcoming events', feed_analysis: 'Connecting ideas to your products', local_scout: 'Researching nearby opportunities', culture_scout: 'Exploring cultural ideas', chief_selection: 'Choosing the angle', campaign: 'Campaign direction selected', creative_brief: 'Writing your post', creative_result: 'Ready for your review', replay: 'Recorded workflow loaded' })[name] ?? (name.startsWith('illustration_') ? `Creating illustration ${name.split('_')[1]}` : name.startsWith('creative_') ? 'Composing and checking your post' : name.replaceAll('_', ' '))

export function WorkflowProgress({ id, onReview }: { id: string | null; onReview?: () => void }) {
  const { run, events, error } = useRun(id)
  return <section className="panel workflow-intro" aria-live="polite"><h2>The workflow</h2>{error && <Notice>{error}</Notice>}{run ? <><Status good={run.state === 'completed'}>{run.state === 'completed' ? 'Ready for review' : run.state}</Status>
    {Object.entries(run.checkpoint).map(([name, stage], i) => <div className="workflow-row" key={name}><span>{i + 1}</span><div><h3>{stageTitle(name)}</h3><p>{stage.state === 'completed' ? 'Completed' : 'In progress'}</p></div></div>)}
    {!Object.keys(run.checkpoint).length && <p>Waiting for the worker to begin.</p>}
    {events.filter(e => e.type === 'workflow_error').map(e => <Notice key={e.id}>{String(e.payload.message ?? 'Workflow failed')}</Notice>)}
    {run.state === 'completed' && onReview && <button className="primary" onClick={onReview}>Review results</button>}
  </> : <p>Start a workflow to see research, creative production and quality checks here.</p>}</section>
}

export function Feed({ usage, onUse, compact = false, onRefresh }: { usage: Usage; onUse: (selection: IdeaSelection) => void; compact?: boolean; onRefresh: () => Promise<void> }) {
  const [topic, setTopic] = useState('')
  const [job, setJob] = useState<Run | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const active = useRun(job?.id ?? null)
  useEffect(() => { let mounted = true; api<Run | null>('/feed').then(value => { if (mounted) setJob(value) }).catch(e => { if (mounted) setError(String(e)) }); return () => { mounted = false } }, [])
  const result = (active.run ?? job)?.checkpoint.feed?.output as FeedResult | undefined
  const start = async () => { setBusy(true); setError(''); try { setJob(await api<Run>('/feed/refresh', { topic })); await onRefresh() } catch (e) { setError(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) } }
  const current = active.run ?? job
  const expired = result ? new Date(result.expires_at).getTime() <= Date.now() : false
  return <>{!compact && <PageHeading title="Your Feed.">Fresh reasons to visit, grounded in what you sell.</PageHeading>}<section className="panel feed-panel"><h2>{compact ? 'Your Feed' : 'Find today\u2019s opportunity'}</h2>
    {error && <Notice>{error}</Notice>}
    <label>Explore a topic <span className="optional">Optional</span><input maxLength={500} value={topic} onChange={e => setTopic(e.target.value)} placeholder="Notebooks for new students, weekend treats..."/></label>
    <div className="form-footer"><button type="button" className="primary" disabled={busy || !usage.live_enabled || (usage.feed_remaining ?? 0) < 1 || Boolean(usage.active_job)} onClick={() => void start()}>{busy ? 'Starting...' : topic.trim() ? 'Explore this topic' : 'Find ideas for me'}</button><span className="small muted">{usage.feed_remaining ?? 0} refreshes left · cached for six hours</span></div>
    {!usage.live_enabled && <p className="small muted">Live discovery is paused. Recorded ideas remain readable.</p>}
    {current && ['queued', 'running'].includes(current.state) && <p role="status">Searching and checking sources...</p>}
    {current?.state === 'failed' && <Notice>Discovery failed. Your existing recordings are preserved; no automatic retry was made.</Notice>}
    {result && <><p className="small muted">Retrieved {new Date(result.retrieved_at).toLocaleString()}{expired ? ' · Expired; refresh before using' : ''}</p><div className="feed-grid">{result.ideas.slice(0, compact ? 3 : 6).map(idea => <article className="idea-card" key={idea.id}><span className="eyebrow">{idea.category === 'local' ? 'Nearby' : idea.category === 'culture' ? 'Broader culture' : 'Evergreen'}</span><h3>{idea.title}</h3><p>{idea.angle}</p><p className="small"><strong>{idea.product_name}</strong>{idea.location ? ` · ${idea.location}` : ''}{idea.event_date ? ` · ${idea.event_date}` : ''}</p><ul className="small">{result.graph.sources.filter(s => idea.source_ids.includes(s.id)).map(s => <li key={s.id}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></li>)}</ul><button type="button" className="text-button" disabled={expired || new Date(idea.expires_at).getTime() <= Date.now()} onClick={() => onUse({ jobId: current!.id, idea })}>Use this idea</button></article>)}</div></>}
    {!result && !current && <p className="empty-note">Find nearby happenings or explore a specific topic. Opening this page uses no API credits.</p>}
  </section></>
}
