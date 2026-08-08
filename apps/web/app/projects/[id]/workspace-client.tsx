'use client'

import React, { useState, useEffect, useRef } from 'react'
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
  listRagChunks,
  listProjectAgents,
  configureProjectAgent,
  updateProject,
  type AgentRun,
  type ProjectAgentResponse,
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

// RAG results rendered per page
const PAGE_SIZE = 10

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
    | 'SETTINGS'

  const urlFile = getParam('file') || ''
  const urlQuery = getParam('q') || ''
  const urlPage = Math.max(0, parseInt(getParam('page') || '0', 10) || 0)
  const urlView: 'chunks' | 'search' =
    getParam('view') === 'search' ? 'search' : 'chunks'
  const urlChunksPage = Math.max(
    0,
    parseInt(getParam('cpage') || '0', 10) || 0,
  )

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
  // RAG result cards are collapsed by default; expand on click. Toggled by
  // global result index (stable across pagination).
  const [expandedResults, setExpandedResults] = useState<Set<number>>(
    () => new Set(),
  )
  // RAG browse view: "All Chunks" (default) vs search results
  const [ragView, setRagView] = useState<'chunks' | 'search'>(urlView)
  const [ragChunks, setRagChunks] = useState<any[]>([])
  const [ragChunksTotal, setRagChunksTotal] = useState(0)
  const [ragChunksLoading, setRagChunksLoading] = useState(false)
  const [chunksPage, setChunksPage] = useState(0)
  // Chunk cards collapsed by default; toggled by chunk id (stable across
  // pagination)
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(
    () => new Set(),
  )

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

  // Per-project agent configuration (loaded from API, not hardcoded)
  // Extended with runtime pipeline status fields
  const [agentsState, setAgentsState] = useState<(ProjectAgentResponse & { status?: string; duration?: string })[]>([])
  const [agentsLoading, setAgentsLoading] = useState(true)

  // Load per-project agent configuration
  useEffect(() => {
    async function loadAgents() {
      try {
        const data = await listProjectAgents(projectId)
        setAgentsState(data.map((a) => ({ ...a, status: 'PENDING', duration: '-' })))
      } catch (err) {
        console.error('Failed to load project agents:', err)
      } finally {
        setAgentsLoading(false)
      }
    }
    loadAgents()
  }, [projectId])

  // Toggle agent enabled/disabled
  const toggleAgent = async (templateId: string, enabled: boolean) => {
    // Optimistic update
    setAgentsState((prev) =>
      prev.map((a) => (a.template_id === templateId ? { ...a, enabled } : a)),
    )
    try {
      await configureProjectAgent(projectId, { template_id: templateId, enabled })
    } catch (err) {
      console.error('Failed to toggle agent:', err)
      // Revert on failure
      setAgentsState((prev) =>
        prev.map((a) =>
          a.template_id === templateId ? { ...a, enabled: !enabled } : a,
        ),
      )
    }
  }

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
  // /projects/[id]/[tab]?file=...&q=...&page=N&view=chunks|search&cpage=N
  const updateUrl = (
    tab: string,
    file?: string,
    q?: string,
    page?: number,
    view?: string,
    cpage?: number,
  ) => {
    const cleanTab = cleanPath(tab).toLowerCase()
    const cleanFile = cleanPath(file)
    const cleanQ = cleanPath(q)

    const params = new URLSearchParams()
    if (cleanFile) params.set('file', cleanFile)
    if (cleanQ) params.set('q', cleanQ)
    if (page && page > 0) params.set('page', String(page))
    if (view) params.set('view', view)
    if (cpage && cpage > 0) params.set('cpage', String(cpage))
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

  // Handle RAG search. `page` seeds the pagination + URL (?page=N) so a
  // shared/bookmarked URL restores the exact result page.
  const executeRagSearch = async (queryText: string, page = 0) => {
    const q = queryText.trim()
    if (!q) return
    updateUrl('rag', undefined, q, page, 'search')
    setRagView('search')
    setRagSearching(true)
    setRagError(null)
    setExpandedResults(new Set())
    try {
      const data = await ragSearch(projectId, q, 30)
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
      setRagPage(page)
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

  // Load the paginated chunk browser for the default "All Chunks" view.
  const loadRagChunks = async (offset: number) => {
    setRagChunksLoading(true)
    try {
      const data = await listRagChunks(projectId, offset, PAGE_SIZE)
      if ((data as any)?.status === 'offline') {
        setRagChunks([])
        setRagChunksTotal(0)
        return
      }
      setRagChunks(data.chunks || [])
      setRagChunksTotal(data.total || 0)
    } catch (err) {
      console.error('Failed to load RAG chunks:', err)
      setRagChunks([])
      setRagChunksTotal(0)
    } finally {
      setRagChunksLoading(false)
    }
  }

  // RAG pagination — keeps ?page=N in the URL (shareable, SEO-friendly)
  const goToRagPage = (page: number) => {
    const total = Math.ceil(ragResults.length / PAGE_SIZE)
    const next = Math.max(0, Math.min(page, total - 1))
    setRagPage(next)
    updateUrl('rag', undefined, ragQuery, next, 'search')
  }

  // Chunk browse pagination — keeps ?cpage=N in the URL
  const goToChunksPage = (page: number) => {
    const total = Math.ceil(ragChunksTotal / PAGE_SIZE)
    const next = Math.max(0, Math.min(page, total - 1))
    setChunksPage(next)
    loadRagChunks(next * PAGE_SIZE)
    updateUrl('rag', undefined, undefined, 0, 'chunks', next)
  }

  const toggleResult = (idx: number) => {
    setExpandedResults((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const toggleChunk = (id: string) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const switchRagView = (v: 'chunks' | 'search') => {
    setRagView(v)
    if (v === 'chunks') {
      if (ragChunks.length === 0 && !ragChunksLoading) {
        loadRagChunks(chunksPage * PAGE_SIZE)
      }
      updateUrl('rag', undefined, undefined, 0, 'chunks', chunksPage)
    } else {
      updateUrl('rag', undefined, ragQuery, ragPage, 'search')
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

  // Refresh the chunks browser when a background index finishes so the
  // default "All Chunks" view always reflects the latest index.
  const wasIndexingRef = useRef(false)
  useEffect(() => {
    const indexing = ragStats?.indexing === true
    if (wasIndexingRef.current && !indexing && ragStats?.state === 'complete') {
      if (ragView === 'chunks') loadRagChunks(chunksPage * PAGE_SIZE)
    }
    wasIndexingRef.current = indexing
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ragStats?.indexing, ragStats?.state, ragView, chunksPage])

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
              if (ag.template_name === data.agent_name) {
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
      executeRagSearch(urlQuery, urlPage)
    }
    if (
      activeTab === 'RAG' &&
      !urlQuery &&
      ragView === 'chunks' &&
      ragChunks.length === 0 &&
      !ragChunksLoading
    ) {
      loadRagChunks(urlChunksPage * PAGE_SIZE)
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
      const cleanPage = cleanPath(searchParams.get('page'))
      const cleanView = cleanPath(searchParams.get('view'))
      const cleanCpage = cleanPath(searchParams.get('cpage'))
      const params = new URLSearchParams()
      if (cleanFile) params.set('file', cleanFile)
      if (cleanQ) params.set('q', cleanQ)
      if (cleanPage) params.set('page', cleanPage)
      if (cleanView) params.set('view', cleanView)
      if (cleanCpage) params.set('cpage', cleanCpage)
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

    setAgentsState((prev) =>
      prev.map((ag) =>
        ag.enabled ? { ...ag, status: 'PENDING', duration: '-' } : ag,
      ),
    )

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
          {(['AGENTS', 'FILES', 'RAG', 'GIT', 'ARTIFACTS', 'TESTS', 'VALIDATION', 'SETTINGS'] as const).map((tab) => {
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
              {agentsState.filter((a) => a.enabled).length} agents
            </span>
          </div>
          <div className="w-full bg-surface-secondary rounded-full h-2 overflow-hidden border border-border">
            <div
              className="h-full bg-gradient-to-r from-primary to-primary-hover rounded-full transition-all duration-500"
              style={{
                width: `${Math.round(
                  (agentsState.filter((a) => a.status !== 'PENDING').length /
                    Math.max(agentsState.filter((a) => a.enabled).length, 1)) *
                    100,
                )}%`,
              }}
            />
          </div>
          <div className="flex flex-wrap gap-1 mt-3">
            {agentsState.filter((a) => a.enabled).map((ag) => (
              <span
                key={ag.template_id}
                className={`text-[9px] px-1.5 py-0.5 rounded ${
                  ag.status === 'COMPLETED'
                    ? 'bg-emerald-500/15 text-emerald-500'
                    : ag.status === 'RUNNING'
                      ? 'bg-primary/15 text-primary animate-pulse'
                      : 'bg-surface-secondary text-muted'
                }`}
              >
                {ag.template_name.split(' ')[0]}
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
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-muted uppercase tracking-wider">
                Agent Sequence
              </h2>
              {agentsLoading && (
                <span className="text-[10px] text-muted animate-pulse">Loading...</span>
              )}
            </div>
            {!agentsLoading && agentsState.length === 0 && (
              <p className="text-xs text-muted">
                No agents configured. Run an instruction to auto-populate.
              </p>
            )}
            <div className="space-y-2">
              {agentsState.map((ag) => (
                <div
                  key={ag.template_id}
                  className={`card-af p-3 flex items-center justify-between text-xs ${
                    !ag.enabled ? 'opacity-50' : ''
                  }`}
                >
                  <span className="font-medium text-foreground">{ag.template_name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted">{ag.duration || '-'}</span>
                    {/* Enable/Disable Toggle */}
                    <button
                      type="button"
                      role="switch"
                      aria-checked={ag.enabled}
                      aria-label={`${ag.enabled ? 'Disable' : 'Enable'} ${ag.template_name}`}
                      onClick={() => toggleAgent(ag.template_id, !ag.enabled)}
                      disabled={isRunning}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1 ${
                        ag.enabled ? 'bg-emerald-500' : 'bg-border'
                      } ${isRunning ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
                    >
                      <span
                        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                          ag.enabled ? 'translate-x-4' : 'translate-x-1'
                        }`}
                      />
                    </button>
                    {/* Pipeline status badge */}
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        ag.status === 'COMPLETED'
                          ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                          : ag.status === 'RUNNING'
                          ? 'bg-primary/15 text-primary animate-pulse'
                          : 'bg-surface-secondary text-muted'
                      }`}
                    >
                      {ag.status || 'PENDING'}
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

          {/* View toggle: browse all chunks (default) or search results */}
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border border-border overflow-hidden text-xs">
              <button
                type="button"
                onClick={() => switchRagView('chunks')}
                className={`px-3 py-1.5 font-medium transition-colors ${
                  ragView === 'chunks'
                    ? 'bg-primary text-white'
                    : 'text-muted hover:bg-hover'
                }`}
                aria-pressed={ragView === 'chunks'}
              >
                🗂 All Chunks{ragChunksTotal > 0 ? ` (${ragChunksTotal})` : ''}
              </button>
              <button
                type="button"
                onClick={() => switchRagView('search')}
                className={`px-3 py-1.5 font-medium transition-colors border-l border-border ${
                  ragView === 'search'
                    ? 'bg-primary text-white'
                    : 'text-muted hover:bg-hover'
                }`}
                aria-pressed={ragView === 'search'}
              >
                🔍 Search Results
                {ragResults.length > 0 ? ` (${ragResults.length})` : ''}
              </button>
            </div>
          </div>

          {/* Default view: browse every indexed chunk (collapsible, paginated) */}
          {ragView === 'chunks' && (
            <div className="space-y-3">
              {ragChunksLoading && (
                <div
                  role="status"
                  aria-live="polite"
                  className="flex items-center gap-3 rounded-[10px] border border-border bg-surface-secondary px-4 py-3.5 text-xs text-muted"
                >
                  <span className="h-4 w-4 flex-shrink-0 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                  Loading indexed chunks…
                </div>
              )}
              {!ragChunksLoading && ragChunks.length === 0 && (
                <div className="rounded-[10px] border border-border bg-surface-secondary px-4 py-3 text-xs text-muted">
                  No chunks indexed yet. Run a re-index or wait for the initial
                  background index to complete.
                </div>
              )}
              {ragChunks.length > 0 && (
                <div className="max-h-[calc(100vh-430px)] overflow-y-auto pr-1 space-y-2">
                  {ragChunks.map((chunk) => {
                    const isOpen = expandedChunks.has(chunk.id)
                    return (
                      <article
                        key={chunk.id}
                        className="bg-surface-secondary border border-border rounded-lg text-xs font-mono overflow-hidden"
                      >
                        <button
                          type="button"
                          onClick={() => toggleChunk(chunk.id)}
                          className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left hover:bg-hover/50 transition-colors"
                          aria-expanded={isOpen}
                          aria-label={`${isOpen ? 'Collapse' : 'Expand'} chunk for ${chunk.file_path}`}
                        >
                          <span className="flex items-center gap-2 min-w-0">
                            <span
                              className={`text-muted text-[9px] transition-transform ${
                                isOpen ? 'rotate-90' : ''
                              }`}
                            >
                              ▶
                            </span>
                            <span className="text-primary font-sans font-semibold truncate">
                              {chunk.file_path} (Lines {chunk.start_line}-
                              {chunk.end_line})
                            </span>
                          </span>
                          <span className="shrink-0 text-muted font-sans">
                            {isOpen ? '−' : '+'}
                          </span>
                        </button>
                        {isOpen && (
                          <pre className="text-foreground-secondary bg-[#090d16] p-2 rounded-b overflow-x-auto text-xs border-t border-border">
                            {chunk.content}
                          </pre>
                        )}
                      </article>
                    )
                  })}
                </div>
              )}
              {ragChunksTotal > PAGE_SIZE && (
                <div className="flex items-center gap-1.5 justify-end pt-1 text-[10px] text-muted select-none">
                  <button
                    type="button"
                    disabled={chunksPage === 0}
                    onClick={() => goToChunksPage(chunksPage - 1)}
                    className="px-1.5 py-0.5 rounded border border-border hover:bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
                    aria-label="Previous chunks page"
                  >
                    ‹
                  </button>
                  <span className="font-mono">
                    {chunksPage + 1}/
                    {Math.ceil(ragChunksTotal / PAGE_SIZE)} ·{' '}
                    {ragChunksTotal} chunks
                  </span>
                  <button
                    type="button"
                    disabled={
                      chunksPage >= Math.ceil(ragChunksTotal / PAGE_SIZE) - 1
                    }
                    onClick={() => goToChunksPage(chunksPage + 1)}
                    className="px-1.5 py-0.5 rounded border border-border hover:bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
                    aria-label="Next chunks page"
                  >
                    ›
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Live search feedback — shown below the form where results render */}
          {ragView === 'search' && ragSearching && (
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

          {ragView === 'search' && !ragSearching && ragError && (
            <div className="rounded-[10px] border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-500">
              ⚠ {ragError}
            </div>
          )}

          {ragView === 'search' &&
            !ragSearching &&
            !ragError &&
            ragSearched &&
            ragResults.length === 0 && (
              <div className="rounded-[10px] border border-border bg-surface-secondary px-4 py-3 text-xs text-muted">
                No results found for{' '}
                <span className="font-mono text-foreground">
                  “{ragQuery.trim()}”
                </span>
              </div>
            )}

          {ragView === 'search' && ragResults.length > 0 && (
            <div className="space-y-3 pt-2">
              {ragResults
                .slice(ragPage * PAGE_SIZE, ragPage * PAGE_SIZE + PAGE_SIZE)
                .map((res, localIdx) => {
                  const globalIdx = ragPage * PAGE_SIZE + localIdx
                  const isOpen = expandedResults.has(globalIdx)
                  return (
                    <article
                      key={`${res.file_path}:${res.start_line}`}
                      className="bg-surface-secondary border border-border rounded-lg text-xs font-mono overflow-hidden"
                    >
                      <button
                        type="button"
                        onClick={() => toggleResult(globalIdx)}
                        className="w-full flex items-center justify-between gap-3 px-3 py-2.5 text-left hover:bg-hover/50 transition-colors"
                        aria-expanded={isOpen}
                        aria-label={`${isOpen ? 'Collapse' : 'Expand'} result for ${res.file_path}`}
                      >
                        <span className="flex items-center gap-2 min-w-0">
                          <span
                            className={`text-muted text-[9px] transition-transform ${
                              isOpen ? 'rotate-90' : ''
                            }`}
                          >
                            ▶
                          </span>
                          <span className="text-primary font-sans font-semibold truncate">
                            {res.file_path} (Lines {res.start_line}-
                            {res.end_line})
                          </span>
                        </span>
                        <span className="shrink-0 flex items-center gap-3">
                          <span className="text-primary font-sans font-semibold">
                            Relevance: {(res.score * 100).toFixed(0)}%
                          </span>
                          <span className="text-muted font-sans">
                            {isOpen ? '−' : '+'}
                          </span>
                        </span>
                      </button>
                      {isOpen && (
                        <pre className="text-foreground-secondary bg-[#090d16] p-2 rounded-b overflow-x-auto text-xs border-t border-border">
                          {res.content}
                        </pre>
                      )}
                    </article>
                  )
                })}
              {ragResults.length > PAGE_SIZE && (
                <div className="flex items-center gap-1.5 justify-end pt-1 text-[10px] text-muted select-none">
                  <button
                    type="button"
                    disabled={ragPage === 0}
                    onClick={() => goToRagPage(ragPage - 1)}
                    className="px-1.5 py-0.5 rounded border border-border hover:bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
                    aria-label="Previous results page"
                  >
                    ‹
                  </button>
                  <span className="font-mono">
                    {ragPage + 1}/
                    {Math.ceil(ragResults.length / PAGE_SIZE)} ·{' '}
                    {ragResults.length} results
                  </span>
                  <button
                    type="button"
                    disabled={
                      ragPage >= Math.ceil(ragResults.length / PAGE_SIZE) - 1
                    }
                    onClick={() => goToRagPage(ragPage + 1)}
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

      {/* Settings Tab — Git & Filesystem Policies */}
      {activeTab === 'SETTINGS' && (
        <SettingsPanel
          project={project}
          projectId={projectId}
          onSaved={(updated) => setProject(updated)}
        />
      )}
    </div>
  )
}

/** Inline settings panel for Git and Filesystem policy configuration. */
function SettingsPanel({
  project,
  projectId,
  onSaved,
}: {
  project: ProjectResponse | null
  projectId: string
  onSaved: (p: ProjectResponse) => void
}) {
  const [gitEnabled, setGitEnabled] = useState(project?.git_enabled ?? true)
  const [branchPatterns, setBranchPatterns] = useState(
    (project?.git_branch_patterns || ['*']).join(', '),
  )
  const [gitRequirePr, setGitRequirePr] = useState(
    project?.git_require_pr ?? false,
  )
  const [gitCommitTemplate, setGitCommitTemplate] = useState(
    project?.git_commit_template || '',
  )
  const [fsRead, setFsRead] = useState(project?.fs_read_enabled ?? true)
  const [fsWrite, setFsWrite] = useState(project?.fs_write_enabled ?? true)
  const [fsDelete, setFsDelete] = useState(project?.fs_delete_enabled ?? true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Sync state when project loads/changes
  useEffect(() => {
    if (project) {
      setGitEnabled(project.git_enabled ?? true)
      setBranchPatterns((project.git_branch_patterns || ['*']).join(', '))
      setGitRequirePr(project.git_require_pr ?? false)
      setGitCommitTemplate(project.git_commit_template || '')
      setFsRead(project.fs_read_enabled ?? true)
      setFsWrite(project.fs_write_enabled ?? true)
      setFsDelete(project.fs_delete_enabled ?? true)
    }
  }, [project])

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const patterns = branchPatterns
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      const updated = await updateProject(projectId, {
        git_enabled: gitEnabled,
        git_branch_patterns: patterns.length > 0 ? patterns : ['*'],
        git_require_pr: gitRequirePr,
        git_commit_template: gitCommitTemplate || null,
        fs_read_enabled: fsRead,
        fs_write_enabled: fsWrite,
        fs_delete_enabled: fsDelete,
      })
      onSaved(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      console.error('Failed to save policies:', err)
    } finally {
      setSaving(false)
    }
  }

  if (!project) {
    return (
      <section className="card-af p-6">
        <p className="text-sm text-muted">Loading project settings...</p>
      </section>
    )
  }

  return (
    <section className="space-y-6">
      {/* Git Policy */}
      <div className="card-af p-6">
        <h2 className="text-base font-semibold text-foreground mb-4">
          🔀 Git Authorization
        </h2>
        <div className="space-y-4">
          {/* Git enable/disable */}
          <label className="flex items-center justify-between">
            <span className="text-sm text-foreground">
              Enable Git operations
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={gitEnabled}
              onClick={() => setGitEnabled(!gitEnabled)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary ${
                gitEnabled ? 'bg-emerald-500' : 'bg-border'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  gitEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </label>
          <p className="text-[11px] text-muted -mt-2">
            When disabled, all Git operations (status, log, commit, rollback)
            are blocked for this project.
          </p>

          {/* Branch patterns */}
          <div>
            <label className="block text-sm text-foreground mb-1">
              Allowed branch patterns
            </label>
            <input
              type="text"
              value={branchPatterns}
              onChange={(e) => setBranchPatterns(e.target.value)}
              placeholder="feature/*, fix/*, hotfix/*"
              className="input-af w-full text-xs"
              disabled={!gitEnabled}
            />
            <p className="text-[11px] text-muted mt-1">
              Comma-separated glob patterns. Use <code>*</code> to allow all.
              The agent cannot create or commit to branches that don&apos;t match.
            </p>
          </div>

          {/* Require PR */}
          <label className="flex items-center justify-between">
            <span className="text-sm text-foreground">
              Require Pull Request (block direct commits)
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={gitRequirePr}
              onClick={() => setGitRequirePr(!gitRequirePr)}
              disabled={!gitEnabled}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary ${
                gitRequirePr ? 'bg-amber-500' : 'bg-border'
              } ${!gitEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  gitRequirePr ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </label>
          <p className="text-[11px] text-muted -mt-2">
            When enabled, the agent cannot commit directly — it must submit
            changes via a Pull Request workflow.
          </p>

          {/* Commit template */}
          <div>
            <label className="block text-sm text-foreground mb-1">
              Commit message template
            </label>
            <textarea
              value={gitCommitTemplate}
              onChange={(e) => setGitCommitTemplate(e.target.value)}
              placeholder="e.g.&#10;Reviewed-by: @team&#10;Refs: PROJ-123"
              rows={3}
              className="input-af w-full text-xs font-mono"
              disabled={!gitEnabled}
            />
            <p className="text-[11px] text-muted mt-1">
              Appended to every agent-generated commit message.
            </p>
          </div>
        </div>
      </div>

      {/* Filesystem Access */}
      <div className="card-af p-6">
        <h2 className="text-base font-semibold text-foreground mb-4">
          📁 Filesystem Access
        </h2>
        <div className="space-y-4">
          {([
            ['fsRead', 'Read files', fsRead, setFsRead, 'Agent can read file contents from the workspace.'],
            ['fsWrite', 'Write files', fsWrite, setFsWrite, 'Agent can create and update files in the workspace.'],
            ['fsDelete', 'Delete files', fsDelete, setFsDelete, 'Agent can delete files from the workspace.'],
          ] as const).map(([key, label, value, setter, help]) => (
            <div key={key}>
              <label className="flex items-center justify-between">
                <span className="text-sm text-foreground">{label}</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={value}
                  onClick={() => setter(!value)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary ${
                    value ? 'bg-emerald-500' : 'bg-border'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      value ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </label>
              <p className="text-[11px] text-muted mt-0.5">{help}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Save button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="btn-primary-af text-sm disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Policies'}
        </button>
        {saved && (
          <span className="text-xs text-emerald-500 font-medium">
            ✓ Saved successfully
          </span>
        )}
      </div>
    </section>
  )
}
