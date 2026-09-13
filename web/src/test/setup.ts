import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

beforeEach(() => {
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true, value: vi.fn(function (this: HTMLDialogElement) { this.open = true }),
  })
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
