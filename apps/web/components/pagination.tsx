'use client'

import { useEffect, useState } from 'react'

const PER_PAGE_OPTIONS = [5, 10, 20, 50, 100]

function generatePageNumbers(
  current: number,
  total: number,
): (number | '...')[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | '...')[] = []
  pages.push(1)
  if (current > 3) pages.push('...')
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  if (current < total - 2) pages.push('...')
  pages.push(total)
  return pages
}

export interface PaginationProps {
  currentPage: number
  totalPages: number
  totalItems: number
  perPage: number
  perPageOptions?: number[]
  /** localStorage key to persist the per-page preference across visits. */
  storageKey?: string
  onPageChange: (page: number) => void
  onPerPageChange: (perPage: number) => void
}

export default function Pagination({
  currentPage,
  totalPages,
  totalItems,
  perPage,
  perPageOptions = PER_PAGE_OPTIONS,
  storageKey,
  onPageChange,
  onPerPageChange,
}: PaginationProps) {
  const [hydrated, setHydrated] = useState(false)

  // On mount, load saved per-page preference from localStorage
  useEffect(() => {
    if (!storageKey) {
      setHydrated(true)
      return
    }
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        const val = Number(saved)
        if (perPageOptions.includes(val) && val !== perPage) {
          onPerPageChange(val)
        }
      }
    } catch {
      // localStorage unavailable (SSR / private browsing)
    }
    setHydrated(true)
    // Only run on mount — storageKey and perPageOptions are stable
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handlePerPageChange = (val: number) => {
    if (storageKey) {
      try {
        localStorage.setItem(storageKey, String(val))
      } catch {
        // ignore
      }
    }
    onPerPageChange(val)
  }

  const safePage = Math.min(currentPage, totalPages)
  const pageNumbers = generatePageNumbers(safePage, totalPages)
  const startItem = Math.min((safePage - 1) * perPage + 1, totalItems)
  const endItem = Math.min(safePage * perPage, totalItems)

  return (
    <div className="flex items-center justify-between border-t border-border px-5 py-4">
      <div className="flex items-center gap-3 text-sm text-muted">
        <span>Rows per page:</span>
        <select
          value={hydrated ? perPage : perPageOptions[0]}
          onChange={(e) => handlePerPageChange(Number(e.target.value))}
          className="bg-surface border border-border rounded-md px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {perPageOptions.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        <span>
          {totalItems > 0 ? `${startItem}–${endItem} of ${totalItems}` : '0 items'}
        </span>
      </div>

      <nav className="flex items-center gap-1.5" aria-label="Pagination">
        {/* Previous */}
        <button
          onClick={() => onPageChange(safePage - 1)}
          disabled={safePage <= 1}
          className="px-3 py-1.5 text-sm rounded-md border border-border text-muted hover:bg-surface-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label="Previous page"
        >
          ‹
        </button>

        {pageNumbers.map((p, i) =>
          p === '...' ? (
            <span
              key={`ellipsis-${i}`}
              className="px-1.5 text-sm text-muted select-none"
            >
              …
            </span>
          ) : (
            <button
              key={p}
              onClick={() => onPageChange(p)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                p === safePage
                  ? 'bg-primary text-white font-semibold'
                  : 'border border-border text-muted hover:bg-surface-secondary'
              }`}
              aria-label={`Page ${p}`}
              aria-current={p === safePage ? 'page' : undefined}
            >
              {p}
            </button>
          ),
        )}

        {/* Next */}
        <button
          onClick={() => onPageChange(safePage + 1)}
          disabled={safePage >= totalPages}
          className="px-3 py-1.5 text-sm rounded-md border border-border text-muted hover:bg-surface-secondary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label="Next page"
        >
          ›
        </button>
      </nav>
    </div>
  )
}
