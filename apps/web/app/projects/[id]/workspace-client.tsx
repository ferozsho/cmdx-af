'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import DiffViewer from '@/components/diff-viewer'
import {
  getProject,
  getProjectTree,
  getFileContent,
  getFileOriginal,
  listArtifacts,
  listProjectRuns,
  type AgentRun,
  ragSearch,
  getRagStats,
  getGitStatus,
  submitInstruction,
  buildSSEUrl,
  type ProjectResponse,
  type RagStats,
} from '@/lib/api'

function formatFileSize(bytes?: number): string {
  if (bytes === undefined || bytes === null) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function cleanPath(str: string | null | undefined): string {
  if (!str) return ''
  let s = str
  try {
    if (s.includes('%')) s = decodeURIComponent(s)
    if (s.includes('%')) s = decodeURIComponent(s)
  } catch {
    // ignore
  }
  return s.replace(/[=%\s]+$/g, '').replace(/^\/+/, '').trim()
}

function hasChangedChild(dirPath: string, gitStatus?: any): boolean {
  if (!gitStatus) return false
  const cleanDir = cleanPath(dirPath)
  const prefix = cleanDir ? `${cleanDir}/` : ''
  const isMatch = (f: string) => {
    const cleanF = cleanPath(f)
    return cleanF.startsWith(prefix)
  }
  return (
    gitStatus.modified_files?.some(isMatch) ||
    gitStatus.untracked_files?.some(isMatch) ||
    gitStatus.staged_files?.some(isMatch) ||
    gitStatus.unpushed_files?.some(isMatch)
  )
}

function FileTreeNode({
  node,
  parentPath = '',
  selectedPath,
  onSelectFile,
  gitStatus,
  mode = 'auto',
}: {
  node: any
  parentPath?: string
  selectedPath: string
  onSelectFile: (path: string) => void
  gitStatus?: any
  mode?: 'auto' | 'collapsed' | 'expanded'
}) {
  const currentPath = parentPath ? `${parentPath}/${node.name}` : node.name

  const cleanSelected = cleanPath(selectedPath)
  const cleanCurrent = cleanPath(currentPath)

  // Directory is an ancestor of selected file if selected path equals or starts with `cleanCurrent/`
  const isAncestorOfSelected =
    node.type === 'dir' &&
    Boolean(cleanSelected && cleanCurrent && (cleanSelected === cleanCurrent || cleanSelected.startsWith(`${cleanCurrent}/`)))

  const [userExpanded, setUserExpanded] = useState<boolean | null>(null)

  // Reset user toggle when selected file changes
  useEffect(() => {
    setUserExpanded(null)
  }, [cleanSelected])

  // Explicit user toggle wins; otherwise honor the global tree mode
  // ('auto' auto-opens ancestors of the selected file)
  const isOpen =
    userExpanded !== null
      ? userExpanded
      : mode === 'collapsed'
        ? false
        : mode === 'expanded'
          ? true
          : isAncestorOfSelected

  if (node.type === 'dir') {
    const dirHasChanges = hasChangedChild(currentPath, gitStatus)

    return (
      <div className="pl-2 space-y-0.5">
        <button
          type="button"
          onClick={() => setUserExpanded(!isOpen)}
          className="w-full text-left font-semibold text-muted hover:text-foreground select-none flex items-center justify-between gap-1.5 py-1 px-1 rounded hover:bg-hover transition-colors cursor-pointer group"
        >
          <div className="flex items-center gap-1.5 truncate min-w-0">
            <span className="text-[10px] text-muted w-3 text-center flex-shrink-0 group-hover:text-primary">
              {isOpen ? '▼' : '▶'}
            </span>
            <span className="flex-shrink-0">📁</span>
            <span className="truncate">{node.name}/</span>
          </div>
          {dirHasChanges && (
            <span
              className="text-[9px] px-1.5 py-0.2 font-sans font-bold rounded bg-amber-500/15 text-amber-500 border border-amber-500/30 flex-shrink-0"
              title="Contains modified/uncommitted files"
            >
              ●
            </span>
          )}
        </button>
        {isOpen && (
          <div className="border-l border-border pl-2 space-y-0.5">
            {(node.children || []).map((child: any) => {
              const childPath = currentPath
                ? `${currentPath}/${child.name}`
                : child.name
              return (
                <FileTreeNode
                  key={childPath}
                  node={child}
                  parentPath={currentPath}
                  selectedPath={selectedPath}
                  onSelectFile={onSelectFile}
                  gitStatus={gitStatus}
                  mode={mode}
                />
              )
            })}
          </div>
        )}
      </div>
    )
  }

  const filePath = currentPath
  const cleanFilePath = cleanPath(filePath)
  const isSelected = cleanSelected === cleanFilePath

  // Status flags
  const isModified = gitStatus?.modified_files?.includes(filePath)
  const isUntracked = gitStatus?.untracked_files?.includes(filePath)
  const isStaged = gitStatus?.staged_files?.includes(filePath)
  const isUnpushed = gitStatus?.unpushed_files?.includes(filePath)

  return (
    <button
      type="button"
      onClick={() => onSelectFile(filePath)}
      className={`w-full text-left font-mono text-xs px-2 py-1.5 rounded flex items-center justify-between gap-2 transition-colors ${
        isSelected
          ? 'bg-primary/15 text-primary font-bold border border-primary/30'
          : 'text-foreground-secondary hover:bg-hover hover:text-foreground'
      }`}
    >
      <div className="flex items-center gap-2 truncate min-w-0">
        <span className="flex-shrink-0">📄</span>
        <span className="truncate">{node.name}</span>
      </div>

      <div className="flex items-center gap-1.5 flex-shrink-0">
        {/* Status Flags */}
        {isModified && (
          <span
            className="text-[9px] px-1.5 py-0.2 font-sans font-bold rounded bg-amber-500/15 text-amber-500 border border-amber-500/30"
            title="Modified locally"
          >
            MODIFIED
          </span>
        )}
        {isUntracked && (
          <span
            className="text-[9px] px-1.5 py-0.2 font-sans font-bold rounded bg-emerald-500/15 text-emerald-500 border border-emerald-500/30"
            title="Untracked new file"
          >
            NEW
          </span>
        )}
        {isStaged && (
          <span
            className="text-[9px] px-1.5 py-0.2 font-sans font-bold rounded bg-blue-500/15 text-blue-500 border border-blue-500/30"
            title="Staged in index"
          >
            STAGED
          </span>
        )}
        {isUnpushed && (
          <span
            className="text-[9px] px-1.5 py-0.2 font-sans font-bold rounded bg-purple-500/15 text-purple-500 border border-purple-500/30"
            title="Unpushed commit"
          >
            UNPUSHED
          </span>
        )}

        {/* File Size */}
        {node.size !== undefined && (
          <span className="text-[10px] text-muted font-sans font-normal">{formatFileSize(node.size)}</span>
        )}
      </div>
    </button>
  )
}

export default function WorkspaceClient({
  projectId,
  initialTab,
}: {
  projectId: string
  initialTab?: string
}) {
  const router = useRouter()
  const searchParams = useSearchParams()

  // Helper to safely parse search parameters even if encoded by proxy/port forwarding
  const getParam = (key: string): string | null => {
    let val = searchParams.get(key)
    if (!val && typeof window !== 'undefined') {
      try {
        const rawSearch = window.location.search
        const match = rawSearch.match(new RegExp(`(?:^|[?&]|%26)${key}=([^&%]*)`, 'i'))
        if (match) val = match[1]
      } catch {
        // ignore
      }
    }
    return val ? cleanPath(val) : null
  }

  // Active tab comes from the URL path segment (/projects/[id]/[tab])
  const activeTab = ((initialTab || 'agents') as string).toUpperCase() as
    | 'AGENTS'
    | 'FILES'
    | 'RAG'
    | 'GIT'
    | 'ARTIFACTS'
    | 'TESTS'
    | 'VALIDATION'

  const urlFile = getParam('file') || ''
  const urlQuery = getParam('q') || ''

  const [prompt, setPrompt] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [events, setEvents] = useState<any[]>([])
  const [ragQuery, setRagQuery] = useState(urlQuery)
  const [ragResults, setRagResults] = useState<any[]>([])
  const [ragStats, setRagStats] = useState<RagStats | null>(null)
  const [ragPage, setRagPage] = useState(0)
  const [ragSearching, setRagSearching] = useState(false)
  const [ragError, setRagError] = useState<string | null>(null)
  const [ragSearched, setRagSearched] = useState(false)

  const [fileTree, setFileTree] = useState<any>(null)
  const [fileTreeError, setFileTreeError] = useState<string | null>(null)
  // File tree collapse/expand control + remount key
  const [treeMode, setTreeMode] = useState<'auto' | 'collapsed' | 'expanded'>(
    'auto',
  )
  const [treeKey, setTreeKey] = useState(0)
  const [gitStatus, setGitStatus] = useState<any>(null)
  const [selectedFilePath, setSelectedFilePath] = useState<string>(cleanPath(urlFile))
  const [selectedFileContent, setSelectedFileContent] = useState<string>('')
  const [selectedFileOriginal, setSelectedFileOriginal] = useState<string>('')
  const [loadingFile, setLoadingFile] = useState<boolean>(false)

  const [artifacts, setArtifacts] = useState<
    {
      id: string
      instruction_id: string
      title: string
      artifact_type: string
      content: string
      created_at: string | null
    }[]
  >([])
  const [artifactsLoading, setArtifactsLoading] = useState(false)

  // Persisted agent runs (for TESTS / VALIDATION tabs)
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [runsLoading, setRunsLoading] = useState(false)

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

  // Store structured results from agent pipeline executions
  const [pipelineResults, setPipelineResults] = useState<Record<string, any>>({})

  // Project data from API
  const [project, setProject] = useState<ProjectResponse | null>(null)
  const [projectLoading, setProjectLoading] = useState(true)
  const [projectError, setProjectError] = useState<string | null>(null)

  // Fetch project details
  useEffect(() => {
    async function loadProject() {
      try {
        const data = await getProject(projectId)
        setProject(data)
      } catch (err) {
        setProjectError(
          err instanceof Error ? err.message : 'Failed to load project',
        )
      } finally {
        setProjectLoading(false)
      }
    }
    loadProject()
  }, [projectId])

  // Function to switch tab with SEO-friendly URL sync:
  // /projects/[id]/[tab]?file=...&q=...
  const updateUrl = (tab: string, file?: string, q?: string) => {
    const cleanTab = cleanPath(tab).toLowerCase()
    const cleanFile = cleanPath(file)
    const cleanQ = cleanPath(q)

    const params = new URLSearchParams()
    if (cleanFile) params.set('file', cleanFile)
    if (cleanQ) params.set('q', cleanQ)
    const qs = params.toString()
    router.push(
      `/projects/${encodeURIComponent(projectId)}/${cleanTab}${
        qs ? `?${qs}` : ''
      }`,
      { scroll: false },
    )
  }

  // Handle file selection with URL search param
  const handleSelectFile = async (path: string) => {
    const targetPath = cleanPath(path)
    if (!targetPath) return
    setSelectedFilePath(targetPath)
    updateUrl('files', targetPath)
    setLoadingFile(true)
    try {
      const data = await getFileContent(projectId, targetPath)
      if (data.content !== undefined) {
        setSelectedFileContent(data.content)
      } else if ((data as any).status === 'offline') {
        setSelectedFileContent(
          '// Workstation offline — connect a device to read this file.',
        )
      } else {
        setSelectedFileContent(`// Unable to load content for ${targetPath}`)
      }
    } catch (err) {
      console.error('Failed to load file content:', err)
      setSelectedFileContent(`// Error loading file content for ${targetPath}`)
    } finally {
      setLoadingFile(false)
    }

    // Fetch git HEAD baseline for the diff view (best-effort)
    setSelectedFileOriginal('')
    try {
      const orig = await getFileOriginal(projectId, targetPath)
      if ((orig as any).status === 'offline') {
        setSelectedFileOriginal('')
      } else {
        setSelectedFileOriginal(orig.content || '')
      }
    } catch (err) {
      console.error('Failed to load file baseline:', err)
      setSelectedFileOriginal('')
    }
  }

  // Handle RAG search
  const executeRagSearch = async (queryText: string) => {
    const q = queryText.trim()
    if (!q) return
    updateUrl('rag', undefined, q)
    setRagSearching(true)
    setRagError(null)
    try {
      const data = await ragSearch(projectId, q, 15)
      if ((data as any)?.status === 'offline') {
        setRagResults([])
        setRagSearched(true)
        setRagError(
          (data as any)?.detail ||
            'Local agent workstation is offline. Start `agentforge start` to enable RAG search.',
        )
        return
      }
      const results = Array.isArray(data) ? data : [data]
      setRagResults(results)
      setRagPage(0)
      setRagSearched(true)
    } catch (err) {
      console.error('Failed to search RAG:', err)
      setRagResults([])
      setRagSearched(true)
      setRagError('Search failed — please try again.')
    } finally {
      setRagSearching(false)
    }
  }

  // Poll live RAG stats while on the RAG tab so progress + last-index stay
  // fresh (covers startup background index, watcher re-index, explicit
  // re-index, and idle stats)
  useEffect(() => {
    if (activeTab !== 'RAG') return
    const tick = async () => {
      try {
        const s = await getRagStats(projectId)
        setRagStats(s)
      } catch {
        // ignore transient errors
      }
    }
    tick()
    const timer = window.setInterval(tick, 2000)
    return () => window.clearInterval(timer)
  }, [activeTab, projectId])

  // Subscribe to SSE events
  useEffect(() => {
    const eventSource = new EventSource(buildSSEUrl(projectId))

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
                  duration:
                    data.status === 'COMPLETED'
                      ? `${(data.data?.duration_seconds || data.duration_seconds || 1).toFixed(1)}s`
                      : ag.duration,
                }
              }
              return ag
            }),
          )
          // Store structured agent output for tabs
          if (data.status === 'COMPLETED' && data.data) {
            setPipelineResults((prev) => ({
              ...prev,
              [data.agent_name]: data.data,
            }))
          }
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
      if (!fileTree && !fileTreeError) {
        getProjectTree(projectId)
          .then((data: any) => {
            if (data?.status === 'offline') {
              setFileTree(null)
              setFileTreeError(
                'Local agent workstation is offline — connect a device to browse files.',
              )
            } else {
              setFileTree(data)
              setFileTreeError(null)
            }
          })
          .catch((err) => {
            const msg =
              err instanceof Error ? err.message : 'Failed to load file tree'
            setFileTreeError(msg)
          })
      }
      if (!gitStatus) {
        getGitStatus(projectId)
          .then((data: any) => {
            setGitStatus(
              data?.status === 'offline' ? { ...data, offline: true } : data,
            )
          })
          .catch((err) => console.error('Failed to load git status:', err))
      }
      if (urlFile) {
        handleSelectFile(urlFile)
      }
    }
    if (activeTab === 'RAG' && urlQuery && ragResults.length === 0) {
      executeRagSearch(urlQuery)
    }
    if (activeTab === 'GIT' && !gitStatus) {
      getGitStatus(projectId)
        .then((data: any) => {
          setGitStatus(
            data?.status === 'offline' ? { ...data, offline: true } : data,
          )
        })
        .catch((err) => console.error('Failed to load git status:', err))
    }
    if (activeTab === 'ARTIFACTS' && artifacts.length === 0 && !artifactsLoading) {
      setArtifactsLoading(true)
      listArtifacts(projectId)
        .then((data) => setArtifacts(data))
        .catch((err) => console.error('Failed to load artifacts:', err))
        .finally(() => setArtifactsLoading(false))
    }
    if (
      (activeTab === 'TESTS' || activeTab === 'VALIDATION') &&
      runs.length === 0 &&
      !runsLoading
    ) {
      setRunsLoading(true)
      listProjectRuns(projectId)
        .then((data) => setRuns(data))
        .catch((err) => console.error('Failed to load runs:', err))
        .finally(() => setRunsLoading(false))
    }
  }, [activeTab, projectId])

  // One-time URL cleanup: strip stale %3D (=) artifacts from query params
  useEffect(() => {
    if (typeof window === 'undefined') return
    const raw = window.location.search
    if (raw.includes('%3D') || raw.includes('%3d')) {
      const cleanFile = cleanPath(searchParams.get('file'))
      const cleanQ = cleanPath(searchParams.get('q'))
      const params = new URLSearchParams()
      if (cleanFile) params.set('file', cleanFile)
      if (cleanQ) params.set('q', cleanQ)
      const cleanSearch = params.toString()
      if (cleanSearch !== raw.replace(/^\?/, '')) {
        const base = window.location.pathname
        router.replace(
          `${base}${cleanSearch ? `?${cleanSearch}` : ''}`,
          { scroll: false },
        )
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
      await submitInstruction(projectId, prompt)
    } catch (err) {
      console.error('Failed to trigger instruction pipeline:', err)
      setIsRunning(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto w-full flex-1 flex flex-col min-h-0 space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-foreground">
              {projectLoading
                ? 'Loading...'
                : project?.name || 'Project'}
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-primary/15 text-primary border border-primary/30">
              ●{' '}
              {project?.execution_target === 'LOCAL'
                ? 'Local · Connected'
                : 'Cloud · Connected'}
            </span>
          </div>
          <p className="text-xs text-muted mt-1">
            {projectLoading
              ? 'Loading project details...'
              : projectError
                ? `Error: ${projectError}`
                : project?.description || 'No description.'}
          </p>
        </div>

        {/* Tab Navigation Links */}
        <nav className="flex gap-2">
          {(['AGENTS', 'FILES', 'RAG', 'GIT', 'ARTIFACTS', 'TESTS', 'VALIDATION'] as const).map((tab) => {
            const isActive = activeTab === tab
            const href = `/projects/${encodeURIComponent(projectId)}/${tab.toLowerCase()}`
            return (
              <Link
                key={tab}
                href={href}
                className={`px-3 py-1.5 rounded-[10px] text-xs font-semibold transition-colors ${
                  isActive
                    ? 'btn-primary-af !px-3 !py-1.5 !text-xs shadow-md'
                    : 'btn-secondary-af !px-3 !py-1.5 !text-xs'
                }`}
              >
                {tab}
              </Link>
            )
          })}
        </nav>
      </header>

      {/* Instruction Form — only on the Agents tab (pipeline launcher belongs
          with the agent sequence; other tabs are for browsing/reviewing) */}
      {activeTab === 'AGENTS' && (
        <section className="card-af p-4">
          <form onSubmit={handleStartPipeline} className="flex gap-3">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Create payment management module with FastAPI endpoints, React admin table, unit tests, and git commit..."
              className="input-af flex-1"
            />
            <button
              type="submit"
              disabled={isRunning}
              className="btn-primary-af text-xs disabled:opacity-50 whitespace-nowrap"
            >
              {isRunning ? 'Running Pipeline...' : 'Run Instruction'}
            </button>
          </form>
        </section>
      )}

      {/* Pipeline Progress Bar */}
      {isRunning && (
        <section className="card-af p-4">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-semibold text-foreground">
              Pipeline Progress
            </span>
            <span className="text-[10px] text-muted">
              {agentsState.filter((a) => a.status === 'COMPLETED').length} /{' '}
              {agentsState.length} agents
            </span>
          </div>
          <div className="w-full bg-surface-secondary rounded-full h-2 overflow-hidden border border-border">
            <div
              className="h-full bg-gradient-to-r from-primary to-primary-hover rounded-full transition-all duration-500"
              style={{
                width: `${Math.round(
                  (agentsState.filter((a) => a.status !== 'PENDING').length /
                    agentsState.length) *
                    100,
                )}%`,
              }}
            />
          </div>
          <div className="flex flex-wrap gap-1 mt-3">
            {agentsState.map((ag) => (
              <span
                key={ag.name}
                className={`text-[9px] px-1.5 py-0.5 rounded ${
                  ag.status === 'COMPLETED'
                    ? 'bg-emerald-500/15 text-emerald-500'
                    : ag.status === 'RUNNING'
                      ? 'bg-primary/15 text-primary animate-pulse'
                      : 'bg-surface-secondary text-muted'
                }`}
              >
                {ag.name.split(' ')[0]}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Main Tab Content */}
      {activeTab === 'AGENTS' && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Agent Sequence List */}
          <div className="md:col-span-1 space-y-3">
            <h2 className="text-sm font-semibold text-muted uppercase tracking-wider">Agent Sequence</h2>
            <div className="space-y-2">
              {agentsState.map((ag) => (
                <div
                  key={ag.name}
                  className="card-af p-3 flex items-center justify-between text-xs"
                >
                  <span className="font-medium text-foreground">{ag.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted">{ag.duration}</span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        ag.status === 'COMPLETED'
                          ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                          : ag.status === 'RUNNING'
                          ? 'bg-primary/15 text-primary animate-pulse'
                          : 'bg-surface-secondary text-muted'
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
          <div className="md:col-span-2 card-af p-4 flex flex-col h-[500px]">
            <h2 className="text-sm font-semibold text-muted uppercase tracking-wider mb-3">
              Live Event Console
            </h2>
            <div className="flex-1 bg-[#0f141e] border border-border/80 rounded-[10px] p-3 font-mono text-xs overflow-y-auto space-y-2 text-[#c8d0df]">
              <div className="text-muted">[System] Connected to SSE stream for project {projectId}</div>
              {events.map((ev, i) => (
                <div key={i} className="text-[#49e56d]">
                  <span className="text-[#7f899c]">[{ev.time}]</span> {ev.text}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {activeTab === 'FILES' && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 min-h-0">
          {/* File Tree Panel */}
          <div className="md:col-span-1 card-af p-4 text-xs space-y-2 min-h-0 max-h-[calc(100vh-219px)] overflow-y-auto">
            <div className="text-sm font-semibold text-foreground font-sans mb-3 flex items-center justify-between gap-2">
              <span>Live Workspace File Tree</span>
              <span className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => {
                    setTreeMode(treeMode === 'expanded' ? 'auto' : 'expanded')
                    setTreeKey((k) => k + 1)
                  }}
                  className="w-6 h-6 grid place-items-center rounded border border-border hover:bg-hover text-muted hover:text-foreground"
                  title={
                    treeMode === 'expanded'
                      ? 'Collapse all folders'
                      : 'Expand all folders'
                  }
                  aria-label={
                    treeMode === 'expanded'
                      ? 'Collapse all folders'
                      : 'Expand all folders'
                  }
                >
                  {treeMode === 'expanded' ? '⤡' : '⤢'}
                </button>
                <span className="text-[10px] bg-primary/15 text-primary border border-primary/30 px-2 py-0.5 rounded font-mono">
                  WSS Connected
                </span>
              </span>
            </div>
            {fileTree ? (
              <div key={treeKey} className="space-y-1 font-mono">
                <div className="font-bold text-primary flex items-center gap-1.5 pb-1">
                  <span>📁</span> {fileTree.name}/
                </div>
                {(fileTree.children || []).map((node: any) => (
                  <FileTreeNode
                    key={node.name}
                    node={node}
                    parentPath=""
                    selectedPath={selectedFilePath}
                    onSelectFile={handleSelectFile}
                    gitStatus={gitStatus}
                    mode={treeMode}
                  />
                ))}
              </div>
            ) : fileTreeError ? (
              <div className="text-red-500 text-xs font-mono">
                ✗ {fileTreeError}
              </div>
            ) : (
              <div className="text-muted font-mono animate-pulse">
                Loading live workspace tree...
              </div>
            )}
          </div>

          {/* File Code / Diff Viewer Panel */}
          <div className="md:col-span-2 space-y-2 min-h-0 max-h-[calc(100vh-219px)]">
            {loadingFile ? (
              <div className="card-af p-12 text-center text-xs text-muted font-mono animate-pulse">
                Fetching file content from local workstation over WSS...
              </div>
            ) : (
              <DiffViewer
                filePath={selectedFilePath || 'Select a file'}
                originalCode={selectedFileOriginal}
                modifiedCode={selectedFileContent || '// Select a file from the tree to view contents'}
              />
            )}
          </div>
        </section>
      )}

      {activeTab === 'RAG' && (
        <section className="card-af p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Local RAG Semantic Search
          </h2>

          {/* Live index status / background progress */}
          {ragStats?.indexing ? (
            <div className="rounded-[10px] p-4 bg-primary/5 border border-primary/20">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="font-semibold text-foreground">
                  ⚡ Indexing workspace in background…
                </span>
                <span className="text-muted font-mono">
                  {ragStats.files_scanned ?? 0} / {ragStats.total_files ?? 0}{' '}
                  files · {ragStats.chunks ?? 0} chunks ·{' '}
                  {Math.round(ragStats.progress ?? 0)}%
                </span>
              </div>
              <div className="h-2 bg-surface-secondary rounded-full overflow-hidden border border-border/50">
                <div
                  className="h-full bg-gradient-to-r from-primary to-primary-hover rounded-full transition-all duration-500"
                  style={{ width: `${Math.max(2, ragStats.progress ?? 0)}%` }}
                />
              </div>
              {ragStats.current_file && (
                <p className="text-[11px] text-muted mt-2 m-0 truncate">
                  Now indexing: {ragStats.current_file}
                </p>
              )}
            </div>
          ) : ragStats && ragStats.online !== false ? (
            <div className="flex items-center justify-between text-xs text-muted bg-surface-secondary border border-border rounded-[10px] px-4 py-3">
              <span>
                <span className="font-semibold text-foreground">
                  {ragStats.files_indexed ?? 0}
                </span>{' '}
                files indexed ·{' '}
                <span className="font-semibold text-foreground">
                  {ragStats.chunks ?? 0}
                </span>{' '}
                chunks
              </span>
              {ragStats.last_index && (
                <span>Last indexed: {ragStats.last_index}</span>
              )}
            </div>
          ) : null}

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
              className="input-af flex-1"
            />
            <button
              type="submit"
              className="btn-primary-af text-xs disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={ragSearching}
            >
              {ragSearching ? 'Searching…' : 'Search RAG'}
            </button>
          </form>

          {/* Live search feedback — shown below the form where results render */}
          {ragSearching && (
            <div
              role="status"
              aria-live="polite"
              className="flex items-center gap-3 rounded-[10px] border border-primary/20 bg-primary/5 px-4 py-3.5 text-xs"
            >
              <span className="h-4 w-4 flex-shrink-0 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              <span className="text-foreground">
                Searching workspace for{' '}
                <span className="font-mono text-primary">
                  “{ragQuery.trim()}”
                </span>
                …
              </span>
            </div>
          )}

          {!ragSearching && ragError && (
            <div className="rounded-[10px] border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-500">
              ⚠ {ragError}
            </div>
          )}

          {!ragSearching && !ragError && ragSearched && ragResults.length === 0 && (
            <div className="rounded-[10px] border border-border bg-surface-secondary px-4 py-3 text-xs text-muted">
              No results found for{' '}
              <span className="font-mono text-foreground">
                “{ragQuery.trim()}”
              </span>
            </div>
          )}

          {ragResults.length > 0 && (
            <div className="space-y-3 pt-2">
              {ragResults
                .slice(ragPage * 5, ragPage * 5 + 5)
                .map((res, i) => (
                  <article
                    key={i}
                    className="bg-surface-secondary border border-border rounded-lg p-3 text-xs space-y-1 font-mono"
                  >
                    <div className="flex justify-between text-primary font-sans font-semibold">
                      <span>
                        {res.file_path} (Lines {res.start_line}-{res.end_line})
                      </span>
                      <span>Relevance: {(res.score * 100).toFixed(0)}%</span>
                    </div>
                    <pre className="text-foreground-secondary bg-[#090d16] p-2 rounded overflow-x-auto text-xs">
                      {res.content}
                    </pre>
                  </article>
                ))}
              {ragResults.length > 5 && (
                <div className="flex items-center gap-1.5 justify-end pt-1 text-[10px] text-muted select-none">
                  <button
                    type="button"
                    disabled={ragPage === 0}
                    onClick={() => setRagPage((p) => Math.max(0, p - 1))}
                    className="px-1.5 py-0.5 rounded border border-border hover:bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
                    aria-label="Previous results page"
                  >
                    ‹
                  </button>
                  <span className="font-mono">
                    {ragPage + 1}/
                    {Math.ceil(ragResults.length / 5)} · {ragResults.length}{' '}
                    results
                  </span>
                  <button
                    type="button"
                    disabled={
                      ragPage >= Math.ceil(ragResults.length / 5) - 1
                    }
                    onClick={() => setRagPage((p) => p + 1)}
                    className="px-1.5 py-0.5 rounded border border-border hover:bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
                    aria-label="Next results page"
                  >
                    ›
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {activeTab === 'GIT' && (
        <section className="card-af p-6 text-xs space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Local Git Status
          </h2>
          {gitStatus?.offline ? (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex items-start gap-3">
              <span className="text-lg">🖥</span>
              <div>
                <div className="text-xs font-bold text-foreground">
                  Local Agent Workstation Offline
                </div>
                <p className="text-xs text-muted mt-0.5 m-0">
                  {gitStatus.detail ||
                    'Connect your workstation to view live git status.'}
                </p>
              </div>
            </div>
          ) : gitStatus ? (
            <>
              <div className="bg-surface-secondary border border-border rounded-lg p-4 font-mono space-y-2 text-foreground">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-muted">Active Branch: </span>
                    <span className="text-primary font-bold">
                      {gitStatus.branch}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      gitStatus.is_dirty
                        ? 'bg-amber-500/15 text-amber-500 border border-amber-500/30'
                        : 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                    }`}
                  >
                    {gitStatus.is_dirty
                      ? 'Dirty (Uncommitted)'
                      : 'Clean Working Tree'}
                  </span>
                </div>
                {gitStatus.staged_files?.length > 0 && (
                  <div>
                    <div className="text-muted mt-2 font-sans font-semibold">
                      Staged:
                    </div>
                    {gitStatus.staged_files.map((f: string, i: number) => (
                      <div key={i} className="text-primary pl-2">
                        ● {f}
                      </div>
                    ))}
                  </div>
                )}
                {gitStatus.modified_files?.length > 0 && (
                  <div>
                    <div className="text-muted mt-2 font-sans font-semibold">
                      Modified:
                    </div>
                    {gitStatus.modified_files.map((f: string, i: number) => (
                      <div key={i} className="text-amber-500 pl-2">
                        ~ {f}
                      </div>
                    ))}
                  </div>
                )}
                {gitStatus.untracked_files?.length > 0 && (
                  <div>
                    <div className="text-muted mt-2 font-sans font-semibold">
                      Untracked:
                    </div>
                    {gitStatus.untracked_files.map((f: string, i: number) => (
                      <div key={i} className="text-emerald-500 pl-2">
                        + {f}
                      </div>
                    ))}
                  </div>
                )}
                {gitStatus.unpushed_files?.length > 0 && (
                  <div>
                    <div className="text-muted mt-2 font-sans font-semibold">
                      Unpushed:
                    </div>
                    {gitStatus.unpushed_files.map((f: string, i: number) => (
                      <div key={i} className="text-blue-500 pl-2">
                        ↑ {f}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {pipelineResults['Git Agent'] && (
                <div className="bg-surface-secondary border border-border rounded-lg p-4 space-y-2">
                  <div className="text-xs font-semibold text-foreground">
                    Last Agent Commit
                  </div>
                  <div className="font-mono text-xs">
                    <span className="text-muted">Branch: </span>
                    <span className="text-primary">
                      {pipelineResults['Git Agent'].branch}
                    </span>
                  </div>
                  <div className="font-mono text-xs">
                    <span className="text-muted">Message: </span>
                    <span className="text-foreground">
                      {pipelineResults['Git Agent'].commit_message}
                    </span>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-muted font-mono animate-pulse">
              Fetching live Git repository status from local agent...
            </div>
          )}
        </section>
      )}

      {activeTab === 'ARTIFACTS' && (
        <section className="card-af p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Generated Artifacts</h2>
          <p className="text-xs text-muted">
            Implementation plans, architecture documents, UI specs, test reports,
            and validation reports appear here after each pipeline run.
          </p>
          {artifactsLoading ? (
            <div className="flex items-center gap-2.5 text-xs text-muted">
              <span className="h-3.5 w-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              Loading artifacts…
            </div>
          ) : artifacts.length > 0 ? (
            <div className="space-y-3">
              {artifacts.map((art) => (
                <details
                  key={art.id}
                  className="bg-surface-secondary border border-border rounded-lg p-4"
                >
                  <summary className="flex items-center gap-3 cursor-pointer list-none">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-primary text-sm">📋</span>
                    </div>
                    <div className="flex-1">
                      <h4 className="text-xs font-semibold text-foreground">
                        {art.title}
                      </h4>
                      <p className="text-[10px] text-muted mt-0.5">
                        {art.artifact_type}
                        {art.created_at
                          ? ` · ${new Date(art.created_at).toLocaleString()}`
                          : ''}
                      </p>
                    </div>
                    <span className="text-[10px] text-muted font-mono">
                      {art.content.length} chars
                    </span>
                    <button
                      type="button"
                      onClick={async (e) => {
                        e.preventDefault()
                        try {
                          await navigator.clipboard.writeText(art.content)
                        } catch {
                          // clipboard unavailable
                        }
                      }}
                      className="text-[10px] px-2 py-1 rounded border border-border hover:bg-hover text-muted hover:text-foreground flex-shrink-0"
                      title="Copy artifact content"
                    >
                      📋 Copy
                    </button>
                  </summary>
                  <pre className="mt-3 bg-[#0d121f] border border-border/60 rounded-lg p-3 text-[11px] text-foreground-secondary font-mono whitespace-pre-wrap overflow-x-auto">
                    {art.content}
                  </pre>
                </details>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-xs text-muted">
                No artifacts yet. Run a pipeline to generate implementation
                artifacts.
              </p>
            </div>
          )}
        </section>
      )}

      {activeTab === 'TESTS' && (
        <section className="card-af p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Test Results
          </h2>
          <p className="text-xs text-muted">
            Latest Test Agent run — loaded from persisted pipeline history.
          </p>
          {(() => {
            const run = runs.find(
              (r) => r.agent_name === 'Test Agent' && r.metadata,
            )
            const meta = ((run?.metadata as any) ||
              pipelineResults['Test Agent']) as any

            if (runsLoading && !meta) {
              return (
                <div className="text-xs text-muted animate-pulse">
                  Loading test results…
                </div>
              )
            }
            if (!meta) {
              return (
                <div className="text-center py-8">
                  <p className="text-xs text-muted">
                    No test results yet. Run a pipeline to generate and
                    persist test reports.
                  </p>
                </div>
              )
            }
            const passed = Number(meta.tests_passed || 0)
            const failed = Number(meta.tests_failed || 0)
            return (
              <>
                {run && (
                  <div className="text-[10px] text-muted font-mono">
                    Latest run:{' '}
                    {run.created_at
                      ? new Date(run.created_at).toLocaleString()
                      : 'recently'}{' '}
                    · {run.status} · {run.duration_seconds.toFixed(1)}s
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                  {[
                    ['Total', passed + failed],
                    ['Passed', passed],
                    ['Failed', failed],
                    ['Coverage', `${meta.coverage_percent || 0}%`],
                  ].map(([label, value]) => (
                    <div
                      key={label as string}
                      className="bg-surface-secondary border border-border rounded-lg p-4 text-center"
                    >
                      <div className="text-[10px] text-muted uppercase">
                        {label}
                      </div>
                      <div
                        className={`text-xl font-bold mt-1 ${
                          label === 'Failed' && Number(value) > 0
                            ? 'text-red-500'
                            : 'text-foreground'
                        }`}
                      >
                        {String(value)}
                      </div>
                    </div>
                  ))}
                </div>
                {meta.test_summary && (
                  <div className="bg-surface-secondary border border-border rounded-lg p-4">
                    <div className="text-xs font-semibold text-foreground mb-1">
                      Summary
                    </div>
                    <p className="text-xs text-muted">{meta.test_summary}</p>
                  </div>
                )}
                {Array.isArray(meta.tests_generated) &&
                  meta.tests_generated.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-foreground mb-2">
                        Test Files Generated
                      </div>
                      <div className="space-y-1">
                        {meta.tests_generated.map((f: string, i: number) => (
                          <div
                            key={i}
                            className="text-xs font-mono text-emerald-600 dark:text-emerald-400"
                          >
                            ✓ {f}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                {run?.output && (
                  <details className="bg-surface-secondary border border-border rounded-lg p-3">
                    <summary className="text-xs font-semibold text-foreground cursor-pointer">
                      Raw output
                    </summary>
                    <pre className="mt-2 text-[11px] text-muted font-mono whitespace-pre-wrap">
                      {run.output}
                    </pre>
                  </details>
                )}
              </>
            )
          })()}
        </section>
      )}

      {activeTab === 'VALIDATION' && (
        <section className="card-af p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">
            Validation Report
          </h2>
          <p className="text-xs text-muted">
            Latest Validation Agent run — loaded from persisted pipeline
            history.
          </p>
          {(() => {
            const run = runs.find(
              (r) => r.agent_name === 'Validation Agent' && r.metadata,
            )
            const meta = ((run?.metadata as any) ||
              pipelineResults['Validation Agent']) as any

            if (runsLoading && !meta) {
              return (
                <div className="text-xs text-muted animate-pulse">
                  Loading validation report…
                </div>
              )
            }
            if (!meta) {
              return (
                <div className="text-center py-8">
                  <p className="text-xs text-muted">
                    No validation report yet. Run a pipeline to lint, typecheck,
                    and security-scan the generated code.
                  </p>
                </div>
              )
            }
            return (
              <>
                {run && (
                  <div className="text-[10px] text-muted font-mono">
                    Latest run:{' '}
                    {run.created_at
                      ? new Date(run.created_at).toLocaleString()
                      : 'recently'}{' '}
                    · {run.status} · {run.duration_seconds.toFixed(1)}s
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    [
                      'Lint Issues',
                      meta.lint_issues || 0,
                      'text-amber-500',
                    ],
                    [
                      'Type Errors',
                      meta.type_errors || 0,
                      'text-red-500',
                    ],
                    [
                      'Security Issues',
                      meta.security_issues || 0,
                      'text-red-500',
                    ],
                  ].map(([label, value, color]) => (
                    <div
                      key={label as string}
                      className="bg-surface-secondary border border-border rounded-lg p-4 text-center"
                    >
                      <div className="text-[10px] text-muted uppercase">
                        {label}
                      </div>
                      <div className={`text-xl font-bold mt-1 ${color}`}>
                        {String(value)}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted">Build Status:</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      meta.build_status === 'PASSED'
                        ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                        : 'bg-red-500/15 text-red-500 border border-red-500/30'
                    }`}
                  >
                    {meta.build_status || '—'}
                  </span>
                </div>
                {Array.isArray(meta.auto_fixes_applied) &&
                  meta.auto_fixes_applied.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-foreground mb-2">
                        Auto-Fixes Applied
                      </div>
                      <div className="space-y-1">
                        {meta.auto_fixes_applied.map(
                          (f: string, i: number) => (
                            <div
                              key={i}
                              className="text-xs font-mono text-primary"
                            >
                              🔧 {f}
                            </div>
                          ),
                        )}
                      </div>
                    </div>
                  )}
                {Array.isArray(meta.recommendations) &&
                  meta.recommendations.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-foreground mb-2">
                        Recommendations
                      </div>
                      <ul className="space-y-1">
                        {meta.recommendations.map((r: string, i: number) => (
                          <li
                            key={i}
                            className="text-xs text-muted flex gap-2"
                          >
                            <span className="text-primary">→</span> {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                {run?.output && (
                  <details className="bg-surface-secondary border border-border rounded-lg p-3">
                    <summary className="text-xs font-semibold text-foreground cursor-pointer">
                      Raw output
                    </summary>
                    <pre className="mt-2 text-[11px] text-muted font-mono whitespace-pre-wrap">
                      {run.output}
                    </pre>
                  </details>
                )}
              </>
            )
          })()}
        </section>
      )}
    </div>
  )
}
