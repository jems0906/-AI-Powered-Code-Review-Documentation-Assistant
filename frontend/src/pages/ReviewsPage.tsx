import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchReviews } from '../api/client'
import { Link } from 'react-router-dom'
import QualityScoreBadge from '../components/QualityScoreBadge'
import { formatDistanceToNow } from 'date-fns'
import type { ReviewStatus } from '../types/api'
import clsx from 'clsx'

const STATUS_OPTIONS: ReviewStatus[] = ['pending', 'in_progress', 'completed', 'failed']

const STATUS_STYLES: Record<ReviewStatus, string> = {
  pending: 'text-gray-400 bg-gray-800',
  in_progress: 'text-blue-300 bg-blue-900/50',
  completed: 'text-green-300 bg-green-900/50',
  failed: 'text-red-300 bg-red-900/50',
}

export default function ReviewsPage() {
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | ''>('')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading } = useQuery({
    queryKey: ['reviews', statusFilter, page],
    queryFn: () =>
      fetchReviews({
        status: statusFilter || undefined,
        limit,
        offset: page * limit,
      }),
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Reviews</h1>
        <div className="flex items-center gap-3">
          <label htmlFor="review-status-filter" className="sr-only">Filter reviews by status</label>
          <select
            id="review-status-filter"
            aria-label="Filter reviews by status"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value as ReviewStatus | ''); setPage(0) }}
            className="bg-gray-800 border border-gray-700 text-sm rounded-lg px-3 py-1.5 text-gray-200"
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 divide-y divide-gray-800">
        {isLoading && (
          <p className="px-5 py-10 text-center text-gray-600 text-sm">Loading…</p>
        )}
        {data?.reviews.map((r) => (
          <Link
            key={r.id}
            to={`/reviews/${r.id}`}
            className="flex items-center justify-between px-5 py-3 hover:bg-gray-800/50 transition-colors"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {r.repo_full_name}{' '}
                <span className="text-gray-500">#{r.pr_number}</span>
              </p>
              <p className="text-xs text-gray-500 truncate max-w-md">{r.pr_title ?? '—'}</p>
            </div>
            <div className="flex items-center gap-4 flex-shrink-0 ml-4">
              <span className="text-xs text-gray-500">{r.comment_count} comments</span>
              <span className={clsx('text-xs px-2 py-0.5 rounded-full', STATUS_STYLES[r.status])}>
                {r.status}
              </span>
              <QualityScoreBadge score={r.quality_score} />
              <span className="text-xs text-gray-600 hidden lg:block">
                {formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}
              </span>
            </div>
          </Link>
        ))}
        {!isLoading && !data?.reviews.length && (
          <p className="px-5 py-10 text-center text-gray-600 text-sm">No reviews found.</p>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > limit && (
        <div className="flex justify-center gap-4 mt-4">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            className="px-4 py-1.5 text-sm rounded bg-gray-800 disabled:opacity-40 hover:bg-gray-700"
          >
            Prev
          </button>
          <span className="text-sm text-gray-500 self-center">
            Page {page + 1} of {Math.ceil(data.total / limit)}
          </span>
          <button
            disabled={(page + 1) * limit >= data.total}
            onClick={() => setPage((p) => p + 1)}
            className="px-4 py-1.5 text-sm rounded bg-gray-800 disabled:opacity-40 hover:bg-gray-700"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
