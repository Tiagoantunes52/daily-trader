import axios from 'axios'

const API_BASE_URL = '/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

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
