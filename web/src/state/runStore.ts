import { createContext, createElement, useContext, useReducer } from 'react'
import type { Dispatch, ReactNode } from 'react'
import type {
  AdBrief, AdFormat, AdView, AdWithVerdict, ApprovalDecision, JudgedAd,
  MomentView, PipelineEvent, QualityVerdict, Run, RunFailure,
} from '../api/types'

export interface RunState {
  runId: string | null
  status: 'idle' | Run['status']
  moments: MomentView[]
  briefs: Record<string, AdBrief>
  adsByBrief: Record<string, Partial<Record<AdFormat, AdWithVerdict>>>
  generatedById: Record<string, AdView>
  verdictsByAd: Record<string, QualityVerdict>
  timeline: PipelineEvent[]
  failures: RunFailure[]
  lastEventId: number
}
export const initialState: RunState = {
  runId: null, status: 'idle', moments: [], briefs: {}, adsByBrief: {},
  generatedById: {}, verdictsByAd: {}, timeline: [], failures: [], lastEventId: -1,
}

function setAd(state: RunState, ad: AdWithVerdict): RunState {
  if (!ad.verdict || ad.verdict.ad_id !== ad.id || ad.verdict.attempt !== ad.attempt) return state
  return {
    ...state,
    adsByBrief: { ...state.adsByBrief, [ad.brief_id]: { ...state.adsByBrief[ad.brief_id], [ad.format]: ad } },
    verdictsByAd: { ...state.verdictsByAd, [ad.id]: ad.verdict },
  }
}

export function runReducer(state: RunState, event: PipelineEvent): RunState {
  if ((state.runId && event.run_id !== state.runId) || Number(event.id) <= state.lastEventId) return state
  let next = { ...state, runId: event.run_id, timeline: [...state.timeline, event], lastEventId: Number(event.id) }
  const payload = event.payload
  switch (event.type) {
    case 'run_started':
      return { ...next, status: 'running' }
    case 'moment_detected':
    case 'frame_extracted': {
      const moment = payload as unknown as MomentView
      const exists = state.moments.some((item) => item.id === moment.id)
      return { ...next, moments: exists ? state.moments.map((item) => item.id === moment.id ? moment : item) : [...state.moments, moment] }
    }
    case 'brief_created': {
      const brief = payload as unknown as AdBrief
      return { ...next, briefs: { ...state.briefs, [brief.id]: brief } }
    }
    case 'ad_generated': {
      const ad = payload as unknown as AdView
      return { ...next, generatedById: { ...state.generatedById, [ad.id]: ad } }
    }
    case 'ad_judged': {
      const verdict = payload as unknown as QualityVerdict
      return { ...next, verdictsByAd: { ...state.verdictsByAd, [verdict.ad_id]: verdict } }
    }
    case 'ad_final': {
      const final = payload as unknown as JudgedAd
      for (const [ad, verdict] of final.attempts) {
        next = { ...next, generatedById: { ...next.generatedById, [ad.id]: ad } }
        if (verdict) next.verdictsByAd = { ...next.verdictsByAd, [ad.id]: verdict }
      }
      return setAd(next, {
        ...final.final_ad, verdict: final.final_verdict, decision: null, errors: final.errors,
        attempts: final.attempts.map(([ad, verdict]) => ({ ad, verdict, is_final: ad.id === final.final_ad.id })),
      })
    }
    case 'ad_decided': {
      const decision = payload as unknown as ApprovalDecision
      const ad = finalAds(state).find((item) => item.id === decision.ad_id)
      return ad ? setAd(next, { ...ad, decision }) : next
    }
    case 'moment_skipped':
      return { ...next, failures: [...state.failures, payload as unknown as RunFailure] }
    case 'run_completed':
    case 'run_failed':
      return {
        ...next, status: event.type === 'run_completed' ? 'completed' : 'failed',
        failures: (payload.failures as RunFailure[] | undefined) ?? state.failures,
      }
    default:
      return next
  }
}

export const finalAds = (state: RunState) => Object.values(state.adsByBrief).flatMap((pair) => Object.values(pair))
export type StoreAction = PipelineEvent | { type: 'reset'; run: Run } | { type: 'reconcile'; runId: string; ads: AdWithVerdict[] }
function storeReducer(state: RunState, action: StoreAction): RunState {
  if (action.type === 'reset') return { ...initialState, runId: action.run.id, status: action.run.status }
  if (action.type === 'reconcile') {
    if (action.runId !== state.runId) return state
    return action.ads.reduce(setAd, { ...state, adsByBrief: {} })
  }
  return runReducer(state, action)
}
const RunContext = createContext<{ state: RunState; dispatch: Dispatch<StoreAction> } | null>(null)
export function RunProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(storeReducer, initialState)
  return createElement(RunContext.Provider, { value: { state, dispatch } }, children)
}
export function useRun() {
  const context = useContext(RunContext)
  if (!context) throw new Error('RunProvider is required')
  return context
}
