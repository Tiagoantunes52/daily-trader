import React, { useState, useEffect } from 'react'
import { updateUser, getUserByEmail, getUserProfile } from '../api/client'
import './UserSettings.css'

export default function UserSettings() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [formData, setFormData] = useState({
    morning_time: '',
    evening_time: '',
    asset_preferences: []
  })

  // Auto-load the current user's preferences on mount
  useEffect(() => {
    const loadCurrentUser = async () => {
      try {
        const authUser = await getUserProfile()
        const userData = await getUserByEmail(authUser.email)
        setUser(userData)
        setFormData({
          morning_time: userData.morning_time || '',
          evening_time: userData.evening_time || '',
          asset_preferences: userData.asset_preferences || []
        })
      } catch {
        setError('Failed to load your profile. Please try again.')
      } finally {
        setLoading(false)
      }
    }
    loadCurrentUser()
  }, [])

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handlePreferenceChange = (asset) => {
    setFormData(prev => ({
      ...prev,
      asset_preferences: prev.asset_preferences.includes(asset)
        ? prev.asset_preferences.filter(a => a !== asset)
        : [...prev.asset_preferences, asset]
    }))
  }

  const handleUpdateUser = async (e) => {
    e.preventDefault()
    if (!user) return

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const updatedUser = await updateUser(user.id, {
        morning_time: formData.morning_time || null,
        evening_time: formData.evening_time || null,
        asset_preferences: formData.asset_preferences.length > 0 ? formData.asset_preferences : null
      })
      setUser(updatedUser)
      setSuccess('Preferences updated successfully!')
    } catch (err) {
      setError(err.message || 'Failed to update preferences')
    } finally {
      setLoading(false)
    }
  }

  if (loading && !user) {
    return (
      <div className="user-settings-page">
        <div className="page-header">
          <h1>User Settings</h1>
        </div>
        <div className="settings-container">
          <p>Loading your profile...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="user-settings-page">
      <div className="page-header">
        <h1>User Settings</h1>
        <p>Manage your delivery preferences</p>
      </div>

      <div className="settings-container">
        {error && (
          <div className="alert alert-error">
            <span>⚠️ {error}</span>
          </div>
        )}
        {success && (
          <div className="alert alert-success">
            <span>✅ {success}</span>
          </div>
        )}

        <div className="settings-section">
          <h2>Delivery Preferences</h2>
          <form onSubmit={handleUpdateUser} className="user-form">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="morning-time">Morning Delivery Time</label>
                <input
                  id="morning-time"
                  type="time"
                  name="morning_time"
                  value={formData.morning_time}
                  onChange={handleInputChange}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="evening-time">Evening Delivery Time</label>
                <input
                  id="evening-time"
                  type="time"
                  name="evening_time"
                  value={formData.evening_time}
                  onChange={handleInputChange}
                  className="form-input"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Asset Preferences</label>
              <div className="checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.asset_preferences.includes('crypto')}
                    onChange={() => handlePreferenceChange('crypto')}
                  />
                  Cryptocurrencies
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.asset_preferences.includes('stock')}
                    onChange={() => handlePreferenceChange('stock')}
                  />
                  Stocks
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? 'Saving...' : 'Save Preferences'}
            </button>
          </form>
        </div>

        {user && (
          <div className="settings-section">
            <h2>Account Information</h2>
            <div className="user-info">
              <div className="info-row">
                <span className="label">Email:</span>
                <span className="value">{user.email}</span>
              </div>
              <div className="info-row">
                <span className="label">Member since:</span>
                <span className="value">{new Date(user.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
