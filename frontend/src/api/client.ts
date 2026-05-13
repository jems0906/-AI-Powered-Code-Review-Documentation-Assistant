import axios from 'axios'
import type {
  ReviewListResponse,
  Review,
  MetricsSummary,
  TrendPoint,
  Repository,
  FeedbackType,
  EngineerMetric,
  FeedbackLearningSignal,
  RepositoryReviewProfileVersion,
  ReviewProfile,
} from '../types/api'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export async function fetchReviews(params?: {
  repo_full_name?: string
  status?: string
  limit?: number
  offset?: number
}): Promise<ReviewListResponse> {
  const { data } = await api.get<ReviewListResponse>('/reviews/', { params })
  return data
}

export async function fetchReview(id: string): Promise<Review> {
  const { data } = await api.get<Review>(`/reviews/${id}`)
  return data
}

export async function triggerReview(payload: {
  repo_full_name: string
  pr_number: number
  review_profile?: string
}): Promise<Review> {
  const { data } = await api.post<Review>('/reviews/trigger', payload)
  return data
}

export async function submitFeedback(
  commentId: string,
  feedback: FeedbackType,
  note?: string,
): Promise<void> {
  await api.post(`/reviews/comments/${commentId}/feedback`, { feedback, note })
}

export async function fetchMetricsSummary(repo?: string): Promise<MetricsSummary> {
  const { data } = await api.get<MetricsSummary>('/metrics/summary', {
    params: repo ? { repo_full_name: repo } : {},
  })
  return data
}

export async function fetchTrends(repo?: string, days = 30): Promise<TrendPoint[]> {
  const { data } = await api.get<TrendPoint[]>('/metrics/trends', {
    params: { days, ...(repo ? { repo_full_name: repo } : {}) },
  })
  return data
}

export async function fetchEngineerMetrics(repo?: string): Promise<EngineerMetric[]> {
  const { data } = await api.get<EngineerMetric[]>('/metrics/engineers', {
    params: repo ? { repo_full_name: repo } : {},
  })
  return data
}

export async function fetchLearningSignals(repo?: string): Promise<FeedbackLearningSignal[]> {
  const { data } = await api.get<FeedbackLearningSignal[]>('/metrics/learning-feedback', {
    params: repo ? { repo_full_name: repo } : {},
  })
  return data
}

// ── Repositories ──────────────────────────────────────────
export async function fetchRepositories(): Promise<Repository[]> {
  const { data } = await api.get<Repository[]>('/repositories/')
  return data
}

export async function updateRepositoryReviewProfile(
  repoId: number,
  reviewProfile: ReviewProfile,
): Promise<Repository> {
  const { data } = await api.patch<Repository>(`/repositories/${repoId}/review-profile`, {
    review_profile: reviewProfile,
  })
  return data
}

export async function fetchRepositoryProfileVersions(
  repoId: number,
): Promise<RepositoryReviewProfileVersion[]> {
  const { data } = await api.get<RepositoryReviewProfileVersion[]>(`/repositories/${repoId}/review-profiles`)
  return data
}

export async function createRepositoryProfileVersion(
  repoId: number,
  reviewProfile: ReviewProfile,
  promptOverrides?: string,
): Promise<RepositoryReviewProfileVersion> {
  const { data } = await api.post<RepositoryReviewProfileVersion>(`/repositories/${repoId}/review-profiles`, {
    review_profile: reviewProfile,
    prompt_overrides: promptOverrides || null,
  })
  return data
}

export async function activateRepositoryProfileVersion(
  repoId: number,
  versionId: number,
): Promise<Repository> {
  const { data } = await api.post<Repository>(`/repositories/${repoId}/review-profiles/${versionId}/activate`)
  return data
}
