import React, { useState, useEffect } from 'react'
import CurrentTips from './pages/CurrentTips'
import TipHistory from './pages/TipHistory'
import UserSettings from './pages/UserSettings'
import LoginPage from './pages/LoginPage'
import OAuthCallback from './pages/OAuthCallback'
import sessionManager from './utils/sessionManager.js'
import { logout } from './api/client.js'
import './App.css'

export default function App() {
  const [currentPage, setCurrentPage] = useState('current')
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    // Initialize session manager and check authentication
    const initializeApp = async () => {
      try {
        await sessionManager.initialize()
        const authenticated = await sessionManager.isAuthenticated()
        setIsAuthenticated(authenticated)
      } catch (error) {
        console.error('App initialization error:', error)
        setIsAuthenticated(false)
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

  // Handle OAuth callback routes
  const path = window.location.pathname
  if (path.includes('/auth/google/callback') || path.includes('/auth/github/callback')) {
    return <OAuthCallback />
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
