'use client'

import React, { useEffect, useState } from 'react'
import {
  listProjects,
  getGitStatus,
  type ProjectResponse,
} from '@/lib/api'

interface GitCommit {
  hash: string
  message: string
  agent: string
  time: string
  files: number
  branch: string
}

export default function GitHistoryPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [gitStatus, setGitStatusState] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listProjects()
      .then((data) => {
        setProjects(data)
        if (data.length > 0) {
          setSelectedProject(data[0].id)
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    getGitStatus(selectedProject)
      .then((data) => setGitStatusState(data))
      .catch(console.error)
  }, [selectedProject])

  // Mock commits for now — real endpoint coming
  const commits: GitCommit[] = gitStatus?.commits || []

  return (
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            Git History
          </h2>
          <p className="text-muted text-sm m-0">
            Every agent stage is attributable, reviewable, and reversible.
          </p>
        </div>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="input-af !w-auto"
          disabled={loading}
        >
          {loading && <option>Loading...</option>}
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {/* Current Branch Status */}
      {gitStatus && (
        <div className="card-af p-5 mb-[18px]">
          <div className="flex items-center gap-4 text-sm">
            <div>
              <span className="text-muted">Branch:</span>{' '}
              <code className="text-primary font-mono font-bold">
                {gitStatus.branch || gitStatus.current_branch || 'main'}
              </code>
            </div>
            <div>
              <span className="text-muted">Status:</span>{' '}
              <span
                className={
                  gitStatus.is_dirty || gitStatus.dirty
                    ? 'text-amber-500 font-bold'
                    : 'text-emerald-600 dark:text-emerald-400 font-bold'
                }
              >
                {gitStatus.is_dirty || gitStatus.dirty
                  ? 'Uncommitted changes'
                  : 'Clean'}
              </span>
            </div>
            {gitStatus.modified_files?.length > 0 && (
              <div className="text-xs text-muted">
                Modified: {gitStatus.modified_files.length} | Untracked:{' '}
                {gitStatus.untracked_files?.length || 0}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Commits List */}
      <div className="space-y-3">
        {commits.length === 0 ? (
          <div className="card-af p-10 text-center">
            <p className="text-sm text-muted">
              {gitStatus
                ? 'No commits found for this branch.'
                : 'Select a project to view git history.'}
            </p>
          </div>
        ) : (
          commits.map((commit) => (
            <div
              key={commit.hash}
              className="card-af p-4 flex items-start gap-3"
            >
              <div className="w-9 h-9 rounded-[9px] bg-primary/10 text-primary grid place-items-center flex-shrink-0 text-sm font-bold">
                ⑂
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-foreground m-0">
                  {commit.message}
                </h4>
                <p className="text-xs text-muted mt-1 m-0">
                  {commit.agent} · {commit.files} files changed · branch{' '}
                  {commit.branch}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-xs font-mono font-bold text-foreground">
                  {commit.hash.slice(0, 7)}
                </div>
                <div className="text-[10px] text-muted mt-0.5">{commit.time}</div>
                <button className="btn-secondary-af text-[10px] !px-2 !py-1 mt-1">
                  Rollback
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Agent Git Commits (from pipeline) */}
      <div className="card-af p-6 mt-[18px]">
        <h3 className="text-sm font-bold text-foreground m-0 mb-2">
          Git History by Agent Pipeline
        </h3>
        <p className="text-xs text-muted m-0">
          Agent-generated commits appear here after each pipeline run. Run an
          instruction from the workspace to see commits.
        </p>
      </div>
    </div>
  )
}
