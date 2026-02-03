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
    this.accessToken = null
    this.refreshTokenValue = null
  }

  /**
   * Initialize session management
   * Sets up automatic token refresh if user is authenticated
   * @returns {Promise<boolean>} True if authenticated, false otherwise
   */
  async initialize() {
    try {
      // Load tokens from localStorage
      this.loadTokens()

      // Check if user has valid session
      const isAuthenticated = await this.isAuthenticated()
      if (isAuthenticated) {
        this.scheduleTokenRefresh()
      }
      return isAuthenticated
    } catch (error) {
      console.error('Failed to initialize session manager:', error)
      return false
    }
  }

  /**
   * Load tokens from localStorage
   */
  loadTokens() {
    try {
      this.accessToken = localStorage.getItem('access_token')
      this.refreshTokenValue = localStorage.getItem('refresh_token')
    } catch (error) {
      console.error('Failed to load tokens from localStorage:', error)
      this.accessToken = null
      this.refreshTokenValue = null
    }
  }

  /**
   * Store tokens in localStorage
   * @param {string} accessToken - JWT access token
   * @param {string} refreshToken - JWT refresh token
   */
  storeTokens(accessToken, refreshToken) {
    try {
      this.accessToken = accessToken
      this.refreshTokenValue = refreshToken
      localStorage.setItem('access_token', accessToken)
      localStorage.setItem('refresh_token', refreshToken)
    } catch (error) {
      console.error('Failed to store tokens in localStorage:', error)
    }
  }

  /**
   * Clear tokens from memory and localStorage
   */
  clearTokens() {
    this.accessToken = null
    this.refreshTokenValue = null
    try {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    } catch (error) {
      console.error('Failed to clear tokens from localStorage:', error)
    }
  }

  /**
   * Check if user is currently authenticated
   * @param {boolean} skipProfileCheck - Skip profile API call (useful during OAuth flows)
   * @returns {Promise<boolean>} True if authenticated, false otherwise
   */
  async isAuthenticated(skipProfileCheck = false) {
    // During OAuth flows, we might want to skip the profile check
    // to avoid race conditions
    if (skipProfileCheck) {
      return false
    }

    // Check if we have an access token
    if (!this.accessToken) {
      return false
    }

    try {
      const response = await fetch('/api/user/profile', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.status === 401) {
        // Token is invalid or expired, clear it
        this.clearTokens()
        return false
      }

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
      if (!this.refreshTokenValue) {
        console.warn('No refresh token available')
        this.handleAuthenticationFailure()
        return false
      }

      const response = await fetch('/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          refresh_token: this.refreshTokenValue
        })
      })

      if (response.ok) {
        const tokenData = await response.json()
        // Store new tokens
        this.storeTokens(tokenData.access_token, tokenData.refresh_token)
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

    // Clear tokens
    this.clearTokens()

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

      // Call logout endpoint if we have an access token
      if (this.accessToken) {
        await fetch('/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.accessToken}`,
            'Content-Type': 'application/json'
          }
        })
      }

      // Clear tokens
      this.clearTokens()

      // Redirect to login
      window.location.href = '/login'

      return true
    } catch (error) {
      console.error('Logout error:', error)
      // Still clear tokens and redirect on error
      this.clearTokens()
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
    // Ensure we have an access token
    if (!this.accessToken) {
      throw new Error('No access token available')
    }

    // Add Authorization header
    const fetchOptions = {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${this.accessToken}`,
        'Content-Type': 'application/json'
      }
    }

    try {
      let response = await fetch(url, fetchOptions)

      // If request fails with 401, try to refresh token and retry
      if (response.status === 401) {
        const refreshSuccess = await this.refreshToken()

        if (refreshSuccess) {
          // Update Authorization header with new token
          fetchOptions.headers['Authorization'] = `Bearer ${this.accessToken}`
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