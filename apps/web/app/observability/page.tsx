'use client'

import React, { useEffect, useState } from 'react'
import { getFullHealth, type FullHealthResponse } from '@/lib/api'

export default function ObservabilityPage() {
  const [health, setHealth] = useState<FullHealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getFullHealth()
      .then((data) => setHealth(data))
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load metrics'),
      )
  }, [])

  const statusColor = (status: string) =>
    status === 'healthy'
      ? 'text-emerald-600 dark:text-emerald-400'
      : status === 'degraded'
        ? 'text-amber-500'
        : status === 'unhealthy'
          ? 'text-red-500'
          : 'text-muted'

  const statusIcon = (status: string) =>
    status === 'healthy' ? '●' : status === 'degraded' ? '◐' : '○'

  return (
    <div>
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            Observability
          </h2>
          <p className="text-muted text-sm m-0">
            Operational metrics for pipelines, agents, RAG, and infrastructure.
          </p>
        </div>
      </div>

      {error && (
        <div className="text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-3 mb-4">
          {error}
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-[18px]">
        {/* Infrastructure Health — real data from /health/full */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-foreground m-0 mb-4">
            Infrastructure Health
          </h3>
          {health?.components ? (
            <div className="space-y-1 text-xs">
              {Object.entries(health.components).map(([name, comp]) => (
                <div
                  key={name}
                  className="flex justify-between py-[11px] border-b border-border last:border-0"
                >
                  <span className="text-muted capitalize">
                    {name.replace('_', ' ')}
                  </span>
                  <span className={`font-bold ${statusColor(comp.status)}`}>
                    <span className="mr-1">{statusIcon(comp.status)}</span>
                    {comp.message || comp.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted animate-pulse">
              Loading infrastructure status...
            </div>
          )}
        </div>

        {/* Platform Info */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-foreground m-0 mb-4">
            Platform Info
          </h3>
          <div className="space-y-1 text-xs">
            {[
              ['App Name', health?.app_name || '—'],
              ['Environment', health?.environment || '—'],
              ['Mode', health?.mode || '—'],
              ['Version', health?.version || '—'],
              ['Overall Status', health?.status || '—'],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between py-[11px] border-b border-border last:border-0"
              >
                <span className="text-muted">{label}</span>
                <span className="text-foreground font-bold">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Agent Duration */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-foreground m-0 mb-4">
            Agent Pipeline (11 Agents)
          </h3>
          <p className="text-xs text-muted mb-3">
            Sequential execution: Planning → Architecture → Visual Analysis →
            UI/UX → Documentation → Frontend → Backend → Database → Test →
            Validation → Git
          </p>
          {[
            ['Planning', 85],
            ['Architecture', 70],
            ['Visual Analysis', 45],
            ['UI/UX', 55],
            ['Documentation', 50],
            ['Frontend', 75],
            ['Backend', 80],
            ['Database', 60],
            ['Test', 65],
            ['Validation', 55],
            ['Git', 30],
          ].map(([name, pct]) => (
            <div
              key={name}
              className="grid grid-cols-[110px_1fr_40px] gap-[10px] items-center my-[10px] text-[11px]"
            >
              <span className="text-foreground truncate">{name}</span>
              <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden border border-border/50">
                <div
                  className="h-full bg-gradient-to-r from-[#1b78d2] to-[#6e38c7] rounded-full"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-muted font-mono text-right">
                ~{pct}s
              </span>
            </div>
          ))}
        </div>

        {/* Pipeline Stats */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-foreground m-0 mb-4">
            Pipeline Stats
          </h3>
          <div className="space-y-1 text-xs">
            {[
              ['Total Agents', '11'],
              ['Parallel Execution', 'Sequential'],
              ['Avg Pipeline Duration', '~12 min'],
              ['Tool Timeout', '120s'],
              [
                'WSS Status',
                health?.status === 'ok' ? 'Connected' : 'Degraded',
              ],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between py-[11px] border-b border-border last:border-0"
              >
                <span className="text-muted">{label}</span>
                <span
                  className={`font-bold ${
                    value === 'Connected'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-foreground'
                  }`}
                >
                  {value === 'Connected' && '● '}
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
