import React, { useState, useEffect, useCallback } from 'react'
import { getTips, getMarketData, generateTips } from '../api/client'
import TipCard from '../components/TipCard'
import MarketDataChart from '../components/MarketDataChart'
import FilterBar from '../components/FilterBar'
import Pagination from '../components/Pagination'
import './CurrentTips.css'

export default function CurrentTips() {
  const [tips, setTips] = useState([])
  const [marketData, setMarketData] = useState([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({
    assetType: null,
    days: null,
    startDate: '',
    endDate: ''
  })
  const [pagination, setPagination] = useState({
    skip: 0,
    limit: 10,
    total: 0
  })

  const fetchData = useCallback(async (filterParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const tipsResponse = await getTips({
        assetType: filterParams.assetType || filters.assetType,
        days: filterParams.days || filters.days,
        skip: filterParams.skip !== undefined ? filterParams.skip : pagination.skip,
        limit: pagination.limit
      })

      setTips(tipsResponse.tips || [])
      setPagination({
        skip: tipsResponse.skip,
        limit: tipsResponse.limit,
        total: tipsResponse.total
      })

      // Extract unique symbols from tips
      const symbols = [...new Set(tipsResponse.tips?.map(t => t.symbol) || [])]
      if (symbols.length > 0) {
        const marketDataResponse = await getMarketData(symbols)
        setMarketData(marketDataResponse.market_data || [])
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch data')
      console.error('Error fetching data:', err)
    } finally {
      setLoading(false)
    }
  }, [filters, pagination.skip, pagination.limit])

  const handleGenerateTips = useCallback(async () => {
    setGenerating(true)
    setError(null)
    try {
      await generateTips()
      // Refresh the tips after generation
      await fetchData()
    } catch (err) {
      setError(err.message || 'Failed to generate tips')
      console.error('Error generating tips:', err)
    } finally {
      setGenerating(false)
    }
  }, [fetchData])

  useEffect(() => {
    // Generate tips on first load
    handleGenerateTips()
  }, [handleGenerateTips])

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters)
  }

  const handleSearch = () => {
    setPagination({ ...pagination, skip: 0 })
    fetchData({ ...filters, skip: 0 })
  }

  const handlePageChange = (newSkip) => {
    fetchData({ ...filters, skip: newSkip })
  }

  return (
    <div className="current-tips-page">
      <div className="page-header">
        <div className="header-content">
          <h1>Current Market Tips</h1>
          <p>Latest trading recommendations and market analysis</p>
        </div>
        <button
          className="refresh-button"
          onClick={handleGenerateTips}
          disabled={generating || loading}
          title="Generate fresh market tips"
        >
          {generating ? '⏳ Generating...' : '🔄 Refresh Tips'}
        </button>
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
          <p>Loading market data...</p>
        </div>
      ) : (
        <>
          {marketData.length > 0 && (
            <div className="market-data-section">
              <h2>Market Data</h2>
              <MarketDataChart marketData={marketData} />
            </div>
          )}

          <div className="tips-section">
            <h2>Trading Tips ({pagination.total})</h2>
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
                <p>No tips found matching your filters</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
