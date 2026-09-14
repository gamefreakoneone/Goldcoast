import { useCallback, useState } from 'react'
import { api, downloadCampaign } from './client'
import { PrivateImage, useRun } from './hooks'
import { useVisiblePolling } from './polling'
import { Icon, Notice, PageHeading, Status } from './ui'
import type { Campaign, CreativeView, Graph, Revision, StudioEvent } from './types'

const stageNames: Record<string, string> = {
  video_evidence: 'Finding the strongest video frame', local_signals: "Checking today's weather", chief_plan: 'The chief sets the direction', local_events: 'Checking the local calendar',
  local_scout: 'Finding a local moment', culture_scout: 'Reading cultural signals',
  chief_selection: 'Choosing the strongest idea', campaign: 'The campaign direction is ready',
  creative_brief: 'Writing your creative brief', creative_result: 'Your creatives are ready for review',
  brand_analysis: 'Learning your visual direction',
}

export function Activity({ events }: { events: StudioEvent[] }) {
  const visible = events.filter(e => e.type.startsWith('stage_') || e.type === 'recorded_stage' || e.type === 'workflow_error' || e.type === 'workflow_replayed' || e.type.startsWith('run_') || e.type === 'tool_started' || e.type.startsWith('notification_'))
  return <section className="panel activity-panel"><h2>Agent activity</h2>{!visible.length && <p className="empty-note">Waiting for the worker to pick up this workflow…</p>}
    <ol className="activity-list">{visible.map(event => {
      const stage = String(event.payload.stage ?? '')
      const label = stageNames[stage] || (stage.startsWith('creative_') ? `Making the ${stage.split('_')[1]} ad · attempt ${stage.split('_')[2]}` : stage.replace(/_/g, ' '))
      const complete = event.type === 'stage_completed' || event.type === 'run_completed'
      return <li key={event.id}><span className={`activity-mark ${complete ? 'done' : ''}`}>{complete ? <Icon name="check" size={16}/> : <span/>}</span>
        <div><strong>{event.type === 'workflow_error' ? 'The workflow stopped' : event.type === 'workflow_replayed' ? 'Recorded workflow loaded' : event.type === 'tool_started' ? 'Checking a source' : label || event.type.replace(/_/g, ' ')}</strong>
          <p>{event.type === 'workflow_error' ? String(event.payload.message) : event.type === 'stage_started' ? 'In progress' : event.type === 'recorded_stage' ? 'Recorded step ? no live call' : event.type === 'stage_completed' ? 'Completed' : String(event.payload.error ?? event.payload.tool ?? '')}</p></div>
        <time>{new Date(event.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time></li>
    })}</ol></section>
}

function EvidenceMap({ graph }: { graph: Graph }) {
  const [entity, setEntity] = useState<string | null>(null)
  const entities = graph.nodes.filter(n => n.kind === 'entity')
  const edges = entity ? graph.edges.filter(e => e.source === entity) : graph.edges
  return <section className="panel evidence-panel"><div className="section-header"><h2>Evidence map</h2><span className="small muted">{graph.sources.length} sources · {graph.edges.length} cited claims</span></div>
    {!entities.length ? <p className="empty-note">This evergreen idea uses your confirmed business details. There is no external event claim.</p> : <>
      <div className="entity-filter"><button className={entity === null ? 'active' : ''} onClick={() => setEntity(null)}>All entities</button>{entities.map(node => <button className={entity === node.id ? 'active' : ''} key={node.id} onClick={() => setEntity(node.id)}>{node.label}</button>)}</div>
      <div className="claim-list">{edges.map((edge, index) => {
        const source = graph.sources.find(s => s.id === edge.target)
        return <article className="claim" key={index}><div className="claim-relation"><strong>{graph.nodes.find(n => n.id === edge.source)?.label}</strong><Icon name="arrow" size={18}/><span>{edge.predicate}: {edge.value}</span><Status good={edge.state === 'supported'}>{edge.state}</Status></div>
          <blockquote>{edge.quote}</blockquote>{source && <a href={source.url} target="_blank" rel="noreferrer">{source.title}<Icon name="arrow" size={15}/></a>}</article>
      })}</div></>}
    <details className="all-sources"><summary>All source material</summary>{graph.sources.map(source => <article className="source" key={source.id}><a href={source.url} target="_blank" rel="noreferrer">{source.title}<Icon name="arrow" size={15}/></a><p className="small muted">Retrieved {new Date(source.retrieved_at).toLocaleString()} · {source.provider === 'weather' ? 'Open-Meteo weather' : source.provider}</p><p>{source.text}</p></article>)}</details>
  </section>
}

function Thinking({ campaign }: { campaign: Campaign }) {
  return <><section className="panel decision-panel"><h2>{campaign.selected.title}</h2><p className="decision-rationale">{campaign.rationale}</p><p>{campaign.selected.angle}</p>
    {campaign.selected.risks.length > 0 && <p className="small muted">Considerations: {campaign.selected.risks.join(' · ')}</p>}
    {campaign.local_signals && <div className="signals-row"><strong>Today's signals</strong>{campaign.local_signals.available ? campaign.local_signals.summary.map(signal => <Status key={signal} good>{signal}</Status>) : <span className="small muted">{campaign.local_signals.reason}</span>}</div>}
    <div className="table-wrap"><table><thead><tr><th>Opportunity</th><th>Product fit</th><th>Timing</th><th>Sources</th><th>Decision</th></tr></thead><tbody>{campaign.candidates.map(candidate => <tr key={candidate.id}><td><strong>{candidate.title}</strong><small>{candidate.product_name} · {candidate.category}</small></td><td>{candidate.fit}/10</td><td>{candidate.timeliness}/10</td><td>{candidate.source_ids.length}</td><td>{candidate.id === campaign.selected.id ? 'Selected' : 'Alternative'}</td></tr>)}</tbody></table></div>
    {campaign.rejected.length > 0 && <details><summary>Why other ideas were excluded</summary><ul>{campaign.rejected.map(item => <li key={item.id}><strong>{item.title}</strong>: {item.reason}</li>)}</ul></details>}
    </section><EvidenceMap graph={campaign.graph}/></>
}

function CampaignVideo({ campaign, runId }: { campaign: Campaign; runId: string }) {
  const video = campaign.video_evidence
  if (!video) return null
  return <section className="panel campaign-video-evidence"><div><span className="eyebrow">Campaign video</span><h2>{video.title || 'Uploaded campaign video'}</h2><p>{video.description || 'No owner description was recorded for this historical video.'}</p><dl><div><dt>Chosen moment</dt><dd>{video.best_frame_s === undefined ? 'Not recorded' : `${video.best_frame_s.toFixed(1)} seconds`}</dd></div><div><dt>Why this frame</dt><dd>{video.frame_reason || 'A frame reason was not recorded.'}</dd></div><div><dt>What the agent saw</dt><dd>{video.observations}</dd></div></dl></div>{video.frame_asset_id ? <PrivateImage path={`/runs/${runId}/video-frame`} alt={`Selected frame from ${video.title || 'campaign video'}`}/> : <div className="media-placeholder">Best frame was not preserved for this historical campaign.</div>}</section>
}

function CreativeCard({ creative, ready, onChanged }: { creative: CreativeView; ready: boolean; onChanged: () => void }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const data = creative.data
  const decide = async (decision: 'approved' | 'rejected') => {
    setBusy(true); setError('')
    try { await api(`/creatives/${creative.id}/decision`, { version: creative.version, decision, note }); onChanged() }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) } finally { setBusy(false) }
  }
  return <article className={`panel creative-card ${data.format}`}><div className="section-header"><h2>{({ landscape: 'Landscape', portrait: 'Portrait', post: 'Instagram post', story: 'Story image' })[data.format]} <span>· {data.width} × {data.height}</span></h2><Status good={creative.passed}>{creative.passed ? 'Quality check passed' : 'Needs changes'}</Status></div>
    <PrivateImage className="creative-preview" path={`/creatives/${creative.id}/content`} alt={`${data.format} advertisement: ${data.brief.headline}`}/>
    <div className="scores">{[['Facts', data.verdict.factuality], ['Brand', data.verdict.brand_fidelity], ['Visuals', data.verdict.visual_quality], ['Readability', data.verdict.legibility]].map(([label, score]) => <div key={label}><span>{label}</span><strong>{score}/10</strong></div>)}</div>
    {data.brief.caption && <details open><summary>Caption</summary><p>{data.brief.caption}</p></details>}
    <p className="judge-feedback">{data.verdict.feedback}</p>
    {data.verdict.score_reasons && <details><summary>Why these scores - {data.verdict.rubric_version}</summary>{Object.entries(data.verdict.score_reasons).map(([criterion, reason]) => <p key={criterion}><strong>{criterion.replace(/_/g, ' ')}: </strong>{reason}</p>)}</details>}
    {data.verdict.critical_issues.length > 0 && <Notice>{data.verdict.critical_issues.join(' · ')}</Notice>}
    {creative.stale && <Notice>This ad is out of date. Start a new workflow before approving or downloading it.</Notice>}
    {error && <Notice>{error}</Notice>}
    <div className="review-actions"><button className="primary" disabled={busy || !ready || !creative.passed || creative.stale || data.decision === 'approved'} onClick={() => void decide('approved')}>{data.decision === 'approved' ? 'Approved' : 'Approve ad'}</button><button className="secondary" disabled={busy || data.decision === 'rejected'} onClick={() => void decide('rejected')}>{data.decision === 'rejected' ? 'Rejected' : 'Reject'}</button><Status good={data.decision === 'approved'}>{data.decision === 'pending' ? 'Awaiting your review' : data.decision}</Status></div>
    {data.decided_via === 'telegram' && data.decision !== 'pending' && <p className="small muted">Decided on Telegram</p>}
    <details className="feedback-input"><summary>Add review feedback</summary><label>Feedback<textarea maxLength={500} value={note} onChange={e => setNote(e.target.value)}/></label></details>
  </article>
}

export function ReviewPage({ id, onNew, onChanged }: { id: string; onNew: () => void; onChanged: () => Promise<void> }) {
  const state = useRun(id)
  const [tab, setTab] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(false)
  const run = state.run
  const [family, setFamily] = useState<{ id: string; revisions: Revision[] } | null>(null)
  const refreshRevisions = useCallback(async (signal: AbortSignal) => {
    const revisions = await api<Revision[]>(`/runs/${id}/revisions`, undefined, 'GET', signal)
    if (!signal.aborted) setFamily({ id, revisions: Array.isArray(revisions) ? revisions : [] })
  }, [id])
  useVisiblePolling(refreshRevisions)
  const revisions = family?.id === id ? family.revisions : []
  const current = revisions.find(revision => revision.id === id)
  const latestRevision = revisions.at(-1)
  const campaign = state.result && 'selected' in state.result ? state.result : null
  const selectedTab = tab ?? (run?.state === 'completed' ? 'creatives' : 'activity')
  const formats = run?.input.creative_type ? (run.input.include_story ? ['post', 'story'] : ['post']) : ['landscape', 'portrait']
  const latest = formats.map(format => state.creatives.filter(c => c.data.format === format).sort((a, b) => b.data.attempt - a.data.attempt)[0]).filter(Boolean)
  const canDownload = latest.length === formats.length && latest.every(c => c.passed && !c.stale && c.data.decision === 'approved')
  const download = async () => { setDownloading(true); setError(''); try { await downloadCampaign(id) } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) } finally { setDownloading(false) } }
  const cancel = async () => { try { await api(`/runs/${id}/cancel`, {}); state.reload(); await onChanged() } catch (reason) { setError(String(reason)) } }
  return <><PageHeading title={run?.state === 'completed' ? 'Made for your neighborhood.' : 'Your agents are on it.'}>{run?.state === 'completed' ? 'Your ads are ready. Take a look before they go anywhere.' : 'Follow the thinking, the sources, and the work as it happens.'}</PageHeading>
    {run?.mode === 'replay' && <Notice tone="info">Historical demonstration{campaign ? ` - recorded ${new Date(campaign.graph.built_at).toLocaleDateString()}` : ''}. Sources and ads reflect the original run, not current conditions. Review decisions apply only to this replay. No API credits are used.</Notice>}
    {(error || state.error) && <Notice>{error || state.error}</Notice>}
    {run?.started_via === 'telegram' && <Status good>Via phone</Status>}
    {run?.input.owner_feedback && <section className="panel"><h2>Requested changes</h2><p>{run.input.owner_feedback}</p></section>}
    {revisions.length > 1 && <section className="panel"><h2>Campaign revisions</h2><nav aria-label="Campaign revisions">
      {current?.parent_id && <p><a href={`#/review/${current.parent_id}`}>View parent campaign</a></p>}
      {revisions[0]?.id !== id && <p><a href={`#/review/${revisions[0].id}`}>View original campaign</a></p>}
      {latestRevision && latestRevision.id !== id && <p><a href={`#/review/${latestRevision.id}`}>View latest revision</a></p>}
      {revisions.map((revision, index) => <p key={revision.id}><a href={`#/review/${revision.id}`} aria-current={revision.id === id ? 'page' : undefined}>{index === 0 ? 'Original' : `Revision ${index}`} · {revision.state}{revision.started_via === 'telegram' ? ' · Via phone' : ''}{revision.id === id ? ' · Viewing' : ''}</a></p>)}
    </nav></section>}
    {campaign && <CampaignVideo campaign={campaign} runId={id}/>}
    {run?.state === 'failed' && <Notice>The workflow stopped. Check Activity for the reason. Paid work will not retry automatically.</Notice>}
    {run?.state === 'cancelled' && <Notice tone="info">This workflow was cancelled.</Notice>}
    <div className="review-toolbar"><div className="segmented tabs">{[['creatives', 'Creatives'], ['thinking', 'The thinking'], ['activity', 'Activity']].map(([value, label]) => <button key={value} className={selectedTab === value ? 'selected' : ''} onClick={() => setTab(value)}>{label}</button>)}</div>
      <div className="download-control">{run && ['queued', 'running'].includes(run.state) ? <button className="secondary" onClick={() => void cancel()}>Stop workflow</button> : <><button className="secondary" disabled={!canDownload || downloading} onClick={() => void download()}><Icon name="download" size={18}/>{downloading ? 'Preparing…' : 'Download campaign'}</button><small>{canDownload ? 'Selected outputs approved' : 'Approve every selected output to download'}</small></>}</div></div>
    {selectedTab === 'activity' && <Activity events={state.events}/>}
    {selectedTab === 'thinking' && (campaign ? <><Thinking campaign={campaign}/><section className="panel"><h2>Weather and creative direction</h2>{latest.length ? latest.map(creative => <p key={creative.id}><strong>{creative.data.format}: </strong>{creative.data.brief.weather_influence ? `${creative.data.brief.weather_influence.influenced ? 'Weather influenced this design' : 'Another direction took priority'} — ${creative.data.brief.weather_influence.rationale}` : 'Weather influence was not recorded'}</p>) : <p>The creative direction will appear after the brief is ready.</p>}</section></> : <section className="panel empty-note">The chief’s recommendation will appear here after discovery.</section>)}
    {selectedTab === 'creatives' && <>{latest.length ? <div className="creative-grid">{latest.map(creative => <CreativeCard key={creative.id + creative.version} creative={creative} ready={run?.state === 'completed'} onChanged={() => { state.reload(); void onChanged() }}/>)}</div> : <section className="panel empty-note">{run?.state === 'failed' ? 'No judged creatives were produced.' : 'Your judged creatives will appear here.'}</section>}
      {state.creatives.length > 2 && <details className="panel attempts"><summary>Previous attempts and judge feedback</summary>{state.creatives.map(c => <p key={c.id}><strong>{c.data.format} · attempt {c.data.attempt}</strong> — {c.passed ? 'Passed' : 'Needs changes'}: {c.data.verdict.feedback}</p>)}</details>}</>}
    <footer className="workspace-footer"><span>{run?.mode === 'replay' ? 'You’re reviewing a recorded example. No API credits were used.' : 'Nothing publishes without your approval.'}</span><button className="text-button" onClick={onNew}>Start a new workflow<Icon name="arrow" size={16}/></button></footer>
  </>
}

