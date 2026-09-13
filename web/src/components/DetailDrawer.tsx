import { useEffect, useRef } from 'react'
import type { AdBrief, AdStyle, Athlete, Business } from '../api/types'
import styles from '../studio.module.css'

export function DetailDrawer({ brief, athlete, business, style, onClose }: {
  brief: AdBrief; athlete?: Athlete; business?: Business; style?: AdStyle; onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => { dialog.current?.showModal() }, [])
  return <dialog ref={dialog} className={styles.drawer} onCancel={onClose} aria-labelledby="detail-title">
    <div className={styles.sectionHeading}><h2 id="detail-title">Why this match?</h2><button onClick={onClose}>Close</button></div>
    <p>{brief.match_reason}</p><p>Match score: {Math.round(brief.match_score * 100)}%</p>
    <h3>{athlete?.name ?? brief.athlete_id}</h3>
    {athlete && <><p>{athlete.country} · {athlete.sport} · {athlete.home_city}</p>
      <h4>Favorite foods</h4><ul>{athlete.favorite_foods.map((food) => <li key={food.cuisine}>{food.cuisine}: {food.dishes.join(', ')}</li>)}</ul>
      <h4>Interests</h4><p>{athlete.interests.map((item) => item.replaceAll('_', ' ')).join(', ')}</p>
      <details><summary>Full athlete record</summary><pre>{JSON.stringify(athlete, null, 2)}</pre></details></>}
    <h3>{business?.name ?? brief.business_id}</h3>
    {business && <><p>{business.short_description}</p><p>{business.address}</p><p>{business.offerings.join(' · ')}</p>
      <p>{business.hours} · {business.price_range}</p><a href={business.website} target="_blank" rel="noreferrer">Business website</a>
      <details><summary>Full business record</summary><pre>{JSON.stringify(business, null, 2)}</pre></details></>}
    <h3>{style?.name ?? brief.ad_style_id}</h3><p>{style?.description}</p>
    <h4>Creative direction</h4><p>{brief.headline_direction}</p><p className={styles.offer}>{brief.offer_text}</p><p>{brief.cta}</p>
  </dialog>
}
