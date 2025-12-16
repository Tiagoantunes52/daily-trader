import React, { useState } from 'react'
import CurrentTips from './pages/CurrentTips'
import TipHistory from './pages/TipHistory'
import './App.css'

export default function App() {
  const [currentPage, setCurrentPage] = useState('current')

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
          </ul>
        </div>
      </nav>

      <main className="main-content">
        {currentPage === 'current' && <CurrentTips />}
        {currentPage === 'history' && <TipHistory />}
      </main>

      <footer className="footer">
        <p>&copy; 2024 Daily Market Tips. All rights reserved.</p>
      </footer>
    </div>
  )
}
