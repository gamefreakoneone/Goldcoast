export interface Resource<T> { id: string; version: number; data: T }
export interface Product { id?: string; name: string; description: string; price: string }
export interface Offer { text: string; valid_until: string; confirmed: true }
export interface Business {
  name: string; category: 'cafe' | 'bakery' | 'restaurant' | 'bar' | 'cafe_goods'; city: string;
  neighborhood: string; address: string; timezone: string; website: string | null;
  description: string; hours: string; products: Product[]; offers: Offer[];
  audience: string; confirmed: boolean;
}
export interface Brand {
  palette: string[]; voice: string; typography: 'sans' | 'serif' | 'mono'; layout: string;
  image_direction: string; prohibited: string[]; reference_asset_ids: string[];
  logo_asset_id: string | null; font_asset_id: string | null; uncertainty: string[]; confirmed: boolean;
}
export type AssetRole = 'logo' | 'product' | 'reference' | 'guidelines' | 'font' | 'video' | 'testimonial'
export interface Asset {
  business_id: string; filename: string; role: AssetRole; mime: string; size: number;
  product_id?: string | null; marketing_kind?: 'owned' | 'inspiration'; source_url?: string | null;
  sha256: string; width: number | null; height: number | null; rights_confirmed: true;
}
export interface User { id: string; name: string; role: 'owner' | 'business' | 'demo' }
export interface Usage {
  feed_remaining?: number; testimonial_remaining?: number; global_feed_remaining?: number; global_testimonial_remaining?: number;
  campaign_remaining: number; brand_remaining: number; active_job: string | null;
  live_enabled: boolean; global_campaign_remaining: number; global_brand_remaining: number;
}
export interface Run {
  id: string; kind: 'campaign' | 'brand' | 'feed' | 'testimonial'; mode: 'live' | 'replay';
  state: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  input: { creative_type?: string; include_story?: boolean; goal?: string; source?: string; regenerate_from?: string; owner_feedback?: string; snapshot?: { profile: Business } };
  checkpoint: Record<string, { state: string; output?: unknown }>;
  counters: Record<string, number>; created_at: number; finished_at: number | null;
}
export interface Source {
  id: string; url: string; title: string; text: string; provider: string;
  retrieved_at: string; expires_at: string; content_hash: string;
}
export interface Graph {
  sources: Source[]; nodes: { id: string; label: string; kind: 'source' | 'entity' }[];
  edges: { source: string; target: string; predicate: string; value: string; quote: string;
    state: 'supported' | 'disputed' | 'stale'; valid_until: string }[]; built_at: string;
}
export interface Candidate {
  id: string; category: 'local' | 'culture' | 'evergreen'; title: string; angle: string;
  product_id?: string; location?: string; event_date?: string; date_quote?: string;
  product_name: string; source_ids: string[]; expires_at: string; fit: number;
  timeliness: number; risks: string[];
}
export interface Signals { available: boolean; reason: string; summary: string[]; sources: Source[]; claims: unknown[] }
export interface Campaign {
  local_signals?: Signals | null;
  candidates: Candidate[]; selected: Candidate; rationale: string; graph: Graph;
  rejected: { id: string; title: string; reason: string }[];
}
export interface Verdict {
  factuality: number; brand_fidelity: number; visual_quality: number; legibility: number;
  critical_issues: string[]; feedback: string; detected_text: string;
}
export interface Creative {
  decided_via?: 'studio' | 'telegram';
  job_id: string; business_id: string; brand_id: string; format: 'landscape' | 'portrait' | 'post' | 'story';
  attempt: number; width: number; height: number; sha256: string;
  brief: { headline: string; subheading: string; cta: string; product_name: string; offer_text: string; image_prompt: string; caption?: string; creative_type?: string; quote?: string; attribution?: string };
  verdict: Verdict; expires_at: string; decision: 'pending' | 'approved' | 'rejected';
  decision_note: string; decided_at: string | null; replay: boolean;
}
export interface CreativeView extends Resource<Creative> { passed: boolean; stale: boolean }
export interface StudioEvent { id: string; type: string; timestamp: number; payload: Record<string, unknown> }
export const terminal = (run: Run) => ['completed', 'failed', 'cancelled'].includes(run.state)

export interface FeedResult { ideas: Candidate[]; graph: Graph; retrieved_at: string; expires_at: string; rejected: { id: string; reason: string }[] }
export interface NotificationConnection { channel: 'telegram'; chat_id: number; chat_title: string; linked_at: string; enabled: boolean }
export interface TelegramLink { code: string; deep_link: string }
