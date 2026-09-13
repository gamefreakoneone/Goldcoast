import type { VerdictScores } from '../api/types'
import styles from '../studio.module.css'

export const scoreLabels: Record<keyof VerdictScores, string> = {
  image_quality: 'Image quality', style_adherence: 'Style adherence', business_accuracy: 'Business accuracy',
  format_compliance: 'Format compliance', brand_safety: 'Brand safety', overall: 'Overall',
}
export function Scores({ scores }: { scores: VerdictScores }) {
  return <dl className={styles.scores}>{(Object.keys(scoreLabels) as (keyof VerdictScores)[]).map((key) =>
    <div key={key}><dt>{scoreLabels[key]}</dt><dd>{scores[key]}<small>/10</small></dd></div>,
  )}</dl>
}
