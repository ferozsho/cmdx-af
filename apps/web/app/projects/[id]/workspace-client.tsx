'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import DiffViewer from '@/components/diff-viewer'

function FileTreeNode({
  node,
  parentPath = '',
  selectedPath,
  onSelectFile,
}: {
  node: any
  parentPath?: string
  selectedPath: string
  onSelectFile: (path: string) => void
}) {
  if (node.type === 'dir') {
    const currentPath = parentPath ? `${parentPath}/${node.name}` : node.name
    return (
      <div className="pl-3 space-y-1">
        <div className="text-gray-400 font-semibold select-none flex items-center gap-1.5 py-0.5">
          <span>📁</span> {node.name}/
        </div>
        <div className="border-l border-gray-800/80 pl-2 space-y-0.5">
          {node.children?.map((child: any, idx: number) => (
            <FileTreeNode
              key={idx}
              node={child}
              parentPath={currentPath}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
            />
          ))}
        </div>
      </div>
    )
  }

  const filePath = parentPath ? `${parentPath}/${node.name}` : node.name
  const isSelected = selectedPath === filePath

  return (
    <button
      onClick={() => onSelectFile(filePath)}
      className={`w-full text-left font-mono text-xs px-2 py-1 rounded flex items-center gap-2 transition-colors ${
        isSelected
          ? 'bg-blue-900/40 text-blue-300 font-bold border border-blue-700/50'
          : 'text-gray-300 hover:bg-gray-800/60 hover:text-white'
      }`}
    >
      <span>📄</span>
      <span className="truncate">{node.name}</span>
    </button>
  )
}

export default function WorkspaceClient({ projectId }: { projectId: string }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  // Read URL search params
  const activeTab = (searchParams.get('tab') || 'agents').toUpperCase() as
    | 'AGENTS'
    | 'FILES'
    | 'RAG'
    | 'GIT'

  const urlFile = searchParams.get('file') || 'plan.md'
  const urlQuery = searchParams.get('q') || ''

  const [prompt, setPrompt] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [events, setEvents] = useState<any[]>([])
  const [ragQuery, setRagQuery] = useState(urlQuery)
  const [ragResults, setRagResults] = useState<any[]>([])

  const [fileTree, setFileTree] = useState<any>(null)
  const [gitStatus, setGitStatus] = useState<any>(null)
  const [selectedFilePath, setSelectedFilePath] = useState<string>(urlFile)
  const [selectedFileContent, setSelectedFileContent] = useState<string>('')
  const [loadingFile, setLoadingFile] = useState<boolean>(false)

  const [agentsState, setAgentsState] = useState<any[]>([
    { name: 'Planning Agent', status: 'PENDING', duration: '-' },
    { name: 'Architecture Agent', status: 'PENDING', duration: '-' },
    { name: 'Visual Analysis Agent', status: 'PENDING', duration: '-' },
    { name: 'UI/UX Agent', status: 'PENDING', duration: '-' },
    { name: 'Documentation Agent', status: 'PENDING', duration: '-' },
    { name: 'Frontend Agent', status: 'PENDING', duration: '-' },
    { name: 'Backend Agent', status: 'PENDING', duration: '-' },
    { name: 'Database Agent', status: 'PENDING', duration: '-' },
    { name: 'Test Agent', status: 'PENDING', duration: '-' },
    { name: 'Validation Agent', status: 'PENDING', duration: '-' },
    { name: 'Git Agent', status: 'PENDING', duration: '-' },
  ])

  // Function to switch tab with URL sync
  const updateUrl = (tab: string, file?: string, q?: string) => {
    const params = new URLSearchParams()
    params.set('tab', tab.toLowerCase())
    if (file) params.set('file', file)
    if (q) params.set('q', q)
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
  }

  // Handle file selection with URL search param
  const handleSelectFile = async (path: string) => {
    setSelectedFilePath(path)
    updateUrl('files', path)
    setLoadingFile(true)
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/projects/${projectId}/files/content?path=${encodeURIComponent(path)}`
      )
      const data = await res.json()
      if (data.content !== undefined) {
        setSelectedFileContent(data.content)
      } else {
        setSelectedFileContent(`// Unable to load content for ${path}`)
      }
    } catch (err) {
      console.error('Failed to load file content:', err)
      setSelectedFileContent(`// Error loading file content for ${path}`)
    } finally {
      setLoadingFile(false)
    }
  }

  // Handle RAG search
  const executeRagSearch = async (queryText: string) => {
    if (!queryText.trim()) return
    updateUrl('rag', undefined, queryText)
    try {
      const res = await fetch(`http://localhost:8000/api/v1/projects/${projectId}/rag/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, top_k: 5 }),
      })
      const data = await res.json()
      setRagResults(data)
    } catch (err) {
      console.error('Failed to search RAG:', err)
    }
  }

  // Subscribe to SSE events
  useEffect(() => {
    const eventSource = new EventSource(`http://localhost:8000/api/v1/projects/${projectId}/stream`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const time = new Date().toLocaleTimeString()

        setEvents((prev) => [
          ...prev,
          { time, text: `[${data.agent_name || 'System'}] ${data.message}` },
        ])

        if (data.agent_name) {
          setAgentsState((prev) =>
            prev.map((ag) => {
              if (ag.name === data.agent_name) {
                return {
                  ...ag,
                  status: data.status,
                  duration: data.status === 'COMPLETED' ? '1.0s' : ag.duration,
                }
              }
              return ag
            })
          )
        }

        if (data.agent_name === 'Git Agent' && data.status === 'COMPLETED') {
          setIsRunning(false)
        }
      } catch (err) {
        console.error('SSE Error:', err)
      }
    }

    return () => {
      eventSource.close()
    }
  }, [projectId])

  // Sync state when tab changes
  useEffect(() => {
    if (activeTab === 'FILES') {
      if (!fileTree) {
        fetch(`http://localhost:8000/api/v1/projects/${projectId}/tree`)
          .then((res) => res.json())
          .then((data) => setFileTree(data))
          .catch((err) => console.error('Failed to load file tree:', err))
      }
      if (urlFile) {
        handleSelectFile(urlFile)
      }
    }
    if (activeTab === 'RAG' && urlQuery && ragResults.length === 0) {
      executeRagSearch(urlQuery)
    }
    if (activeTab === 'GIT' && !gitStatus) {
      fetch(`http://localhost:8000/api/v1/projects/${projectId}/git/status`)
        .then((res) => res.json())
        .then((data) => setGitStatus(data))
        .catch((err) => console.error('Failed to load git status:', err))
    }
  }, [activeTab, projectId])

  const handleStartPipeline = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) return
    setIsRunning(true)
    setEvents((prev) => [
      ...prev,
      { time: new Date().toLocaleTimeString(), text: `[Instruction Submitted] ${prompt}` },
    ])

    setAgentsState((prev) => prev.map((ag) => ({ ...ag, status: 'PENDING', duration: '-' })))

    try {
      await fetch(`http://localhost:8000/api/v1/projects/${projectId}/instructions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })
    } catch (err) {
      console.error('Failed to trigger instruction pipeline:', err)
      setIsRunning(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white">Commerce Platform</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
              ● FEROZ-PC (Connected)
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Local Workspace: <code className="text-gray-200">D:\Projects\cmdx-framework</code>
          </p>
        </div>

        {/* Tab Navigation Links */}
        <nav className="flex gap-2">
          {(['AGENTS', 'FILES', 'RAG', 'GIT'] as TabType[]).map((tab) => {
            const isActive = activeTab === tab
            const href = `/projects/${projectId}?tab=${tab.toLowerCase()}`
            return (
              <Link
                key={tab}
                href={href}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/30'
                    : 'bg-[#111827] text-gray-400 hover:text-white border border-gray-800'
                }`}
              >
                {tab}
              </Link>
            )
          })}
        </nav>
      </header>

      {/* Instruction Form */}
      <section className="bg-[#111827] border border-gray-800 rounded-xl p-4">
        <form onSubmit={handleStartPipeline} className="flex gap-3">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Create payment management module with FastAPI endpoints, React admin table, unit tests, and git commit..."
            className="flex-1 bg-[#0d121f] border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={isRunning}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-lg transition-colors"
          >
            {isRunning ? 'Running Pipeline...' : 'Run Instruction'}
          </button>
        </form>
      </section>

      {/* Main Tab Content */}
      {activeTab === 'AGENTS' && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Agent Sequence List */}
          <div className="md:col-span-1 space-y-3">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Agent Sequence</h2>
            <div className="space-y-2">
              {agentsState.map((ag) => (
                <div
                  key={ag.name}
                  className="bg-[#111827] border border-gray-800 rounded-lg p-3 flex items-center justify-between text-xs"
                >
                  <span className="font-medium text-white">{ag.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500">{ag.duration}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        ag.status === 'COMPLETED'
                          ? 'bg-emerald-950 text-emerald-400'
                          : ag.status === 'RUNNING'
                          ? 'bg-blue-950 text-blue-400 animate-pulse'
                          : 'bg-gray-800 text-gray-400'
                      }`}
                    >
                      {ag.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Live Event Console */}
          <div className="md:col-span-2 bg-[#111827] border border-gray-800 rounded-xl p-4 flex flex-col h-[500px]">
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Live Event Console</h2>
            <div className="flex-1 bg-[#090d16] border border-gray-900 rounded-lg p-3 font-mono text-xs overflow-y-auto space-y-2">
              <div className="text-gray-500">[System] Connected to WSS stream for project {projectId}</div>
              {events.map((ev, i) => (
                <div key={i} className="text-emerald-400">
                  <span className="text-gray-500">[{ev.time}]</span> {ev.text}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {activeTab === 'FILES' && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* File Tree Panel */}
          <div className="md:col-span-1 bg-[#111827] border border-gray-800 rounded-xl p-4 text-xs text-gray-300 space-y-2 max-h-[600px] overflow-y-auto">
            <div className="text-sm font-semibold text-white font-sans mb-3 flex items-center justify-between">
              <span>Live Workspace File Tree</span>
              <span className="text-[10px] bg-blue-950 text-blue-400 border border-blue-800 px-2 py-0.5 rounded font-mono">
                WSS Connected
              </span>
            </div>
            {fileTree ? (
              <div className="space-y-1 font-mono">
                <div className="font-bold text-blue-400 flex items-center gap-1.5 pb-1">
                  <span>📁</span> {fileTree.name}/
                </div>
                {fileTree.children?.map((node: any, idx: number) => (
                  <FileTreeNode
                    key={idx}
                    node={node}
                    parentPath=""
                    selectedPath={selectedFilePath}
                    onSelectFile={handleSelectFile}
                  />
                ))}
              </div>
            ) : (
              <div className="text-gray-500 font-mono animate-pulse">Loading live workspace tree...</div>
            )}
          </div>

          {/* File Code / Diff Viewer Panel */}
          <div className="md:col-span-2 space-y-2">
            {loadingFile ? (
              <div className="bg-[#111827] border border-gray-800 rounded-xl p-12 text-center text-xs text-gray-400 font-mono animate-pulse">
                Fetching file content from local workstation over WSS...
              </div>
            ) : (
              <DiffViewer
                filePath={selectedFilePath || 'Select a file'}
                originalCode="// Baseline snapshot"
                modifiedCode={selectedFileContent || '// Select a file from the tree to view contents'}
              />
            )}
          </div>
        </section>
      )}

      {activeTab === 'RAG' && (
        <section className="bg-[#111827] border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white">Local RAG Semantic Search</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              executeRagSearch(ragQuery)
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={ragQuery}
              onChange={(e) => setRagQuery(e.target.value)}
              placeholder="Search codebase semantically (e.g. payment processing logic)..."
              className="flex-1 bg-[#0d121f] border border-gray-800 rounded-lg px-3 py-2 text-xs text-white"
            />
            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg text-xs font-semibold">
              Search RAG
            </button>
          </form>

          {ragResults.length > 0 && (
            <div className="space-y-3 pt-2">
              {ragResults.map((res, i) => (
                <article key={i} className="bg-[#0d121f] border border-gray-800 rounded-lg p-3 text-xs space-y-1 font-mono">
                  <div className="flex justify-between text-blue-400 font-sans font-semibold">
                    <span>
                      {res.file_path} (Lines {res.start_line}-{res.end_line})
                    </span>
                    <span>Relevance: {(res.score * 100).toFixed(0)}%</span>
                  </div>
                  <pre className="text-gray-300 bg-[#090d16] p-2 rounded overflow-x-auto">{res.content}</pre>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {activeTab === 'GIT' && (
        <section className="bg-[#111827] border border-gray-800 rounded-xl p-6 text-xs space-y-4">
          <h2 className="text-sm font-semibold text-white">Local Git Isolation Status</h2>
          {gitStatus ? (
            <div className="bg-[#0d121f] border border-gray-800 rounded-lg p-4 font-mono space-y-2 text-gray-300">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-gray-500">Active Branch: </span>
                  <span className="text-blue-400 font-bold">{gitStatus.branch}</span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    gitStatus.is_dirty
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-emerald-950 text-emerald-400'
                  }`}
                >
                  {gitStatus.is_dirty ? 'Dirty (Uncommitted Changes)' : 'Clean Working Tree'}
                </span>
              </div>
              {gitStatus.modified_files?.length > 0 && (
                <div>
                  <div className="text-gray-500 mt-2 font-sans font-semibold">Modified Files:</div>
                  {gitStatus.modified_files.map((f: string, i: number) => (
                    <div key={i} className="text-amber-400 pl-2">
                      ~ {f}
                    </div>
                  ))}
                </div>
              )}
              {gitStatus.untracked_files?.length > 0 && (
                <div>
                  <div className="text-gray-500 mt-2 font-sans font-semibold">Untracked Files:</div>
                  {gitStatus.untracked_files.map((f: string, i: number) => (
                    <div key={i} className="text-emerald-400 pl-2">
                      + {f}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-gray-500 font-mono animate-pulse">
              Fetching live Git repository status from local agent...
            </div>
          )}
        </section>
      )}
    </div>
  )
}
