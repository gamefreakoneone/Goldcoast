import { useEffect, useRef, useState } from 'react'
import type { EventType, PipelineEvent, QualityVerdict } from '../api/types'
import { Scores } from './Scores'
import styles from '../studio.module.css'

const labels: Record<EventType, [string, string]> = {
  run_started: ['▶', 'Watching'], clip_loaded: ['▶', 'Clip loaded'], clip_manifest_hit: ['↺', 'Clip recognized'],
  moment_detected: ['✦', 'Hype detected'], frame_extracted: ['▣', 'Frame extracted'], moment_skipped: ['!', 'Moment skipped'],
  athlete_resolved: ['◎', 'Athlete resolved'], business_matched: ['↗', 'Business matched'], brief_created: ['≡', 'Brief created'],
  ad_generating: ['◌', 'Generating'], ad_generated: ['▧', 'Ad generated'], ad_judged: ['✓', 'Judged'],
  ad_regenerating: ['↻', 'Regenerating'], ad_final: ['◆', 'Final'], run_completed: ['✓', 'Run completed'],
  run_failed: ['!', 'Run failed'], ad_decided: ['✓', 'Human decision'],
}
export function AgentTimeline({ events }: { events: PipelineEvent[] }) {
  const list = useRef<HTMLOListElement>(null)
  const [follow, setFollow] = useState(true)
  useEffect(() => {
    if (follow && list.current) list.current.scrollTop = list.current.scrollHeight
  }, [events.length, follow])
  return <section className={styles.panel} aria-labelledby="timeline-title">
    <div className={styles.sectionHeading}><h2 id="timeline-title">Agent timeline</h2><label className={styles.toggle}><input type="checkbox" checked={follow} onChange={(event) => setFollow(event.target.checked)} /> Follow events</label></div>
    <p className={styles.muted}>{events.length} events · every hand-off, in order</p>
    {!events.length && <p className={styles.empty}>Start a run to watch the story unfold.</p>}
    <ol ref={list} className={styles.timeline}>
      {events.map((event) => <li key={event.id} data-event-type={event.type}>
        <span className={styles.eventIcon} aria-hidden="true">{labels[event.type][0]}</span>
        <details>
          <summary><strong>{labels[event.type][1]}</strong><time>{new Date(event.timestamp).toLocaleTimeString()}</time></summary>
          {event.type === 'ad_judged' && <Scores scores={(event.payload as unknown as QualityVerdict).scores} />}
          {event.type === 'ad_regenerating' && <ul>{(event.payload.hints as string[] ?? []).map((hint) => <li key={hint}>{hint}</li>)}</ul>}
          {event.type === 'run_failed' && <p className={styles.error}>{String(event.payload.reason ?? event.payload.error ?? event.payload.message ?? 'Run failed; inspect the recorded details below.')}</p>}
          <pre>{JSON.stringify(event.payload, null, 2)}</pre>
        </details>
      </li>)}
    </ol>
  </section>
}
