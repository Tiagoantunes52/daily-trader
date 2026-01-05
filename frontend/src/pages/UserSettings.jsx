import React, { useState } from 'react'
import PropTypes from 'prop-types'
import { createUser, updateUser, getUser } from '../api/client'
import './UserSettings.css'

export default function UserSettings() {
  const [userId, setUserId] = useState('')
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [formData, setFormData] = useState({
    email: '',
    morning_time: '',
    evening_time: '',
    asset_preferences: []
  })

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handlePreferenceChange = (asset) => {
    setFormData(prev => ({
      ...prev,
      asset_preferences: prev.asset_preferences.includes(asset)
        ? prev.asset_preferences.filter(a => a !== asset)
        : [...prev.asset_preferences, asset]
    }))
  }

  const handleLoadUser = async () => {
    if (!userId) {
      setError('Please enter a user ID')
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const userData = await getUser(userId)
      setUser(userData)
      setFormData({
        email: userData.email,
        morning_time: userData.morning_time || '',
        evening_time: userData.evening_time || '',
        asset_preferences: userData.asset_preferences ? JSON.parse(userData.asset_preferences) : []
      })
    } catch (err) {
      setError(err.message || 'Failed to load user')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const newUser = await createUser({
        email: formData.email,
        morning_time: formData.morning_time || null,
        evening_time: formData.evening_time || null,
        asset_preferences: formData.asset_preferences.length > 0 ? formData.asset_preferences : null
      })
      setUser(newUser)
      setUserId(newUser.id)
      setSuccess(`User created successfully! ID: ${newUser.id}`)
    } catch (err) {
      setError(err.message || 'Failed to create user')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateUser = async (e) => {
    e.preventDefault()
    if (!user) {
      setError('No user loaded')
      return
    }

    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const updatedUser = await updateUser(user.id, {
        email: formData.email,
        morning_time: formData.morning_time || null,
        evening_time: formData.evening_time || null,
        asset_preferences: formData.asset_preferences.length > 0 ? formData.asset_preferences : null
      })
      setUser(updatedUser)
      setSuccess('User updated successfully!')
    } catch (err) {
      setError(err.message || 'Failed to update user')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="user-settings-page">
      <div className="page-header">
        <h1>User Settings</h1>
        <p>Manage your profile and preferences</p>
      </div>

      <div className="settings-container">
        {/* Load User Section */}
        <div className="settings-section">
          <h2>Load Existing User</h2>
          <div className="load-user-form">
            <div className="form-group">
              <label htmlFor="user-id">User ID</label>
              <input
                id="user-id"
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="Enter user ID"
                className="form-input"
              />
            </div>
            <button
              onClick={handleLoadUser}
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? 'Loading...' : 'Load User'}
            </button>
          </div>
        </div>

        {/* Error/Success Messages */}
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

        {/* User Form */}
        <div className="settings-section">
          <h2>{user ? 'Update User' : 'Create New User'}</h2>
          <form onSubmit={user ? handleUpdateUser : handleCreateUser} className="user-form">
            <div className="form-group">
              <label htmlFor="email">Email Address *</label>
              <input
                id="email"
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="user@example.com"
                className="form-input"
                required
              />
            </div>

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
              {loading ? 'Saving...' : user ? 'Update User' : 'Create User'}
            </button>
          </form>
        </div>

        {/* User Info Display */}
        {user && (
          <div className="settings-section">
            <h2>User Information</h2>
            <div className="user-info">
              <div className="info-row">
                <span className="label">User ID:</span>
                <span className="value">{user.id}</span>
              </div>
              <div className="info-row">
                <span className="label">Email:</span>
                <span className="value">{user.email}</span>
              </div>
              <div className="info-row">
                <span className="label">Created:</span>
                <span className="value">{new Date(user.created_at).toLocaleDateString()}</span>
              </div>
              <div className="info-row">
                <span className="label">Last Updated:</span>
                <span className="value">{new Date(user.updated_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
