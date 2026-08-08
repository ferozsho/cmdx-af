'use client'

import React, { useEffect, useState } from 'react'
import {
  getAgentMetrics,
  getFullHealth,
  type FullHealthResponse,
} from '@/lib/api'

const AGENT_ORDER = [
  'Planning Agent',
  'Architecture Agent',
  'Visual Analysis Agent',
  'UI/UX Agent',
  'Documentation Agent',
  'Frontend Agent',
  'Backend Agent',
  'Database Agent',
  'Test Agent',
  'Validation Agent',
  'Git Agent',
]

export default function ObservabilityPage() {
  const [health, setHealth] = useState<FullHealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [agentMetrics, setAgentMetrics] = useState<{
    agents: {
      name: string
      runs: number
      avg_duration_seconds: number
      last_run: string | null
    }[]
    total_runs: number
    avg_duration_seconds: number
    llm_usage: {
      calls: number
      total_tokens: number
      cost: number
      models: number
    }
  } | null>(null)

  useEffect(() => {
    getFullHealth()
      .then((data) => setHealth(data))
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Failed to load metrics'),
      )
    getAgentMetrics()
      .then((data) => setAgentMetrics(data))
      .catch(() => setAgentMetrics(null))
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

        {/* Agent Duration — real data from /observability/agent-metrics */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-foreground m-0 mb-4">
            Agent Pipeline (11 Agents)
          </h3>
          <p className="text-xs text-muted mb-3">
            Sequential execution: Planning → Architecture → Visual Analysis →
            UI/UX → Documentation → Frontend → Backend → Database → Test →
            Validation → Git
          </p>
          {AGENT_ORDER.map((name) => {
            const metric = agentMetrics?.agents.find((a) => a.name === name)
            const dur = metric?.avg_duration_seconds
            const pct =
              dur !== undefined
                ? Math.min(100, Math.max(3, Math.round((dur / 120) * 100)))
                : 0
            return (
              <div
                key={name}
                className="grid grid-cols-[110px_1fr_40px] gap-[10px] items-center my-[10px] text-[11px]"
              >
                <span className="text-foreground truncate">{name}</span>
                <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden border border-border/50">
                  <div
                    className="h-full bg-gradient-to-r from-[#1b78d2] to-[#6e38c7] rounded-full transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-muted font-mono text-right">
                  {dur !== undefined
                    ? `${dur.toFixed(1)}s`
                    : '—'}
                </span>
              </div>
            )
          })}
          {agentMetrics && agentMetrics.total_runs === 0 && (
            <p className="text-[11px] text-muted mt-2">
              No pipeline runs recorded yet — durations appear after the first
              run.
            </p>
          )}
        </div>

        {/* Pipeline Stats — real totals from agent-metrics */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-foreground m-0 mb-4">
            Pipeline Stats
          </h3>
          <div className="space-y-1 text-xs">
            {[
              ['Total Agents', '11'],
              ['Total Runs', String(agentMetrics?.total_runs ?? '—')],
              ['Parallel Execution', 'Sequential'],
              [
                'Avg Agent Duration',
                agentMetrics?.avg_duration_seconds
                  ? `~${agentMetrics.avg_duration_seconds.toFixed(1)}s`
                  : '—',
              ],
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

        {/* LLM Usage — real totals from llm_usage table */}
        <div className="card-af p-[18px]">
          <h3 className="text-sm font-bold text-foreground m-0 mb-4">
            LLM Usage
          </h3>
          <div className="space-y-1 text-xs">
            {[
              ['API Calls', String(agentMetrics?.llm_usage.calls ?? '—')],
              [
                'Total Tokens',
                agentMetrics?.llm_usage.total_tokens
                  ? agentMetrics.llm_usage.total_tokens.toLocaleString()
                  : '—',
              ],
              [
                'Estimated Cost',
                agentMetrics?.llm_usage.cost
                  ? `$${agentMetrics.llm_usage.cost.toFixed(4)}`
                  : '—',
              ],
              ['Models', String(agentMetrics?.llm_usage.models ?? '—')],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between py-[11px] border-b border-border last:border-0"
              >
                <span className="text-muted">{label}</span>
                <span className="text-foreground font-bold font-mono">
                  {value}
                </span>
              </div>
            ))}
          </div>
          {agentMetrics && agentMetrics.llm_usage.calls === 0 && (
            <p className="text-[11px] text-muted mt-2">
              No LLM calls recorded yet — usage appears after the first pipeline
              run.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
