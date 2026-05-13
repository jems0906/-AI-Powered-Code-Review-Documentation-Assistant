import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  activateRepositoryProfileVersion,
  fetchRepositories,
  fetchRepositoryProfileVersions,
  updateRepositoryReviewProfile,
} from '../api/client'
import type { ReviewProfile } from '../types/api'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null)

  const { data: repositories } = useQuery({
    queryKey: ['repositories'],
    queryFn: fetchRepositories,
  })

  const activeRepoId = useMemo(() => {
    if (!repositories?.length) return null
    if (selectedRepoId === null) return repositories[0].id
    return selectedRepoId
  }, [repositories, selectedRepoId])

  const { data: profileVersions } = useQuery({
    queryKey: ['repository-profile-versions', activeRepoId],
    queryFn: () => fetchRepositoryProfileVersions(activeRepoId ?? 0),
    enabled: activeRepoId !== null,
  })

  const selectedRepo = useMemo(() => {
    if (!repositories?.length) return null
    if (selectedRepoId === null) return repositories[0]
    return repositories.find((r) => r.id === selectedRepoId) ?? repositories[0]
  }, [repositories, selectedRepoId])

  const updateProfileMutation = useMutation({
    mutationFn: ({ repoId, profile }: { repoId: number; profile: ReviewProfile }) =>
      updateRepositoryReviewProfile(repoId, profile),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
    },
  })

  const activateVersionMutation = useMutation({
    mutationFn: ({ repoId, versionId }: { repoId: number; versionId: number }) =>
      activateRepositoryProfileVersion(repoId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      queryClient.invalidateQueries({ queryKey: ['repository-profile-versions', activeRepoId] })
    },
  })

  const currentProfile: ReviewProfile = selectedRepo?.review_profile ?? 'balanced'

  const handleProfileChange = (profile: ReviewProfile) => {
    if (!selectedRepo) return
    updateProfileMutation.mutate({ repoId: selectedRepo.id, profile })
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="font-semibold mb-1">Repository Scope</h2>
        <p className="text-sm text-gray-500 mb-4">
          Select a repository and persist its default review strictness profile.
        </p>
        {repositories?.length ? (
          <>
            <label htmlFor="repository-select" className="sr-only">Select repository</label>
            <select
              id="repository-select"
              value={selectedRepo?.id ?? ''}
              onChange={(e) => setSelectedRepoId(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 text-sm rounded-lg px-3 py-2 text-gray-200"
            >
              {repositories.map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.full_name}
                </option>
              ))}
            </select>
          </>
        ) : (
          <p className="text-sm text-gray-500">No repositories found yet. Trigger a review first.</p>
        )}
      </div>

      {/* Review Profile */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="font-semibold mb-1">Default Review Profile</h2>
        <p className="text-sm text-gray-500 mb-4">
          Controls how strict the AI reviewer is. Can be overridden per repository.
        </p>
        <div className="grid grid-cols-3 gap-3">
          {(['pedantic', 'balanced', 'relaxed'] as const).map((p) => (
            <button
              key={p}
              onClick={() => handleProfileChange(p)}
              disabled={!selectedRepo || updateProfileMutation.isPending}
              className={`px-4 py-3 rounded-lg text-sm font-medium transition-colors border ${
                currentProfile === p
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-gray-800 border-gray-700 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <div className="capitalize font-semibold">{p}</div>
              <div className="text-xs opacity-70 mt-1">
                {p === 'pedantic' && 'Flag everything'}
                {p === 'balanced' && 'Real issues only'}
                {p === 'relaxed' && 'Critical only'}
              </div>
            </button>
          ))}
        </div>
        {updateProfileMutation.isPending && (
          <p className="text-xs text-gray-500 mt-3">Saving profile...</p>
        )}
        {updateProfileMutation.isSuccess && (
          <p className="text-xs text-green-400 mt-3">Profile saved.</p>
        )}
        {updateProfileMutation.isError && (
          <p className="text-xs text-red-400 mt-3">Could not save profile.</p>
        )}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="font-semibold mb-1">Review Profile Versions</h2>
        <p className="text-sm text-gray-500 mb-4">
          Profile changes are versioned. Activate any previous version to roll back behavior.
        </p>
        <div className="space-y-2">
          {(profileVersions ?? []).map((version) => (
            <div key={version.id} className="flex items-center justify-between gap-3 rounded-lg border border-gray-800 bg-gray-950 px-3 py-2">
              <div>
                <p className="text-sm text-gray-200">
                  v{version.version_number} • <span className="capitalize">{version.review_profile}</span>
                </p>
                <p className="text-xs text-gray-500">{new Date(version.created_at).toLocaleString()}</p>
              </div>
              {version.is_active ? (
                <span className="text-xs px-2 py-1 rounded bg-green-700/30 border border-green-600/40 text-green-300">
                  Active
                </span>
              ) : (
                <button
                  onClick={() => selectedRepo && activateVersionMutation.mutate({ repoId: selectedRepo.id, versionId: version.id })}
                  className="px-3 py-1 text-xs rounded bg-gray-800 border border-gray-700 hover:bg-gray-700"
                >
                  Activate
                </button>
              )}
            </div>
          ))}
          {!(profileVersions?.length) && (
            <p className="text-xs text-gray-500">No profile versions yet.</p>
          )}
        </div>
      </div>

      {/* Integration status */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="font-semibold mb-4">Integrations</h2>
        <div className="space-y-3 text-sm">
          <IntegrationRow name="GitHub Webhook" status="Configure in GitHub → Settings → Webhooks" />
          <IntegrationRow name="GitLab Webhook" status="Configure Merge Request Hook with X-Gitlab-Token secret" />
          <IntegrationRow name="Slack Notifications" status="Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID in .env" />
          <IntegrationRow name="OpenAI" status="Set OPENAI_API_KEY in .env" />
          <IntegrationRow name="Anthropic Claude" status="Set ANTHROPIC_API_KEY in .env" />
        </div>
      </div>

      {/* Webhook info */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="font-semibold mb-2">Webhook Endpoint</h2>
        <code className="text-xs bg-gray-800 px-3 py-2 rounded block text-indigo-300">
          POST /api/webhooks/github
        </code>
        <code className="text-xs bg-gray-800 px-3 py-2 rounded block text-indigo-300 mt-2">
          POST /api/webhooks/gitlab
        </code>
        <p className="text-xs text-gray-500 mt-2">
          Point your GitHub webhook here. Select <strong>Pull requests</strong> events.
          Use the same secret as <code>GITHUB_WEBHOOK_SECRET</code>.
        </p>
      </div>
    </div>
  )
}

function IntegrationRow({ name, status }: { name: string; status: string }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="font-medium text-gray-200">{name}</span>
      <span className="text-gray-500 text-right max-w-xs">{status}</span>
    </div>
  )
}
