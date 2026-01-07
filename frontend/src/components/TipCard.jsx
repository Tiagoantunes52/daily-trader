import PropTypes from 'prop-types'
import React from 'react'
import './TipCard.css'

export default function TipCard({ tip }) {
  const getRecommendationColor = (recommendation) => {
    switch (recommendation) {
      case 'BUY':
        return 'buy'
      case 'SELL':
        return 'sell'
      case 'HOLD':
        return 'hold'
      default:
        return 'neutral'
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="tip-card">
      <div className="tip-header">
        <div className="tip-symbol">
          <span className="symbol">{tip.symbol}</span>
          <span className={`type ${tip.type}`}>{tip.type}</span>
        </div>
        <div className={`recommendation ${getRecommendationColor(tip.recommendation)}`}>
          {tip.recommendation}
        </div>
      </div>

      <div className="tip-body">
        <p className="reasoning">{tip.reasoning}</p>

        <div className="tip-meta">
          <div className="confidence">
            <span className="label">Confidence:</span>
            <span className="value">{tip.confidence}%</span>
          </div>
          <div className="delivery-type">
            <span className="label">Delivery:</span>
            <span className="value">{tip.delivery_type}</span>
          </div>
        </div>

        {tip.indicators && tip.indicators.length > 0 && (
          <div className="indicators">
            <span className="label">Indicators:</span>
            <div className="indicator-list">
              {tip.indicators.map((indicator, idx) => (
                <span key={idx} className="indicator-badge">{indicator}</span>
              ))}
            </div>
          </div>
        )}

        {tip.sources && tip.sources.length > 0 && (
          <div className="sources">
            <span className="label">Sources:</span>
            <div className="source-list">
              {tip.sources.map((source, idx) => (
                <a key={idx} href={source.url} target="_blank" rel="noopener noreferrer" className="source-link">
                  {source.name}
                </a>
              ))}
            </div>
          </div>
        )}

        <div className="generated-at">
          {formatDate(tip.generated_at)}
        </div>
      </div>
    </div>
  )
}

TipCard.propTypes = {
  tip: PropTypes.shape({
    id: PropTypes.string.isRequired,
    symbol: PropTypes.string.isRequired,
    type: PropTypes.string.isRequired,
    recommendation: PropTypes.string.isRequired,
    reasoning: PropTypes.string.isRequired,
    confidence: PropTypes.number.isRequired,
    indicators: PropTypes.arrayOf(PropTypes.string),
    sources: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      url: PropTypes.string.isRequired,
    })),
    generated_at: PropTypes.string.isRequired,
    delivery_type: PropTypes.string.isRequired,
  }).isRequired,
}
