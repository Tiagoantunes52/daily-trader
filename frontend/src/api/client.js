import axios from 'axios'

const API_BASE_URL = '/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  withCredentials: true, // Include cookies for authentication
})

// Add request interceptor to handle authentication
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If request failed with 401 and we haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Dynamically import session manager to avoid circular dependency
        const { default: sessionManager } = await import('../utils/sessionManager.js')
        
        // Try to refresh the token
        const refreshSuccess = await sessionManager.refreshToken()
        
        if (refreshSuccess) {
          // Retry the original request
          return client(originalRequest)
        } else {
          // Refresh failed, let session manager handle authentication failure
          return Promise.reject(error)
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError)
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  }
)

export const getTips = async (filters = {}) => {
  const params = new URLSearchParams()
  
  if (filters.assetType) params.append('asset_type', filters.assetType)
  if (filters.days) params.append('days', filters.days)
  if (filters.skip !== undefined) params.append('skip', filters.skip)
  if (filters.limit !== undefined) params.append('limit', filters.limit)
  
  const response = await client.get('/tips', { params })
  return response.data
}

export const getMarketData = async (symbols = []) => {
  const params = new URLSearchParams()
  
  symbols.forEach(symbol => params.append('symbols', symbol))
  
  const response = await client.get('/market-data', { params })
  return response.data
}

export const getTipHistory = async (filters = {}) => {
  const params = new URLSearchParams()
  
  if (filters.days !== undefined) params.append('days', filters.days)
  if (filters.assetType) params.append('asset_type', filters.assetType)
  if (filters.skip !== undefined) params.append('skip', filters.skip)
  if (filters.limit !== undefined) params.append('limit', filters.limit)
  
  const response = await client.get('/tip-history', { params })
  return response.data
}

export const generateTips = async () => {
  const response = await client.post('/tips/generate')
  return response.data
}

export default client

// Authentication Endpoints
export const login = async (email, password) => {
  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
    credentials: 'include'
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Login failed')
  }
  
  return response.json()
}

export const logout = async () => {
  const { default: sessionManager } = await import('../utils/sessionManager.js')
  return sessionManager.logout()
}

export const refreshToken = async () => {
  const { default: sessionManager } = await import('../utils/sessionManager.js')
  return sessionManager.refreshToken()
}

export const isAuthenticated = async () => {
  const { default: sessionManager } = await import('../utils/sessionManager.js')
  return sessionManager.isAuthenticated()
}

// User Profile Endpoints (Protected)
export const getUserProfile = async () => {
  const { default: sessionManager } = await import('../utils/sessionManager.js')
  const response = await sessionManager.authenticatedFetch('/api/user/profile')
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Failed to get user profile')
  }
  
  return response.json()
}

export const updateUserProfile = async (profileData) => {
  const { default: sessionManager } = await import('../utils/sessionManager.js')
  const response = await sessionManager.authenticatedFetch('/api/user/profile', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(profileData)
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Failed to update profile')
  }
  
  return response.json()
}

export const changePassword = async (currentPassword, newPassword) => {
  const { default: sessionManager } = await import('../utils/sessionManager.js')
  const response = await sessionManager.authenticatedFetch('/api/user/change-password', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword
    })
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Failed to change password')
  }
  
  return response.json()
}

export const deleteAccount = async () => {
  const { default: sessionManager } = await import('../utils/sessionManager.js')
  const response = await sessionManager.authenticatedFetch('/api/user/account', {
    method: 'DELETE'
  })
  
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.message || 'Failed to delete account')
  }
  
  return response.json()
}

// User Management Endpoints
export const createUser = async (userData) => {
  const response = await client.post('/users', userData)
  return response.data
}

export const getUser = async (userId) => {
  const response = await client.get(`/users/${userId}`)
  return response.data
}

export const getUserByEmail = async (email) => {
  const response = await client.get(`/users/email/${email}`)
  return response.data
}

export const updateUser = async (userId, userData) => {
  const response = await client.put(`/users/${userId}`, userData)
  return response.data
}

export const deleteUser = async (userId) => {
  const response = await client.delete(`/users/${userId}`)
  return response.data
}
