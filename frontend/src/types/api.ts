// Central API types matching backend schemas

export type ReviewStatus = 'pending' | 'in_progress' | 'completed' | 'failed'
export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type CommentCategory = 'security' | 'performance' | 'best_practice' | 'edge_case' | 'documentation' | 'style'
export type FeedbackType = 'accepted' | 'rejected' | 'partial'
export type ReviewProfile = 'pedantic' | 'balanced' | 'relaxed'

export interface ReviewComment {
  id: string
  file_path: string
  line_start: number | null
  line_end: number | null
  category: CommentCategory
  severity: SeverityLevel
  body: string
  suggested_fix: string | null
  suggested_diff: string | null
  feedback: FeedbackType | null
  created_at: string
}

export interface Review {
  id: string
  repo_full_name: string
  pr_number: number
  pr_title: string | null
  pr_author: string | null
  pr_url: string | null
  status: ReviewStatus
  review_profile: ReviewProfile
  quality_score: number | null
  comment_count: number
  accepted_count: number
  rejected_count: number
  summary: string | null
  generated_docs: string | null
  generated_tests: string | null
  ai_provider: string | null
  created_at: string
  completed_at: string | null
  comments: ReviewComment[]
}

export interface ReviewListResponse {
  reviews: Review[]
  total: number
}

export interface MetricsSummary {
  total_reviews: number
  total_comments: number
  acceptance_rate: number
  avg_quality_score: number
}

export interface TrendPoint {
  date: string
  avg_quality: number
  count: number
}

export interface EngineerMetric {
  engineer: string
  total_reviews: number
  avg_quality_score: number
  recent_30d_quality: number
  previous_30d_quality: number
  quality_delta: number
  acceptance_rate: number
}

export interface FeedbackLearningSignal {
  category: string
  accepted: number
  rejected: number
  acceptance_rate: number
}

export interface Repository {
  id: number
  github_id: number
  full_name: string
  owner: string
  name: string
  default_branch: string
  language: string | null
  review_profile: ReviewProfile
  active_profile_version: number | null
  created_at: string
}

export interface RepositoryReviewProfileVersion {
  id: number
  repository_id: number
  version_number: number
  review_profile: ReviewProfile
  prompt_overrides: string | null
  learning_snapshot: Record<string, unknown> | null
  is_active: boolean
  created_at: string
}
