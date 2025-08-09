// Jest setup file for voice flow testing
import '@testing-library/jest-dom'
import { TextEncoder, TextDecoder } from 'util'

// Polyfill for TextEncoder/TextDecoder in test environment
global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      push: jest.fn(),
      replace: jest.fn(),
      prefetch: jest.fn(),
      back: jest.fn(),
      forward: jest.fn(),
      refresh: jest.fn(),
    }
  },
  useSearchParams() {
    return new URLSearchParams()
  },
  usePathname() {
    return '/reception'
  },
}))

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
  unobserve: jest.fn(),
}))

// Mock ResizeObserver
global.ResizeObserver = jest.fn(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
  unobserve: jest.fn(),
}))

// Mock fetch API for tests
global.fetch = jest.fn(() => 
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ status: 'ok' })
  })
)

// Suppress console warnings in tests
const originalWarn = console.warn
const originalError = console.error

beforeAll(() => {
  console.warn = (...args) => {
    // Suppress specific warnings that are expected in tests
    if (
      typeof args[0] === 'string' && 
      (
        args[0].includes('Warning: ReactDOM.render is deprecated') ||
        args[0].includes('Warning: An invalid form control') ||
        args[0].includes('Warning: validateDOMNesting')
      )
    ) {
      return
    }
    originalWarn.call(console, ...args)
  }

  console.error = (...args) => {
    // Suppress specific errors that are expected in tests
    if (
      typeof args[0] === 'string' && 
      (
        args[0].includes('Error: Uncaught [TypeError: Cannot read properties of null') ||
        args[0].includes('The above error occurred in the <') ||
        args[0].includes('React will try to recreate this component tree') ||
        args[0].includes('ReactDOMTestUtils.act is deprecated') ||
        args[0].includes('Warning: An update to') ||
        args[0].includes('inside a test was not wrapped in act') ||
        args[0].includes('Warning: `ReactDOMTestUtils.act` is deprecated') ||
        args[0].includes('WebSocket connection failed') ||
        args[0].includes('WebSocket disconnected') ||
        args[0].includes('Attempting reconnection') ||
        args[0].includes('Microphone permission denied')
      )
    ) {
      return
    }
    originalError.call(console, ...args)
  }
})

afterAll(() => {
  console.warn = originalWarn
  console.error = originalError
})