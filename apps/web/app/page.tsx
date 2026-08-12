'use client'

import React, { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import {
  listProjects,
  listDevices,
  updateProject,
  deleteProject,
  getProjectStats,
  getAgentMetrics,
  validateProjectPath,
  reindexRag,
  getReindexStatus,
  getRagStats,
  type ProjectResponse,
  type DeviceResponse,
  type ValidatePathResponse,
  type ReindexJob,
  type RagStats,
} from '@/lib/api'

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [devices, setDevices] = useState<DeviceResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState({ agent_runs: 0, tests_passed: 0 })
  const [llmStats, setLlmStats] = useState({ calls: 0, total_tokens: 0, cost: 0 })

  const TECH_OPTIONS = [
    'Python', 'FastAPI', 'Django', 'Next.js', 'React', 'Node.js',
    'TypeScript', 'PHP', 'Moodle', 'PostgreSQL', 'MySQL', 'MongoDB',
    'Redis', 'Docker',
  ]

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [editTarget, setEditTarget] = useState<'LOCAL' | 'CLOUD'>('LOCAL')
  const [editLocalPath, setEditLocalPath] = useState('')
  const [editTechStack, setEditTechStack] = useState<string[]>([])
  const [editSaving, setEditSaving] = useState(false)
  const [editSaveError, setEditSaveError] = useState<string | null>(null)

  // Edit modal: folder validation state
  const [editChecking, setEditChecking] = useState(false)
  const [editPathResult, setEditPathResult] =
    useState<ValidatePathResponse | null>(null)
  const [editPathError, setEditPathError] = useState<string | null>(null)

  // Edit modal: background RAG indexing state
  const [reindexState, setReindexState] = useState<
    'idle' | 'running' | 'done' | 'failed'
  >('idle')
  const [reindexJob, setReindexJob] = useState<ReindexJob | null>(null)
  const [reindexError, setReindexError] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  // Delete state
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  // Live RAG index progress per project (for background-indexing badges)
  const [ragIndex, setRagIndex] = useState<Record<string, RagStats>>({})

  useEffect(() => {
    async function load() {
      try {
        const [projData, devData, statsData, metricsData] = await Promise.all([
          listProjects(),
          listDevices(),
          getProjectStats().catch(() => ({ agent_runs: 0, tests_passed: 0 })),
          getAgentMetrics().catch(() => null),
        ])
        setProjects(projData)
        setDevices(devData)
        setStats(statsData)
        if (metricsData?.llm_usage) {
          setLlmStats({
            calls: metricsData.llm_usage.calls || 0,
            total_tokens: metricsData.llm_usage.total_tokens || 0,
            cost: metricsData.llm_usage.cost || 0,
          })
        }
      } catch (err) {
        console.error('Failed to load dashboard data:', err)
        setError('Could not load dashboard data. Is the API running?')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Poll live RAG progress for local-path projects so cards show when the
  // background index is running (startup / watcher / explicit re-index)
  useEffect(() => {
    if (loading) return
    const local = projects.filter((p) => p.local_path)
    if (local.length === 0) return
    let timer: number | null = null
    const tick = async () => {
      const updates: Record<string, RagStats> = {}
      await Promise.all(
        local.map(async (p) => {
          try {
            const s = await getRagStats(p.id)
            updates[p.id] = s
          } catch {
            // ignore offline / transient errors
          }
        }),
      )
      setRagIndex((prev) => ({ ...prev, ...updates }))
    }
    tick()
    timer = window.setInterval(tick, 5000)
    return () => {
      if (timer) window.clearInterval(timer)
    }
  }, [loading, projects])

  const handleEdit = (project: ProjectResponse) => {
    setEditingId(project.id)
    setEditName(project.name)
    setEditDesc(project.description || '')
    setEditTarget(
      project.execution_target === 'CLOUD' ? 'CLOUD' : 'LOCAL',
    )
    setEditLocalPath(project.local_path || '')
    const stack = project.tech_stack
    setEditTechStack(
      stack && typeof stack === 'object'
        ? Object.keys(stack).filter((k) => stack[k])
        : [],
    )
    setDeletingId(null)
    setDeleteConfirm(false)
    setEditSaveError(null)
    setEditPathResult(null)
    setEditPathError(null)
    setReindexState('idle')
    setReindexJob(null)
    setReindexError(null)
  }

  const handleCheckEditFolder = async () => {
    if (!editLocalPath.trim()) return
    setEditChecking(true)
    setEditPathResult(null)
    setEditPathError(null)
    try {
      const result = await validateProjectPath(editLocalPath.trim())
      setEditPathResult(result)
      // Auto-populate tech stack from detection
      if (result.detected_stack.length > 0) {
        setEditTechStack((prev) => {
          const merged = new Set([...prev, ...result.detected_stack])
          return Array.from(merged)
        })
      }
    } catch (err) {
      setEditPathError(
        err instanceof Error ? err.message : 'Failed to validate folder',
      )
    } finally {
      setEditChecking(false)
    }
  }

  const pollReindex = (projectId: string) => {
    if (pollRef.current) window.clearInterval(pollRef.current)
    pollRef.current = window.setInterval(async () => {
      try {
        const res = await getReindexStatus(projectId)
        if (res.job) setReindexJob(res.job)
        if (res.status === 'done') {
          if (pollRef.current) window.clearInterval(pollRef.current)
          pollRef.current = null
          setReindexState('done')
          window.setTimeout(() => {
            setEditingId(null)
            setReindexState('idle')
            setReindexJob(null)
          }, 1600)
        } else if (res.status === 'failed') {
          if (pollRef.current) window.clearInterval(pollRef.current)
          pollRef.current = null
          setReindexState('failed')
          setReindexError(res.job?.error || 'Indexing failed.')
        }
      } catch {
        // transient poll error — keep polling
      }
    }, 1500)
  }

  const startReindex = async (projectId: string) => {
    setReindexState('running')
    setReindexJob(null)
    setReindexError(null)
    try {
      await reindexRag(projectId)
      pollReindex(projectId)
    } catch (err) {
      setReindexState('failed')
      setReindexError(
        err instanceof Error ? err.message : 'Failed to start indexing',
      )
    }
  }

  const closeEditModal = () => {
    if (pollRef.current) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
    setEditingId(null)
    setEditSaving(false)
    setEditSaveError(null)
    setEditPathResult(null)
    setEditPathError(null)
    setReindexState('idle')
    setReindexJob(null)
    setReindexError(null)
  }

  const handleSaveEdit = async () => {
    if (!editingId || !editName.trim()) return
    setEditSaving(true)
    setEditSaveError(null)
    try {
      const saved = await updateProject(editingId, {
        name: editName.trim(),
        description: editDesc.trim(),
        execution_target: editTarget,
        local_path: editLocalPath.trim() || undefined,
        tech_stack: editTechStack,
      })
      setProjects((prev) =>
        prev.map((p) =>
          p.id === editingId
            ? {
                ...p,
                name: saved.name,
                description: saved.description,
                execution_target: saved.execution_target,
                local_path: saved.local_path,
              }
            : p,
        ),
      )
      setEditSaving(false)
      // Kick off background RAG indexing (click-and-forget)
      if (editTarget === 'LOCAL' && editLocalPath.trim()) {
        await startReindex(editingId)
      } else {
        closeEditModal()
      }
    } catch (err) {
      console.error('Failed to update project:', err)
      setEditSaveError(
        err instanceof Error ? err.message : 'Failed to update project',
      )
      setEditSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deletingId) return
    try {
      await deleteProject(deletingId)
      setProjects((prev) => prev.filter((p) => p.id !== deletingId))
      setDeletingId(null)
      setDeleteConfirm(false)
    } catch (err) {
      console.error('Failed to delete project:', err)
    }
  }

  const startDelete = (id: string) => {
    setDeletingId(id)
    setDeleteConfirm(false)
    setEditingId(null)
  }

  const onlineDevices = devices.filter((d) => d.status === 'online').length

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-surface-secondary rounded w-64 border border-border" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="card-af p-5 h-28" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card-af p-6 text-center border-red-500/30 bg-red-500/10 text-foreground">
        <p className="text-red-500 font-medium text-sm">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 text-sm text-red-400 hover:underline"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            Projects
          </h2>
          <p className="text-muted text-sm m-0">
            Monitor agentic coding projects and recent pipeline activity.
          </p>
        </div>
        <Link
          href="/projects/new"
          className="btn-primary-af text-sm inline-block"
        >
          ＋ Create Project
        </Link>
      </div>

      {/* KPI Cards — matches prototype .stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-[18px] mb-[22px]">
        <StatCard
          label="Projects"
          value={projects.length}
          trend={`${projects.filter((p) => p.execution_target === 'LOCAL').length} Local`}
          icon="▦"
        />
        <StatCard
          label="Devices"
          value={devices.length}
          trend={`${onlineDevices} Online`}
          icon="◉"
        />
        <StatCard
          label="Agent Runs"
          value={stats.agent_runs}
          trend="Total pipeline runs"
          icon="⚡"
        />
        <StatCard
          label="Tests Passed"
          value={stats.tests_passed}
          trend="Across all projects"
          icon="✓"
        />
        <StatCard
          label="LLM Calls"
          value={llmStats.calls.toLocaleString()}
          trend="Total API requests"
          icon="🤖"
        />
        <StatCard
          label="Tokens"
          value={llmStats.total_tokens.toLocaleString()}
          trend="Total tokens used"
          icon="⬡"
        />
        <StatCard
          label="Est. Cost"
          value={`$${llmStats.cost.toFixed(4)}`}
          trend="All providers"
          icon="💰"
        />
      </div>

      {/* Projects Grid — matches prototype .projects-grid (3 columns) */}
      {projects.length === 0 ? (
        <div className="card-af p-10 text-center">
          <p className="text-muted text-sm">No projects yet.</p>
          <Link
            href="/projects/new"
            className="text-primary text-sm font-medium hover:underline mt-2 inline-block"
          >
            Create your first project →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-[18px]">
          {projects.map((project) => {
            // Device presence is not enough: a device may still be marked
            // online while the project workspace cannot answer tool requests.
            // `ragIndex` is populated by the project's live RAG-status call,
            // so only present a workspace as connected after that call has
            // confirmed it is reachable.
            const isOnline = ragIndex[project.id]?.online === true
            return (
            <div
              key={project.id}
              className={`card-af p-5 block transition-all ${
                isOnline ? 'card-af-hover' : 'opacity-60 grayscale-[30%]'
              }`}
            >
              {/* Header row: icon + execution badge + action buttons.
                  Buttons are in-flow (not absolute) so they never overlap
                  the badge, and they live outside the Link below. */}
              <div className="flex items-start justify-between gap-2 mb-0">
                <div className="w-11 h-11 rounded-[12px] bg-primary/10 text-primary grid place-items-center text-[21px] flex-shrink-0">
                  ⚡
                </div>
                <div className="flex items-center gap-[8px] flex-shrink-0">
                  <span className={`inline-flex items-center gap-[6px] rounded-full py-[5px] px-[10px] text-xs font-bold ${
                    isOnline
                      ? 'bg-primary/15 text-primary'
                      : 'bg-red-500/15 text-red-500'
                  }`}>
                    ● {isOnline ? project.execution_target : 'OFFLINE'}
                  </span>
                  <div className="flex gap-1.5">
                    <button
                      type="button"
                      onClick={(e) => { e.preventDefault(); handleEdit(project) }}
                      className="btn-secondary-af !p-1.5 !text-xs !rounded-lg"
                      title="Edit project"
                      aria-label="Edit project"
                    >
                      ✏️
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.preventDefault(); startDelete(project.id) }}
                      className="btn-secondary-af !p-1.5 !text-xs !rounded-lg hover:!border-red-500/50 hover:!text-red-500"
                      title="Delete project"
                      aria-label="Delete project"
                    >
                      🗑
                    </button>
                  </div>
                </div>
              </div>

              <Link
                href={isOnline ? `/projects/${encodeURIComponent(project.id)}/agents` : '#'}
                className={`block ${!isOnline ? 'pointer-events-none' : ''}`}
                onClick={(e) => { if (!isOnline) e.preventDefault() }}
              >
                <h3 className="font-bold text-foreground text-[15px] mt-3 mb-0">
                  {project.name}
                </h3>
                <p className="text-muted text-[13px] mt-0.5 min-h-[40px] line-clamp-2">
                  {project.description || 'No description provided.'}
                </p>
              </Link>

              {/* Tech stack tags */}
              {project.tech_stack && Object.keys(project.tech_stack).length > 0 && (
                <div className="flex flex-wrap gap-[6px] my-[14px]">
                  {Object.keys(project.tech_stack).map((tech) => (
                    <span
                      key={tech}
                      className="text-[11px] py-[5px] px-2 border border-border rounded-[7px] bg-surface-secondary text-foreground-secondary"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              )}
              {project.local_path && (
                <div
                  className="text-[10px] text-muted font-mono truncate mb-[10px]"
                  title={project.local_path}
                >
                  📁 {project.local_path}
                </div>
              )}
              {ragIndex[project.id]?.indexing && (
                <div className="mb-[10px]">
                  <div className="flex items-center justify-between text-[10px] text-muted mb-1">
                    <span className="font-semibold text-foreground">
                      ⚡ Indexing workspace…
                    </span>
                    <span className="font-mono">
                      {Math.round(ragIndex[project.id]?.progress ?? 0)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden border border-border/50">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-primary-hover rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.max(
                          2,
                          ragIndex[project.id]?.progress ?? 0,
                        )}%`,
                      }}
                    />
                  </div>
                  {ragIndex[project.id]?.current_file && (
                    <p className="text-[10px] text-muted mt-1 m-0 truncate">
                      {ragIndex[project.id]?.current_file}
                    </p>
                  )}
                </div>
              )}
              {!isOnline && (
                <div className="mb-[10px] rounded-[8px] bg-red-500/10 border border-red-500/20 px-3 py-2 text-[11px] text-red-600 dark:text-red-400 leading-relaxed">
                  ✗ Local agent workstation is offline — connect a device to browse files.
                </div>
              )}
              <div className="flex justify-between pt-[14px] border-t border-border text-xs text-muted">
                <span>
                  {project.created_at
                    ? new Date(project.created_at).toLocaleDateString()
                    : '—'}
                </span>
                {isOnline ? (
                  <Link
                    href={`/projects/${encodeURIComponent(project.id)}/agents`}
                    className="text-primary font-medium hover:underline"
                  >
                    Open Workspace →
                  </Link>
                ) : (
                  <span className="text-muted italic text-[11px]">
                    Workspace offline
                  </span>
                )}
              </div>
            </div>
          )})}
        </div>
      )}

      {/* Edit Project Modal */}
      {editingId && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[5vh] pb-[5vh] bg-black/50 backdrop-blur-sm overflow-y-auto">
          <div className="card-af max-w-[860px] w-full mx-4 p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-foreground mb-4">
              Edit Project
            </h3>

            {reindexState === 'running' && (
              <div className="space-y-4 py-8 text-center">
                <div className="w-14 h-14 mx-auto rounded-2xl bg-primary/10 text-primary grid place-items-center text-3xl animate-pulse">
                  ◫
                </div>
                <h4 className="font-bold text-foreground">
                  Indexing project folder in background…
                </h4>
                <p className="text-xs text-muted max-w-md mx-auto">
                  Your project folder is being indexed for semantic search.
                  You can close this window — indexing continues in the
                  background.
                </p>
                <div className="h-2 bg-surface-secondary rounded-full overflow-hidden border border-border/50 max-w-sm mx-auto">
                  <div
                    className="h-full bg-gradient-to-r from-[#1b78d2] to-[#6e38c7] rounded-full animate-pulse"
                    style={{ width: '100%' }}
                  />
                </div>
                {reindexJob && (
                  <p className="text-[11px] text-muted font-mono">
                    files: {reindexJob.files_indexed} · chunks:{' '}
                    {reindexJob.chunks}
                  </p>
                )}
                <div className="flex justify-center pt-2">
                  <button
                    type="button"
                    onClick={closeEditModal}
                    className="btn-secondary-af text-xs"
                  >
                    Close (continue in background)
                  </button>
                </div>
              </div>
            )}

            {reindexState === 'done' && (
              <div className="space-y-3 py-8 text-center">
                <div className="w-14 h-14 mx-auto rounded-2xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 grid place-items-center text-3xl">
                  ✓
                </div>
                <h4 className="font-bold text-foreground">Project indexed</h4>
                <p className="text-xs text-muted">
                  {reindexJob
                    ? `${reindexJob.files_indexed} files · ${reindexJob.chunks} chunks indexed.`
                    : 'RAG indexing completed.'}
                </p>
              </div>
            )}

            {reindexState === 'failed' && (
              <div className="space-y-3 py-8 text-center">
                <div className="w-14 h-14 mx-auto rounded-2xl bg-red-500/15 text-red-500 grid place-items-center text-3xl">
                  ✗
                </div>
                <h4 className="font-bold text-foreground">Indexing failed</h4>
                <p className="text-xs text-muted max-w-md mx-auto">
                  {reindexError || 'Something went wrong during indexing.'}
                </p>
                <div className="flex justify-center gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => editingId && startReindex(editingId)}
                    className="btn-secondary-af text-xs"
                  >
                    Retry
                  </button>
                  <button
                    type="button"
                    onClick={closeEditModal}
                    className="btn-primary-af text-xs"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}

            {reindexState === 'idle' && (
              <div className="space-y-4">
                {/* Execution Target */}
                <div>
                  <label className="block text-[13px] font-bold text-foreground mb-2">
                    Execution Target
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setEditTarget('LOCAL')}
                      className={`p-3 border rounded-xl text-left transition-colors ${
                        editTarget === 'LOCAL'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'btn-secondary-af !font-normal'
                      }`}
                    >
                      <div className="font-bold text-xs">Local Machine</div>
                      <div className="text-[10px] opacity-80 mt-0.5">
                        Runs via WSS on your PC
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditTarget('CLOUD')}
                      className={`p-3 border rounded-xl text-left transition-colors ${
                        editTarget === 'CLOUD'
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'btn-secondary-af !font-normal'
                      }`}
                    >
                      <div className="font-bold text-xs">Cloud Workspace</div>
                      <div className="text-[10px] opacity-80 mt-0.5">
                        Runs in isolated container
                      </div>
                    </button>
                  </div>
                </div>

                {/* Project Name + Description in 2-col grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[13px] font-bold text-foreground mb-1">
                      Project Name
                    </label>
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="input-af"
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="block text-[13px] font-bold text-foreground mb-1">
                      Description
                    </label>
                    <input
                      type="text"
                      value={editDesc}
                      onChange={(e) => setEditDesc(e.target.value)}
                      className="input-af"
                    />
                  </div>
                </div>

                {/* Local Workspace Path + validation */}
                {editTarget === 'LOCAL' && (
                  <div>
                    <label className="block text-[13px] font-bold text-foreground mb-1">
                      Local Workspace Path
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={editLocalPath}
                        onChange={(e) => {
                          setEditLocalPath(e.target.value)
                          setEditPathResult(null)
                          setEditPathError(null)
                        }}
                        placeholder="e.g. D:\Projects\cmdx-framework"
                        className="input-af font-mono !text-xs flex-1"
                      />
                      <button
                        type="button"
                        onClick={handleCheckEditFolder}
                        disabled={editChecking || !editLocalPath.trim()}
                        className="btn-secondary-af !py-2.5 text-xs whitespace-nowrap disabled:opacity-50"
                      >
                        {editChecking ? 'Checking...' : 'Check Folder'}
                      </button>
                    </div>
                    {editChecking && (
                      <div className="mt-2 text-xs text-muted animate-pulse">
                        Validating project folder...
                      </div>
                    )}
                    {editPathResult && (
                      <div
                        className={`mt-2 rounded-[10px] p-3 text-xs space-y-1 ${
                          editPathResult.valid
                            ? 'bg-emerald-500/10 border border-emerald-500/30'
                            : 'bg-red-500/10 border border-red-500/30'
                        }`}
                      >
                        <div className="font-semibold text-sm">
                          {editPathResult.valid
                            ? '✓ Folder Valid'
                            : '✕ Folder Issues'}
                        </div>
                        {editPathResult.files_count > 0 && (
                          <div className="text-foreground-secondary">
                            {editPathResult.files_count} files ·{' '}
                            {editPathResult.directories_count} dirs
                            {editPathResult.git_repository
                              ? ' · git repo'
                              : ''}
                          </div>
                        )}
                        {editPathResult.detected_stack.length > 0 && (
                          <div className="text-primary font-semibold">
                            Detected:{' '}
                            {editPathResult.detected_stack.join(', ')}
                          </div>
                        )}
                        {editPathResult.warnings.map((w, i) => (
                          <div
                            key={i}
                            className="text-amber-600 dark:text-amber-400"
                          >
                            ⚠ {w}
                          </div>
                        ))}
                      </div>
                    )}
                    {editPathError && (
                      <div className="mt-2 text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-2.5">
                        {editPathError}
                      </div>
                    )}
                    <p className="text-[10px] text-muted mt-1.5">
                      Saving with a folder path automatically starts RAG
                      indexing in the background.
                    </p>
                  </div>
                )}

                {/* Technology Stack */}
                <div>
                  <label className="block text-[13px] font-bold text-foreground mb-2">
                    Technology Stack
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {TECH_OPTIONS.map((tech) => {
                      const selected = editTechStack.includes(tech)
                      return (
                        <button
                          key={tech}
                          type="button"
                          onClick={() =>
                            setEditTechStack((prev) =>
                              prev.includes(tech)
                                ? prev.filter((t) => t !== tech)
                                : [...prev, tech],
                            )
                          }
                          className={`text-[11px] px-2.5 py-1 rounded-md border transition-colors ${
                            selected
                              ? 'bg-primary/15 border-primary text-primary font-bold'
                              : 'bg-surface-secondary border-border text-muted'
                          }`}
                        >
                          {tech}
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* Footer */}
            {editSaveError && (
              <div className="mt-4 text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-2.5">
                {editSaveError}
              </div>
            )}
            {reindexState === 'idle' && (
              <div className="flex justify-end gap-2.5 pt-4 mt-4 border-t border-border">
                <button
                  type="button"
                  onClick={closeEditModal}
                  className="btn-secondary-af text-xs"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveEdit}
                  disabled={editSaving || !editName.trim()}
                  className="btn-primary-af text-xs disabled:opacity-50"
                >
                  {editSaving
                    ? 'Saving...'
                    : editTarget === 'LOCAL' && editLocalPath.trim()
                      ? 'Save & Index in Background'
                      : 'Save Changes'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card-af max-w-[400px] w-full mx-4 p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-foreground">Delete Project</h3>
            <p className="text-sm text-muted">
              {deleteConfirm
                ? 'This action cannot be undone. All project data will be permanently removed.'
                : 'Are you sure you want to delete this project?'}
            </p>
            <div className="flex justify-end gap-2.5 pt-2 border-t border-border">
              <button
                type="button"
                onClick={() => { setDeletingId(null); setDeleteConfirm(false) }}
                className="btn-secondary-af text-xs"
              >
                Cancel
              </button>
              {!deleteConfirm ? (
                <button
                  type="button"
                  onClick={() => setDeleteConfirm(true)}
                  className="btn-primary-af text-xs !bg-red-600 hover:!bg-red-700"
                >
                  Yes, Delete
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleDelete}
                  className="btn-primary-af text-xs !bg-red-600 hover:!bg-red-700"
                >
                  Confirm Delete
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  trend,
  icon,
}: {
  label: string
  value: string | number
  trend: string
  icon: string
}) {
  return (
    <div className="card-af p-5">
      <div className="flex justify-between text-muted text-[13px]">
        <span>{label}</span>
        <span>{icon}</span>
      </div>
      <div className="text-[30px] font-extrabold text-foreground my-[7px]">
        {value}
      </div>
      <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">{trend}</div>
    </div>
  )
}
