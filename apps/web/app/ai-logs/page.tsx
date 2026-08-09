'use client'

import React, { useEffect, useState } from 'react'
import {
  listProjects,
  getProjectLlmLogs,
  getLlmLogStats,
  type ProjectResponse,
  type LlmLogEntry,
  type LlmLogStats,
} from '@/lib/api'

const STATUS_COLORS: Record<string, string> = {
  success: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
  error: 'bg-red-500/10 text-red-500 border-red-500/30',
}

export default function AiLogsPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [logs, setLogs] = useState<LlmLogEntry[]>([])
  const [stats, setStats] = useState<LlmLogStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [logsLoading, setLogsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [filterProvider, setFilterProvider] = useState<string>('')
  const [filterModel, setFilterModel] = useState<string>('')

  // Pagination
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(0)
  const limit = 50

  // Detail modal
  const [selectedLog, setSelectedLog] = useState<LlmLogEntry | null>(null)

  // Load projects on mount
  useEffect(() => {
    listProjects()
      .then((data) => {
        setProjects(data)
        if (data.length > 0) {
          setSelectedProject(data[0].id)
        }
      })
      .catch((err) => {
        console.error('Failed to load projects:', err)
        setError('Could not load projects. Is the API running?')
      })
      .finally(() => setLoading(false))
  }, [])

  // Load logs and stats when project or filters change
  useEffect(() => {
    if (!selectedProject) return
    setLogsLoading(true)
    setOffset(0)

    Promise.all([
      getProjectLlmLogs(selectedProject, {
        status: filterStatus || undefined,
        provider: filterProvider || undefined,
        model: filterModel || undefined,
        limit,
        offset: 0,
      }),
      getLlmLogStats(selectedProject).catch(() => null),
    ])
      .then(([logData, statsData]) => {
        setLogs(logData.items)
        setTotal(logData.total)
        setStats(statsData)
      })
      .catch((err) => {
        console.error('Failed to load logs:', err)
        setError('Could not load AI interaction logs.')
      })
      .finally(() => setLogsLoading(false))
  }, [selectedProject, filterStatus, filterProvider, filterModel])

  const loadPage = (newOffset: number) => {
    if (!selectedProject) return
    setLogsLoading(true)
    setOffset(newOffset)
    getProjectLlmLogs(selectedProject, {
      status: filterStatus || undefined,
      provider: filterProvider || undefined,
      model: filterModel || undefined,
      limit,
      offset: newOffset,
    })
      .then((data) => {
        setLogs(data.items)
        setTotal(data.total)
      })
      .catch((err) => {
        console.error('Failed to load page:', err)
      })
      .finally(() => setLogsLoading(false))
  }

  const totalPages = Math.max(1, Math.ceil(total / limit))
  const currentPage = Math.floor(offset / limit) + 1

  // Collect unique providers and models from logs for filter dropdowns
  const uniqueProviders = Array.from(new Set(logs.map((l) => l.provider))).sort()
  const uniqueModels = Array.from(new Set(logs.map((l) => l.model))).sort()

  return (
    <div>
      {/* Page Header — matches Git/RAG page pattern */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            AI Logs
          </h2>
          <p className="text-muted text-sm m-0">
            Complete audit trail of every AI prompt, response, and provider interaction
            — no truncation.
          </p>
        </div>
        <select
          value={selectedProject}
          onChange={(e) => {
            setSelectedProject(e.target.value)
            setFilterStatus('')
            setFilterProvider('')
            setFilterModel('')
          }}
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

      {error && (
        <div className="text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-3 mb-4">
          {error}
        </div>
      )}

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-7 gap-3 mb-[18px]">
          {[
            ['Total Calls', String(stats.total_calls)],
            ['Errors', String(stats.error_count)],
            ['Total Tokens', stats.total_tokens.toLocaleString()],
            ['Total Cost', `$${stats.total_cost.toFixed(4)}`],
            [
              'Total Duration',
              stats.total_duration_ms > 1000
                ? `${(stats.total_duration_ms / 1000).toFixed(1)}s`
                : `${stats.total_duration_ms}ms`,
            ],
            ['Models', String(stats.unique_models)],
            ['Providers', String(stats.unique_providers)],
          ].map(([label, value]) => (
            <div key={label} className="card-af p-3 text-center">
              <div className="text-[10px] uppercase tracking-[.12em] text-muted mb-1">
                {label}
              </div>
              <div
                className={`text-sm font-bold font-mono ${
                  label === 'Errors' && stats.error_count > 0
                    ? 'text-red-500'
                    : 'text-foreground'
                }`}
              >
                {value}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filters Row */}
      <div className="flex flex-wrap items-center gap-3 mb-[18px]">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="input-af !w-auto text-xs"
        >
          <option value="">All Statuses</option>
          <option value="success">Success</option>
          <option value="error">Error</option>
        </select>
        <select
          value={filterProvider}
          onChange={(e) => setFilterProvider(e.target.value)}
          className="input-af !w-auto text-xs"
        >
          <option value="">All Providers</option>
          {uniqueProviders.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <select
          value={filterModel}
          onChange={(e) => setFilterModel(e.target.value)}
          className="input-af !w-auto text-xs"
        >
          <option value="">All Models</option>
          {uniqueModels.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        {(filterStatus || filterProvider || filterModel) && (
          <button
            onClick={() => {
              setFilterStatus('')
              setFilterProvider('')
              setFilterModel('')
            }}
            className="text-xs text-primary hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Logs Table */}
      {!selectedProject ? (
        <div className="card-af p-10 text-center">
          <p className="text-sm text-muted">
            Select a project to view AI interaction logs.
          </p>
        </div>
      ) : logsLoading ? (
        <div className="card-af p-10 text-center">
          <div className="text-xs text-muted font-mono animate-pulse">
            Loading logs…
          </div>
        </div>
      ) : logs.length === 0 ? (
        <div className="card-af p-10 text-center">
          <p className="text-sm text-muted">
            No AI interactions recorded for this project.
          </p>
        </div>
      ) : (
        <>
          <div className="card-af overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-muted">
                    <th className="text-left py-3 px-4 font-medium">Time</th>
                    <th className="text-left py-3 px-4 font-medium">Status</th>
                    <th className="text-left py-3 px-4 font-medium">Provider</th>
                    <th className="text-left py-3 px-4 font-medium">Model</th>
                    <th className="text-right py-3 px-4 font-medium">Tokens</th>
                    <th className="text-right py-3 px-4 font-medium">Cost</th>
                    <th className="text-right py-3 px-4 font-medium">Duration</th>
                    <th className="text-left py-3 px-4 font-medium">Prompt</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr
                      key={log.id}
                      onClick={() => setSelectedLog(log)}
                      className="border-b border-border hover:bg-surface-secondary/50 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 text-muted whitespace-nowrap font-mono">
                        {log.created_at
                          ? new Date(log.created_at).toLocaleString()
                          : '—'}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                            STATUS_COLORS[log.status] ||
                            'bg-muted/10 text-muted border-muted/30'
                          }`}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-foreground">{log.provider}</td>
                      <td className="py-3 px-4 text-foreground font-mono">
                        {log.model}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-foreground">
                        {log.total_tokens.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-foreground">
                        ${log.cost.toFixed(6)}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-muted">
                        {log.duration_ms > 1000
                          ? `${(log.duration_ms / 1000).toFixed(1)}s`
                          : `${log.duration_ms}ms`}
                      </td>
                      <td className="py-3 px-4 text-muted max-w-[300px] truncate">
                        {log.prompt_text || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4 text-xs">
              <span className="text-muted">
                Page {currentPage} of {totalPages} ({total} total)
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => loadPage(0)}
                  disabled={offset === 0}
                  className="px-3 py-1.5 rounded-[8px] border border-border disabled:opacity-30 hover:bg-surface-secondary transition-colors"
                >
                  First
                </button>
                <button
                  onClick={() => loadPage(Math.max(0, offset - limit))}
                  disabled={offset === 0}
                  className="px-3 py-1.5 rounded-[8px] border border-border disabled:opacity-30 hover:bg-surface-secondary transition-colors"
                >
                  Prev
                </button>
                <button
                  onClick={() =>
                    loadPage(Math.min(offset + limit, (totalPages - 1) * limit))
                  }
                  disabled={currentPage >= totalPages}
                  className="px-3 py-1.5 rounded-[8px] border border-border disabled:opacity-30 hover:bg-surface-secondary transition-colors"
                >
                  Next
                </button>
                <button
                  onClick={() => loadPage((totalPages - 1) * limit)}
                  disabled={currentPage >= totalPages}
                  className="px-3 py-1.5 rounded-[8px] border border-border disabled:opacity-30 hover:bg-surface-secondary transition-colors"
                >
                  Last
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Detail Modal — full prompt/response, no truncation */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setSelectedLog(null)}
          />
          {/* Modal */}
          <div
            role="dialog"
            aria-modal="true"
            className="relative z-10 w-full max-w-4xl mx-4 max-h-[85vh] bg-surface rounded-[16px] shadow-2xl border border-border overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-surface-secondary/50 flex-shrink-0">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  AI Interaction Detail
                </h3>
                <p className="text-[11px] text-muted mt-0.5">
                  {selectedLog.provider} / {selectedLog.model} —{' '}
                  {selectedLog.created_at
                    ? new Date(selectedLog.created_at).toLocaleString()
                    : '—'}
                </p>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-muted hover:text-foreground transition-colors text-lg leading-none"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Body — scrollable */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {/* Metadata */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  ['Status', selectedLog.status],
                  ['Provider', selectedLog.provider],
                  ['Model', selectedLog.model],
                  ['Temperature', selectedLog.temperature ?? '—'],
                  [
                    'Prompt Tokens',
                    selectedLog.prompt_tokens.toLocaleString(),
                  ],
                  [
                    'Completion Tokens',
                    selectedLog.completion_tokens.toLocaleString(),
                  ],
                  ['Total Tokens', selectedLog.total_tokens.toLocaleString()],
                  ['Cost', `$${selectedLog.cost.toFixed(6)}`],
                  [
                    'Duration',
                    selectedLog.duration_ms > 1000
                      ? `${(selectedLog.duration_ms / 1000).toFixed(1)}s`
                      : `${selectedLog.duration_ms}ms`,
                  ],
                  ['JSON Mode', selectedLog.json_mode ? 'Yes' : 'No'],
                  ['Request ID', selectedLog.request_id || '—'],
                  [
                    'Instruction ID',
                    selectedLog.instruction_id || '—',
                  ],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div className="text-[10px] uppercase tracking-[.1em] text-muted mb-0.5">
                      {label}
                    </div>
                    <div className="text-xs font-mono text-foreground break-all">
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Error message (if any) */}
              {selectedLog.error_message && (
                <div>
                  <div className="text-xs font-bold text-red-500 mb-1.5">
                    Error
                  </div>
                  <pre className="text-xs bg-red-500/5 border border-red-500/20 rounded-[8px] p-3 whitespace-pre-wrap break-all font-mono text-red-600 dark:text-red-400">
                    {selectedLog.error_message}
                  </pre>
                </div>
              )}

              {/* System Prompt */}
              <div>
                <div className="text-xs font-bold text-foreground mb-1.5">
                  System Prompt
                </div>
                <pre className="text-xs bg-surface-secondary rounded-[8px] p-3 whitespace-pre-wrap break-all font-mono text-muted max-h-[30vh] overflow-y-auto border border-border">
                  {selectedLog.system_prompt_text || '(none)'}
                </pre>
              </div>

              {/* User Prompt */}
              <div>
                <div className="text-xs font-bold text-foreground mb-1.5">
                  Prompt
                </div>
                <pre className="text-xs bg-surface-secondary rounded-[8px] p-3 whitespace-pre-wrap break-all font-mono text-foreground max-h-[30vh] overflow-y-auto border border-border">
                  {selectedLog.prompt_text || '(none)'}
                </pre>
              </div>

              {/* Response */}
              <div>
                <div className="text-xs font-bold text-foreground mb-1.5">
                  Response
                </div>
                <pre className="text-xs bg-surface-secondary rounded-[8px] p-3 whitespace-pre-wrap break-all font-mono text-foreground max-h-[30vh] overflow-y-auto border border-border">
                  {selectedLog.response_text || '(none)'}
                </pre>
              </div>
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-3 px-5 py-3 border-t border-border bg-surface-secondary/30 flex-shrink-0">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 text-xs font-medium rounded-[8px] border border-border hover:bg-surface-secondary transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
