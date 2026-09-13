export interface AuthConfig {
  issuer: string; client_id: string; authorization_endpoint: string;
  token_endpoint: string; logout_endpoint: string; provider?: string;
}
const base = import.meta.env.VITE_STUDIO_API_BASE || '/api/v2'
let configuration: Promise<AuthConfig> | null = null
let tokens: { access: string; refresh?: string; expires: number } | null = null
let initialization: Promise<boolean> | null = null
let refreshing: Promise<void> | null = null
const pendingKey = 'goldcoast.pkce'

export function authConfig() {
  configuration ??= fetch(base + '/auth/config').then(async response => {
    if (!response.ok) throw new Error('The studio is unavailable. Check that the API is running.')
    return response.json() as Promise<AuthConfig>
  }).catch(error => { configuration = null; throw error })
  return configuration
}

function randomString() {
  return btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32))))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export async function pkceChallenge(verifier: string) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

async function exchange(body: URLSearchParams) {
  const config = await authConfig()
  const response = await fetch(config.token_endpoint, {
    method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body,
  })
  if (!response.ok) { tokens = null; throw new Error('Your session expired. Please sign in again.') }
  const value = await response.json()
  if (typeof value.access_token !== 'string' || !Number.isFinite(value.expires_in)) {
    throw new Error('The sign-in provider returned an invalid session.')
  }
  tokens = { access: value.access_token, refresh: value.refresh_token ?? tokens?.refresh,
    expires: Date.now() + value.expires_in * 1000 }
}

export async function signIn() {
  const config = await authConfig()
  const verifier = randomString()
  const state = randomString()
  const redirect = location.origin + location.pathname
  sessionStorage.setItem(pendingKey, JSON.stringify({ verifier, state, redirect, created: Date.now() }))
  const url = new URL(config.authorization_endpoint)
  url.search = new URLSearchParams({ client_id: config.client_id, response_type: 'code',
    scope: 'openid profile', redirect_uri: redirect, state,
    code_challenge: await pkceChallenge(verifier), code_challenge_method: 'S256' }).toString()
  location.assign(url.toString())
}

export function initializeSession() {
  initialization ??= (async () => {
    const params = new URLSearchParams(location.search)
    if (!params.has('code') && !params.has('error')) return Boolean(tokens)
    const raw = sessionStorage.getItem(pendingKey)
    sessionStorage.removeItem(pendingKey)
    history.replaceState({}, '', location.pathname + location.hash)
    if (params.has('error')) throw new Error('Sign-in was not completed. Please try again.')
    if (!raw) throw new Error('This sign-in request has expired. Please sign in again.')
    const pending = JSON.parse(raw)
    if (params.get('state') !== pending.state || Date.now() - pending.created > 600_000) {
      throw new Error('Sign-in state did not match. Please start again.')
    }
    const config = await authConfig()
    if (params.has('iss') && params.get('iss') !== config.issuer) throw new Error('Unexpected sign-in provider.')
    await exchange(new URLSearchParams({ grant_type: 'authorization_code', client_id: config.client_id,
      code: params.get('code')!, redirect_uri: pending.redirect, code_verifier: pending.verifier }))
    return true
  })()
  return initialization
}

export async function accessToken(staleToken?: string): Promise<string> {
  if (!tokens) throw new Error('Please sign in to continue.')
  const force = staleToken === tokens.access
  if (force || tokens.expires < Date.now() + 30_000) {
    if (!tokens.refresh) throw new Error('Your session expired. Please sign in again.')
    if (!refreshing) {
      const refresh = tokens.refresh
      refreshing = authConfig().then(config => exchange(new URLSearchParams({
        grant_type: 'refresh_token', client_id: config.client_id, refresh_token: refresh,
      }))).finally(() => { refreshing = null })
    }
    await refreshing
  }
  if (!tokens) throw new Error('Please sign in again.')
  return tokens.access
}

export async function signOut() {
  tokens = null
  sessionStorage.removeItem(pendingKey)
  initialization = null
  const config = await authConfig()
  const url = new URL(config.logout_endpoint)
  url.searchParams.set('client_id', config.client_id)
  url.searchParams.set(config.provider === 'cognito' ? 'logout_uri' : 'post_logout_redirect_uri', location.origin + '/')
  location.assign(url.toString())
}
