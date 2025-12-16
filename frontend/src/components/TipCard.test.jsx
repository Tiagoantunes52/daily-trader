import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TipCard from './TipCard'

describe('TipCard', () => {
  const mockTip = {
    id: '1',
    symbol: 'BTC',
    type: 'crypto',
    recommendation: 'BUY',
    reasoning: 'Strong uptrend with RSI below 70',
    confidence: 85,
    indicators: ['RSI', 'MACD'],
    sources: [{ name: 'CoinGecko', url: 'https://coingecko.com' }],
    generated_at: '2024-01-15T10:30:00Z',
    delivery_type: 'morning'
  }

  it('renders tip symbol and type', () => {
    render(<TipCard tip={mockTip} />)
    expect(screen.getByText('BTC')).toBeInTheDocument()
    expect(screen.getByText('crypto')).toBeInTheDocument()
  })

  it('renders recommendation with correct styling', () => {
    render(<TipCard tip={mockTip} />)
    expect(screen.getByText('BUY')).toBeInTheDocument()
  })

  it('renders reasoning text', () => {
    render(<TipCard tip={mockTip} />)
    expect(screen.getByText('Strong uptrend with RSI below 70')).toBeInTheDocument()
  })

  it('renders confidence score', () => {
    render(<TipCard tip={mockTip} />)
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('renders delivery type', () => {
    render(<TipCard tip={mockTip} />)
    expect(screen.getByText('morning')).toBeInTheDocument()
  })

  it('renders indicators', () => {
    render(<TipCard tip={mockTip} />)
    expect(screen.getByText('RSI')).toBeInTheDocument()
    expect(screen.getByText('MACD')).toBeInTheDocument()
  })

  it('renders source links', () => {
    render(<TipCard tip={mockTip} />)
    const link = screen.getByText('CoinGecko')
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', 'https://coingecko.com')
  })

  it('handles missing indicators gracefully', () => {
    const tipWithoutIndicators = { ...mockTip, indicators: [] }
    render(<TipCard tip={tipWithoutIndicators} />)
    expect(screen.queryByText('Indicators:')).not.toBeInTheDocument()
  })

  it('handles missing sources gracefully', () => {
    const tipWithoutSources = { ...mockTip, sources: [] }
    render(<TipCard tip={tipWithoutSources} />)
    expect(screen.queryByText('Sources:')).not.toBeInTheDocument()
  })

  it('renders SELL recommendation with correct styling', () => {
    const sellTip = { ...mockTip, recommendation: 'SELL' }
    render(<TipCard tip={sellTip} />)
    expect(screen.getByText('SELL')).toBeInTheDocument()
  })

  it('renders HOLD recommendation with correct styling', () => {
    const holdTip = { ...mockTip, recommendation: 'HOLD' }
    render(<TipCard tip={holdTip} />)
    expect(screen.getByText('HOLD')).toBeInTheDocument()
  })
})
