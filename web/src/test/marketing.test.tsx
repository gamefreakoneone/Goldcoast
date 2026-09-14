import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MarketingApp from '../marketing/MarketingApp'
import { api } from '../marketing/client'
import { initializeSession } from '../marketing/auth'
import type { Business, Resource } from '../marketing/types'

vi.mock('../marketing/auth', () => ({ initializeSession: vi.fn(async () => true), signIn: vi.fn(), signOut: vi.fn() }))
vi.mock('../marketing/client', () => ({ api: vi.fn(), authenticatedFetch: vi.fn(), streamEvents: vi.fn(async () => undefined), downloadCampaign: vi.fn() }))
const mockApi = vi.mocked(api)
let business: Resource<Business> | null
beforeEach(() => {
  history.replaceState({}, '', '/')
  business = null
  mockApi.mockReset()
  mockApi.mockImplementation(async (path, body) => {
    if (path === '/me') return { id: 'a'.repeat(32), name: 'Demo owner', role: 'owner' }
    if (path === '/usage') return { campaign_remaining: 0, brand_remaining: 0, live_enabled: false, active_job: null, global_campaign_remaining: 3, global_brand_remaining: 3 }
    if (path === '/business') {
      if (body) business = { id: 'b'.repeat(32), version: 1, data: (body as { profile: Business }).profile }
      return business
    }
    if (path === '/brand') return null
    if (path === '/assets' || path === '/runs') return []
    throw new Error('Unexpected API route: ' + path)
  })
  window.scrollTo = vi.fn()
})

describe('marketing workspace', () => {
  it('discovers a phone campaign while idle without reloading the website', async () => {
    vi.useFakeTimers()
    const initial = mockApi.getMockImplementation()!
    let phone = false
    mockApi.mockImplementation(async (path, ...args) => path === '/runs' && phone ? [{ id: 'phone', kind: 'campaign', mode: 'live', state: 'completed', started_via: 'telegram', input: { goal: 'Cold brew from my phone' }, created_at: 1 }] : initial(path, ...args))
    const view = render(<MarketingApp />)
    await act(async () => { await Promise.resolve() })
    fireEvent.click(screen.getByRole('button', { name: 'Campaigns' }))
    expect(screen.queryByText('Cold brew from my phone')).not.toBeInTheDocument()
    phone = true
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(screen.getByText('Cold brew from my phone')).toBeVisible()
    expect(screen.getByText(/Via phone/)).toBeVisible()
    view.unmount()
    vi.useRealTimers()
  })
  it('starts in replay and does not silently start paid work', async () => {
    render(<MarketingApp />)
    await screen.findByRole('heading', { name: 'Your daily marketing desk.' })
    expect(screen.getByRole('button', { name: 'Replay' })).toHaveClass('selected')
    expect(screen.getByRole('button', { name: 'Try recorded example' })).toBeEnabled()
    expect(mockApi.mock.calls.every(([, body]) => body === undefined)).toBe(true)
    await userEvent.click(screen.getByRole('button', { name: 'Live' }))
    expect(screen.getByRole('button', { name: /Start today/ })).toBeDisabled()
    expect(screen.getByText('Confirm your business and brand kit to start.')).toBeVisible()
  })

  it('removes testimonial creation and allowance controls from the workspace', async () => {
    render(<MarketingApp />)
    await screen.findByRole('heading', { name: 'Your daily marketing desk.' })
    await userEvent.click(screen.getByRole('button', { name: 'Brand library' }))
    expect(screen.getByRole('heading', { name: 'Campaign videos' })).toBeVisible()
    expect(screen.queryByText('Customer voices')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Settings' }))
    expect(screen.queryByText('Testimonial analyses remaining')).not.toBeInTheDocument()
    expect(screen.queryByText('Owner controls')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Grant allowance' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Your live allowance' })).toBeVisible()
  })

  it('starts a live campaign from a named campaign video without testimonial controls', async () => {
    const readyBusiness = { id: 'b'.repeat(32), version: 1, data: { name: 'Cafe', category: 'cafe' as const, city: 'LA', neighborhood: '', address: '', timezone: 'America/Los_Angeles', website: null, description: '', hours: '', products: [{ id: 'boba', name: 'Boba tea', description: '', price: '' }], offers: [], audience: '', confirmed: true } }
    const original = mockApi.getMockImplementation()!
    mockApi.mockImplementation(async (path, body) => {
      if (path === '/business') return readyBusiness
      if (path === '/brand') return { id: 'k', version: 1, data: { palette: ['#123456', '#ffffff'], voice: 'Warm', typography: 'serif', layout: '', image_direction: '', prohibited: [], reference_asset_ids: ['photo'], logo_asset_id: null, font_asset_id: null, uncertainty: [], confirmed: true } }
      if (path === '/assets') return [{ id: 'video', version: 1, data: { business_id: readyBusiness.id, filename: 'boba.mp4', title: 'Limited Edition Boba Tea', description: 'A fresh boba tea being poured.', role: 'video', product_id: 'boba', mime: 'video/mp4', size: 5, sha256: 'hash', width: null, height: null, rights_confirmed: true } }]
      if (path === '/usage') return { campaign_remaining: 5, brand_remaining: 1, live_enabled: true, active_job: null, global_campaign_remaining: 5, global_brand_remaining: 1 }
      if (path === '/workflows') return { id: '1'.repeat(32), kind: 'campaign', mode: 'live', state: 'queued', input: body, checkpoint: {}, counters: {}, created_at: 1, finished_at: null }
      return original(path, body)
    })
    render(<MarketingApp />)
    await screen.findByRole('heading', { name: 'Your daily marketing desk.' })
    await userEvent.click(screen.getByRole('button', { name: 'Live' }))
    expect(screen.queryByText('Testimonial quote')).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText(/Campaign video/), 'video')
    expect(screen.getByText(/video agent will choose its strongest frame/i)).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: /Start today/ }))
    await waitFor(() => expect(mockApi).toHaveBeenCalledWith('/workflows', expect.objectContaining({ video_asset_id: 'video', product_id: 'boba', creative_type: 'auto' })))
  })

  it('uses the restored return route after sign-in completes', async () => {
    vi.mocked(initializeSession).mockImplementationOnce(async () => {
      history.replaceState({}, '', '/#/brand')
      return true
    })
    render(<MarketingApp />)
    await screen.findByRole('heading', { name: 'Your brand, without the prompt.' })
    expect(screen.queryByRole('heading', { name: 'Your daily marketing desk.' })).not.toBeInTheDocument()
  })

  it('saves real typed business details with an expected version', async () => {
    render(<MarketingApp />)
    await screen.findByRole('heading', { name: 'Your daily marketing desk.' })
    await userEvent.click(screen.getByRole('button', { name: 'Business' }))
    await userEvent.type(screen.getByLabelText('Business name'), 'Morrow Coffee')
    await userEvent.type(screen.getByLabelText('City'), 'Los Angeles')
    await userEvent.type(screen.getByLabelText('Product 1 name'), 'Latte')
    await userEvent.click(screen.getByLabelText('I confirm these business details, products, and offers.'))
    await userEvent.click(screen.getByRole('button', { name: 'Save business details' }))
    await waitFor(() => expect(mockApi).toHaveBeenCalledWith('/business', expect.objectContaining({ version: 0, profile: expect.objectContaining({ name: 'Morrow Coffee', city: 'Los Angeles', confirmed: true }) }), 'PUT'))
    expect(business?.data.products[0].name).toBe('Latte')
  })
})
