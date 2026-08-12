'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { listProjects, type ProjectResponse } from '@/lib/api'

export default function LiveWorkspacePage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load all projects so the user can choose one from the Live Workspace.
  // Uses the DB-only `rag_gate` field — no per-project RAG probing here
  // (the RAG check happens when a project is selected, plus on dashboard cards).
  useEffect(() => {
    let ignore = false
    const load = async () => {
      try {
        const data = await listProjects()
        if (!ignore) setProjects(data)
      } catch (err) {
        console.error('Failed to load projects:', err)
        if (!ignore) setError('Could not load projects. Is the API running?')
      } finally {
        if (!ignore) setLoading(false)
      }
    }
    void load()
    return () => {
      ignore = true
    }
  }, [])

  // Auto-refresh while any project is RAG-locked so cards unlock the moment
  // the worker finishes indexing (cheap DB-only listProjects call).
  useEffect(() => {
    const hasLocked = projects.some((p) => p.rag_gate?.locked === true)
    if (!hasLocked) return
    let timer: number | null = null
    const refresh = async () => {
      try {
        const data = await listProjects()
        setProjects(data)
        if (!data.some((p) => p.rag_gate?.locked === true) && timer) {
          window.clearInterval(timer)
          timer = null
        }
      } catch {
        // ignore transient errors — next tick retries
      }
    }
    timer = window.setInterval(refresh, 5000)
    return () => {
      if (timer) window.clearInterval(timer)
    }
  }, [projects])

  return (
    <div className="max-w-7xl mx-auto w-full flex-1 flex flex-col min-h-0 space-y-6">
      {/* Page header */}
      <div className="flex items-start justify-between mb-[4px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            Live Workspace
          </h2>
          <p className="text-muted text-sm m-0">
            Choose a project to open its workspace.
          </p>
        </div>
        <Link href="/projects/new" className="btn-primary-af text-sm">
          ＋ Create Project
        </Link>
      </div>

      {error && (
        <div className="rounded-[10px] p-3 text-xs font-medium bg-red-500/10 text-red-500 border border-red-500/30">
          {error}
        </div>
      )}

      {loading ? (
        <div className="card-af p-12 text-center text-xs text-muted font-mono animate-pulse">
          Loading projects…
        </div>
      ) : projects.length === 0 ? (
        <div className="card-af p-12 text-center">
          <p className="text-sm text-muted m-0">
            No projects yet.{' '}
            <Link
              href="/projects/new"
              className="text-primary hover:underline font-medium"
            >
              Create your first project
            </Link>
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-[18px]">
          {projects.map((project) => {
            // RAG readiness gate: a project with no completed index is locked
            // and cannot be opened until indexing finishes.
            const ragLocked = project.rag_gate?.locked === true
            const openable = !ragLocked
            const techStack = project.tech_stack
            const tags = techStack
              ? Object.keys(techStack).filter((k) => techStack[k])
              : []
            return (
              <div
                key={project.id}
                className={`card-af p-5 block transition-all ${
                  openable ? 'card-af-hover' : 'opacity-60 grayscale-[30%]'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-0">
                  <div className="w-11 h-11 rounded-[12px] bg-primary/10 text-primary grid place-items-center text-[21px] flex-shrink-0">
                    ⚡
                  </div>
                  <div className="flex items-center gap-[8px] flex-shrink-0">
                    <span className="inline-flex items-center gap-[6px] rounded-full py-[5px] px-[10px] text-xs font-bold bg-primary/15 text-primary">
                      ● {project.execution_target}
                    </span>
                    {ragLocked && (
                      <span className="inline-flex items-center gap-[6px] rounded-full py-[5px] px-[10px] text-xs font-bold bg-amber-500/15 text-amber-600 dark:text-amber-400">
                        🔒 RAG Index Required
                      </span>
                    )}
                  </div>
                </div>

                <Link
                  href={
                    openable
                      ? `/projects/${encodeURIComponent(project.id)}/agents`
                      : '#'
                  }
                  className={`block ${!openable ? 'pointer-events-none' : ''}`}
                  onClick={(e) => {
                    if (!openable) e.preventDefault()
                  }}
                  aria-disabled={!openable}
                  title={
                    ragLocked
                      ? 'RAG index required — unlocks once indexing completes'
                      : undefined
                  }
                >
                  <h3 className="font-bold text-foreground text-[15px] mt-3 mb-0">
                    {project.name}
                  </h3>
                  <p className="text-muted text-[13px] mt-0.5 min-h-[40px] line-clamp-2">
                    {project.description || 'No description provided.'}
                  </p>
                </Link>

                {tags.length > 0 && (
                  <div className="flex flex-wrap gap-[6px] my-[14px]">
                    {tags.map((tech) => (
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

                {ragLocked && (
                  <div className="mb-[10px] rounded-[8px] bg-amber-500/10 border border-amber-500/20 px-3 py-2 text-[11px] text-amber-700 dark:text-amber-400 leading-relaxed">
                    🔒 RAG index required — this project unlocks automatically
                    once indexing completes.
                  </div>
                )}

                <div className="flex justify-between pt-[14px] border-t border-border text-xs text-muted">
                  <span>
                    {project.created_at
                      ? new Date(project.created_at).toLocaleDateString()
                      : '—'}
                  </span>
                  {openable ? (
                    <Link
                      href={`/projects/${encodeURIComponent(project.id)}/agents`}
                      className="text-primary font-medium hover:underline"
                    >
                      Open Workspace →
                    </Link>
                  ) : (
                    <span className="text-amber-600 dark:text-amber-400 italic text-[11px] font-medium">
                      🔒 Indexing…
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
