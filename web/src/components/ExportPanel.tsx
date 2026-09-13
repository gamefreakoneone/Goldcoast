import { useState } from 'react'
import { api, errorMessage, mediaUrl } from '../api/client'
import type { ExportManifest } from '../api/types'
import styles from '../studio.module.css'

export function ExportPanel({ runId, approved }: { runId: string | null; approved: number }) {
  const [manifest, setManifest] = useState<ExportManifest | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function exportAds() {
    if (!runId) return
    setBusy(true)
    setError('')
    try { setManifest(await api.export(runId)) }
    catch (failure) { setError(errorMessage(failure)) }
    finally { setBusy(false) }
  }
  return <section className={styles.exportPanel} aria-labelledby="export-title">
    <div className={styles.sectionHeading}><div><h2 id="export-title">Ready to go</h2><p>{approved} approved for export</p></div>
      <button className={styles.primary} disabled={!runId || busy} onClick={() => void exportAds()}>{busy ? 'Exporting…' : 'Export approved'}</button></div>
    {manifest && <div><p>Exported {manifest.ads.length} approved files</p>
      <ul>{manifest.ads.map((ad) => <li key={ad.ad_id}><a href={mediaUrl(ad.image_url)} download>{ad.path.split('/').at(-1)}</a></li>)}</ul>
      <details><summary>Export manifest</summary><pre>{JSON.stringify(manifest, null, 2)}</pre></details>
    </div>}
    {error && <p className={styles.error} role="alert">{error}</p>}
  </section>
}
