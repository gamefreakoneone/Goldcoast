import type { ReactNode } from 'react'

export function Icon({ name, size = 22 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    today: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z" /></>,
    brand: <><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 6"/></>,
    business: <><path d="M4 9v12h16V9M3 9l2-6h14l2 6M3 9c0 4 4 4 4 0 0 4 5 4 5 0 0 4 5 4 5 0 0 4 4 4 4 0M9 21v-7h6v7"/></>,
    campaigns: <><path d="m3 10 18-7-7 18-4-7-7-4Z M10 14 21 3"/></>,
    settings: <><path d="m9 3-1 3-3 1v3l-2 2 2 2v3l3 1 1 3h6l1-3 3-1v-3l2-2-2-2V7l-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/></>,
    arrow: <><path d="M4 12h16m-6-6 6 6-6 6"/></>,
    upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    logout: <><path d="M9 3H4v18h5M8 12h13m-5-5 5 5-5 5"/></>,
    download: <><path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/></>,
    close: <path d="m6 6 12 12M6 18 18 6"/>,
    plus: <path d="M12 4v16M4 12h16"/>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.today}</svg>
}

export function Wordmark() {
  return <div className="wordmark">goldcoast<svg width="38" height="34" viewBox="0 0 38 34" aria-hidden="true"><path d="M9 25a10 10 0 0 1 20 0Z" fill="currentColor"/><g fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 3v6M4 10l5 5M34 10l-5 5M0 25h6M32 25h6M10 4l2 6M28 4l-2 6"/></g></svg></div>
}

export function PageHeading({ title, children }: { title: string; children: ReactNode }) {
  return <header className="page-heading"><h1>{title}</h1><p>{children}</p></header>
}

export function Notice({ children, tone = 'error' }: { children: ReactNode; tone?: 'error' | 'success' | 'info' }) {
  return <div className={`notice ${tone}`} role={tone === 'error' ? 'alert' : 'status'}>{children}</div>
}

export function Status({ good, children }: { good: boolean; children: ReactNode }) {
  return <span className={`status ${good ? 'good' : 'neutral'}`}>{good ? <span className="check-dot"><Icon name="check" size={13}/></span> : <span className="dot"/>}{children}</span>
}
