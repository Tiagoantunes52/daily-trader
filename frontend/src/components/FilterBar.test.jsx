import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FilterBar from './FilterBar'

describe('FilterBar', () => {
  const mockFilters = {
    assetType: null,
    days: null,
    startDate: '',
    endDate: ''
  }

  it('renders all filter inputs', () => {
    const onFilterChange = vi.fn()
    const onSearch = vi.fn()

    render(
      <FilterBar
        filters={mockFilters}
        onFilterChange={onFilterChange}
        onSearch={onSearch}
      />
    )

    expect(screen.getByLabelText('Asset Type')).toBeInTheDocument()
    expect(screen.getByLabelText('Time Range')).toBeInTheDocument()
    expect(screen.getByLabelText('Start Date')).toBeInTheDocument()
    expect(screen.getByLabelText('End Date')).toBeInTheDocument()
  })

  it('renders search button', () => {
    const onFilterChange = vi.fn()
    const onSearch = vi.fn()

    render(
      <FilterBar
        filters={mockFilters}
        onFilterChange={onFilterChange}
        onSearch={onSearch}
      />
    )

    expect(screen.getByText('Search')).toBeInTheDocument()
  })

  it('calls onFilterChange when asset type changes', () => {
    const onFilterChange = vi.fn()
    const onSearch = vi.fn()

    render(
      <FilterBar
        filters={mockFilters}
        onFilterChange={onFilterChange}
        onSearch={onSearch}
      />
    )

    const assetTypeSelect = screen.getByLabelText('Asset Type')
    fireEvent.change(assetTypeSelect, { target: { value: 'crypto' } })

    expect(onFilterChange).toHaveBeenCalled()
  })

  it('calls onFilterChange when time range changes', () => {
    const onFilterChange = vi.fn()
    const onSearch = vi.fn()

    render(
      <FilterBar
        filters={mockFilters}
        onFilterChange={onFilterChange}
        onSearch={onSearch}
      />
    )

    const daysSelect = screen.getByLabelText('Time Range')
    fireEvent.change(daysSelect, { target: { value: '7' } })

    expect(onFilterChange).toHaveBeenCalled()
  })

  it('calls onSearch when search button is clicked', () => {
    const onFilterChange = vi.fn()
    const onSearch = vi.fn()

    render(
      <FilterBar
        filters={mockFilters}
        onFilterChange={onFilterChange}
        onSearch={onSearch}
      />
    )

    const searchButton = screen.getByText('Search')
    fireEvent.click(searchButton)

    expect(onSearch).toHaveBeenCalled()
  })

  it('displays selected filter values', () => {
    const onFilterChange = vi.fn()
    const onSearch = vi.fn()
    const filtersWithValues = {
      assetType: 'crypto',
      days: 7,
      startDate: '2024-01-01',
      endDate: '2024-01-31'
    }

    render(
      <FilterBar
        filters={filtersWithValues}
        onFilterChange={onFilterChange}
        onSearch={onSearch}
      />
    )

    expect(screen.getByLabelText('Asset Type')).toHaveValue('crypto')
    expect(screen.getByLabelText('Time Range')).toHaveValue('7')
    expect(screen.getByLabelText('Start Date')).toHaveValue('2024-01-01')
    expect(screen.getByLabelText('End Date')).toHaveValue('2024-01-31')
  })
})
