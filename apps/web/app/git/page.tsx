'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  listProjects,
  getGitStatus,
  getGitLog,
  getGitProvenance,
  rollbackGit,
  type GitProvenanceResponse,
  type ProjectResponse,
} from '@/lib/api'
import ConfirmModal from '@/components/confirm-modal'
import Pagination from '@/components/pagination'

export default function GitHistoryPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const urlProject = searchParams.get('project') || ''

  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [selectedProject, setSelectedProject] = useState(urlProject)
  const [gitStatus, setGitStatusState] = useState<any>(null)
  const [commits, setCommits] = useState<any[]>([])
  const [provenance, setProvenance] = useState<GitProvenanceResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [rollingBack, setRollingBack] = useState<string | null>(null)
  const [rollbackMsg, setRollbackMsg] = useState<string | null>(null)
  const [rollbackTarget, setRollbackTarget] = useState<any>(null)

  // Pagination (client-side)
  const [perPage, setPerPage] = useState(10)
  const [page, setPage] = useState(1)

  // Sync project to URL
  useEffect(() => {
    if (selectedProject === urlProject) return
    const params = new URLSearchParams(searchParams.toString())
    if (selectedProject) {
      params.set('project', selectedProject)
    } else {
      params.delete('project')
    }
    const qs = params.toString()
    router.replace(`/git${qs ? `?${qs}` : ''}`, { scroll: false })
  }, [selectedProject])

  useEffect(() => {
    listProjects()
      .then((data) => {
        setProjects(data)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    setPage(1)
    getGitStatus(selectedProject)
      .then((data) => setGitStatusState(data))
      .catch(console.error)
    getGitLog(selectedProject)
      .then((data) => setCommits(Array.isArray(data) ? data : []))
      .catch(() => setCommits([]))
    getGitProvenance(selectedProject)
      .then(setProvenance)
      .catch(() => setProvenance([]))
  }, [selectedProject])

  const handleRollback = (commit: any) => {
    if (!selectedProject) return
    setRollbackTarget(commit)
  }

  const confirmRollback = async () => {
    if (!selectedProject || !rollbackTarget) return
    const commit = rollbackTarget
    setRollbackTarget(null)
    setRollingBack(commit.hash)
    setRollbackMsg(null)
    try {
      const res = await rollbackGit(selectedProject, commit.hash)
      setRollbackMsg(`✓ ${res.detail}`)
      const [status, log] = await Promise.all([
        getGitStatus(selectedProject),
        getGitLog(selectedProject),
      ])
      setGitStatusState(status)
      setCommits(Array.isArray(log) ? log : [])
    } catch (err) {
      setRollbackMsg(
        `✗ Rollback failed: ${err instanceof Error ? err.message : 'unknown error'}`,
      )
    } finally {
      setRollingBack(null)
    }
  }

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
          <option value="">— None —</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {/* Current Branch Status */}
      {gitStatus && gitStatus.status === 'offline' && (
        <div className="card-af p-5 mb-[18px] bg-amber-500/10 border-amber-500/30 flex items-start gap-3">
          <span className="text-lg">🖥</span>
          <div>
            <div className="text-xs font-bold text-foreground">
              Local Agent Workstation Offline
            </div>
            <p className="text-xs text-muted mt-0.5 m-0">
              {gitStatus.detail ||
                'Connect your workstation to view live git history.'}{' '}
              <Link href="/devices" className="text-primary hover:underline font-bold">
                Go to Devices
              </Link>
            </p>
          </div>
        </div>
      )}

      {gitStatus && gitStatus.status !== 'offline' && (
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

      {rollbackMsg && (
        <div
          className={`card-af p-3 mb-[18px] text-xs font-medium ${
            rollbackMsg.startsWith('✗')
              ? 'border-red-500/30 bg-red-500/10 text-red-500'
              : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
          }`}
        >
          {rollbackMsg}
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
          (() => {
            const totalPages = Math.max(1, Math.ceil(commits.length / perPage))
            const safePage = Math.min(page, totalPages)
            const pagedCommits = commits.slice(
              (safePage - 1) * perPage,
              safePage * perPage,
            )
            return (
              <>
                {pagedCommits.map((commit: any) => {
                  const record = provenance.find(
                    (item) =>
                      item.commit_hash === commit.hash ||
                      commit.hash?.startsWith(item.commit_hash) ||
                      item.commit_hash?.startsWith(commit.hash),
                  )
                  return (
                    <div
                      key={commit.hash}
                      className="card-af p-4 flex items-start gap-3"
                    >
                    <div className="w-9 h-9 rounded-[9px] bg-primary/10 text-primary grid place-items-center flex-shrink-0 text-sm font-bold">
                      ⑂
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-sm font-bold text-foreground m-0">
                          {commit.message}
                        </h4>
                        {record?.ai_generated && (
                          <span className="rounded border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-[9px] font-bold text-primary">
                            AI GENERATED
                          </span>
                        )}
                        {record && (
                          <span className="rounded border border-border px-1.5 py-0.5 text-[9px] font-bold text-muted">
                            {record.verification_status}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted mt-1 m-0">
                        {commit.author}
                        {commit.files != null && commit.files > 0
                          ? ` · ${commit.files} files`
                          : ''}
                      </p>
                      {record && (
                        <details className="mt-2 text-[10px] text-muted">
                          <summary className="cursor-pointer font-semibold text-primary">
                            Provenance · {record.model_name || 'model unavailable'}
                          </summary>
                          <div className="mt-2 rounded border border-border bg-surface-secondary p-2 font-mono break-all space-y-1">
                            <div>instruction: {record.instruction_id}</div>
                            <div>digest: sha256:{record.provenance_digest}</div>
                            <div>prompt: sha256:{record.prompt_digest}</div>
                            <div>files: {record.changed_files.join(', ') || 'none recorded'}</div>
                          </div>
                        </details>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-sm font-mono font-bold text-foreground">
                        {(commit.hash || '').slice(0, 7)}
                      </div>
                      <div className="text-xs text-muted mt-0.5">
                        {commit.time
                          ? new Date(commit.time).toLocaleDateString()
                          : ''}
                      </div>
                      <button
                        onClick={() => handleRollback(commit)}
                        disabled={rollingBack === commit.hash}
                        className="mt-2 text-xs font-bold text-red-500 hover:underline disabled:opacity-50"
                      >
                        {rollingBack === commit.hash
                          ? 'Rolling back...'
                          : '⏪ Rollback'}
                      </button>
                    </div>
                    </div>
                  )
                })}
                <Pagination
                  storageKey="git-perpage"
                  currentPage={safePage}
                  totalPages={totalPages}
                  totalItems={commits.length}
                  perPage={perPage}
                  onPageChange={(p) => setPage(p)}
                  onPerPageChange={(pp) => {
                    setPerPage(pp)
                    setPage(1)
                  }}
                />
              </>
            )
          })()
        )}
      </div>

      {/* Durable pipeline provenance remains visible if the workstation is offline. */}
      <div className="card-af p-6 mt-[18px]">
        <h3 className="text-sm font-bold text-foreground m-0 mb-2">
          AI Change Provenance
        </h3>
        <p className="text-xs text-muted m-0">
          {provenance.length > 0
            ? `${provenance.length} attributable AI commit record${provenance.length === 1 ? '' : 's'} stored.`
            : 'Agent-generated commits are recorded with prompt hashes, model identity, and tamper-evident Git trailers.'}
        </p>
      </div>
      <ConfirmModal
        open={!!rollbackTarget}
        title="Rollback Workspace"
        message={`Roll back workspace to commit ${String(rollbackTarget?.hash || '').slice(0, 8)}? This is a HARD reset — all uncommitted changes will be lost.`}
        confirmLabel="Rollback"
        variant="danger"
        onConfirm={confirmRollback}
        onCancel={() => setRollbackTarget(null)}
      />
    </div>
  )
}
