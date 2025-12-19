import PropTypes from 'prop-types'
import React from 'react'
import './Pagination.css'

export default function Pagination({ total, skip, limit, onPageChange }) {
  const currentPage = Math.floor(skip / limit) + 1
  const totalPages = Math.ceil(total / limit)

  const handlePrevious = () => {
    if (currentPage > 1) {
      onPageChange((currentPage - 2) * limit)
    }
  }

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage * limit)
    }
  }

  const handlePageClick = (page) => {
    onPageChange((page - 1) * limit)
  }

  const getPageNumbers = () => {
    const pages = []
    const maxVisible = 5
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2))
    let endPage = Math.min(totalPages, startPage + maxVisible - 1)

    if (endPage - startPage < maxVisible - 1) {
      startPage = Math.max(1, endPage - maxVisible + 1)
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i)
    }

    return pages
  }

  if (totalPages <= 1) {
    return null
  }

  return (
    <div className="pagination">
      <button
        className="pagination-button"
        onClick={handlePrevious}
        disabled={currentPage === 1}
      >
        ← Previous
      </button>

      <div className="page-numbers">
        {getPageNumbers().map((page) => (
          <button
            key={page}
            className={`page-number ${page === currentPage ? 'active' : ''}`}
            onClick={() => handlePageClick(page)}
          >
            {page}
          </button>
        ))}
      </div>

      <button
        className="pagination-button"
        onClick={handleNext}
        disabled={currentPage === totalPages}
      >
        Next →
      </button>

      <span className="pagination-info">
        Page {currentPage} of {totalPages} ({total} total)
      </span>
    </div>
  )
}

Pagination.propTypes = {
  total: PropTypes.number.isRequired,
  skip: PropTypes.number.isRequired,
  limit: PropTypes.number.isRequired,
  onPageChange: PropTypes.func.isRequired,
}
