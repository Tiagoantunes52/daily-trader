import { useEffect, useState } from 'react'
import { logout } from './api/client.js'
import './App.css'
import CurrentTips from './pages/CurrentTips'
import LoginPage from './pages/LoginPage'
import OAuthCallback from './pages/OAuthCallback'
import TipHistory from './pages/TipHistory'
import UserSettings from './pages/UserSettings'
import sessionManager from './utils/sessionManager.js'

export default function App() {
  const [currentPage, setCurrentPage] = useState('current')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Handle OAuth callback routes FIRST, before any other logic
  const path = window.location.pathname
  const isOAuthCallback = path.includes('/auth/google/callback') || path.includes('/auth/github/callback')

  if (isOAuthCallback) {
    return <OAuthCallback />
  }

  useEffect(() => {
    // Initialize session manager and check authentication
    const initializeApp = async () => {
      try {
        // Initialize session manager and get authentication status
        // This avoids making two separate API calls
        const authenticated = await sessionManager.initialize()
        setIsAuthenticated(authenticated)
      } catch (error) {
        console.error('App initialization error:', error)
        setIsAuthenticated(false)
      } finally {
        setIsLoading(false)
      }
    }

    initializeApp()

    // Cleanup session manager on unmount
    return () => {
      sessionManager.cleanup()
    }
  }, [])

  const handleLogout = async () => {
    try {
      await logout()
      setIsAuthenticated(false)
    } catch (error) {
      console.error('Logout error:', error)
      // Still redirect to login even if logout request fails
      window.location.href = '/login'
    }
  }

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner large"></div>
        <p>Loading...</p>
      </div>
    )
  }

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <LoginPage />
  }

  return (
    <div className="app">
      <nav className="navbar">
        <div className="navbar-container">
          <div className="navbar-brand">
            <h1>📈 Daily Market Tips</h1>
          </div>
          <ul className="navbar-menu">
            <li>
              <button
                className={`nav-link ${currentPage === 'current' ? 'active' : ''}`}
                onClick={() => setCurrentPage('current')}
              >
                Current Tips
              </button>
            </li>
            <li>
              <button
                className={`nav-link ${currentPage === 'history' ? 'active' : ''}`}
                onClick={() => setCurrentPage('history')}
              >
                History
              </button>
            </li>
            <li>
              <button
                className={`nav-link ${currentPage === 'settings' ? 'active' : ''}`}
                onClick={() => setCurrentPage('settings')}
              >
                Settings
              </button>
            </li>
            <li>
              <button
                className="nav-link logout-button"
                onClick={handleLogout}
              >
                Logout
              </button>
            </li>
          </ul>
        </div>
      </nav>

      <main className="main-content">
        {currentPage === 'current' && <CurrentTips />}
        {currentPage === 'history' && <TipHistory />}
        {currentPage === 'settings' && <UserSettings />}
      </main>

      <footer className="footer">
        <p>&copy; 2024 Daily Market Tips. All rights reserved.</p>
      </footer>
    </div>
  )
}
