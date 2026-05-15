import { useEffect, useState } from 'react'
import './OAuthCallback.css'

export default function OAuthCallback() {
  const [status, setStatus] = useState('processing') // 'processing', 'success', 'error'
  const [message, setMessage] = useState('Processing authentication...')

  useEffect(() => {
    const controller = new AbortController()

    const handleOAuthCallback = async () => {
      try {
        const urlParams = new URLSearchParams(window.location.search)
        const code = urlParams.get('code')
        const state = urlParams.get('state')
        const error = urlParams.get('error')
        const errorDescription = urlParams.get('error_description')

        if (error) {
          setStatus('error')
          setMessage(errorDescription || `OAuth error: ${error}`)
          return
        }

        if (!code || !state) {
          setStatus('error')
          setMessage('Missing required OAuth parameters')
          return
        }

        // Verify state — do NOT remove it yet; removal happens only on success.
        // Moving removal here causes React StrictMode's double-invoke to see a missing
        // state on the second mount and flash an error before the fetch resolves.
        const storedState = sessionStorage.getItem('oauth_state')
        if (!storedState || storedState !== state) {
          setStatus('error')
          setMessage('Invalid state parameter. Please try logging in again.')
          return
        }

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

        const response = await fetch(
          `/auth/${provider}/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
          { method: 'GET', credentials: 'include', signal: controller.signal }
        )

        // Ignore result if this effect instance was cleaned up (StrictMode unmount)
        if (controller.signal.aborted) return

        const data = await response.json()

        if (response.ok) {
          // Only remove state after confirmed success — prevents the second StrictMode
          // mount from seeing a missing state and flashing the error screen.
          sessionStorage.removeItem('oauth_state')
          setStatus('success')
          setMessage('Authentication successful! Redirecting to dashboard...')

          const { default: sessionManager } = await import('../utils/sessionManager.js')
          sessionManager.storeTokens(data.access_token, data.refresh_token)
          await sessionManager.initialize()

          setTimeout(() => {
            window.location.href = '/'
          }, 2000)
        } else {
          setStatus('error')
          setMessage(data.message || 'Authentication failed. Please try again.')
        }
      } catch (error) {
        if (error.name === 'AbortError') return
        setStatus('error')
        setMessage('Network error occurred. Please try again.')
      }
    }

    handleOAuthCallback()

    return () => {
      controller.abort()
    }
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