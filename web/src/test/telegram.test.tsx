import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { TelegramPanel } from '../marketing/TelegramPanel'
import { api } from '../marketing/client'

vi.mock('../marketing/client', () => ({ api: vi.fn() }))
const mock = vi.mocked(api)
const connection = { channel: 'telegram', chat_id: 42, chat_title: 'Sam', linked_at: '2026-09-13T12:00:00Z', enabled: true }
beforeEach(() => mock.mockReset())
afterEach(() => vi.useRealTimers())

it('shows not configured without connection actions', async () => {
  mock.mockImplementation(async path => path === '/notifications/config' ? { configured: false } : null)
  render(<TelegramPanel />)
  expect(await screen.findByText('Not configured')).toBeVisible()
  expect(screen.queryByRole('button', { name: 'Connect Telegram' })).not.toBeInTheDocument()
})

it('connects through a deep link and polls until connected', async () => {
  let connected = false
  mock.mockImplementation(async (path) => {
    if (path === '/notifications/config') return { configured: true }
    if (path === '/notifications/telegram/link') return { code: 'Ab123456', deep_link: 'https://t.me/bot?start=Ab123456' }
    return connected ? connection : null
  })
  const view = render(<TelegramPanel />)
  expect(await screen.findByText('Not connected')).toBeVisible()
  await userEvent.click(screen.getByRole('button', { name: 'Connect Telegram' }))
  expect(screen.getByRole('link', { name: 'Open Telegram' })).toHaveAttribute('href', 'https://t.me/bot?start=Ab123456')
  expect(screen.getByText('/start Ab123456')).toBeVisible()
  connected = true
  await waitFor(() => expect(screen.getByText('Connected as Sam')).toBeVisible(), { timeout: 4500 })
  expect(screen.queryByText('/start Ab123456')).not.toBeInTheDocument()
  view.unmount()
})

it('toggles notifications and disconnects through the API', async () => {
  mock.mockImplementation(async (path, body, method) => {
    if (path === '/notifications/config') return { configured: true }
    if (method === 'DELETE') return { unlinked: true }
    return body ? { ...connection, enabled: false } : connection
  })
  render(<TelegramPanel />)
  expect(await screen.findByText('Connected as Sam')).toBeVisible()
  await userEvent.click(screen.getByLabelText('Enable Telegram approvals'))
  expect(mock).toHaveBeenCalledWith('/notifications', { enabled: false }, 'PUT')
  expect(screen.getByLabelText('Enable Telegram approvals')).not.toBeChecked()
  await userEvent.click(screen.getByRole('button', { name: 'Disconnect Telegram' }))
  expect(await screen.findByText('Not connected')).toBeVisible()
  expect(mock).toHaveBeenCalledWith('/notifications/telegram', {}, 'DELETE')
})

it('cleans pending polling up on unmount', async () => {
  vi.useFakeTimers()
  mock.mockImplementation(async path => path === '/notifications/config' ? { configured: true } : path === '/notifications/telegram/link' ? { code: 'Ab123456', deep_link: 'https://t.me/bot?start=Ab123456' } : null)
  const view = render(<TelegramPanel />)
  await act(async () => { await Promise.resolve() })
  await act(async () => { screen.getByRole('button', { name: 'Connect Telegram' }).click() })
  view.unmount()
  const count = mock.mock.calls.length
  await act(async () => { await vi.advanceTimersByTimeAsync(9000) })
  expect(mock.mock.calls).toHaveLength(count)
})
