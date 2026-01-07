import React, { useState, useEffect, useCallback } from 'react'
import { getTipHistory } from '../api/client'
import TipCard from '../components/TipCard'
import FilterBar from '../components/FilterBar'
import Pagination from '../components/Pagination'
import './TipHistory.css'

export default function TipHistory() {
  const [tips, setTips] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({
    assetType: null,
    days: 7,
    startDate: '',
    endDate: ''
  })
  const [pagination, setPagination] = useState({
    skip: 0,
    limit: 20,
    total: 0
  })

  const fetchHistory = useCallback(async (filterParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await getTipHistory({
        days: filterParams.days !== undefined ? filterParams.days : filters.days,
        assetType: filterParams.assetType || filters.assetType,
        skip: filterParams.skip !== undefined ? filterParams.skip : pagination.skip,
        limit: pagination.limit
      })

      setTips(response.tips || [])
      setPagination({
        skip: response.skip,
        limit: response.limit,
        total: response.total
      })
    } catch (err) {
      setError(err.message || 'Failed to fetch history')
      console.error('Error fetching history:', err)
    } finally {
      setLoading(false)
    }
  }, [filters, pagination.skip, pagination.limit])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters)
  }

  const handleSearch = () => {
    setPagination({ ...pagination, skip: 0 })
    fetchHistory({ ...filters, skip: 0 })
  }

  const handlePageChange = (newSkip) => {
    fetchHistory({ ...filters, skip: newSkip })
  }

  const getDaysLabel = () => {
    if (!filters.days) return 'All Time'
    if (filters.days === 1) return 'Last 24 Hours'
    if (filters.days === 7) return 'Last 7 Days'
    if (filters.days === 30) return 'Last 30 Days'
    if (filters.days === 90) return 'Last 90 Days'
    return `Last ${filters.days} Days`
  }

  return (
    <div className="tip-history-page">
      <div className="page-header">
        <h1>Tip History</h1>
        <p>View past trading recommendations and analysis</p>
      </div>

      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onSearch={handleSearch}
      />

      {error && (
        <div className="error-message">
          <span>⚠️ {error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading history...</p>
        </div>
      ) : (
        <div className="history-section">
          <div className="history-header">
            <h2>Tips from {getDaysLabel()}</h2>
            <span className="total-count">{pagination.total} tips</span>
          </div>

          {tips.length > 0 ? (
            <>
              <div className="tips-list">
                {tips.map((tip) => (
                  <TipCard key={tip.id} tip={tip} />
                ))}
              </div>
              <Pagination
                total={pagination.total}
                skip={pagination.skip}
                limit={pagination.limit}
                onPageChange={handlePageChange}
              />
            </>
          ) : (
            <div className="no-data">
              <p>No tips found for the selected period</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
