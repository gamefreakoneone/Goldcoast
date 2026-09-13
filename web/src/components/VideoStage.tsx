import { useEffect, useRef, useState } from 'react'
import { mediaUrl } from '../api/client'
import type { ClipInfo, MomentView } from '../api/types'
import { MediaImage } from './MediaImage'
import styles from '../studio.module.css'

export function VideoStage({ clip, moments, runId }: { clip?: ClipInfo; moments: MomentView[]; runId: string | null }) {
  const video = useRef<HTMLVideoElement>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [failedClip, setFailedClip] = useState<string | null>(null)
  const [time, setTime] = useState(0)
  const moment = moments.find((item) => item.id === selectedId) ?? moments[0]
  const bestFrame = moment?.best_frame_s
  const clipUrl = clip?.clip_url
  useEffect(() => {
    const player = video.current
    if (!player) return
    const sync = () => {
      if (bestFrame !== undefined) {
        player.pause()
        player.currentTime = bestFrame
      } else {
        player.currentTime = 0
        if (runId) void player.play().catch(() => undefined)
      }
    }
    if (player.readyState >= 1) sync()
    player.addEventListener('loadedmetadata', sync)
    return () => player.removeEventListener('loadedmetadata', sync)
  }, [bestFrame, runId, clipUrl])
  const highlighted = moment && time >= moment.start_s && time <= moment.end_s
  return (
    <section className={styles.panel} aria-labelledby="stage-title">
      <div className={styles.sectionHeading}><h2 id="stage-title">The moment</h2><span>{moments.length} detected</span></div>
      <div className={styles.stageMedia}>
        <div className={styles.videoWrap}>
          {clip?.available && failedClip !== clip.clip_url ? <video ref={video} src={mediaUrl(clip.clip_url)} controls muted playsInline preload="metadata"
            aria-label="Olympics clip" onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
            onSeeked={(event) => setTime(event.currentTarget.currentTime)} onError={() => setFailedClip(clip.clip_url)} /> :
            <div className={styles.placeholder}>Video unavailable<small>{clip?.clip_path ?? 'Choose a clip to begin'}</small></div>}
          {highlighted && <div className={styles.highlight}>Hype window · {moment.start_s}–{moment.end_s}s</div>}
        </div>
        <figure className={styles.frame}>
          {moment ? <MediaImage key={moment.id} url={moment.best_frame_url} path={moment.best_frame_path} alt={`Best frame at ${moment.best_frame_s}s`} /> :
            <div className={styles.placeholder}>Waiting for a hype moment</div>}
          <figcaption>{moment ? `Best frame · ${moment.best_frame_s}s` : 'Extracted frame'}</figcaption>
        </figure>
      </div>
      <div className={styles.momentTabs} aria-label="Detected moments">
        {moments.map((item, index) => <button key={item.id} aria-pressed={item.id === moment?.id} onClick={() => setSelectedId(item.id)}>Moment {index + 1} · {item.best_frame_s}s</button>)}
      </div>
      <p>{moment?.description ?? 'Play the clip, follow the agents, and discover the local businesses behind each ad.'}</p>
      {moment && <small>Hype {moment.hype_score}/10 · {moment.event_context} · {moment.source === 'manual' ? 'Hand-edited moment' : 'Recorded detection'}</small>}
    </section>
  )
}
