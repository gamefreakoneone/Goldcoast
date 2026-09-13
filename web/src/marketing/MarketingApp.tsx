import { useCallback, useEffect, useRef, useState } from 'react'
import { initializeSession, signIn, signOut } from './auth'
import { api } from './client'
import { BrandPage, BusinessPage } from './BrandBusiness'
import { PrivateImage } from './hooks'
import { ReviewPage } from './Review'
import { Icon, Notice, PageHeading, Status, Wordmark } from './ui'
import type { Asset, Brand, Business, Resource, Run, Usage, User } from './types'
import './marketing.css'

type Page = 'today' | 'brand' | 'business' | 'campaigns' | 'settings' | 'review'
interface Data { user: User; usage: Usage; business: Resource<Business> | null; brand: Resource<Brand> | null; assets: Resource<Asset>[]; runs: Run[] }
const nav: { page: Page; label: string }[] = [{ page: 'today', label: 'Today' }, { page: 'brand', label: 'Brand library' }, { page: 'business', label: 'Business' }, { page: 'campaigns', label: 'Campaigns' }, { page: 'settings', label: 'Settings' }]
function currentRoute(): { page: Page; id: string | null } {
  const [page, id] = location.hash.replace(/^#\//, '').split('/')
  return { page: [...nav.map(n => n.page), 'review'].includes(page as Page) ? page as Page : 'today', id: id && /^[a-f0-9]{32}$/.test(id) ? id : null }
}

function Today({ data, navigate, refresh }: { data: Data; navigate: (page: Page, id?: string) => void; refresh: () => Promise<void> }) {
  const [goal, setGoal] = useState('')
  const [mode, setMode] = useState<'replay' | 'live'>('replay')
  const [source, setSource] = useState('')
  const [video, setVideo] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const recorded = data.runs.filter(r => r.kind === 'campaign' && r.state === 'completed')
  const replaySource = source || recorded[0]?.id || ''
  const ready = Boolean(data.business?.data.confirmed && data.business.data.products.length && data.brand?.data.confirmed)
  const liveAllowed = ready && data.usage.live_enabled && data.usage.campaign_remaining > 0 && !data.usage.active_job
  const start = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const run = await api<Run>('/workflows', { mode, goal: goal.trim() || 'Bring more neighbors in today', video_asset_id: video || null, replay_source: mode === 'replay' ? replaySource : null })
      await refresh(); navigate('review', run.id)
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) } finally { setBusy(false) }
  }
  const pictures = data.assets.filter(a => a.data.mime.startsWith('image/') && a.data.role !== 'logo').slice(0, 2)
  return <><PageHeading title="Your daily marketing desk.">Turn what’s happening nearby into a reason to stop by.</PageHeading>{error && <Notice>{error}</Notice>}
    <div className="today-grid"><form className="panel brief-panel" onSubmit={start}><h2>What should we focus on?</h2>
      <label className="visually-hidden" htmlFor="daily-brief">Today's campaign brief</label><textarea id="daily-brief" className="daily-brief" maxLength={1500} readOnly={mode === 'replay'} value={mode === 'replay' ? recorded.find(r => r.id === replaySource)?.input.goal ?? '' : goal} onChange={e => setGoal(e.target.value)} placeholder={`Bring in the afternoon crowd with our ${data.business?.data.products[0]?.name.toLowerCase() || 'signature drink'}.`}/>
      <p className="small muted">{mode === 'replay' && recorded.length ? 'Replay uses the original brief and brand snapshot. No API credits are used.' : 'Your agents will find the angle. You make the final call.'}</p>
      {mode === 'replay' && recorded.length > 0 && <label className="replay-select">Recorded campaign<select value={replaySource} onChange={e => setSource(e.target.value)}>{recorded.map(run => <option key={run.id} value={run.id}>{new Date(run.created_at * 1000).toLocaleDateString()} · {run.input.goal || 'Recorded campaign'}</option>)}</select></label>}
      {mode === 'replay' && !recorded.length && <p className="small muted replay-empty">No recorded campaigns yet. A completed live campaign can be replayed without API usage.</p>}
      {mode === 'live' && data.assets.some(a => a.data.role === 'video') && <label className="replay-select">Optional video context<select value={video} onChange={e => setVideo(e.target.value)}><option value="">Let the agents discover today’s context</option>{data.assets.filter(a => a.data.role === 'video').map(a => <option key={a.id} value={a.id}>{a.data.filename}</option>)}</select></label>}
      <div className="brief-actions"><div className="mode-controls"><div className="segmented"><button type="button" className={mode === 'replay' ? 'selected' : ''} onClick={() => setMode('replay')}>Replay</button><button type="button" className={mode === 'live' ? 'selected' : ''} onClick={() => setMode('live')}>Live</button></div><span className="small muted">{mode === 'replay' ? 'No API usage' : `Uses 1 campaign · ${data.usage.campaign_remaining} left`}</span></div>
        <button className="primary start-button" disabled={busy || (mode === 'live' ? !liveAllowed : !replaySource)}>{busy ? 'Starting…' : 'Start today’s workflow'}<Icon name="arrow" size={20}/></button></div>
      {mode === 'live' && !liveAllowed && <p className="small muted">{!ready ? 'Confirm your business and brand kit to start.' : !data.usage.live_enabled ? 'Live generation is paused by the owner.' : data.usage.active_job ? 'A live workflow is already active.' : 'Ask the owner for a live campaign allowance.'}</p>}
    </form><aside className="panel brand-summary"><h2>Your brand, on hand.</h2>{pictures.length ? <div className="brand-thumbnails">{pictures.map(asset => <PrivateImage key={asset.id} path={`/assets/${asset.id}/content`} alt={asset.data.filename}/>)}</div> : <div className="brand-empty"><Icon name="brand" size={38}/><p>Your photos and brand direction belong here.</p></div>}
      <h3>{data.business?.data.name || 'Make yourself at home.'}</h3><Status good={Boolean(data.brand?.data.confirmed)}>{data.brand?.data.confirmed ? 'Brand confirmed' : 'Brand setup needed'}</Status><p>{data.brand?.data.voice || 'Start with your business details, then bring your visual references.'}</p><button className="text-button" onClick={() => navigate(data.business ? 'brand' : 'business')}>{data.business ? 'Open brand library' : 'Set up your business'}<Icon name="arrow" size={18}/></button>
    </aside></div>
    <section className="panel workflow-intro"><h2>The workflow</h2>{[['Discover the moment', 'Local events and cultural signals, with sources.'], ['Make it yours', 'Your products, your visual references, two ad formats.'], ['Review before it goes out', 'A quality check, then your approval.']].map(([title, text], i) => <div className="workflow-row" key={title}><span>{i + 1}</span><div><h3>{title}</h3><p>{text}</p></div></div>)}</section>
    <footer className="workspace-footer">Nothing publishes without your approval.</footer></>
}

function History({ runs, open }: { runs: Run[]; open: (run: Run) => void }) {
  return <><PageHeading title="Your campaign shelf.">Every idea, decision, and finished creative, in one place.</PageHeading><section className="panel history-panel"><h2>Past workflows</h2>{runs.length ? <div className="table-wrap"><table><thead><tr><th>Workflow</th><th>Started</th><th>Mode</th><th>Status</th><th/></tr></thead><tbody>{runs.map(run => <tr key={run.id}><td><strong>{run.kind === 'brand' ? 'Brand analysis' : run.input.goal || 'Daily campaign'}</strong><small>{run.id.slice(0, 8)}</small></td><td>{new Date(run.created_at * 1000).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</td><td>{run.mode}</td><td><Status good={run.state === 'completed'}>{run.state}</Status></td><td><button className="text-button" onClick={() => open(run)}>Open<Icon name="arrow" size={17}/></button></td></tr>)}</tbody></table></div> : <p className="empty-note">Your first workflow will appear here. Start with your business and brand library.</p>}</section></>
}

function SettingsPage({ data, refresh }: { data: Data; refresh: () => Promise<void> }) {
  const [tenant, setTenant] = useState(data.user.id)
  const [campaign, setCampaign] = useState(1)
  const [brand, setBrand] = useState(1)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const act = async (path: string, body: unknown) => {
    setBusy(true); setError(''); setNotice('')
    try { await api(path, body); await refresh(); setNotice('Settings updated.') }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) } finally { setBusy(false) }
  }
  return <><PageHeading title="A little control goes a long way.">Manage your account and keep live usage intentional.</PageHeading>{error && <Notice>{error}</Notice>}{notice && <Notice tone="success">{notice}</Notice>}
    <div className="settings-grid"><section className="panel"><h2>Your account</h2><dl className="settings-list"><div><dt>Name</dt><dd>{data.user.name}</dd></div><div><dt>Access</dt><dd>{data.user.role}</dd></div><div><dt>Account ID</dt><dd><code>{data.user.id}</code></dd></div></dl><p className="small muted">Share your account ID with the owner to request a live allowance.</p></section>
      <section className="panel"><h2>Your live allowance</h2><dl className="settings-list"><div><dt>Campaigns remaining</dt><dd>{data.usage.campaign_remaining}</dd></div><div><dt>Brand analyses remaining</dt><dd>{data.usage.brand_remaining}</dd></div><div><dt>Live generation</dt><dd>{data.usage.live_enabled ? 'Enabled' : 'Paused'}</dd></div></dl><p className="small muted">Replays use no API credits. One live workflow can run at a time.</p></section></div>
    {data.user.role === 'owner' && <section className="panel owner-controls"><h2>Owner controls</h2><div className="settings-grid"><div><h3>Shared live budget</h3><p>{data.usage.global_campaign_remaining} campaigns · {data.usage.global_brand_remaining} brand analyses remaining</p><button className={data.usage.live_enabled ? 'danger' : 'primary'} disabled={busy} onClick={() => void act('/admin/controls', { enabled: !data.usage.live_enabled })}>{data.usage.live_enabled ? 'Pause all live generation' : 'Enable live generation'}</button><p className="small muted">Pausing blocks the next provider call in every live workflow.</p><button className="text-button" disabled={busy} onClick={() => void act('/admin/controls', { campaign: 1, brand: 1 })}>Add 1 to each shared allowance</button></div>
      <form onSubmit={e => { e.preventDefault(); void act(`/admin/grants/${tenant}`, { campaign, brand }) }}><h3>Grant account usage</h3><label>Account ID<input required pattern="[a-f0-9]{32}" value={tenant} onChange={e => setTenant(e.target.value)}/></label><div className="form-grid"><label>Campaigns<input type="number" min={0} max={100} value={campaign} onChange={e => setCampaign(Number(e.target.value))}/></label><label>Brand analyses<input type="number" min={0} max={100} value={brand} onChange={e => setBrand(Number(e.target.value))}/></label></div><button className="primary" disabled={busy}>Grant allowance</button></form></div></section>}
  </>
}

export default function MarketingApp() {
  const [logged, setLogged] = useState(false)
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<Data | null>(null)
  const [error, setError] = useState('')
  const [route, setRoute] = useState(currentRoute)
  const [analysisId, setAnalysisId] = useState<string | null>(null)
  const requestNumber = useRef(0)
  const refresh = useCallback(async () => {
    const number = ++requestNumber.current
    const [user, usage, business, brand, assets, runs] = await Promise.all([
      api<User>('/me'), api<Usage>('/usage'), api<Resource<Business> | null>('/business'),
      api<Resource<Brand> | null>('/brand'), api<Resource<Asset>[]>('/assets'), api<Run[]>('/runs'),
    ])
    if (number === requestNumber.current) setData({ user, usage, business, brand, assets, runs })
  }, [])
  useEffect(() => { initializeSession().then(setLogged).catch(reason => setError(reason.message)).finally(() => setLoading(false)) }, [])
  useEffect(() => { if (logged) { setLoading(true); refresh().catch(reason => setError(reason.message)).finally(() => setLoading(false)) } }, [logged, refresh])
  const active = data?.runs.some(run => ['queued', 'running'].includes(run.state)) ?? false
  useEffect(() => { if (!active) return; const timer = setInterval(() => { void refresh().catch(() => undefined) }, 3000); return () => clearInterval(timer) }, [active, refresh])
  useEffect(() => { const update = () => setRoute(currentRoute()); window.addEventListener('popstate', update); window.addEventListener('hashchange', update); return () => { window.removeEventListener('popstate', update); window.removeEventListener('hashchange', update) } }, [])
  const navigate = (page: Page, id?: string) => { history.pushState({}, '', `#/${page}${id ? '/' + id : ''}`); setRoute({ page, id: id ?? null }); window.scrollTo(0, 0) }
  const login = async () => { setError(''); try { await signIn() } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) } }
  const logout = async () => { setLogged(false); setData(null); try { await signOut() } catch (reason) { setError(String(reason)) } }
  if (!logged || !data) return <div className="login-page"><div className="login-photo"><img src="/marketing/latte.png" alt="A warm latte in a neighborhood café"/></div><main className="login-copy"><Wordmark/><h1>Your neighborhood.<br/>Your next great ad.</h1><p>Bring your brand. Let your agents find a timely reason for people to stop by.</p>{error && <Notice>{error}</Notice>}<button className="primary" disabled={loading} onClick={() => void login()}>{loading ? 'Opening your workspace…' : 'Sign in to your workspace'}<Icon name="arrow" size={19}/></button><p className="small muted">Invitation-only access. Replay first. Nothing publishes without your approval.</p><small className="demo-caption">Illustrative café photography created for this demo.</small></main></div>
  const businessName = data.business?.data.name || data.user.name
  const selectedNav = route.page === 'review' ? 'campaigns' : route.page
  const selectedRun = data.runs.find(run => run.id === route.id)
  return <div className="marketing-shell"><a className="skip-link" href="#main-content">Skip to content</a><aside className="sidebar"><Wordmark/><nav aria-label="Main navigation">{nav.map(item => <button key={item.page} className={selectedNav === item.page ? 'active' : ''} aria-current={selectedNav === item.page ? 'page' : undefined} onClick={() => navigate(item.page)}><Icon name={item.page}/>{item.label}</button>)}</nav><div className="sidebar-account"><button onClick={() => navigate('business')}><span className="avatar">{businessName.charAt(0).toUpperCase()}</span><span>{businessName}</span><Icon name="arrow" size={16}/></button><button onClick={() => void logout()}><Icon name="logout"/>Sign out</button></div></aside>
    <main className="workspace" id="main-content"><div className="topbar"><span>Workspace <span className="slash">/</span> {route.page === 'review' ? 'Campaign review' : nav.find(n => n.page === route.page)?.label}</span><span>{businessName}{selectedRun?.mode === 'replay' ? ' · Recorded replay' : data.business?.data.city ? ' · ' + data.business.data.city : ''}</span></div>
      {error && <Notice>{error}</Notice>}
      {route.page === 'today' && <Today data={data} navigate={navigate} refresh={refresh}/>}
      {route.page === 'business' && <BusinessPage key={data.business?.version ?? 0} value={data.business} onSaved={refresh}/>}
      {route.page === 'brand' && <BrandPage key={data.brand?.version ?? 0} brand={data.brand} business={data.business} assets={data.assets} usage={data.usage} analysisId={analysisId ?? data.runs.find(r => r.kind === 'brand')?.id ?? null} onAnalysis={setAnalysisId} onSaved={refresh}/>}
      {route.page === 'campaigns' && <History runs={data.runs} open={run => { if (run.kind === 'brand') { setAnalysisId(run.id); navigate('brand') } else navigate('review', run.id) }}/>} 
      {route.page === 'settings' && <SettingsPage data={data} refresh={refresh}/>}
      {route.page === 'review' && (route.id ? <ReviewPage key={route.id} id={route.id} onNew={() => navigate('today')} onChanged={refresh}/> : <Notice>Select a campaign from your history.</Notice>)}
    </main></div>
}
