import type { SeverityLevel, CommentCategory } from '../types/api'
import clsx from 'clsx'

const SEVERITY_STYLES: Record<SeverityLevel, string> = {
  critical: 'bg-red-900/60 text-red-300 border border-red-700',
  high: 'bg-orange-900/60 text-orange-300 border border-orange-700',
  medium: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700',
  low: 'bg-blue-900/60 text-blue-300 border border-blue-700',
  info: 'bg-gray-800 text-gray-400 border border-gray-700',
}

const CATEGORY_EMOJI: Record<CommentCategory, string> = {
  security: '🔒',
  performance: '⚡',
  best_practice: '✅',
  edge_case: '⚠️',
  documentation: '📝',
  style: '🎨',
}

interface Props {
  severity: SeverityLevel
  category: CommentCategory
  body: string
  suggestedFix?: string | null
  suggestedDiff?: string | null
  filePath: string
  lineStart?: number | null
  onAccept?: () => void
  onReject?: () => void
  feedback?: string | null
}

export default function ReviewCommentCard({
  severity,
  category,
  body,
  suggestedFix,
  suggestedDiff,
  filePath,
  lineStart,
  onAccept,
  onReject,
  feedback,
}: Props) {
  return (
    <div className={clsx('rounded-lg p-4 mb-3', SEVERITY_STYLES[severity])}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide mb-1">
          <span>{CATEGORY_EMOJI[category]}</span>
          <span>{category.replace('_', ' ')}</span>
          <span className="opacity-60">•</span>
          <span>{severity}</span>
        </div>
        <span className="text-xs opacity-50 flex-shrink-0">
          {filePath}{lineStart ? `:${lineStart}` : ''}
        </span>
      </div>

      <p className="text-sm leading-relaxed whitespace-pre-wrap mt-1">{body}</p>

      {suggestedFix && (
        <pre className="mt-3 p-3 bg-black/40 rounded text-xs overflow-x-auto text-green-300">
          {suggestedFix}
        </pre>
      )}

      {suggestedDiff && !suggestedFix && (
        <pre className="mt-3 p-3 bg-black/40 rounded text-xs overflow-x-auto font-mono">
          {suggestedDiff.split('\n').map((line, i) => (
            <span
              key={i}
              className={clsx('block', {
                'text-green-400': line.startsWith('+'),
                'text-red-400': line.startsWith('-'),
                'text-gray-500': line.startsWith('@@'),
              })}
            >
              {line}
            </span>
          ))}
        </pre>
      )}

      {!feedback && (onAccept || onReject) && (
        <div className="flex gap-2 mt-3">
          {onAccept && (
            <button
              onClick={onAccept}
              className="px-3 py-1 text-xs rounded bg-green-700 hover:bg-green-600 text-white transition-colors"
            >
              Accept
            </button>
          )}
          {onReject && (
            <button
              onClick={onReject}
              className="px-3 py-1 text-xs rounded bg-red-800 hover:bg-red-700 text-white transition-colors"
            >
              Reject
            </button>
          )}
        </div>
      )}
      {feedback && (
        <div className="mt-2 text-xs opacity-60">
          Feedback: <span className="font-semibold">{feedback}</span>
        </div>
      )}
    </div>
  )
}
