import { useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchReview, submitFeedback } from '../api/client'
import QualityScoreBadge from '../components/QualityScoreBadge'
import ReviewCommentCard from '../components/ReviewCommentCard'
import type { CommentCategory, SeverityLevel } from '../types/api'
import { ExternalLink, ArrowLeft } from 'lucide-react'
import { Highlight, themes } from 'prism-react-renderer'

const CATEGORIES: CommentCategory[] = [
  'security', 'performance', 'best_practice', 'edge_case', 'documentation', 'style',
]
const SEVERITIES: SeverityLevel[] = ['critical', 'high', 'medium', 'low', 'info']
const TABS = ['comments', 'summary', 'docs', 'tests'] as const

function normalizeGeneratedCode(content: string | null | undefined): { code: string; language: string } {
  if (!content) return { code: '', language: 'text' }

  let normalized = content.replace(/\\r\\n/g, '\n').replace(/\\n/g, '\n').replace(/\\t/g, '\t').trim()
  let language = 'text'

  const fencedMatch = normalized.match(/^```([\w#+.-]+)?\n([\s\S]*?)```$/)
  if (fencedMatch) {
    language = fencedMatch[1]?.toLowerCase() || 'text'
    normalized = fencedMatch[2].trim()
  } else if (normalized.startsWith('`') && normalized.endsWith('`')) {
    // Some seeded payloads are wrapped with a single backtick around multiline text.
    normalized = normalized.slice(1, -1).trim()
  }

  const lines = normalized.split('\n')
  if (language === 'text' && lines.length > 1 && /^[a-zA-Z][\w#+.-]*$/.test(lines[0].trim())) {
    language = lines[0].trim().toLowerCase()
    lines.shift()
  }

  return {
    code: lines.join('\n').trim(),
    language,
  }
}

function CodePanel({
  content,
  emptyText,
  parsed,
}: {
  content: string | null | undefined
  emptyText: string
  parsed?: { code: string; language: string }
}) {
  const normalized = parsed ?? normalizeGeneratedCode(content)
  const { code, language } = normalized
  if (!code) {
    return <span className="text-sm text-gray-400">{emptyText}</span>
  }

  return (
    <Highlight theme={themes.vsDark} code={code} language={language}>
      {({ className, tokens, getLineProps, getTokenProps }) => (
        <pre className={`${className} text-xs overflow-x-auto rounded-lg p-4 m-0`}>
          {tokens.map((line, i) => (
            <div key={i} {...getLineProps({ line })}>
              {line.map((token, key) => (
                <span key={key} {...getTokenProps({ token })} />
              ))}
            </div>
          ))}
        </pre>
      )}
    </Highlight>
  )
}

function renderTabLabel(
  tab: typeof TABS[number],
  commentCount: number,
  testsLanguageBadge: string | null,
) {
  if (tab === 'comments') return `Comments (${commentCount})`
  if (tab === 'summary') return 'Summary'
  if (tab === 'docs') return 'Generated Docs'

  return (
    <span className="inline-flex items-center gap-2">
      <span>Generated Tests</span>
      {testsLanguageBadge && (
        <span className="px-1.5 py-0.5 rounded-md border border-indigo-500/40 bg-indigo-500/10 text-[10px] font-semibold tracking-wide text-indigo-300">
          {testsLanguageBadge}
        </span>
      )}
    </span>
  )
}

export default function ReviewDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [catFilter, setCatFilter] = useState<CommentCategory | ''>('')
  const [sevFilter, setSevFilter] = useState<SeverityLevel | ''>('')
  const [activeTab, setActiveTab] = useState<'comments' | 'summary' | 'docs' | 'tests'>('comments')
  const [commentView, setCommentView] = useState<'grouped' | 'inline'>('grouped')

  const { data: review, isLoading } = useQuery({
    queryKey: ['review', id],
    queryFn: () => fetchReview(id!),
    enabled: !!id,
  })

  const parsedGeneratedTests = useMemo(
    () => normalizeGeneratedCode(review?.generated_tests),
    [review?.generated_tests],
  )

  const feedbackMutation = useMutation({
    mutationFn: ({ commentId, feedback }: { commentId: string; feedback: 'accepted' | 'rejected' }) =>
      submitFeedback(commentId, feedback),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review', id] }),
  })

  if (isLoading) return <div className="p-6 text-gray-500">Loading review…</div>
  if (!review) return <div className="p-6 text-red-400">Review not found.</div>
  const testsLanguage = parsedGeneratedTests.language
  const testsLanguageBadge = testsLanguage && testsLanguage !== 'text' ? testsLanguage.toUpperCase() : null

  const filteredComments = review.comments.filter((c) => {
    if (catFilter && c.category !== catFilter) return false
    if (sevFilter && c.severity !== sevFilter) return false
    return true
  })

  const grouped = filteredComments.reduce<Record<string, typeof filteredComments>>((acc, c) => {
    ;(acc[c.file_path] ??= []).push(c)
    return acc
  }, {})

  const inlineComments = [...filteredComments].sort((a, b) => {
    if (a.file_path !== b.file_path) return a.file_path.localeCompare(b.file_path)
    return (a.line_start ?? 0) - (b.line_start ?? 0)
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <Link to="/reviews" className="text-gray-500 hover:text-gray-300 mt-1">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold truncate">
              {review.repo_full_name} <span className="text-gray-500">#{review.pr_number}</span>
            </h1>
            {review.pr_url && (
              <a
                href={review.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Open pull request in GitHub"
                title="Open pull request in GitHub"
                className="text-indigo-400 hover:text-indigo-300"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            )}
          </div>
          <p className="text-gray-400 text-sm truncate">{review.pr_title}</p>
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span>Author: <span className="text-gray-300">{review.pr_author ?? '—'}</span></span>
            <span>Profile: <span className="text-gray-300">{review.review_profile}</span></span>
            <span>AI: <span className="text-gray-300">{review.ai_provider ?? '—'}</span></span>
          </div>
        </div>
        <QualityScoreBadge score={review.quality_score} />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 mb-4">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm capitalize transition-colors ${
              activeTab === tab
                ? 'border-b-2 border-indigo-500 text-indigo-400'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {renderTabLabel(tab, review.comment_count, testsLanguageBadge)}
          </button>
        ))}
      </div>

      {activeTab === 'summary' && (
        <div className="prose prose-invert prose-sm max-w-none bg-gray-900 rounded-xl p-5 border border-gray-800 whitespace-pre-wrap text-sm text-gray-300">
          {review.summary ?? 'No summary available.'}
        </div>
      )}

      {activeTab === 'docs' && (
        <div className="max-w-none bg-gray-900 rounded-xl p-5 border border-gray-800">
          <CodePanel content={review.generated_docs} emptyText="No generated documentation." />
        </div>
      )}

      {activeTab === 'tests' && (
        <div className="max-w-none bg-gray-900 rounded-xl p-5 border border-gray-800">
          <CodePanel content={review.generated_tests} parsed={parsedGeneratedTests} emptyText="No generated tests." />
        </div>
      )}

      {activeTab === 'comments' && (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-3 mb-4">
            <label htmlFor="category-filter" className="sr-only">Filter comments by category</label>
            <select
              id="category-filter"
              aria-label="Filter comments by category"
              value={catFilter}
              onChange={(e) => setCatFilter(e.target.value as CommentCategory | '')}
              className="bg-gray-800 border border-gray-700 text-xs rounded px-2 py-1"
            >
              <option value="">All categories</option>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <label htmlFor="severity-filter" className="sr-only">Filter comments by severity</label>
            <select
              id="severity-filter"
              aria-label="Filter comments by severity"
              value={sevFilter}
              onChange={(e) => setSevFilter(e.target.value as SeverityLevel | '')}
              className="bg-gray-800 border border-gray-700 text-xs rounded px-2 py-1"
            >
              <option value="">All severities</option>
              {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <span className="text-xs text-gray-600 self-center">
              {filteredComments.length} comment{filteredComments.length !== 1 ? 's' : ''}
            </span>
            <div className="ml-auto flex gap-1 rounded-lg border border-gray-700 p-1">
              <button
                onClick={() => setCommentView('grouped')}
                className={`px-2 py-1 text-xs rounded ${commentView === 'grouped' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
              >
                Grouped
              </button>
              <button
                onClick={() => setCommentView('inline')}
                className={`px-2 py-1 text-xs rounded ${commentView === 'inline' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
              >
                Inline
              </button>
            </div>
          </div>

          {/* Grouped by file */}
          {commentView === 'grouped' && Object.entries(grouped).map(([filePath, comments]) => (
            <div key={filePath} className="mb-6">
              <h3 className="text-xs font-mono text-gray-400 mb-2 bg-gray-900 px-3 py-1.5 rounded-t-lg border border-gray-800">
                {filePath}
              </h3>
              {comments.map((c) => (
                <ReviewCommentCard
                  key={c.id}
                  severity={c.severity}
                  category={c.category}
                  body={c.body}
                  suggestedFix={c.suggested_fix}
                  suggestedDiff={c.suggested_diff}
                  filePath={c.file_path}
                  lineStart={c.line_start}
                  feedback={c.feedback}
                  onAccept={() => feedbackMutation.mutate({ commentId: c.id, feedback: 'accepted' })}
                  onReject={() => feedbackMutation.mutate({ commentId: c.id, feedback: 'rejected' })}
                />
              ))}
            </div>
          ))}

          {commentView === 'inline' && (
            <div className="space-y-3">
              {inlineComments.map((c) => (
                <ReviewCommentCard
                  key={c.id}
                  severity={c.severity}
                  category={c.category}
                  body={c.body}
                  suggestedFix={c.suggested_fix}
                  suggestedDiff={c.suggested_diff}
                  filePath={c.file_path}
                  lineStart={c.line_start}
                  feedback={c.feedback}
                  onAccept={() => feedbackMutation.mutate({ commentId: c.id, feedback: 'accepted' })}
                  onReject={() => feedbackMutation.mutate({ commentId: c.id, feedback: 'rejected' })}
                />
              ))}
            </div>
          )}
          {filteredComments.length === 0 && (
            <p className="text-center text-gray-600 py-10 text-sm">No comments match the current filters.</p>
          )}
        </>
      )}
    </div>
  )
}
