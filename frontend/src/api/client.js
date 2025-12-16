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

export default client
