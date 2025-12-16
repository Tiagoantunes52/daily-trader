import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Pagination from './Pagination'

describe('Pagination', () => {
  it('does not render when total pages is 1', () => {
    const onPageChange = vi.fn()
    const { container } = render(
      <Pagination total={10} skip={0} limit={10} onPageChange={onPageChange} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders pagination controls when multiple pages exist', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination total={50} skip={0} limit={10} onPageChange={onPageChange} />
    )
    expect(screen.getByText('← Previous')).toBeInTheDocument()
    expect(screen.getByText('Next →')).toBeInTheDocument()
  })

  it('disables previous button on first page', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination total={50} skip={0} limit={10} onPageChange={onPageChange} />
    )
    expect(screen.getByText('← Previous')).toBeDisabled()
  })

  it('disables next button on last page', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination total={50} skip={40} limit={10} onPageChange={onPageChange} />
    )
    expect(screen.getByText('Next →')).toBeDisabled()
  })

  it('calls onPageChange when next button is clicked', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination total={50} skip={0} limit={10} onPageChange={onPageChange} />
    )
    fireEvent.click(screen.getByText('Next →'))
    expect(onPageChange).toHaveBeenCalledWith(10)
  })

  it('calls onPageChange when previous button is clicked', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination total={50} skip={10} limit={10} onPageChange={onPageChange} />
    )
    fireEvent.click(screen.getByText('← Previous'))
    expect(onPageChange).toHaveBeenCalledWith(0)
  })

  it('calls onPageChange when page number is clicked', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination total={50} skip={0} limit={10} onPageChange={onPageChange} />
    )
    fireEvent.click(screen.getByText('2'))
    expect(onPageChange).toHaveBeenCalledWith(10)
  })

  it('displays pagination info', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination total={50} skip={0} limit={10} onPageChange={onPageChange} />
    )
    expect(screen.getByText(/Page 1 of 5/)).toBeInTheDocument()
  })

  it('highlights current page', () => {
    const onPageChange = vi.fn()
    render(
      <Pagination total={50} skip={10} limit={10} onPageChange={onPageChange} />
    )
    const currentPageButton = screen.getByText('2')
    expect(currentPageButton).toHaveClass('active')
  })
})
