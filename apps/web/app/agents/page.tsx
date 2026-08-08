'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { listAgents, type AgentTemplateResponse } from '@/lib/api'

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentTemplateResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const data = await listAgents()
      setAgents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div>
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            Agent Templates
          </h2>
          <p className="text-muted text-sm m-0">
            Define, version, and manage reusable agent templates for your
            pipeline. Updates create new versions automatically.
          </p>
        </div>
        <Link href="/agents/new" className="btn-primary-af text-sm">
          + New Agent
        </Link>
      </div>

      {error && (
        <div className="text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-3 mb-4">
          {error}
          <button onClick={load} className="ml-3 underline">Retry</button>
        </div>
      )}

      {loading ? (
        <div className="card-af p-8 text-center text-muted animate-pulse">
          Loading agent templates...
        </div>
      ) : agents.length === 0 ? (
        <div className="card-af p-8 text-center">
          <p className="text-muted text-sm">No agent templates defined yet.</p>
          <Link href="/agents/new" className="text-primary text-sm hover:underline mt-1 inline-block">
            Create your first agent &rarr;
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div key={agent.id} className="card-af p-4 transition-all flex flex-col">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-bold text-foreground text-sm truncate">
                    {agent.name}
                  </h3>
                  <p className="text-muted text-xs mt-0.5 line-clamp-2">
                    {agent.description || 'No description'}
                  </p>
                </div>
                <Link
                  href={`/agents/${encodeURIComponent(agent.id)}/edit`}
                  className="btn-secondary-af !p-1.5 !text-xs !rounded-lg flex-shrink-0"
                  title="Edit agent"
                >
                  ✏️
                </Link>
              </div>

              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-primary/15 text-primary">
                  {agent.capability}
                </span>
                <span className="text-[10px] text-muted">v{agent.version}</span>
                {!agent.is_active && (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/15 text-red-500">
                    Inactive
                  </span>
                )}
              </div>

              {(agent.tools || []).length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border">
                  {agent.tools.map((tool: string) => (
                    <span key={tool} className="text-[10px] px-2 py-0.5 rounded-md bg-surface-secondary text-foreground-secondary border border-border">
                      {tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
