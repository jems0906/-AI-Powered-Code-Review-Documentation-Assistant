import type { SeverityLevel } from '../types/api'
import clsx from 'clsx'

interface Props {
  score: number | null
}

export default function QualityScoreBadge({ score }: Props) {
  if (score === null || score === undefined) return <span className="text-gray-600 text-sm">—</span>

  const color =
    score >= 8 ? 'text-green-400' :
    score >= 5 ? 'text-yellow-400' :
    'text-red-400'

  return (
    <span className={clsx('text-lg font-bold tabular-nums', color)}>
      {score.toFixed(1)}<span className="text-xs text-gray-500">/10</span>
    </span>
  )
}

const SEVERITY_DOT: Record<SeverityLevel, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-blue-500',
  info: 'bg-gray-500',
}

export function SeverityDot({ severity }: { severity: SeverityLevel }) {
  return <span className={clsx('inline-block w-2 h-2 rounded-full', SEVERITY_DOT[severity])} />
}
