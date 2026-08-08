'use client'

import React, { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import {
  listProjects,
  ragSearch,
  getRagStats,
  reindexRag,
  getReindexStatus,
  type ProjectResponse,
  type ReindexJob,
  type RagStats,
} from '@/lib/api'

export default function RagManagerPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [ragStats, setRagStats] = useState<RagStats | null>(null)
  const [reindexing, setReindexing] = useState(false)
  const [reindexJob, setReindexJob] = useState<ReindexJob | null>(null)
  const [reindexMessage, setReindexMessage] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    }
  }, [])

  // Load projects on mount
  React.useEffect(() => {
    listProjects()
      .then((data) => {
        setProjects(data)
        if (data.length > 0) setSelectedProject(data[0].id)
      })
      .catch(console.error)
      .finally(() => setLoadingProjects(false))
  }, [])

  // Poll live RAG stats; keep polling every 2s while indexing so the UI
  // shows real background progress (startup / watcher / explicit re-index)
  useEffect(() => {
    if (!selectedProject) return
    let timer: number | null = null
    const tick = async () => {
      try {
        const s = await getRagStats(selectedProject)
        setRagStats(s)
      } catch {
        // ignore transient errors
      }
    }
    tick()
    const shouldPoll = reindexing || ragStats?.indexing
    if (shouldPoll) {
      timer = window.setInterval(tick, 2000)
    }
    return () => {
      if (timer) window.clearInterval(timer)
    }
  }, [selectedProject, reindexing, ragStats?.indexing])

  const handleReindex = async () => {
    if (!selectedProject) return
    setReindexing(true)
    setReindexMessage(null)
    setReindexJob(null)
    try {
      await reindexRag(selectedProject)
      // Poll the background job until it finishes
      if (pollRef.current) window.clearInterval(pollRef.current)
      pollRef.current = window.setInterval(async () => {
        try {
          const res = await getReindexStatus(selectedProject)
          if (res.job) setReindexJob(res.job)
          if (res.status === 'done' && res.job) {
            if (pollRef.current) window.clearInterval(pollRef.current)
            pollRef.current = null
            setReindexing(false)
            setReindexMessage(
              `Re-index complete: ${res.job.files_indexed} files, ${res.job.chunks} chunks.`,
            )
            setRagStats({
              files_indexed: res.job.files_indexed,
              chunks: res.job.chunks,
              last_index: res.job.last_index,
              online: true,
            })
          } else if (res.status === 'failed' && res.job) {
            if (pollRef.current) window.clearInterval(pollRef.current)
            pollRef.current = null
            setReindexing(false)
            setReindexMessage(
              `Re-index failed: ${res.job.error || 'unknown error'}`,
            )
          }
        } catch (err) {
          if (pollRef.current) window.clearInterval(pollRef.current)
          pollRef.current = null
          setReindexing(false)
          setReindexMessage(
            `Re-index failed: ${err instanceof Error ? err.message : 'unknown error'}`,
          )
        }
      }, 1500)
    } catch (err) {
      setReindexing(false)
      setReindexMessage(
        `Re-index failed: ${err instanceof Error ? err.message : 'unknown error'}`,
      )
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || !selectedProject) return
    setSearching(true)
    setSearchError(null)
    try {
      const data = await ragSearch(selectedProject, query)
      setResults(Array.isArray(data) ? data : [data])
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setSearching(false)
    }
  }

  return (
    <div>
      {/* Page Header — matches prototype .page-title */}
      <div className="flex items-start justify-between mb-[22px]">
        <div>
          <h2 className="text-[26px] font-bold text-foreground m-0 mb-[5px]">
            RAG Manager
          </h2>
          <p className="text-muted text-sm m-0">
            Index coverage, vector retrieval and project context quality.
          </p>
        </div>
        <button
          onClick={handleReindex}
          disabled={reindexing || !selectedProject || ragStats?.online === false}
          className="btn-primary-af text-xs disabled:opacity-50"
        >
          {reindexing ? 'Re-indexing...' : '↻ Re-index Project'}
        </button>
      </div>

      {ragStats?.online === false && (
        <div className="mb-[18px] rounded-[10px] p-4 bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
          <span className="text-lg">🖥</span>
          <div>
            <div className="text-xs font-bold text-foreground">
              Local Agent Workstation Offline
            </div>
            <p className="text-xs text-muted mt-0.5 m-0">
              Connect your workstation to index and search this project.{' '}
              <Link href="/devices" className="text-primary hover:underline font-bold">
                Go to Devices
              </Link>
            </p>
          </div>
        </div>
      )}

      {reindexMessage && (
        <div
          className={`mb-[18px] rounded-[10px] p-3 text-xs font-medium ${
            reindexMessage.startsWith('Re-index failed')
              ? 'bg-red-500/10 text-red-500 border border-red-500/30'
              : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
          }`}
        >
          {reindexMessage}
        </div>
      )}

      {reindexing && (
        <div className="card-af p-4 mb-[18px] flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between text-xs mb-2">
              <span className="font-semibold text-foreground">
                Re-indexing project in background…
              </span>
              <span className="text-muted font-mono">
                {ragStats?.indexing
                  ? `${ragStats.files_scanned ?? 0} / ${ragStats.total_files ?? 0} files · ${ragStats.chunks ?? 0} chunks · ${Math.round(ragStats.progress ?? 0)}%`
                  : reindexJob
                    ? `${reindexJob.files_indexed} files · ${reindexJob.chunks} chunks`
                    : ''}
              </span>
            </div>
            <div className="h-2 bg-surface-secondary rounded-full overflow-hidden border border-border/50">
              <div
                className="h-full bg-gradient-to-r from-[#1b78d2] to-[#6e38c7] rounded-full transition-all duration-500"
                style={{
                  width: ragStats?.indexing
                    ? `${Math.max(2, ragStats.progress ?? 0)}%`
                    : '100%',
                }}
              />
            </div>
            <p className="text-[11px] text-muted mt-2 m-0">
              {ragStats?.indexing && ragStats.current_file
                ? `Indexing ${ragStats.current_file} — you can keep working, it continues in the background.`
                : 'You can keep working — indexing continues in the background.'}
            </p>
          </div>
        </div>
      )}

      {/* RAG Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-[18px] mb-[18px]">
        {[
          ['Files Indexed', ragStats?.files_indexed ?? '—'],
          ['Chunks', ragStats?.chunks ?? '—'],
          ['Coverage', ragStats?.files_indexed ? `${Math.min(100, (ragStats.files_indexed * 10))}%` : '—'],
          ['Last Index', ragStats?.last_index ?? '—'],
        ].map(([label, value]) => (
          <div
            key={label}
            className="card-af p-5"
          >
            <div className="text-xs font-semibold text-muted uppercase tracking-wider">
              {label}
            </div>
            <div className="text-2xl font-bold text-foreground mt-2">{value}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="card-af p-5 space-y-4">
        <h3 className="text-sm font-bold text-foreground m-0">
          Semantic Code Search
        </h3>
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="flex gap-3">
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="input-af max-w-[200px]"
              disabled={loadingProjects}
            >
              {loadingProjects && <option>Loading projects...</option>}
              {!loadingProjects && projects.length === 0 && (
                <option>No projects</option>
              )}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="How are database models structured in this project?"
              className="input-af flex-1"
            />
            <button
              type="submit"
              disabled={searching || !query.trim() || !selectedProject || ragStats?.online === false}
              className="btn-primary-af text-xs disabled:opacity-50"
            >
              {searching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {searchError && (
          <div className="text-xs text-red-500 bg-red-500/10 border border-red-500/30 rounded-[10px] p-3">
            {searchError}
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-3 pt-2">
            {results.map((r: any, i: number) => (
              <div
                key={i}
                className="card-af p-4 flex gap-3 text-xs"
              >
                <div className="w-9 h-9 rounded-[9px] bg-primary/10 text-primary grid place-items-center flex-shrink-0 text-sm font-bold">
                  ◫
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-foreground text-xs m-0 truncate">
                    {r.file || r.file_path || 'Unknown file'}
                    {r.lines && (
                      <span className="font-normal text-muted ml-2">
                        lines {r.lines}
                      </span>
                    )}
                  </h4>
                  <p className="text-muted text-xs mt-1 line-clamp-2 m-0">
                    {r.text || r.content || r.snippet || 'No preview available'}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  {r.score !== undefined && (
                    <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                      {typeof r.score === 'number'
                        ? `${Math.round(r.score * 100)}%`
                        : r.score}
                    </span>
                  )}
                  <div className="text-[10px] text-muted mt-0.5">similarity</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {results.length === 0 && !searching && query && (
          <div className="text-center py-8">
            <p className="text-sm text-muted">
              No results found. Try a different query or select a different project.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
