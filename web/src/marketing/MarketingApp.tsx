import { useCallback, useEffect, useRef, useState } from 'react'

import { initializeSession, signIn, signOut } from './auth'

import { api } from './client'

import { BrandPage, BusinessPage } from './BrandBusiness'

import { PrivateImage } from './hooks'
import { useVisiblePolling } from './polling'

import { ReviewPage } from './Review'
import { Feed, WorkflowProgress, type IdeaSelection } from './Feed'
import { SchedulePanel } from './SchedulePanel'
import { TelegramPanel } from './TelegramPanel'

import { Icon, Notice, PageHeading, Status, Wordmark } from './ui'

import type { Asset, Brand, Business, Resource, Run, Usage, User } from './types'

import './marketing.css'



type Page = 'feed' | 'today' | 'brand' | 'business' | 'campaigns' | 'settings' | 'review'

interface Data { user: User; usage: Usage; business: Resource<Business> | null; brand: Resource<Brand> | null; assets: Resource<Asset>[]; runs: Run[] }

const nav: { page: Page; label: string }[] = [{ page: 'today', label: 'Today' }, { page: 'feed', label: 'Your Feed' }, { page: 'brand', label: 'Brand library' }, { page: 'business', label: 'Business' }, { page: 'campaigns', label: 'Campaigns' }, { page: 'settings', label: 'Settings' }]

function currentRoute(): { page: Page; id: string | null } {

  const [page, id] = location.hash.replace(/^#\//, '').split('/')

  return { page: [...nav.map(n => n.page), 'review'].includes(page as Page) ? page as Page : 'today', id: id && /^[a-f0-9]{32}$/.test(id) ? id : null }

}



function Today({ data, navigate, refresh, selection, onUse, runId, clearSelection }: { selection: IdeaSelection | null; onUse: (value: IdeaSelection) => void; clearSelection: () => void; runId: string | null; data: Data; navigate: (page: Page, id?: string) => void; refresh: () => Promise<void> }) {

  const [goal, setGoal] = useState(selection?.idea.angle ?? '')

  const [mode, setMode] = useState<'replay' | 'live'>(selection ? 'live' : 'replay')

  const [source, setSource] = useState('')

  const [video, setVideo] = useState('')
  const [creativeType, setCreativeType] = useState('auto')
  const [includeStory, setIncludeStory] = useState(false)
  const [product, setProduct] = useState('')

  const [busy, setBusy] = useState(false)

  const [error, setError] = useState('')

  const recorded = data.runs.filter(r => r.kind === 'campaign' && r.state === 'completed')

  const replaySource = source || 'sample'

  const ready = Boolean(data.business?.data.confirmed && data.business.data.products.length && data.brand?.data.confirmed)

  const liveAllowed = ready && data.usage.live_enabled && data.usage.campaign_remaining > 0 && !data.usage.active_job

  const start = async (event: React.FormEvent) => {

    event.preventDefault(); setBusy(true); setError('')

    try {

      const run = mode === 'replay' && replaySource === 'sample' ? await api<Run>('/replays/sample', {}) : await api<Run>('/workflows', { mode, goal: goal.trim() || 'Bring more neighbors in today', video_asset_id: video || null, replay_source: mode === 'replay' ? replaySource : null, feed_job_id: selection?.jobId ?? null, idea_id: selection?.idea.id ?? null, product_id: product || selection?.idea.product_id || null, creative_type: creativeType, include_story: includeStory })

      await refresh(); navigate('today', run.id)

    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) } finally { setBusy(false) }

  }

  const pictures = data.assets.filter(a => a.data.role === 'product').slice(0, 2)
  const videos = data.assets.filter(a => a.data.role === 'video')
  const selectedVideo = videos.find(asset => asset.id === video)

  return <><PageHeading title="Your daily marketing desk.">Turn what’s happening nearby into a reason to stop by.</PageHeading>{error && <Notice>{error}</Notice>}

    <div className="today-grid"><form className="panel brief-panel" onSubmit={start}><h2>What should we focus on?</h2>{selection && <Notice tone="info">Selected: {selection.idea.title}<button type="button" className="text-button" onClick={() => { clearSelection(); setGoal('') }}>Choose for me instead</button></Notice>}

      <label className="visually-hidden" htmlFor="daily-brief">Today's campaign brief</label><textarea id="daily-brief" className="daily-brief" maxLength={1500} readOnly={mode === 'replay'} value={mode === 'replay' ? recorded.find(r => r.id === replaySource)?.input.goal ?? 'Explore a recorded Morrow Coffee campaign: local research, visual brand references, and two judged ads. No API credits needed.' : goal} onChange={e => setGoal(e.target.value)} placeholder={`Bring in the afternoon crowd with our ${data.business?.data.products[0]?.name.toLowerCase() || 'signature drink'}.`}/>

      <p className="small muted">{mode === 'replay' && recorded.length ? 'Replay uses the original brief and brand snapshot. No API credits are used.' : 'Your agents will find the angle. You make the final call.'}</p>

      {mode === 'replay' && <label className="replay-select">Recorded campaign<select value={replaySource} onChange={e => setSource(e.target.value)}><option value="sample">Morrow Coffee - recorded example - free</option>{recorded.map(run => <option key={run.id} value={run.id}>{new Date(run.created_at * 1000).toLocaleDateString()} · {run.input.goal || 'Recorded campaign'}</option>)}</select></label>}

      {mode === 'replay' && !recorded.length && <p className="small muted replay-empty">Try the recorded example now, or upload your own brand material to create a live campaign.</p>}

      {mode === 'live' && <div className="campaign-video-select"><label>Campaign video <span className="optional">Optional</span><select value={video} onChange={e => { const asset = videos.find(item => item.id === e.target.value); setVideo(e.target.value); if (asset?.data.product_id) setProduct(asset.data.product_id) }}><option value="">Create from current topics without a video</option>{videos.map(a => <option key={a.id} value={a.id}>{a.data.title || a.data.filename}</option>)}</select></label>{selectedVideo ? <p className="small muted">The video agent will choose its strongest frame. {selectedVideo.data.description}</p> : !videos.length ? <p className="small muted">Upload and name an MP4 in <a href="#/brand">Brand library</a> to build a campaign around it.</p> : null}</div>}

      {mode === 'live' && <div className="form-grid"><label>Creative type<select value={creativeType} onChange={e => setCreativeType(e.target.value)}><option value="auto">Choose for me</option><option value="product">Product spotlight</option><option value="timely">Timely promotion</option><option value="comic">Four-panel comic</option></select></label><label>Product<select value={product || selection?.idea.product_id || ''} disabled={Boolean(selection)} onChange={e => setProduct(e.target.value)}><option value="">Let the agent choose</option>{data.business?.data.products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label className="checkbox"><input type="checkbox" checked={includeStory} onChange={e => setIncludeStory(e.target.checked)}/>Also make a vertical Story image</label></div>}
      <div className="brief-actions"><div className="mode-controls"><div className="segmented"><button type="button" className={mode === 'replay' ? 'selected' : ''} onClick={() => setMode('replay')}>Replay</button><button type="button" className={mode === 'live' ? 'selected' : ''} onClick={() => setMode('live')}>Live</button></div><span className="small muted">{mode === 'replay' ? 'No API usage' : `Uses 1 campaign · ${data.usage.campaign_remaining} left`}</span></div>

        <button className="primary start-button" disabled={busy || (mode === 'live' ? !liveAllowed : !replaySource)}>{busy ? 'Starting...' : mode === 'replay' && replaySource === 'sample' ? 'Try recorded example' : 'Start today’s workflow'}<Icon name="arrow" size={20}/></button></div>

      {mode === 'live' && !liveAllowed && <p className="small muted">{!ready ? 'Confirm your business and brand kit to start.' : !data.usage.live_enabled ? 'Live generation is paused by the owner.' : data.usage.active_job ? 'A live workflow is already active.' : 'Ask the owner for a live campaign allowance.'}</p>}

    </form><aside className="panel brand-summary"><h2>Your brand, on hand.</h2>{data.brand?.data.logo_asset_id && <PrivateImage className="summary-logo" path={`/assets/${data.brand.data.logo_asset_id}/content`} alt="Business logo"/>}{pictures.length ? <div className="brand-thumbnails">{pictures.map(asset => <PrivateImage key={asset.id} path={`/assets/${asset.id}/content`} alt={asset.data.filename}/>)}</div> : <div className="brand-empty"><Icon name="brand" size={38}/><p>Your photos and brand direction belong here.</p></div>}

      <h3>{data.business?.data.name || 'Make yourself at home.'}</h3><Status good={Boolean(data.brand?.data.confirmed)}>{data.brand?.data.confirmed ? 'Brand confirmed' : 'Brand setup needed'}</Status><p>{data.business?.data.description}</p><div className="summary-palette">{data.brand?.data.palette.map(color => <span key={color} title={color} style={{ background: color }}/>)}</div><p>{data.brand?.data.voice || 'Start with your business details, then bring your visual references.'}</p><button className="text-button" onClick={() => navigate(data.business ? 'brand' : 'business')}>{data.business ? 'Open brand library' : 'Set up your business'}<Icon name="arrow" size={18}/></button>

    </aside></div>

    <WorkflowProgress id={runId ?? data.runs.find(r => r.kind === 'campaign')?.id ?? null} onReview={() => { const id = runId ?? data.runs.find(r => r.kind === 'campaign')?.id; if (id) navigate('review', id) }}/>
    <Feed compact usage={data.usage} onUse={onUse} onRefresh={refresh}/>

    <footer className="workspace-footer">Nothing publishes without your approval.</footer></>

}



function History({ runs, open }: { runs: Run[]; open: (run: Run) => void }) {

  return <><PageHeading title="Your campaign shelf.">Every idea, decision, and finished creative, in one place.</PageHeading><section className="panel history-panel"><h2>Past workflows</h2>{runs.length ? <div className="table-wrap"><table><thead><tr><th>Workflow</th><th>Started</th><th>Mode</th><th>Status</th><th/></tr></thead><tbody>{runs.map(run => <tr key={run.id}><td><strong>{run.kind === 'brand' ? 'Brand analysis' : run.input.goal || 'Daily campaign'}</strong><small>{run.id.slice(0, 8)}{run.started_via === 'telegram' && ' - Via phone'}{run.input.regenerate_from && ' - Feedback revision'}</small></td><td>{new Date(run.created_at * 1000).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</td><td>{run.mode}</td><td><Status good={run.state === 'completed'}>{run.state}</Status></td><td><button className="text-button" onClick={() => open(run)}>Open<Icon name="arrow" size={17}/></button></td></tr>)}</tbody></table></div> : <p className="empty-note">Your first workflow will appear here. Start with your business and brand library.</p>}</section></>

}



function SettingsPage({ data }: { data: Data }) {
  return <><PageHeading title="A little control goes a long way.">Manage your account and keep live usage intentional.</PageHeading>

    <div className="settings-grid"><section className="panel"><h2>Your account</h2><dl className="settings-list"><div><dt>Name</dt><dd>{data.user.name}</dd></div><div><dt>Access</dt><dd>{data.user.role}</dd></div><div><dt>Account ID</dt><dd><code>{data.user.id}</code></dd></div></dl><p className="small muted">Share your account ID with the operator to request a live allowance.</p></section>

      <section className="panel"><h2>Your live allowance</h2><dl className="settings-list"><div><dt>Campaigns remaining</dt><dd>{data.usage.campaign_remaining}</dd></div><div><dt>Brand analyses remaining</dt><dd>{data.usage.brand_remaining}</dd></div><div><dt>Feed refreshes remaining</dt><dd>{data.usage.feed_remaining ?? 0}</dd></div><div><dt>Live generation</dt><dd>{data.usage.live_enabled ? 'Enabled' : 'Paused'}</dd></div></dl><p className="small muted">Campaign-video analysis is included in a campaign. Replays use no API credits.</p></section></div>

    <TelegramPanel/><SchedulePanel timezone={data.business?.data.timezone ?? 'your business timezone'}/>

  </>

}



export default function MarketingApp() {

  const [logged, setLogged] = useState(false)

  const [loading, setLoading] = useState(true)

  const [data, setData] = useState<Data | null>(null)

  const [error, setError] = useState('')

  const [route, setRoute] = useState(currentRoute)

  const [selection, setSelection] = useState<IdeaSelection | null>(null)

  const [analysisId, setAnalysisId] = useState<string | null>(null)

  const requestNumber = useRef(0)
  const runRequestNumber = useRef(0)

  const refresh = useCallback(async () => {

    const number = ++requestNumber.current
    const runNumber = ++runRequestNumber.current

    const [user, usage, business, brand, assets, runs] = await Promise.all([

      api<User>('/me'), api<Usage>('/usage'), api<Resource<Business> | null>('/business'),

      api<Resource<Brand> | null>('/brand'), api<Resource<Asset>[]>('/assets'), api<Run[]>('/runs'),

    ])

    if (number === requestNumber.current) setData(previous => ({ user, business, brand, assets, usage: runNumber === runRequestNumber.current || !previous ? usage : previous.usage, runs: runNumber === runRequestNumber.current || !previous ? runs : previous.runs }))

  }, [])

  useEffect(() => { initializeSession().then(value => { setLogged(value); setRoute(currentRoute()) }).catch(reason => setError(reason.message)).finally(() => setLoading(false)) }, [])

  useEffect(() => { if (logged) { setLoading(true); refresh().catch(reason => setError(reason.message)).finally(() => setLoading(false)) } }, [logged, refresh])

  const refreshRuns = useCallback(async (signal: AbortSignal) => {
    const number = ++runRequestNumber.current
    const [runs, usage] = await Promise.all([
      api<Run[]>('/runs', undefined, 'GET', signal), api<Usage>('/usage', undefined, 'GET', signal),
    ])
    if (!signal.aborted && number === runRequestNumber.current) setData(previous => previous ? { ...previous, runs, usage } : previous)
  }, [])
  useVisiblePolling(refreshRuns, logged && data !== null)
  useEffect(() => () => { requestNumber.current++; runRequestNumber.current++ }, [logged])

  useEffect(() => { const update = () => setRoute(currentRoute()); window.addEventListener('popstate', update); window.addEventListener('hashchange', update); return () => { window.removeEventListener('popstate', update); window.removeEventListener('hashchange', update) } }, [])

  const navigate = (page: Page, id?: string) => { history.pushState({}, '', `#/${page}${id ? '/' + id : ''}`); setRoute({ page, id: id ?? null }); window.scrollTo(0, 0) }

  const useIdea = (value: IdeaSelection) => { setSelection(value); navigate('today') }

  const login = async () => { setError(''); try { await signIn() } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) } }

  const logout = async () => { setLogged(false); setData(null); try { await signOut() } catch (reason) { setError(String(reason)) } }

  if (!logged || !data) return <div className="login-page"><div className="login-photo"><img src="/marketing/latte.png" alt="A warm latte in a neighborhood café"/></div><main className="login-copy"><Wordmark/><h1>Your neighborhood.<br/>Your next great ad.</h1><p>Bring your brand. Let your agents find a timely reason for people to stop by.</p>{error && <Notice>{error}</Notice>}<button className="primary" disabled={loading} onClick={() => void login()}>{loading ? 'Opening your workspace…' : 'Sign in to your workspace'}<Icon name="arrow" size={19}/></button><p className="small muted">Invitation-only access. Replay first. Nothing publishes without your approval.</p><small className="demo-caption">Illustrative café photography created for this demo.</small></main></div>

  const businessName = data.business?.data.name || data.user.name

  const selectedNav = route.page === 'review' ? 'campaigns' : route.page

  const selectedRun = data.runs.find(run => run.id === route.id)

  return <div className="marketing-shell"><a className="skip-link" href="#main-content">Skip to content</a><aside className="sidebar"><Wordmark/><nav aria-label="Main navigation">{nav.map(item => <button key={item.page} className={selectedNav === item.page ? 'active' : ''} aria-current={selectedNav === item.page ? 'page' : undefined} onClick={() => navigate(item.page)}><Icon name={item.page}/>{item.label}</button>)}</nav><div className="sidebar-account"><button onClick={() => navigate('business')}><span className="avatar">{businessName.charAt(0).toUpperCase()}</span><span>{businessName}</span><Icon name="arrow" size={16}/></button><button onClick={() => void logout()}><Icon name="logout"/>Sign out</button></div></aside>

    <main className="workspace" id="main-content"><div className="topbar"><span>Workspace <span className="slash">/</span> {route.page === 'review' ? 'Campaign review' : nav.find(n => n.page === route.page)?.label}</span><span>{businessName}{selectedRun?.mode === 'replay' ? ' · Recorded replay' : data.business?.data.city ? ' · ' + data.business.data.city : ''}</span></div>

      {error && <Notice>{error}</Notice>}

      {route.page === 'today' && <Today key={selection?.idea.id ?? 'daily'} data={data} navigate={navigate} refresh={refresh} runId={route.id} selection={selection} onUse={useIdea} clearSelection={() => setSelection(null)}/>}

      {route.page === 'feed' && <Feed usage={data.usage} onUse={useIdea} onRefresh={refresh}/>}

      {route.page === 'business' && <BusinessPage key={data.business?.version ?? 0} value={data.business} onSaved={refresh}/>}

      {route.page === 'brand' && <BrandPage key={data.brand?.version ?? 0} brand={data.brand} business={data.business} assets={data.assets} usage={data.usage} analysisId={analysisId ?? data.runs.find(r => r.kind === 'brand')?.id ?? null} onAnalysis={setAnalysisId} onSaved={refresh}/>}

      {route.page === 'campaigns' && <History runs={data.runs.filter(r => r.kind === 'campaign' || r.kind === 'brand')} open={run => { if (run.kind === 'brand') { setAnalysisId(run.id); navigate('brand') } else navigate('review', run.id) }}/>} 

      {route.page === 'settings' && <SettingsPage data={data}/>}

      {route.page === 'review' && (route.id ? <ReviewPage key={route.id} id={route.id} onNew={() => navigate('today')} onChanged={refresh}/> : <Notice>Select a campaign from your history.</Notice>)}

    </main></div>

}

