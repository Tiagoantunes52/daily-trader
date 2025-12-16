import React from 'react'
import './FilterBar.css'

export default function FilterBar({ filters, onFilterChange, onSearch }) {
  const handleAssetTypeChange = (e) => {
    onFilterChange({ ...filters, assetType: e.target.value })
  }

  const handleDaysChange = (e) => {
    onFilterChange({ ...filters, days: parseInt(e.target.value) || null })
  }

  const handleStartDateChange = (e) => {
    onFilterChange({ ...filters, startDate: e.target.value })
  }

  const handleEndDateChange = (e) => {
    onFilterChange({ ...filters, endDate: e.target.value })
  }

  const handleSearch = (e) => {
    e.preventDefault()
    onSearch()
  }

  return (
    <div className="filter-bar">
      <form onSubmit={handleSearch} className="filter-form">
        <div className="filter-group">
          <label htmlFor="asset-type">Asset Type</label>
          <select
            id="asset-type"
            value={filters.assetType || ''}
            onChange={handleAssetTypeChange}
            className="filter-select"
          >
            <option value="">All Assets</option>
            <option value="crypto">Crypto</option>
            <option value="stock">Stock</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="days">Time Range</label>
          <select
            id="days"
            value={filters.days || ''}
            onChange={handleDaysChange}
            className="filter-select"
          >
            <option value="">All Time</option>
            <option value="1">Last 24 Hours</option>
            <option value="7">Last 7 Days</option>
            <option value="30">Last 30 Days</option>
            <option value="90">Last 90 Days</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="start-date">Start Date</label>
          <input
            id="start-date"
            type="date"
            value={filters.startDate || ''}
            onChange={handleStartDateChange}
            className="filter-input"
          />
        </div>

        <div className="filter-group">
          <label htmlFor="end-date">End Date</label>
          <input
            id="end-date"
            type="date"
            value={filters.endDate || ''}
            onChange={handleEndDateChange}
            className="filter-input"
          />
        </div>

        <button type="submit" className="search-button">
          Search
        </button>
      </form>
    </div>
  )
}
