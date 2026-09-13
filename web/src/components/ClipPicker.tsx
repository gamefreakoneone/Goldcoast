import { useState } from 'react'
import type { ClipInfo, Run, RunCreate } from '../api/types'
import styles from '../studio.module.css'

export const demoSource = '20260912-230559-0d2470'
const fileName = (path: string) => path.replaceAll('\\', '/').split('/').at(-1)

export function ClipPicker({ clips, runs, selected, onSelect, onStart, busy }: {
  clips: ClipInfo[]; runs: Run[]; selected?: ClipInfo; onSelect: (clip: ClipInfo) => void
  onStart: (body: RunCreate) => void; busy: boolean
}) {
  const [replay, setReplay] = useState(true)
  const [source, setSource] = useState(demoSource)
  const sources = runs.filter((run) => run.status === 'completed' && fileName(run.clip_path) === selected?.file)
  const chosen = sources.some((run) => run.id === source) ? source : sources[0]?.id ?? ''
  return (
    <form className={styles.picker} onSubmit={(event) => {
      event.preventDefault()
      if (selected) onStart({ clip_path: selected.clip_path, replay, replay_from: replay ? chosen : null })
    }}>
      <label>Clip
        <select value={selected?.file ?? ''} disabled={busy || !clips.length} onChange={(event) => {
          const clip = clips.find((item) => item.file === event.target.value)
          if (clip) onSelect(clip)
        }}>
          {!clips.length && <option value="">No clips available</option>}
          {clips.map((clip) => <option key={clip.file} value={clip.file}>{clip.file}{clip.available ? '' : ' · video unavailable'}</option>)}
        </select>
      </label>
      <label className={styles.toggle}><input type="checkbox" checked={replay} disabled={busy} onChange={(event) => setReplay(event.target.checked)} /> Replay recording</label>
      {replay && <label>Recording
        <select value={chosen} disabled={busy || !sources.length} onChange={(event) => setSource(event.target.value)}>
          {!sources.length && <option value="">No matching completed recording</option>}
          {sources.map((run) => <option key={run.id} value={run.id}>{run.id}{run.id === demoSource ? ' · original demo' : ''}</option>)}
        </select>
      </label>}
      <button className={styles.primary} disabled={busy || !selected || (replay ? !chosen : !selected.available)}>
        {busy ? 'Working…' : replay ? 'Start replay' : 'Start live run'}
      </button>
    </form>
  )
}
