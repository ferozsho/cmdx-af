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
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Git History</h1>
          <p className="text-sm text-gray-400 mt-1">
            Every agent stage is attributable, reviewable, and reversible.
          </p>
        </div>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="bg-[#111827] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
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
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-4 text-sm">
            <div>
              <span className="text-gray-400">Branch:</span>{' '}
              <code className="text-emerald-400 font-mono">
                {gitStatus.branch || gitStatus.current_branch || 'main'}
              </code>
            </div>
            <div>
              <span className="text-gray-400">Status:</span>{' '}
              <span
                className={
                  gitStatus.is_dirty || gitStatus.dirty
                    ? 'text-amber-400'
                    : 'text-emerald-400'
                }
              >
                {gitStatus.is_dirty || gitStatus.dirty
                  ? 'Uncommitted changes'
                  : 'Clean'}
              </span>
            </div>
            {gitStatus.modified_files?.length > 0 && (
              <div className="text-xs text-gray-500">
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
          <div className="bg-[#111827] border border-gray-800 rounded-xl p-10 text-center">
            <p className="text-sm text-gray-500">
              {gitStatus
                ? 'No commits found for this branch.'
                : 'Select a project to view git history.'}
            </p>
          </div>
        ) : (
          commits.map((commit) => (
            <div
              key={commit.hash}
              className="bg-[#111827] border border-gray-800 rounded-xl p-5 flex items-start gap-4"
            >
              <div className="w-10 h-10 rounded-lg bg-purple-950/50 border border-purple-800 flex items-center justify-center flex-shrink-0">
                <span className="text-purple-300 text-sm">⑂</span>
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-white">
                  {commit.message}
                </h4>
                <p className="text-xs text-gray-400 mt-1">
                  {commit.agent} · {commit.files} files changed · branch{' '}
                  {commit.branch}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-xs font-mono font-bold text-gray-300">
                  {commit.hash.slice(0, 7)}
                </div>
                <div className="text-[10px] text-gray-500 mt-1">{commit.time}</div>
                <button className="text-[10px] text-red-400 hover:underline mt-1">
                  Rollback
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Agent Git Commits (from pipeline) */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-3">
          Git History by Agent Pipeline
        </h3>
        <p className="text-xs text-gray-500">
          Agent-generated commits appear here after each pipeline run. Run an
          instruction from the workspace to see commits.
        </p>
      </div>
    </div>
  )
}
