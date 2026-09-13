import type { AdBrief, AdWithVerdict, Business, DecisionValue } from '../api/types'
import { finalAds } from '../state/runStore'
import type { RunState } from '../state/runStore'
import { AdCard } from './AdCard'
import styles from '../studio.module.css'

export function groupAds(ads: AdWithVerdict[]) {
  const groups = new Map<string, Map<string, AdWithVerdict[]>>()
  for (const ad of ads) {
    if (!ad.verdict) continue
    if (!groups.has(ad.business_id)) groups.set(ad.business_id, new Map())
    const briefs = groups.get(ad.business_id)!
    const pair = briefs.get(ad.brief_id) ?? []
    const old = pair.findIndex((item) => item.format === ad.format)
    if (old >= 0) pair[old] = ad
    else pair.push(ad)
    briefs.set(ad.brief_id, pair.sort((a, b) => a.format.localeCompare(b.format)))
  }
  return groups
}

export function galleryAds(state: RunState): AdWithVerdict[] {
  const finals = finalAds(state)
  const pending = new Map<string, AdWithVerdict>()
  for (const ad of Object.values(state.generatedById)) {
    const verdict = state.verdictsByAd[ad.id]
    if (!verdict || state.adsByBrief[ad.brief_id]?.[ad.format]) continue
    const key = `${ad.brief_id}/${ad.format}`
    if ((pending.get(key)?.attempt ?? 0) > ad.attempt) continue
    const attempts = Object.values(state.generatedById)
      .filter((item) => item.brief_id === ad.brief_id && item.format === ad.format)
      .sort((a, b) => a.attempt - b.attempt)
      .map((item) => ({ ad: item, verdict: state.verdictsByAd[item.id] ?? null, is_final: false }))
    pending.set(key, { ...ad, verdict, decision: null, errors: [], attempts })
  }
  return [...finals, ...pending.values()]
}

export function AdGallery({ state, businesses, onDetail, onDecision }: {
  state: RunState; businesses: Business[]; onDetail: (brief: AdBrief) => void
  onDecision: (id: string, decision: DecisionValue, note: string) => Promise<void>
}) {
  const groups = groupAds(galleryAds(state))
  const finals = finalAds(state)
  return <section aria-labelledby="gallery-title">
    <div className={styles.sectionHeading}><h2 id="gallery-title">Local discoveries</h2><span>{finals.length} final ads</span></div>
    <p className={styles.muted}>Two formats per moment. Judge checked, human approved.</p>
    {!groups.size && <div className={styles.empty}>Judged ads will appear here as the agents work.</div>}
    {[...groups].map(([businessId, briefs]) => <section key={businessId} className={styles.business}>
      <h3>{businesses.find((item) => item.id === businessId)?.name ?? businessId}</h3>
      {[...briefs].map(([briefId, ads]) => {
        const brief = state.briefs[briefId]
        const moment = state.moments.find((item) => item.id === brief?.moment_id)
        return <div key={briefId} className={styles.brief} data-brief-id={briefId}>
          <div className={styles.sectionHeading}><span>{moment ? `Moment · ${moment.best_frame_s}s` : 'Matched brief'}</span>
            {brief && <button onClick={() => onDetail(brief)}>Why this match?</button>}</div>
          {brief && <p className={styles.offer}>{brief.offer_text}</p>}
          <div className={styles.formatPair}>{ads.map((ad) => <AdCard key={ad.id} ad={ad}
            isFinal={state.adsByBrief[ad.brief_id]?.[ad.format]?.id === ad.id} onDecision={onDecision} />)}</div>
        </div>
      })}
    </section>)}
  </section>
}
