import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'

const App = import.meta.env.VITE_LEGACY_UI === '1'
  ? lazy(() => import('./App'))
  : lazy(() => import('./marketing/MarketingApp'))

createRoot(document.getElementById('root')!).render(
  <StrictMode><Suspense fallback={<p>Opening Goldcoast?</p>}><App /></Suspense></StrictMode>,
)
