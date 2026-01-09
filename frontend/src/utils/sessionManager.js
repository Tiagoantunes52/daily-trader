/**
 * Session Management Utilities
 * 
 * Handles JWT token management, automatic refresh, and logout functionality
 * for the Daily Market Tips application.
 * 
 * Requirements: 5.1, 5.3, 5.5
 */

class SessionManager {
  constructor() {
    this.refreshTimer = null
    this.isRefreshing = false
    this.refreshPromise = null
  }

  /**
   * Initialize session management
   * Sets up automatic token refresh if user is authenticated
   */
  async initialize() {
    try {
      // Check if user has valid session
      const isAuthenticated = await this.isAuthenticated()
      if (isAuthenticated) {
        this.scheduleTokenRefresh()
      }
    } catch (error) {
      console.error('Failed to initialize session manager:', error)
    }
  }

  /**
   * Check if user is currently authenticated
   * @returns {Promise<boolean>} True if authenticated, false otherwise
   */
  async isAuthenticated() {
    try {
      const response = await fetch('/api/user/profile', {
        method: 'GET',
        credentials: 'include'
      })
      return response.ok
    } catch (error) {
      console.error('Authentication check failed:', error)
      return false
    }
  }

  /**
   * Refresh the access token using the refresh token
   * @returns {Promise<boolean>} True if refresh successful, false otherwise
   */
  async refreshToken() {
    // Prevent multiple simultaneous refresh attempts
    if (this.isRefreshing) {
      return this.refreshPromise
    }

    this.isRefreshing = true
    this.refreshPromise = this._performTokenRefresh()

    try {
      const result = await this.refreshPromise
      return result
    } finally {
      this.isRefreshing = false
      this.refreshPromise = null
    }
  }

  /**
   * Internal method to perform the actual token refresh
   * @private
   */
  async _performTokenRefresh() {
    try {
      const response = await fetch('/auth/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        // Token refreshed successfully, schedule next refresh
        this.scheduleTokenRefresh()
        return true
      } else {
        // Refresh failed, user needs to log in again
        console.warn('Token refresh failed, redirecting to login')
        this.handleAuthenticationFailure()
        return false
      }
    } catch (error) {
      console.error('Token refresh error:', error)
      this.handleAuthenticationFailure()
      return false
    }
  }

  /**
   * Schedule automatic token refresh
   * Refreshes token 2 minutes before expiration (13 minutes for 15-minute tokens)
   */
  scheduleTokenRefresh() {
    // Clear existing timer
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer)
    }

    // Schedule refresh for 13 minutes (780 seconds)
    // This gives 2 minutes buffer before the 15-minute token expires
    const refreshInterval = 13 * 60 * 1000 // 13 minutes in milliseconds

    this.refreshTimer = setTimeout(async () => {
      await this.refreshToken()
    }, refreshInterval)
  }

  /**
   * Handle authentication failure
   * Clears timers and redirects to login page
   */
  handleAuthenticationFailure() {
    // Clear refresh timer
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer)
      this.refreshTimer = null
    }

    // Redirect to login page
    window.location.href = '/login'
  }

  /**
   * Logout the current user
   * Clears session and redirects to login page
   * @returns {Promise<boolean>} True if logout successful
   */
  async logout() {
    try {
      // Clear refresh timer
      if (this.refreshTimer) {
        clearTimeout(this.refreshTimer)
        this.refreshTimer = null
      }

      // Call logout endpoint
      const response = await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      // Redirect to login regardless of response
      // (backend should clear cookies even if request fails)
      window.location.href = '/login'
      
      return response.ok
    } catch (error) {
      console.error('Logout error:', error)
      // Still redirect to login on error
      window.location.href = '/login'
      return false
    }
  }

  /**
   * Make an authenticated API request with automatic token refresh
   * @param {string} url - The API endpoint URL
   * @param {Object} options - Fetch options
   * @returns {Promise<Response>} The fetch response
   */
  async authenticatedFetch(url, options = {}) {
    // Ensure credentials are included
    const fetchOptions = {
      ...options,
      credentials: 'include'
    }

    try {
      let response = await fetch(url, fetchOptions)

      // If request fails with 401, try to refresh token and retry
      if (response.status === 401) {
        const refreshSuccess = await this.refreshToken()
        
        if (refreshSuccess) {
          // Retry the original request
          response = await fetch(url, fetchOptions)
        } else {
          // Refresh failed, authentication failure will be handled
          return response
        }
      }

      return response
    } catch (error) {
      console.error('Authenticated fetch error:', error)
      throw error
    }
  }

  /**
   * Clean up session manager
   * Clears timers and resets state
   */
  cleanup() {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer)
      this.refreshTimer = null
    }
    this.isRefreshing = false
    this.refreshPromise = null
  }
}

// Create singleton instance
const sessionManager = new SessionManager()

export default sessionManager