import { useEffect, useState } from 'react'
import './OAuthCallback.css'

export default function OAuthCallback() {
  const [status, setStatus] = useState('processing') // 'processing', 'success', 'error'
  const [message, setMessage] = useState('Processing authentication...')

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        console.log('OAuth callback started')
        console.log('Current URL:', window.location.href)

        // Extract URL parameters
        const urlParams = new URLSearchParams(window.location.search)
        const code = urlParams.get('code')
        const state = urlParams.get('state')
        const error = urlParams.get('error')
        const errorDescription = urlParams.get('error_description')

        console.log('URL params:', { code: code?.substring(0, 20) + '...', state, error, errorDescription })

        // Check for OAuth errors
        if (error) {
          console.error('OAuth error:', error, errorDescription)
          setStatus('error')
          setMessage(errorDescription || `OAuth error: ${error}`)
          return
        }

        // Validate required parameters
        if (!code || !state) {
          console.error('Missing required parameters:', { code: !!code, state: !!state })
          setStatus('error')
          setMessage('Missing required OAuth parameters')
          return
        }

        // Verify state parameter to prevent CSRF attacks
        const storedState = sessionStorage.getItem('oauth_state')
        console.log('State verification:', { received: state, stored: storedState })

        if (!storedState || storedState !== state) {
          console.error('State mismatch - possible CSRF attack')
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
          console.error('Unknown provider from path:', path)
          setStatus('error')
          setMessage('Unknown OAuth provider')
          return
        }

        console.log('Making callback request to:', `/auth/${provider}/callback`)
        const response = await fetch(`/auth/${provider}/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`, {
          method: 'GET',
          credentials: 'include'
        })

        console.log('Callback response status:', response.status)
        const data = await response.json()
        console.log('Callback response data:', data)

        if (response.ok) {
          // Authentication successful
          console.log('Authentication successful, storing tokens')
          setStatus('success')
          setMessage('Authentication successful! Redirecting to dashboard...')

          // Store tokens in session manager
          const { default: sessionManager } = await import('../utils/sessionManager.js')
          sessionManager.storeTokens(data.access_token, data.refresh_token)
          console.log('Tokens stored, initializing session manager')
          await sessionManager.initialize()

          // Redirect to dashboard after a short delay
          console.log('Redirecting to dashboard in 2 seconds')
          setTimeout(() => {
            window.location.href = '/'
          }, 2000)
        } else {
          // Authentication failed
          console.error('Authentication failed:', data)
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