import React from 'react'
import './MarketDataChart.css'

export default function MarketDataChart({ marketData }) {
  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(price)
  }

  const formatVolume = (volume) => {
    if (volume >= 1e9) return (volume / 1e9).toFixed(2) + 'B'
    if (volume >= 1e6) return (volume / 1e6).toFixed(2) + 'M'
    if (volume >= 1e3) return (volume / 1e3).toFixed(2) + 'K'
    return volume.toFixed(0)
  }

  const getPriceChangeColor = (change) => {
    if (change > 0) return 'positive'
    if (change < 0) return 'negative'
    return 'neutral'
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const renderHistoricalChart = (historicalData) => {
    if (!historicalData || !historicalData.prices || historicalData.prices.length === 0) {
      return <div className="no-chart">No historical data available</div>
    }

    const prices = historicalData.prices
    const minPrice = Math.min(...prices)
    const maxPrice = Math.max(...prices)
    const range = maxPrice - minPrice || 1

    return (
      <div className="chart-container">
        <div className="chart">
          {prices.map((price, idx) => {
            const height = ((price - minPrice) / range) * 100
            return (
              <div
                key={idx}
                className="chart-bar"
                style={{ height: `${height}%` }}
                title={`$${price.toFixed(2)}`}
              />
            )
          })}
        </div>
        <div className="chart-labels">
          <span>${minPrice.toFixed(2)}</span>
          <span>${maxPrice.toFixed(2)}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="market-data-grid">
      {marketData.map((data) => (
        <div key={data.symbol} className="market-data-card">
          <div className="market-header">
            <div className="market-symbol">
              <span className="symbol">{data.symbol}</span>
              <span className={`type ${data.type}`}>{data.type}</span>
            </div>
            <div className="market-price">
              <span className="current-price">{formatPrice(data.current_price)}</span>
              <span className={`price-change ${getPriceChangeColor(data.price_change_24h)}`}>
                {data.price_change_24h > 0 ? '+' : ''}{data.price_change_24h.toFixed(2)}%
              </span>
            </div>
          </div>

          <div className="market-body">
            <div className="volume">
              <span className="label">24h Volume:</span>
              <span className="value">{formatVolume(data.volume_24h)}</span>
            </div>

            <div className="historical-section">
              <div className="historical-header">
                <span className="label">Historical Data ({data.historical_data.period})</span>
              </div>
              {renderHistoricalChart(data.historical_data)}
            </div>

            {data.source && (
              <div className="source-info">
                <span className="label">Source:</span>
                <a href={data.source.url} target="_blank" rel="noopener noreferrer" className="source-link">
                  {data.source.name}
                </a>
                <span className="fetched-at">
                  Updated: {formatDate(data.source.fetched_at)}
                </span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
