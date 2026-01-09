import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import sessionManager from './sessionManager.js'

// Mock fetch globally
global.fetch = vi.fn()

// Mock window.location
const mockLocation = {
  href: ''
}
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true
})

describe('SessionManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocation.href = ''
    
    // Clear any existing timers
    sessionManager.cleanup()
  })

  afterEach(() => {
    sessionManager.cleanup()
  })

  describe('isAuthenticated', () => {
    it('returns true when user profile request succeeds', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ id: 1, email: 'test@example.com' })
      })

      const result = await sessionManager.isAuthenticated()

      expect(result).toBe(true)
      expect(fetch).toHaveBeenCalledWith('/api/user/profile', {
        method: 'GET',
        credentials: 'include'
      })
    })

    it('returns false when user profile request fails', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 401
      })

      const result = await sessionManager.isAuthenticated()

      expect(result).toBe(false)
    })

    it('returns false when network error occurs', async () => {
      fetch.mockRejectedValue(new Error('Network error'))

      const result = await sessionManager.isAuthenticated()

      expect(result).toBe(false)
    })
  })

  describe('refreshToken', () => {
    it('successfully refreshes token and schedules next refresh', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ access_token: 'new_token' })
      })

      const result = await sessionManager.refreshToken()

      expect(result).toBe(true)
      expect(fetch).toHaveBeenCalledWith('/auth/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })
    })

    it('handles refresh failure and redirects to login', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 401
      })

      const result = await sessionManager.refreshToken()

      expect(result).toBe(false)
      expect(mockLocation.href).toBe('/login')
    })

    it('handles network error during refresh', async () => {
      fetch.mockRejectedValue(new Error('Network error'))

      const result = await sessionManager.refreshToken()

      expect(result).toBe(false)
      expect(mockLocation.href).toBe('/login')
    })

    it('prevents multiple simultaneous refresh attempts', async () => {
      let resolveFirstCall
      const firstCallPromise = new Promise(resolve => {
        resolveFirstCall = resolve
      })

      fetch.mockImplementationOnce(() => firstCallPromise)

      // Start first refresh
      const firstRefresh = sessionManager.refreshToken()
      
      // Start second refresh immediately
      const secondRefresh = sessionManager.refreshToken()

      // Resolve the first call
      resolveFirstCall({
        ok: true,
        json: vi.fn().mockResolvedValue({ access_token: 'new_token' })
      })

      const [firstResult, secondResult] = await Promise.all([firstRefresh, secondRefresh])

      expect(firstResult).toBe(true)
      expect(secondResult).toBe(true)
      expect(fetch).toHaveBeenCalledTimes(1) // Only one actual fetch call
    })
  })

  describe('logout', () => {
    it('successfully logs out and redirects to login', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ message: 'Logged out successfully' })
      })

      const result = await sessionManager.logout()

      expect(result).toBe(true)
      expect(fetch).toHaveBeenCalledWith('/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })
      expect(mockLocation.href).toBe('/login')
    })

    it('redirects to login even when logout request fails', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 500
      })

      const result = await sessionManager.logout()

      expect(result).toBe(false)
      expect(mockLocation.href).toBe('/login')
    })

    it('redirects to login when network error occurs', async () => {
      fetch.mockRejectedValue(new Error('Network error'))

      const result = await sessionManager.logout()

      expect(result).toBe(false)
      expect(mockLocation.href).toBe('/login')
    })

    it('clears refresh timer on logout', async () => {
      // Set up a refresh timer
      sessionManager.scheduleTokenRefresh()
      expect(sessionManager.refreshTimer).not.toBeNull()

      fetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ message: 'Logged out successfully' })
      })

      await sessionManager.logout()

      expect(sessionManager.refreshTimer).toBeNull()
    })
  })

  describe('authenticatedFetch', () => {
    it('makes successful authenticated request', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({ data: 'test' })
      }
      fetch.mockResolvedValue(mockResponse)

      const response = await sessionManager.authenticatedFetch('/api/test')

      expect(response).toBe(mockResponse)
      expect(fetch).toHaveBeenCalledWith('/api/test', {
        credentials: 'include'
      })
    })

    it('retries request after successful token refresh on 401', async () => {
      const unauthorizedResponse = {
        ok: false,
        status: 401
      }
      const successResponse = {
        ok: true,
        status: 200,
        json: vi.fn().mockResolvedValue({ data: 'test' })
      }
      const refreshResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ access_token: 'new_token' })
      }

      fetch
        .mockResolvedValueOnce(unauthorizedResponse) // First request fails with 401
        .mockResolvedValueOnce(refreshResponse) // Token refresh succeeds
        .mockResolvedValueOnce(successResponse) // Retry succeeds

      const response = await sessionManager.authenticatedFetch('/api/test')

      expect(response).toBe(successResponse)
      expect(fetch).toHaveBeenCalledTimes(3)
      expect(fetch).toHaveBeenNthCalledWith(1, '/api/test', { credentials: 'include' })
      expect(fetch).toHaveBeenNthCalledWith(2, '/auth/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      })
      expect(fetch).toHaveBeenNthCalledWith(3, '/api/test', { credentials: 'include' })
    })

    it('returns 401 response when token refresh fails', async () => {
      const unauthorizedResponse = {
        ok: false,
        status: 401
      }
      const refreshFailResponse = {
        ok: false,
        status: 401
      }

      fetch
        .mockResolvedValueOnce(unauthorizedResponse) // First request fails with 401
        .mockResolvedValueOnce(refreshFailResponse) // Token refresh fails

      const response = await sessionManager.authenticatedFetch('/api/test')

      expect(response).toBe(unauthorizedResponse)
      expect(mockLocation.href).toBe('/login') // Should redirect to login
    })

    it('passes through options to fetch', async () => {
      const mockResponse = {
        ok: true,
        status: 200
      }
      fetch.mockResolvedValue(mockResponse)

      const options = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test: 'data' })
      }

      await sessionManager.authenticatedFetch('/api/test', options)

      expect(fetch).toHaveBeenCalledWith('/api/test', {
        ...options,
        credentials: 'include'
      })
    })
  })

  describe('initialize', () => {
    it('schedules token refresh when user is authenticated', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ id: 1, email: 'test@example.com' })
      })

      await sessionManager.initialize()

      expect(sessionManager.refreshTimer).not.toBeNull()
    })

    it('does not schedule token refresh when user is not authenticated', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 401
      })

      await sessionManager.initialize()

      expect(sessionManager.refreshTimer).toBeNull()
    })

    it('handles initialization errors gracefully', async () => {
      fetch.mockRejectedValue(new Error('Network error'))

      await expect(sessionManager.initialize()).resolves.not.toThrow()
      expect(sessionManager.refreshTimer).toBeNull()
    })
  })

  describe('scheduleTokenRefresh', () => {
    it('schedules refresh timer for 13 minutes', () => {
      vi.useFakeTimers()
      
      sessionManager.scheduleTokenRefresh()

      expect(sessionManager.refreshTimer).not.toBeNull()
      
      vi.useRealTimers()
    })

    it('clears existing timer before scheduling new one', () => {
      vi.useFakeTimers()
      
      // Schedule first timer
      sessionManager.scheduleTokenRefresh()
      const firstTimer = sessionManager.refreshTimer

      // Schedule second timer
      sessionManager.scheduleTokenRefresh()
      const secondTimer = sessionManager.refreshTimer

      expect(firstTimer).not.toBe(secondTimer)
      expect(sessionManager.refreshTimer).toBe(secondTimer)
      
      vi.useRealTimers()
    })
  })

  describe('cleanup', () => {
    it('clears refresh timer and resets state', () => {
      // Set up some state
      sessionManager.scheduleTokenRefresh()
      sessionManager.isRefreshing = true

      sessionManager.cleanup()

      expect(sessionManager.refreshTimer).toBeNull()
      expect(sessionManager.isRefreshing).toBe(false)
      expect(sessionManager.refreshPromise).toBeNull()
    })
  })

  describe('handleAuthenticationFailure', () => {
    it('clears refresh timer and redirects to login', () => {
      sessionManager.scheduleTokenRefresh()
      expect(sessionManager.refreshTimer).not.toBeNull()

      sessionManager.handleAuthenticationFailure()

      expect(sessionManager.refreshTimer).toBeNull()
      expect(mockLocation.href).toBe('/login')
    })
  })
})