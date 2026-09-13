import { useState } from 'react'
import { errorMessage, mediaUrl } from '../api/client'
import type { AdWithVerdict, DecisionValue } from '../api/types'
import { MediaImage } from './MediaImage'
import { Scores } from './Scores'
import styles from '../studio.module.css'

export function AdCard({ ad, isFinal, onDecision }: {
  ad: AdWithVerdict; isFinal: boolean; onDecision: (id: string, decision: DecisionValue, note: string) => Promise<void>
}) {
  const [note, setNote] = useState(ad.decision?.note ?? '')
  const [rejecting, setRejecting] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function decide(decision: DecisionValue) {
    setBusy(true)
    setError('')
    try {
      await onDecision(ad.id, decision, note)
      setRejecting(false)
    } catch (failure) {
      setError(errorMessage(failure))
    } finally {
      setBusy(false)
    }
  }
  if (!ad.verdict) return <p>Awaiting judge verdict</p>
  return <article className={styles.adCard} data-ad-id={ad.id} data-final={isFinal} aria-label={`${ad.format} ad`}>
    <div className={styles.cardHeading}><h4>{ad.format === 'landscape' ? 'Landscape' : 'Portrait'}</h4><span className={ad.verdict.passed ? styles.pass : styles.fail}>{ad.verdict.passed ? 'Pass' : 'Fail'}</span></div>
    <a className={styles.adImage} href={mediaUrl(ad.image_url)} target="_blank" rel="noreferrer" aria-label={`Open ${ad.format} image`}>
      <MediaImage url={ad.image_url} path={ad.image_path} alt={`${ad.format} discovery ad`} />
    </a>
    <Scores scores={ad.verdict.scores} />
    <details className={styles.reviewDetails}><summary>Judge notes · {ad.verdict.issues.length}</summary>
      {ad.verdict.issues.length ? <ul>{ad.verdict.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul> : <p>No issues reported.</p>}
      {ad.verdict.regeneration_hints.map((hint) => <p key={hint}>{hint}</p>)}
    </details>
    <details className={styles.reviewDetails}><summary>Attempt history · {ad.attempts.length}</summary>
      {ad.attempts.map((attempt) => <section key={attempt.ad.id} className={styles.attempt}>
        <a href={mediaUrl(attempt.ad.image_url)} target="_blank" rel="noreferrer">Attempt {attempt.ad.attempt}{attempt.is_final ? ' · final selection' : ''}</a>
        {attempt.verdict ? <><p>{attempt.verdict.passed ? 'Pass' : 'Fail'}</p><Scores scores={attempt.verdict.scores} />
          <ul>{attempt.verdict.issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
          {attempt.verdict.regeneration_hints.map((hint) => <p key={hint}>{hint}</p>)}
        </> : <p>No verdict recorded</p>}
      </section>)}
      {ad.errors.map((item, index) => <p className={styles.error} key={index}>{item}</p>)}
    </details>
    <p className={styles.decision} role="status">{ad.decision ? `${ad.decision.decision === 'approved' ? 'Approved' : 'Rejected'} by ${ad.decision.reviewer}` : isFinal ? 'Awaiting human review' : 'Judge checked · awaiting final selection'}</p>
    {ad.decision?.decision === 'rejected' && <p>Reason: {ad.decision.note || 'No reason supplied'}</p>}
    {rejecting && <label>Rejection reason<textarea value={note} onChange={(event) => setNote(event.target.value)} /></label>}
    <div className={styles.actions}>
      <button className={styles.primary} disabled={busy || !isFinal} onClick={() => void decide('approved')}>Approve</button>
      {rejecting ? <><button disabled={busy} onClick={() => void decide('rejected')}>Confirm rejection</button><button disabled={busy} onClick={() => setRejecting(false)}>Cancel</button></> :
        <button disabled={busy || !isFinal} onClick={() => setRejecting(true)}>Reject</button>}
    </div>
    {error && <p role="alert" className={styles.error}>{error}</p>}
  </article>
}
