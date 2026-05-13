import { useQuery } from '@tanstack/react-query'
import { fetchEngineerMetrics, fetchLearningSignals, fetchMetricsSummary, fetchTrends } from '../api/client'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar,
} from 'recharts'
import { format, parseISO } from 'date-fns'

export default function MetricsPage() {
  const { data: summary } = useQuery({
    queryKey: ['metrics', 'summary'],
    queryFn: () => fetchMetricsSummary(),
  })
  const { data: trends } = useQuery({
    queryKey: ['metrics', 'trends', 30],
    queryFn: () => fetchTrends(undefined, 30),
  })
  const { data: engineerMetrics } = useQuery({
    queryKey: ['metrics', 'engineers'],
    queryFn: () => fetchEngineerMetrics(),
  })
  const { data: learningSignals } = useQuery({
    queryKey: ['metrics', 'learning-feedback'],
    queryFn: () => fetchLearningSignals(),
  })

  const chartData = trends?.map((t) => ({
    date: format(parseISO(t.date), 'MMM d'),
    quality: t.avg_quality,
    reviews: t.count,
  })) ?? []

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Metrics & Trends</h1>

      {/* Summary */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <KpiCard label="Total Reviews" value={summary.total_reviews} />
          <KpiCard label="Total Comments" value={summary.total_comments} />
          <KpiCard label="Acceptance Rate" value={`${(summary.acceptance_rate * 100).toFixed(0)}%`} />
          <KpiCard label="Avg Quality" value={`${summary.avg_quality_score}/10`} />
        </div>
      )}

      {/* Quality trend */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="font-semibold mb-4 text-sm">Code Quality Over Time</h2>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Line type="monotone" dataKey="quality" stroke="#6366f1" strokeWidth={2} dot={false} name="Avg Quality" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Review volume */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="font-semibold mb-4 text-sm">Review Volume</h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
              labelStyle={{ color: '#e5e7eb' }}
            />
            <Bar dataKey="reviews" fill="#6366f1" radius={[4, 4, 0, 0]} name="Reviews" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Engineer improvement tracking */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mt-6">
        <h2 className="font-semibold mb-4 text-sm">Engineer Improvement Tracking</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-800">
                <th className="py-2 pr-3">Engineer</th>
                <th className="py-2 pr-3">Reviews</th>
                <th className="py-2 pr-3">Avg Quality</th>
                <th className="py-2 pr-3">30d Delta</th>
                <th className="py-2 pr-3">Acceptance</th>
              </tr>
            </thead>
            <tbody>
              {(engineerMetrics ?? []).map((row) => (
                <tr key={row.engineer} className="border-b border-gray-800/60">
                  <td className="py-2 pr-3 text-gray-200">{row.engineer}</td>
                  <td className="py-2 pr-3">{row.total_reviews}</td>
                  <td className="py-2 pr-3">{row.avg_quality_score.toFixed(2)}</td>
                  <td className={`py-2 pr-3 ${row.quality_delta >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {row.quality_delta >= 0 ? '+' : ''}{row.quality_delta.toFixed(2)}
                  </td>
                  <td className="py-2 pr-3">{(row.acceptance_rate * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!(engineerMetrics?.length) && (
            <p className="text-xs text-gray-500 py-3">No engineer metrics yet.</p>
          )}
        </div>
      </div>

      {/* Learning signals */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mt-6">
        <h2 className="font-semibold mb-4 text-sm">Feedback Learning Signals</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {(learningSignals ?? []).slice(0, 6).map((signal) => (
            <div key={signal.category} className="rounded-lg border border-gray-800 bg-gray-950 px-3 py-2">
              <p className="text-xs text-gray-400 uppercase tracking-wide">{signal.category.replace('_', ' ')}</p>
              <p className="text-sm text-gray-200">
                Accepted {signal.accepted} / Rejected {signal.rejected}
              </p>
              <p className="text-xs text-indigo-300">Acceptance {(signal.acceptance_rate * 100).toFixed(0)}%</p>
            </div>
          ))}
        </div>
        {!(learningSignals?.length) && (
          <p className="text-xs text-gray-500">No feedback signals available yet.</p>
        )}
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
