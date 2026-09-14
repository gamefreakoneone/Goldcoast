import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { AssetLibrary } from '../marketing/AssetLibrary'
import { authenticatedFetch } from '../marketing/client'

vi.mock('../marketing/client', () => ({ authenticatedFetch: vi.fn(), api: vi.fn() }))
beforeEach(() => { vi.clearAllMocks(); URL.createObjectURL = vi.fn(() => 'blob:preview'); URL.revokeObjectURL = vi.fn() })

it('stages a drop before permission or business setup, with explicit classification', () => {
  const { container } = render(<AssetLibrary assets={[]} business={null} onSaved={vi.fn()} referenceIds={[]} onReferences={vi.fn()}/>)
  fireEvent.drop(container.querySelector('.upload-zone')!, { dataTransfer: { files: [new File(['x'], 'matcha.png', { type: 'image/png' })] } })
  expect(screen.getByRole('img', { name: 'matcha.png' })).toBeInTheDocument()
  expect(screen.getByLabelText('Category')).toHaveValue('product')
  expect(screen.getByLabelText(/Product/)).toHaveValue('')
  expect(screen.getByRole('button', { name: /Upload pending/ })).toBeDisabled()
  expect(authenticatedFetch).not.toHaveBeenCalled()
})

it('retries failed files without uploading successful files again', async () => {
  const business = { id: 'b', version: 1, data: { name: 'Cafe', category: 'cafe' as const, city: 'LA', neighborhood: '', address: '', timezone: 'America/Los_Angeles', website: null, description: '', hours: '', products: [], offers: [], audience: '', confirmed: true } }
  vi.mocked(authenticatedFetch).mockResolvedValueOnce(new Response()).mockRejectedValueOnce(new Error('Try again')).mockResolvedValueOnce(new Response())
  const { container } = render(<AssetLibrary assets={[]} business={business} onSaved={vi.fn()} referenceIds={[]} onReferences={vi.fn()}/>)
  fireEvent.drop(container.querySelector('.upload-zone')!, { dataTransfer: { files: ['a', 'b'].map(n => new File(['x'], `${n}.png`, { type: 'image/png' })) } })
  fireEvent.click(screen.getByLabelText('I have permission to use this material.'))
  fireEvent.click(screen.getByRole('button', { name: /Upload pending/ }))
  await screen.findByText('Try again')
  fireEvent.click(screen.getByRole('button', { name: /Upload pending/ }))
  await waitFor(() => expect(authenticatedFetch).toHaveBeenCalledTimes(3))
})

it('requires a name and description for campaign videos and uploads both', async () => {
  const product = { id: 'boba', name: 'Boba tea', description: '', price: '' }
  const business = { id: 'b', version: 1, data: { name: 'Cafe', category: 'cafe' as const, city: 'LA', neighborhood: '', address: '', timezone: 'America/Los_Angeles', website: null, description: '', hours: '', products: [product], offers: [], audience: '', confirmed: true } }
  vi.mocked(authenticatedFetch).mockResolvedValue(new Response())
  const { container } = render(<AssetLibrary assets={[]} business={business} onSaved={vi.fn()} referenceIds={[]} onReferences={vi.fn()}/>)
  fireEvent.drop(container.querySelector('.upload-zone')!, { dataTransfer: { files: [new File(['video'], 'boba.mp4', { type: 'video/mp4' })] } })
  expect(screen.getByLabelText('Category')).toHaveValue('video')
  fireEvent.click(screen.getByLabelText('I have permission to use this material.'))
  expect(screen.getByRole('button', { name: /Upload pending/ })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Video name'), { target: { value: 'Limited Edition Boba Tea' } })
  fireEvent.change(screen.getByLabelText('What does this video show?'), { target: { value: 'A fresh purple boba tea being poured.' } })
  fireEvent.change(screen.getByLabelText(/Product/), { target: { value: 'boba' } })
  fireEvent.click(screen.getByRole('button', { name: /Upload pending/ }))
  await waitFor(() => expect(authenticatedFetch).toHaveBeenCalledTimes(1))
  const body = vi.mocked(authenticatedFetch).mock.calls[0][1]?.body as FormData
  expect(body.get('role')).toBe('video')
  expect(body.get('title')).toBe('Limited Edition Boba Tea')
  expect(body.get('description')).toBe('A fresh purple boba tea being poured.')
  expect(body.get('product_id')).toBe('boba')
})
