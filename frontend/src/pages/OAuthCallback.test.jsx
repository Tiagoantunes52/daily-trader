import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import OAuthCallback from './OAuthCallback'

// Mock fetch globally
global.fetch = vi.fn()

// Mock sessionStorage
const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage
})

// Mock window.location
const mockLocation = {
  pathname: '/auth/google/callback',
  search: '?code=test_code&state=test_state',
  href: ''
}
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true
})

describe('OAuthCallback', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLocation.pathname = '/auth/google/callback'
    mockLocation.search = '?code=test_code&state=test_state'
    mockLocation.href = ''
    mockSessionStorage.getItem.mockReturnValue('test_state')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Successful OAuth Callback', () => {
    it('handles successful Google OAuth callback', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          access_token: 'test_access_token',
          refresh_token: 'test_refresh_token'
        })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/auth/google/callback?code=test_code&state=test_state',
          {
            method: 'GET',
            credentials: 'include'
          }
        )
      })
      
      await waitFor(() => {
        expect(screen.getByText('Success!')).toBeInTheDocument()
        expect(screen.getByText('Authentication successful! Redirecting to dashboard...')).toBeInTheDocument()
      })
      
      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('oauth_state')
    })

    it('handles successful GitHub OAuth callback', async () => {
      mockLocation.pathname = '/auth/github/callback'
      
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          access_token: 'test_access_token',
          refresh_token: 'test_refresh_token'
        })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/auth/github/callback?code=test_code&state=test_state',
          {
            method: 'GET',
            credentials: 'include'
          }
        )
      })
      
      await waitFor(() => {
        expect(screen.getByText('Success!')).toBeInTheDocument()
      })
      
      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('oauth_state')
    })
  })

  describe('OAuth Error Handling', () => {
    it('handles OAuth error from provider', async () => {
      mockLocation.search = '?error=access_denied&error_description=User%20denied%20access'
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(screen.getByText('Authentication Failed')).toBeInTheDocument()
        expect(screen.getByText('User denied access')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: 'Return to Login' })).toBeInTheDocument()
      })
      
      expect(fetch).not.toHaveBeenCalled()
    })

    it('handles missing authorization code', async () => {
      mockLocation.search = '?state=test_state'
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(screen.getByText('Authentication Failed')).toBeInTheDocument()
        expect(screen.getByText('Missing required OAuth parameters')).toBeInTheDocument()
      })
      
      expect(fetch).not.toHaveBeenCalled()
    })

    it('handles invalid state parameter (CSRF protection)', async () => {
      mockSessionStorage.getItem.mockReturnValue('different_state')
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(screen.getByText('Authentication Failed')).toBeInTheDocument()
        expect(screen.getByText('Invalid state parameter. Please try logging in again.')).toBeInTheDocument()
      })
      
      expect(fetch).not.toHaveBeenCalled()
    })

    it('handles backend authentication failure', async () => {
      const mockResponse = {
        ok: false,
        json: vi.fn().mockResolvedValue({
          message: 'OAuth authentication failed'
        })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(screen.getByText('Authentication Failed')).toBeInTheDocument()
        expect(screen.getByText('OAuth authentication failed')).toBeInTheDocument()
      })
      
      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('oauth_state')
    })

    it('handles network error', async () => {
      fetch.mockRejectedValue(new Error('Network error'))
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(screen.getByText('Authentication Failed')).toBeInTheDocument()
        expect(screen.getByText('Network error occurred. Please try again.')).toBeInTheDocument()
      })
      
      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('oauth_state')
    })
  })

  describe('Token Storage', () => {
    it('relies on backend to set secure cookies', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          access_token: 'test_access_token',
          refresh_token: 'test_refresh_token'
        })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/auth/google/callback?code=test_code&state=test_state',
          {
            method: 'GET',
            credentials: 'include'
          }
        )
      })
      
      // Verify that tokens are not stored in localStorage or sessionStorage
      expect(mockSessionStorage.setItem).not.toHaveBeenCalledWith('access_token', expect.anything())
      expect(mockSessionStorage.setItem).not.toHaveBeenCalledWith('refresh_token', expect.anything())
      
      // Only oauth_state should be removed
      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith('oauth_state')
      expect(mockSessionStorage.removeItem).toHaveBeenCalledTimes(1)
    })
  })

  describe('User Interaction', () => {
    it('redirects to login when retry button is clicked', async () => {
      mockLocation.search = '?error=access_denied'
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Return to Login' })).toBeInTheDocument()
      })
      
      const retryButton = screen.getByRole('button', { name: 'Return to Login' })
      fireEvent.click(retryButton)
      
      expect(mockLocation.href).toBe('/login')
    })
  })

  describe('Provider Detection', () => {
    it('correctly identifies Google provider from URL path', async () => {
      mockLocation.pathname = '/auth/google/callback'
      
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          access_token: 'test_access_token',
          refresh_token: 'test_refresh_token'
        })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/auth/google/callback?code=test_code&state=test_state',
          expect.any(Object)
        )
      })
    })

    it('correctly identifies GitHub provider from URL path', async () => {
      mockLocation.pathname = '/auth/github/callback'
      
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({
          access_token: 'test_access_token',
          refresh_token: 'test_refresh_token'
        })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<OAuthCallback />)
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/auth/github/callback?code=test_code&state=test_state',
          expect.any(Object)
        )
      })
    })
  })
})