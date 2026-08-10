'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { listProjects, type ProjectResponse } from '@/lib/api'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listProjects()
      .then((data) => setProjects(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">◉ Live Workspace</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card-af p-5 h-40 animate-pulse bg-surface-secondary" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">◉ Live Workspace</h1>
          <p className="text-sm text-muted mt-1">
            {projects.length} project{projects.length !== 1 ? 's' : ''} — select one to open its workspace.
          </p>
        </div>
        <Link href="/projects/new" className="btn-primary-af text-sm flex items-center gap-1.5">
          <span>＋</span> New Project
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="card-af p-12 text-center">
          <p className="text-muted text-sm">No projects yet.</p>
          <Link
            href="/projects/new"
            className="text-primary text-sm font-medium hover:underline mt-2 inline-block"
          >
            Create your first project →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((p) => (
            <Link
              key={p.id}
              href={`/projects/${encodeURIComponent(p.id)}/agents`}
              className="card-af card-af-hover p-5 block group"
            >
              <div className="flex items-start gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary grid place-items-center text-lg flex-shrink-0">
                  ⚡
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="font-bold text-foreground text-[15px] group-hover:text-primary transition-colors">
                    {p.name}
                  </h3>
                  <p className="text-[13px] text-muted mt-0.5 line-clamp-2">
                    {p.description || 'No description'}
                  </p>
                </div>
              </div>

              {p.tech_stack && Object.keys(p.tech_stack).length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {Object.keys(p.tech_stack).map((t) => (
                    <span
                      key={t}
                      className="text-[10px] px-2 py-1 rounded-md bg-surface-secondary border border-border text-muted"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-between pt-3 border-t border-border text-xs text-muted">
                <span className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${p.execution_target === 'LOCAL' ? 'bg-emerald-500' : 'bg-blue-500'}`} />
                  {p.execution_target}
                </span>
                <span className="truncate max-w-[180px] text-[11px]">
                  {p.local_path || '—'}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
