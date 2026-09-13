import { useEffect, useRef, useState } from 'react'
import { api, errorMessage, subscribeToRun } from './api/client'
import type { Connection } from './api/client'
import type { AdBrief, AdStyle, Athlete, Business, ClipInfo, DecisionValue, Run, RunCreate } from './api/types'
import { AdGallery } from './components/AdGallery'
import { AgentTimeline } from './components/AgentTimeline'
import { ClipPicker } from './components/ClipPicker'
import { DetailDrawer } from './components/DetailDrawer'
import { ExportPanel } from './components/ExportPanel'
import { VideoStage } from './components/VideoStage'
import { finalAds, RunProvider, useRun } from './state/runStore'
import styles from './studio.module.css'

function Studio() {
  const { state, dispatch } = useRun()
  const [clips, setClips] = useState<ClipInfo[]>([])
  const [runs, setRuns] = useState<Run[]>([])
  const [athletes, setAthletes] = useState<Athlete[]>([])
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [adStyles, setAdStyles] = useState<AdStyle[]>([])
  const [clip, setClip] = useState<ClipInfo>()
  const [detail, setDetail] = useState<AdBrief | null>(null)
  const [connection, setConnection] = useState<Connection>('closed')
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadAttempt, setLoadAttempt] = useState(0)
  const currentRun = useRef<string | null>(null)
  const stop = useRef<(() => void) | null>(null)
  useEffect(() => {
    let active = true
    void Promise.all([api.clips(), api.runs(), api.athletes(), api.businesses(), api.styles()]).then(([c, r, a, b, s]) => {
      if (!active) return
      setClips(c); setRuns(r); setAthletes(a); setBusinesses(b); setAdStyles(s); setClip(c[0]); setError('')
    }).catch((failure) => { if (active) setError(errorMessage(failure)) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [loadAttempt])
  useEffect(() => () => { stop.current?.(); currentRun.current = null }, [])
  async function reconcile(id: string) {
    const ads = await api.ads(id)
    if (currentRun.current === id) dispatch({ type: 'reconcile', runId: id, ads })
  }
  async function start(body: RunCreate) {
    setStarting(true); setError(''); setDetail(null)
    try {
      const run = await api.start(body)
      stop.current?.()
      currentRun.current = run.id
      dispatch({ type: 'reset', run })
      setRevision((value) => value + 1)
      stop.current = subscribeToRun(run.id, (event) => {
        dispatch(event)
        if (event.type === 'run_completed' || event.type === 'run_failed') {
          void reconcile(run.id).catch((failure) => {
            if (currentRun.current === run.id) setError(errorMessage(failure))
          })
          void api.runs().then(setRuns).catch((failure) => setError(errorMessage(failure)))
        }
      }, setConnection, setError)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setStarting(false) }
  }
  async function decide(id: string, decision: DecisionValue, note: string) {
    const runId = currentRun.current
    if (!runId) return
    await api.decide(id, { decision, reviewer: 'demo', note })
    await reconcile(runId)
    if (currentRun.current === runId) setRevision((value) => value + 1)
  }
  const ads = finalAds(state)
  return <div className={styles.app}>
    <header className={styles.header}><div className={styles.brand}>Goldcoast<span>Local discovery studio</span></div><p>LA 2028 · From a big moment to a nearby favorite</p></header>
    <main>
      <ClipPicker clips={clips} runs={runs} selected={clip} onSelect={setClip} onStart={(body) => void start(body)} busy={loading || starting || state.status === 'running'} />
      {loading && <p role="status">Loading clips and recordings…</p>}
      {error && <div role="alert" className={styles.error}>{error} <button onClick={() => {
        if (state.runId) void reconcile(state.runId).then(() => setError('')).catch((failure) => setError(errorMessage(failure)))
        else { setLoading(true); setLoadAttempt((value) => value + 1) }
      }}>Retry loading</button></div>}
      {connection === 'reconnecting' && <p role="status" className={styles.banner}>Connection interrupted. Reconnecting from the last event…</p>}
      {state.runId && <div className={styles.runSummary} role="status"><strong>{state.status === 'completed' ? 'Run completed' : state.status === 'failed' ? 'Run failed' : 'Agents working'}</strong>
        <span>{state.moments.length} moments · {Object.keys(state.briefs).length} briefs · {ads.length} final ads · {Object.keys(state.generatedById).length} attempts</span><small>Run {state.runId}</small></div>}
      {state.failures.map((failure, index) => <p key={index} className={styles.error}>{failure.stage}: {failure.message}</p>)}
      <div className={styles.workspace}><div className={styles.leftRail}>
        <VideoStage clip={clip} moments={state.moments} runId={state.runId} />
        <AgentTimeline events={state.timeline} />
      </div><div className={styles.galleryRail}>
        <AdGallery state={state} businesses={businesses} onDetail={setDetail} onDecision={decide} />
        <ExportPanel key={`${state.runId}/${revision}`} runId={state.runId} approved={ads.filter((ad) => ad.decision?.decision === 'approved').length} />
      </div></div>
    </main>
    {detail && <DetailDrawer brief={detail} athlete={athletes.find((item) => item.id === detail.athlete_id)} business={businesses.find((item) => item.id === detail.business_id)} style={adStyles.find((item) => item.id === detail.ad_style_id)} onClose={() => setDetail(null)} />}
  </div>
}
export default function App() { return <RunProvider><Studio /></RunProvider> }
