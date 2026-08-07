'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import DiffViewer from '@/components/diff-viewer'
import {
  getProject,
  getProjectTree,
  getFileContent,
  ragSearch,
  getGitStatus,
  submitInstruction,
  buildSSEUrl,
  type ProjectResponse,
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
}: {
  node: any
  parentPath?: string
  selectedPath: string
  onSelectFile: (path: string) => void
  gitStatus?: any
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

  // Open if user explicitly expanded OR if it is an ancestor of the selected file
  const isOpen = userExpanded !== null ? userExpanded : isAncestorOfSelected

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
            {node.children?.map((child: any) => {
              const childPath = currentPath ? `${currentPath}/${child.name}` : child.name
              return (
                <FileTreeNode
                  key={childPath}
                  node={child}
                  parentPath={currentPath}
                  selectedPath={selectedPath}
                  onSelectFile={onSelectFile}
                  gitStatus={gitStatus}
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

export default function WorkspaceClient({ projectId }: { projectId: string }) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

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

  // Read URL search params
  const activeTab = (getParam('tab') || 'agents').toUpperCase() as
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

  const [fileTree, setFileTree] = useState<any>(null)
  const [fileTreeError, setFileTreeError] = useState<string | null>(null)
  const [gitStatus, setGitStatus] = useState<any>(null)
  const [selectedFilePath, setSelectedFilePath] = useState<string>(cleanPath(urlFile))
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

  // Function to switch tab with URL sync
  const updateUrl = (tab: string, file?: string, q?: string) => {
    const cleanTab = cleanPath(tab).toLowerCase()
    const cleanFile = cleanPath(file)
    const cleanQ = cleanPath(q)

    const params = new URLSearchParams()
    params.set('tab', cleanTab)
    if (cleanFile) params.set('file', cleanFile)
    if (cleanQ) params.set('q', cleanQ)
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
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
      } else {
        setSelectedFileContent(`// Unable to load content for ${targetPath}`)
      }
    } catch (err) {
      console.error('Failed to load file content:', err)
      setSelectedFileContent(`// Error loading file content for ${targetPath}`)
    } finally {
      setLoadingFile(false)
    }
  }

  // Handle RAG search
  const executeRagSearch = async (queryText: string) => {
    if (!queryText.trim()) return
    updateUrl('rag', undefined, queryText)
    try {
      const data = await ragSearch(projectId, queryText)
      setRagResults(Array.isArray(data) ? data : [data])
    } catch (err) {
      console.error('Failed to search RAG:', err)
    }
  }

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
      if (!fileTree && !fileTreeError) {
        getProjectTree(projectId)
          .then((data) => {
            setFileTree(data)
            setFileTreeError(null)
          })
          .catch((err) => {
            const msg =
              err instanceof Error ? err.message : 'Failed to load file tree'
            setFileTreeError(msg)
          })
      }
      if (!gitStatus) {
        getGitStatus(projectId)
          .then((data) => setGitStatus(data))
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
        .then((data) => setGitStatus(data))
        .catch((err) => console.error('Failed to load git status:', err))
    }
  }, [activeTab, projectId])

  // One-time URL cleanup: remove any stale %3D (=) artifacts from the file param
  useEffect(() => {
    if (typeof window === 'undefined') return
    const raw = window.location.search
    if (raw.includes('%3D') || raw.includes('%3d')) {
      const cleanFile = cleanPath(searchParams.get('file'))
      const cleanQ = cleanPath(searchParams.get('q'))
      const cleanTab = cleanPath(searchParams.get('tab'))
      const params = new URLSearchParams()
      if (cleanTab) params.set('tab', cleanTab.toLowerCase())
      if (cleanFile) params.set('file', cleanFile)
      if (cleanQ) params.set('q', cleanQ)
      const cleanSearch = params.toString()
      if (cleanSearch && raw !== `?${cleanSearch}`) {
        router.replace(`${pathname}?${cleanSearch}`, { scroll: false })
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
    <div className="max-w-7xl mx-auto space-y-6">
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
            const href = `/projects/${projectId}?tab=${tab.toLowerCase()}`
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

      {/* Instruction Form */}
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
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* File Tree Panel */}
          <div className="md:col-span-1 card-af p-4 text-xs space-y-2 max-h-[600px] overflow-y-auto">
            <div className="text-sm font-semibold text-foreground font-sans mb-3 flex items-center justify-between">
              <span>Live Workspace File Tree</span>
              <span className="text-[10px] bg-primary/15 text-primary border border-primary/30 px-2 py-0.5 rounded font-mono">
                WSS Connected
              </span>
            </div>
            {fileTree ? (
              <div className="space-y-1 font-mono">
                <div className="font-bold text-primary flex items-center gap-1.5 pb-1">
                  <span>📁</span> {fileTree.name}/
                </div>
                {fileTree.children?.map((node: any) => (
                  <FileTreeNode
                    key={node.name}
                    node={node}
                    parentPath=""
                    selectedPath={selectedFilePath}
                    onSelectFile={handleSelectFile}
                    gitStatus={gitStatus}
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
          <div className="md:col-span-2 space-y-2">
            {loadingFile ? (
              <div className="card-af p-12 text-center text-xs text-muted font-mono animate-pulse">
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
        <section className="card-af p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Local RAG Semantic Search</h2>
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
            <button type="submit" className="btn-primary-af text-xs">
              Search RAG
            </button>
          </form>

          {ragResults.length > 0 && (
            <div className="space-y-3 pt-2">
              {ragResults.map((res, i) => (
                <article key={i} className="bg-surface-secondary border border-border rounded-lg p-3 text-xs space-y-1 font-mono">
                  <div className="flex justify-between text-primary font-sans font-semibold">
                    <span>
                      {res.file_path} (Lines {res.start_line}-{res.end_line})
                    </span>
                    <span>Relevance: {(res.score * 100).toFixed(0)}%</span>
                  </div>
                  <pre className="text-foreground-secondary bg-[#090d16] p-2 rounded overflow-x-auto text-xs">{res.content}</pre>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      {activeTab === 'GIT' && (
        <section className="card-af p-6 text-xs space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Local Git Isolation Status</h2>
          {gitStatus ? (
            <div className="bg-surface-secondary border border-border rounded-lg p-4 font-mono space-y-2 text-foreground">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-muted">Active Branch: </span>
                  <span className="text-primary font-bold">{gitStatus.branch}</span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    gitStatus.is_dirty
                      ? 'bg-amber-500/15 text-amber-500 border border-amber-500/30'
                      : 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                  }`}
                >
                  {gitStatus.is_dirty ? 'Dirty (Uncommitted Changes)' : 'Clean Working Tree'}
                </span>
              </div>
              {gitStatus.modified_files?.length > 0 && (
                <div>
                  <div className="text-muted mt-2 font-sans font-semibold">Modified Files:</div>
                  {gitStatus.modified_files.map((f: string, i: number) => (
                    <div key={i} className="text-amber-500 pl-2">
                      ~ {f}
                    </div>
                  ))}
                </div>
              )}
              {gitStatus.untracked_files?.length > 0 && (
                <div>
                  <div className="text-muted mt-2 font-sans font-semibold">Untracked Files:</div>
                  {gitStatus.untracked_files.map((f: string, i: number) => (
                    <div key={i} className="text-emerald-500 pl-2">
                      + {f}
                    </div>
                  ))}
                </div>
              )}
            </div>
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
          <div className="space-y-3">
            {events
              .filter((ev: any) =>
                ev.text?.includes('plan') ||
                ev.text?.includes('artifact') ||
                ev.text?.includes('document'),
              )
              .map((ev: any, i: number) => (
                <div
                  key={i}
                  className="bg-surface-secondary border border-border rounded-lg p-4 flex gap-3"
                >
                  <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-primary text-sm">📋</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="text-xs font-semibold text-foreground">
                      {ev.text?.split(']')[1] || ev.text}
                    </h4>
                    <p className="text-[10px] text-muted mt-1">
                      Generated during pipeline execution
                    </p>
                  </div>
                </div>
              ))}
            {events.filter((ev: any) =>
              ev.text?.includes('plan') ||
              ev.text?.includes('artifact') ||
              ev.text?.includes('document'),
            ).length === 0 && (
              <div className="text-center py-8">
                <p className="text-xs text-muted">
                  No artifacts yet. Run a pipeline to generate implementation
                  artifacts.
                </p>
              </div>
            )}
          </div>
        </section>
      )}

      {activeTab === 'TESTS' && (
        <section className="card-af p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Test Results</h2>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            {[
              ['Total', '—'],
              ['Passed', '—'],
              ['Failed', '—'],
              ['Coverage', '—'],
            ].map(([label, value]) => (
              <div
                key={label}
                className="bg-surface-secondary border border-border rounded-lg p-4 text-center"
              >
                <div className="text-[10px] text-muted uppercase">{label}</div>
                <div className="text-xl font-bold text-foreground mt-1">{value}</div>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted">
            Test results appear here after the Test Agent runs during a pipeline
            execution.
          </p>
        </section>
      )}

      {activeTab === 'VALIDATION' && (
        <section className="card-af p-6 space-y-4">
          <h2 className="text-sm font-semibold text-foreground">Validation Report</h2>
          <div className="space-y-2 text-xs">
            {[
              ['Python Syntax', '—'],
              ['Ruff Lint', '—'],
              ['Ruff Format', '—'],
              ['mypy Type Check', '—'],
              ['Bandit Security', '—'],
              ['Dependency Check', '—'],
              ['Environment Variables', '—'],
            ].map(([check, status]) => (
              <div
                key={check}
                className="flex justify-between py-2 border-b border-border last:border-0"
              >
                <span className="text-foreground-secondary">{check}</span>
                <span className="text-muted font-mono">{status}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted">
            Validation results appear after the Validation Agent completes during
            pipeline execution.
          </p>
        </section>
      )}
    </div>
  )
}
