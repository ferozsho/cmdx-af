'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  listProjects,
  ragSearch,
  getRagStats,
  type ProjectResponse,
} from '@/lib/api'

export default function RagManagerPage() {
  const [projects, setProjects] = useState<ProjectResponse[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [ragStats, setRagStats] = useState<{
    files_indexed: number
    chunks: number
    last_index: string | null
  } | null>(null)

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

  // Fetch RAG stats when project changes
  useEffect(() => {
    if (!selectedProject) return
    getRagStats(selectedProject)
      .then((data) => setRagStats(data))
      .catch(() => setRagStats(null))
  }, [selectedProject])

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
          onClick={() => {
            /* TODO: real re-index */
          }}
          className="btn-primary-af text-xs"
        >
          ↻ Re-index Project
        </button>
      </div>

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
              disabled={searching || !query.trim() || !selectedProject}
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
