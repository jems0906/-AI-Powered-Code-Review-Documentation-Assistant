import { useQuery } from '@tanstack/react-query'
import { fetchReviews, fetchMetricsSummary } from '../api/client'
import { Link } from 'react-router-dom'
import QualityScoreBadge from '../components/QualityScoreBadge'
import { formatDistanceToNow } from 'date-fns'
import type { ReviewStatus } from '../types/api'
import clsx from 'clsx'

const STATUS_STYLES: Record<ReviewStatus, string> = {
  pending: 'text-gray-400 bg-gray-800',
  in_progress: 'text-blue-300 bg-blue-900/50',
  completed: 'text-green-300 bg-green-900/50',
  failed: 'text-red-300 bg-red-900/50',
}

export default function DashboardPage() {
  const { data: listData } = useQuery({
    queryKey: ['reviews', 'recent'],
    queryFn: () => fetchReviews({ limit: 10 }),
  })
  const { data: metrics } = useQuery({
    queryKey: ['metrics', 'summary'],
    queryFn: () => fetchMetricsSummary(),
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* KPI Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <KpiCard label="Total Reviews" value={metrics.total_reviews} />
          <KpiCard label="Total Comments" value={metrics.total_comments} />
          <KpiCard
            label="Acceptance Rate"
            value={`${(metrics.acceptance_rate * 100).toFixed(0)}%`}
          />
          <KpiCard label="Avg Quality" value={`${metrics.avg_quality_score}/10`} />
        </div>
      )}

      {/* Recent Reviews */}
      <div className="bg-gray-900 rounded-xl border border-gray-800">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
          <h2 className="font-semibold">Recent Reviews</h2>
          <Link to="/reviews" className="text-indigo-400 hover:text-indigo-300 text-sm">
            View all →
          </Link>
        </div>
        <div className="divide-y divide-gray-800">
          {listData?.reviews.map((r) => (
            <Link
              key={r.id}
              to={`/reviews/${r.id}`}
              className="flex items-center justify-between px-5 py-3 hover:bg-gray-800/50 transition-colors"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  {r.repo_full_name} <span className="text-gray-500">#{r.pr_number}</span>
                </p>
                <p className="text-xs text-gray-500 truncate">{r.pr_title ?? '—'}</p>
              </div>
              <div className="flex items-center gap-4 flex-shrink-0">
                <span className={clsx('text-xs px-2 py-0.5 rounded-full', STATUS_STYLES[r.status])}>
                  {r.status}
                </span>
                <QualityScoreBadge score={r.quality_score} />
                <span className="text-xs text-gray-600 hidden md:block">
                  {formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}
                </span>
              </div>
            </Link>
          ))}
          {!listData?.reviews.length && (
            <p className="px-5 py-6 text-sm text-gray-600 text-center">
              No reviews yet. Set up a GitHub webhook to get started.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  )
}
