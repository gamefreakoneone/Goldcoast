export type AdFormat = 'landscape' | 'portrait'
export type Source = 'gemini' | 'manual'
export interface AthleteHints {
  name: string | null
  country: string | null
  kit_colors: string[]
  bib_number: string | null
  crowd_reaction: string | null
  source: Source
}
export interface ManifestMoment {
  start_s: number
  end_s: number
  best_frame_s: number
  hype_score: number
  description: string
  event_context: string
  athlete_hints: AthleteHints | null
}
export interface ClipEntry {
  file: string
  sport: string | null
  athlete_id: string | null
  analyzed: boolean
  analyzed_by: Source | null
  analyzed_at: string | null
  notes: string
  moments: ManifestMoment[]
}
export interface ClipInfo extends ClipEntry {
  clip_path: string
  clip_url: string
  available: boolean
}
export interface HypeMoment extends ManifestMoment {
  id: string
  run_id: string
  clip_path: string
  best_frame_path: string | null
  sport: string
  athlete_id: string | null
  source: Source
}
export interface MomentView extends HypeMoment {
  best_frame_url: string | null
  clip_url: string
}
export interface AdBrief {
  id: string
  run_id: string
  moment_id: string
  athlete_id: string
  business_id: string
  ad_style_id: string
  match_reason: string
  match_score: number
  headline_direction: string
  offer_text: string
  cta: string
  formats: AdFormat[]
}
export interface AdMetadata {
  format_mismatch: boolean
  resized_from: [number, number] | null
  portrait_omitted: boolean
  composited: boolean
}
export interface GeneratedAd {
  id: string
  run_id: string
  brief_id: string
  business_id: string
  format: AdFormat
  attempt: number
  image_path: string
  prompt_used: string
  model_id: string
  created_at: string
  metadata: AdMetadata
}
export interface AdView extends GeneratedAd { image_url: string }
export interface VerdictScores {
  image_quality: number
  style_adherence: number
  business_accuracy: number
  format_compliance: number
  brand_safety: number
  overall: number
}
export interface QualityVerdict {
  id: string
  run_id: string
  ad_id: string
  attempt: number
  scores: VerdictScores
  passed: boolean
  issues: string[]
  regeneration_hints: string[]
  model_id: string
  created_at: string
}
export type DecisionValue = 'approved' | 'rejected'
export interface ApprovalDecision {
  ad_id: string
  decision: DecisionValue
  reviewer: string
  note: string | null
  decided_at: string
}
export interface DecisionCreate {
  ad_id?: string | null
  decision: DecisionValue
  reviewer: string
  note: string | null
}
export interface AdAttempt {
  ad: AdView
  verdict: QualityVerdict | null
  is_final: boolean
}
export interface AdWithVerdict extends AdView {
  verdict: QualityVerdict
  decision: ApprovalDecision | null
  attempts: AdAttempt[]
  errors: string[]
}
export interface JudgedAd {
  final_ad: AdView
  final_verdict: QualityVerdict
  attempts: [AdView, QualityVerdict | null][]
  errors: string[]
}
export interface RunFailure {
  stage: string
  message: string
  moment_id: string | null
  brief_id: string | null
  format: AdFormat | null
}
export interface Run {
  id: string
  clip_path: string
  status: 'running' | 'completed' | 'failed'
  started_at: string
  finished_at: string | null
  replay: boolean
  moment_ids: string[]
  brief_ids: string[]
  ad_ids: string[]
  failures: RunFailure[]
  replay_from: string | null
}
export interface RunCreate {
  clip_path: string
  replay?: boolean | null
  replay_from?: string | null
}
export const eventTypes = [
  'run_started', 'clip_loaded', 'clip_manifest_hit', 'moment_detected', 'moment_skipped',
  'frame_extracted', 'athlete_resolved', 'business_matched', 'brief_created',
  'ad_generating', 'ad_generated', 'ad_judged', 'ad_regenerating', 'ad_final',
  'run_completed', 'run_failed', 'ad_decided',
] as const
export type EventType = typeof eventTypes[number]
export interface PipelineEvent {
  id: string
  run_id: string
  type: EventType
  timestamp: string
  payload: Record<string, unknown>
}
export interface FoodPreference { cuisine: string; dishes: string[] }
export interface AthleteIdentification {
  kit_colors: string[]
  bib_number: string | null
  distinguishing_features: string[]
}
export interface Athlete {
  id: string
  name: string
  aliases: string[]
  country: string
  sport: string
  discipline: string
  event: string
  home_city: string
  favorite_foods: FoodPreference[]
  interests: string[]
  identification: AthleteIdentification
  headshot: string | null
  social_handles: Record<string, string>
  fun_facts: string[]
}
export interface Business {
  id: string
  name: string
  category: 'restaurant' | 'cafe' | 'bar' | 'sports_venue' | 'retail' | 'experience'
  tags: string[]
  address: string
  neighborhood: string
  nearest_venue: string
  short_description: string
  offerings: string[]
  logo: string
  brand_colors: string[]
  tagline: string
  offer_text: string | null
  cta: string
  website: string
  instagram: string
  hours: string | null
  price_range: string | null
  reference_photos: string[]
}
export interface AdStyle {
  id: string
  name: string
  description: string
  mood_keywords: string[]
  palette: string[]
  typography_guidance: string
  layout_notes: Record<AdFormat, string>
  required_elements: string[]
  use_when: string[]
  reference_images: string[]
}
export interface Venue {
  id: string
  name: string
  sport: string
  lat: number
  lng: number
  neighborhood: string
}
export interface ExportAd {
  ad_id: string
  brief_id: string
  business_id: string
  format: AdFormat
  path: string
  image_url: string
  decision: ApprovalDecision
}
export interface ExportManifest { run_id: string; exported_at: string; ads: ExportAd[] }
