import { useEffect, useState } from 'react'
import './OAuthCallback.css'

export default function OAuthCallback() {
  const [status, setStatus] = useState('processing') // 'processing', 'success', 'error'
  const [message, setMessage] = useState('Processing authentication...')

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        // Extract URL parameters
        const urlParams = new URLSearchParams(window.location.search)
        const code = urlParams.get('code')
        const state = urlParams.get('state')
        const error = urlParams.get('error')
        const errorDescription = urlParams.get('error_description')

        // Check for OAuth errors
        if (error) {
          setStatus('error')
          setMessage(errorDescription || `OAuth error: ${error}`)
          return
        }

        // Validate required parameters
        if (!code || !state) {
          setStatus('error')
          setMessage('Missing required OAuth parameters')
          return
        }

        // Verify state parameter to prevent CSRF attacks
        const storedState = sessionStorage.getItem('oauth_state')
        if (!storedState || storedState !== state) {
          setStatus('error')
          setMessage('Invalid state parameter. Please try logging in again.')
          return
        }

        // Clear stored state
        sessionStorage.removeItem('oauth_state')

        // Determine provider from current path
        const path = window.location.pathname
        let provider
        if (path.includes('/google/')) {
          provider = 'google'
        } else if (path.includes('/github/')) {
          provider = 'github'
        } else {
          setStatus('error')
          setMessage('Unknown OAuth provider')
          return
        }

        const response = await fetch(`/auth/${provider}/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`, {
          method: 'GET',
          credentials: 'include' // Include cookies for session management
        })

        const data = await response.json()

        if (response.ok) {
          // Authentication successful
          setStatus('success')
          setMessage('Authentication successful! Redirecting to dashboard...')
          
          // Store tokens in secure cookies (handled by backend)
          // Redirect to dashboard after a short delay
          setTimeout(() => {
            window.location.href = '/dashboard'
          }, 2000)
        } else {
          // Authentication failed
          setStatus('error')
          setMessage(data.message || 'Authentication failed. Please try again.')
        }
      } catch (error) {
        console.error('OAuth callback error:', error)
        setStatus('error')
        setMessage('Network error occurred. Please try again.')
      }
    }

    handleOAuthCallback()
  }, [])

  const handleRetry = () => {
    window.location.href = '/login'
  }

  return (
    <div className="oauth-callback-page">
      <div className="oauth-callback-container">
        <div className="oauth-callback-content">
          {status === 'processing' && (
            <>
              <div className="loading-spinner large"></div>
              <h2>Authenticating...</h2>
              <p>{message}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="success-icon">✓</div>
              <h2>Success!</h2>
              <p>{message}</p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="error-icon">✗</div>
              <h2>Authentication Failed</h2>
              <p>{message}</p>
              <button 
                className="retry-button"
                onClick={handleRetry}
              >
                Return to Login
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}