'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import {
  listProjects,
  ragSearch,
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
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">RAG Manager</h1>
          <p className="text-sm text-gray-400 mt-1">
            Semantic code search and vector index management for your projects.
          </p>
        </div>
        <button
          onClick={() => {
            /* TODO: real re-index */
          }}
          className="bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs px-4 py-2 rounded-lg transition-colors"
        >
          ↻ Re-index Project
        </button>
      </div>

      {/* RAG Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          ['Files Indexed', '—'],
          ['Chunks', '—'],
          ['Coverage', '—'],
          ['Last Index', '—'],
        ].map(([label, value]) => (
          <div
            key={label}
            className="bg-[#111827] border border-gray-800 rounded-xl p-5"
          >
            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              {label}
            </div>
            <div className="text-2xl font-bold text-white mt-2">{value}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-6">
        <h3 className="text-sm font-semibold text-white mb-4">
          Semantic Code Search
        </h3>
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="flex gap-3">
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
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
              className="flex-1 bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={searching || !query.trim() || !selectedProject}
              className="bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs px-5 py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              {searching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {searchError && (
          <div className="mt-3 text-xs text-red-400 bg-red-950/30 border border-red-800 rounded-lg p-3">
            {searchError}
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="mt-5 space-y-3">
            {results.map((r: any, i: number) => (
              <div
                key={i}
                className="bg-[#0d121f] border border-gray-800 rounded-lg p-4 flex gap-3"
              >
                <div className="w-10 h-10 rounded-lg bg-purple-950/50 border border-purple-800 flex items-center justify-center flex-shrink-0">
                  <span className="text-purple-300 text-sm">◫</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-semibold text-white truncate">
                    {r.file || r.file_path || 'Unknown file'}
                    {r.lines && (
                      <span className="font-normal text-gray-500 ml-2">
                        lines {r.lines}
                      </span>
                    )}
                  </h4>
                  <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                    {r.text || r.content || r.snippet || 'No preview available'}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  {r.score !== undefined && (
                    <span className="text-xs font-bold text-emerald-400">
                      {typeof r.score === 'number'
                        ? `${Math.round(r.score * 100)}%`
                        : r.score}
                    </span>
                  )}
                  <div className="text-[10px] text-gray-500 mt-1">similarity</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {results.length === 0 && !searching && query && (
          <div className="mt-5 text-center py-8">
            <p className="text-sm text-gray-500">
              No results found. Try a different query or select a different project.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
