import { useEffect, useState } from 'react'
import { mediaUrl } from '../api/client'
import styles from '../studio.module.css'

export function MediaImage({ url, path, alt }: { url: string | null; path: string | null; alt: string }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const [retries, setRetries] = useState(0)
  useEffect(() => {
    if (!url || failedUrl !== url || retries >= 2) return
    const timer = window.setTimeout(() => {
      setRetries((value) => value + 1)
      setFailedUrl(null)
    }, 750)
    return () => window.clearTimeout(timer)
  }, [failedUrl, retries, url])
  return !url || failedUrl === url ? (
    <div className={styles.placeholder} role="img" aria-label={`${alt} unavailable`}>
      Media unavailable <small>{path ?? 'No extracted frame'}</small>
    </div>
  ) : <img src={mediaUrl(url)} alt={alt} onError={() => setFailedUrl(url)} />
}
