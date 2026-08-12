'use client'

import React, { useState, useEffect, useRef } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { useRouter, useSearchParams } from 'next/navigation'
import DiffViewer from '@/components/diff-viewer'
import AiFixModal from '@/components/ai-fix-modal'
import Markdown from '@/components/markdown'
import {
  getProject,
  getProjectTree,
  getFileContent,
  getFileOriginal,
  listArtifacts,
  listProjectRuns,
  listVerificationRuns,
  listTechLeadHistory,
  queryTechLead,
  listRagChunks,
  listProjectAgents,
  configureProjectAgent,
  updateProject,
  listApprovals,
  decideApproval,
  listInstructionHistory,
  listUserInstructions,
  listSessions,
  createSession,
  getSessionContext,
  type SessionResponse,
  type SessionContextResponse,
  type AgentRun,
  type VerificationRunResponse,
  type TechLeadInteractionResponse,
  type ProjectAgentResponse,
  ragSearch,
  getRagStats,
  getGitStatus,
  getGitLog,
  submitInstruction,
  cancelInstruction,
  subscribeProjectEvents,
  type ProjectResponse,
  type ApprovalResponse,
  type RagStats,
  type RagChunk,
} from '@/lib/api'

// ── Local types for loosely-typed API payloads ────────────────────────────
interface GitStatusData {
  status?: string
  detail?: string
  branch?: string
  current_branch?: string
  is_dirty?: boolean
  dirty?: boolean
  modified_files?: string[]
  untracked_files?: string[]
  staged_files?: string[]
  unpushed_files?: string[]
  offline?: boolean
}

interface GitChangedFile {
  path: string
  insertions?: number
  deletions?: number
}

interface GitCommitLogEntry {
  hash?: string
  message?: string
  author?: string
  time?: string
  insertions?: number
  deletions?: number
  changed_files?: GitChangedFile[]
}

interface FileTreeNodeData {
  name: string
  type: 'file' | 'dir'
  size?: number
  status?: string
  children?: FileTreeNodeData[]
}

interface RagResultItem {
  file?: string
  file_path?: string
  lines?: number
  start_line?: number
  end_line?: number
  text?: string
  content?: string
  snippet?: string
  score?: number | string
}

interface SseConsoleEvent {
  time: string
  text: string
}

interface HistoryRun {
  agent_name: string
  status: string
  duration_seconds: number
  output: string | null
  metadata: Record<string, unknown>
  created_at: string | null
}

interface InstructionSummary {
  id: string
  project_id: string
  user_id: string | null
  prompt: string
  status: string
  created_at: string | null
  runs?: HistoryRun[]
}

interface ModelInfo {
  name: string
  provider: string
  context_limit: number
  vision: boolean
  label: string
}

interface AgentResultPayload {
  branch?: string
  commit_message?: string
}

interface TestAgentMeta {
  tests_passed?: number
  tests_failed?: number
  coverage_percent?: number
  test_summary?: string
  tests_generated?: string[]
}

interface ValidationAgentMeta {
  lint_issues?: number
  type_errors?: number
  security_issues?: number
  build_status?: string
  tool_checks?: unknown[]
  auto_fixes_applied?: string[]
  recommendations?: string[]
}

function isOfflineResponse(
  value: unknown,
): value is { status: 'offline'; detail?: string } {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { status?: unknown }).status === 'offline'
  )
}

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

/** VS Code–style JSON syntax highlighting for raw agent output. */
function highlightJSON(raw: string): React.ReactNode {
  try {
    const formatted = JSON.stringify(JSON.parse(raw), null, 2)
    // Split into tokens: strings, numbers, booleans, null, keys, punctuation
    const parts = formatted.split(
      /("(?:[^"\\]|\\.)*"\s*:)|("(?:[^"\\]|\\.)*")|(\btrue\b|\bfalse\b|\bnull\b)|(-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)/g,
    )
    return (
      <>
        {parts.map((part, i) => {
          if (part === undefined) return null
          // Key (before colon)
          if (/^"/.test(part) && /":\s*$/.test(part)) {
            return (
              <span key={i} className="text-[#9cdcfe]">
                {part}
              </span>
            )
          }
          // String value
          if (/^"/.test(part)) {
            return (
              <span key={i} className="text-[#ce9178]">
                {part}
              </span>
            )
          }
          // Boolean or null
          if (/^(true|false|null)$/.test(part)) {
            return (
              <span key={i} className="text-[#569cd6]">
                {part}
              </span>
            )
          }
          // Number
          if (/^-?\d/.test(part)) {
            return (
              <span key={i} className="text-[#b5cea8]">
                {part}
              </span>
            )
          }
          // Everything else (punctuation, whitespace)
          return (
            <span key={i} className="text-[#d4d4d4]">
              {part}
            </span>
          )
        })}
      </>
    )
  } catch {
    return raw
  }
}

function hasChangedChild(
  dirPath: string,
  gitStatus?: GitStatusData | null,
): boolean {
  if (!gitStatus) return false
  const cleanDir = cleanPath(dirPath)
  const prefix = cleanDir ? `${cleanDir}/` : ''
  const isMatch = (f: string) => {
    const cleanF = cleanPath(f)
    return cleanF.startsWith(prefix)
  }
  return Boolean(
    gitStatus.modified_files?.some(isMatch) ||
      gitStatus.untracked_files?.some(isMatch) ||
      gitStatus.staged_files?.some(isMatch) ||
      gitStatus.unpushed_files?.some(isMatch),
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
  node: FileTreeNodeData
  parentPath?: string
  selectedPath: string
  onSelectFile: (path: string) => void
  gitStatus?: GitStatusData | null
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
  const [prevSelected, setPrevSelected] = useState(cleanSelected)

  // Reset user toggle when selected file changes. Adjusting state during
  // render is the React-recommended pattern (avoids set-state-in-effect).
  if (prevSelected !== cleanSelected) {
    setPrevSelected(cleanSelected)
    setUserExpanded(null)
  }

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
            {(node.children || []).map((child: FileTreeNodeData) => {
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
    | 'LEAD'
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
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [historyList, setHistoryList] = useState<string[]>([])
  const [attachments, setAttachments] = useState<
    { name: string; dataUrl: string; mimeType: string }[]
  >([])
  const [isRunning, setIsRunning] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)
  const [activeInstructionId, setActiveInstructionId] = useState<string | null>(null)
  const activeInstructionIdRef = useRef<string | null>(null)
  // AI FIX modal state
  const [fixModalOpen, setFixModalOpen] = useState(false)
  const [fixModalInfo, setFixModalInfo] = useState<{
    prompt: string
    errors: string[]
    recommendations: string[]
    agentNames: string[]
  } | null>(null)
  const [fixSubmitting, setFixSubmitting] = useState(false)
  const [fixingIds, setFixingIds] = useState<string[]>([])
  const [fixedIds, setFixedIds] = useState<Set<string>>(new Set())
  const fixInstructionRef = useRef<InstructionSummary | null>(null)

  // Agent enablement prompt state
  const [agentEnablePrompt, setAgentEnablePrompt] = useState<{
    disabled: { template_id: string; template_name: string }[]
    selectedIds: Set<string>
    onConfirm: (selectedIds: Set<string>) => void
    onSkip: () => void
  } | null>(null)
  const [sessions, setSessions] = useState<SessionResponse[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [sessionContext, setSessionContext] = useState<SessionContextResponse | null>(null)
  const [events, setEvents] = useState<SseConsoleEvent[]>([])
  const [ragQuery, setRagQuery] = useState(urlQuery)
  const [ragResults, setRagResults] = useState<RagResultItem[]>([])
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
  const [ragChunks, setRagChunks] = useState<RagChunk[]>([])
  const [ragChunksTotal, setRagChunksTotal] = useState(0)
  const [ragChunksLoading, setRagChunksLoading] = useState(false)
  const [chunksPage, setChunksPage] = useState(0)
  // Chunk cards collapsed by default; toggled by chunk id (stable across
  // pagination)
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(
    () => new Set(),
  )

  const [fileTree, setFileTree] = useState<FileTreeNodeData | null>(null)
  const [fileTreeError, setFileTreeError] = useState<string | null>(null)
  // Global offline state — set when any tool-backed endpoint returns offline
  const [isOffline, setIsOffline] = useState(false)
  // File tree collapse/expand control + remount key
  const [treeMode, setTreeMode] = useState<'auto' | 'collapsed' | 'expanded'>(
    'auto',
  )
  const [treeKey, setTreeKey] = useState(0)
  const [gitStatus, setGitStatus] = useState<GitStatusData | null>(null)
  const [gitLog, setGitLog] = useState<GitCommitLogEntry[]>([])
  const [gitLogLoading, setGitLogLoading] = useState(false)
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
  const [verificationRuns, setVerificationRuns] = useState<
    VerificationRunResponse[]
  >([])

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
  const [pipelineResults, setPipelineResults] = useState<
    Record<string, unknown>
  >({})

  // Instruction history for the history panel
  const [instructionHistory, setInstructionHistory] = useState<
    InstructionSummary[]
  >([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [expandedHistory, setExpandedHistory] = useState<string | null>(null)
  const [historyPage, setHistoryPage] = useState(0)
  const [historyHasMore, setHistoryHasMore] = useState(true)
  const PAGE_SIZE_HISTORY = 10

  // Filter state
  const [historyAgentFilter, setHistoryAgentFilter] = useState('')
  const [historyDateFrom, setHistoryDateFrom] = useState('')
  const [historyDateTo, setHistoryDateTo] = useState('')

  // Load instruction history with filters and pagination
  const loadHistory = async (
    page = 0,
    agent?: string,
    dateFrom?: string,
    dateTo?: string,
  ) => {
    setHistoryLoading(true)
    try {
      const data = await listInstructionHistory(projectId, {
        limit: PAGE_SIZE_HISTORY + 1, // fetch one extra to detect hasMore
        offset: page * PAGE_SIZE_HISTORY,
        agent_name: agent || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      })
      setHistoryHasMore(data.length > PAGE_SIZE_HISTORY)
      setInstructionHistory(data.slice(0, PAGE_SIZE_HISTORY))
      setHistoryPage(page)
    } catch (err) {
      console.error('Failed to load instruction history:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    let ignore = false
    const run = async () => {
      try {
        const data = await listInstructionHistory(projectId, {
          limit: PAGE_SIZE_HISTORY + 1,
          offset: 0,
        })
        if (ignore) return
        setHistoryHasMore(data.length > PAGE_SIZE_HISTORY)
        setInstructionHistory(data.slice(0, PAGE_SIZE_HISTORY))
        setHistoryPage(0)
      } catch (err) {
        if (!ignore) console.error('Failed to load instruction history:', err)
      } finally {
        if (!ignore) setHistoryLoading(false)
      }
    }
    void run()
    return () => {
      ignore = true
    }
  }, [projectId])

  // Load user-wide instruction prompts for UP/DOWN arrow key cycling
  useEffect(() => {
    listUserInstructions(50)
      .then((data) => {
        // Deduplicate by prompt text, keep most recent first
        const seen = new Set<string>()
        const unique = data
          .filter((i) => {
            const p = i.prompt.trim()
            if (seen.has(p)) return false
            seen.add(p)
            return true
          })
          .map((i) => i.prompt.trim())
        setHistoryList(unique)
      })
      .catch(() => {})
  }, [projectId])

  // Load sessions for this project
  useEffect(() => {
    let ignore = false
    listSessions(projectId)
      .then((data) => {
        if (ignore) return
        setSessions(data)
        setActiveSessionId((prev) => prev ?? data[0]?.id ?? null)
      })
      .catch(() => {})
    return () => {
      ignore = true
    }
  }, [projectId])

  // Load session context when active session changes
  useEffect(() => {
    if (!activeSessionId) return
    let ignore = false
    getSessionContext(projectId, activeSessionId)
      .then((ctx) => {
        if (!ignore) setSessionContext(ctx)
      })
      .catch(() => {
        if (!ignore) setSessionContext(null)
      })
    return () => {
      ignore = true
    }
  }, [activeSessionId, projectId])

  // Derive the effective context — null whenever no session is active.
  const effectiveSessionContext = activeSessionId ? sessionContext : null

  // Refresh history after pipeline completes
  useEffect(() => {
    if (isRunning || activeTab !== 'AGENTS') return
    let ignore = false
    const run = async () => {
      try {
        const data = await listInstructionHistory(projectId, {
          limit: PAGE_SIZE_HISTORY + 1,
          offset: 0,
          agent_name: historyAgentFilter || undefined,
          date_from: historyDateFrom || undefined,
          date_to: historyDateTo || undefined,
        })
        if (ignore) return
        setHistoryHasMore(data.length > PAGE_SIZE_HISTORY)
        setInstructionHistory(data.slice(0, PAGE_SIZE_HISTORY))
        setHistoryPage(0)
      } catch (err) {
        if (!ignore) console.error('Failed to load instruction history:', err)
      } finally {
        if (!ignore) setHistoryLoading(false)
      }
    }
    void run()
    return () => {
      ignore = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunning, projectId, activeTab])

  // Apply filters
  const applyFilters = () => {
    setExpandedHistory(null)
    loadHistory(0, historyAgentFilter, historyDateFrom, historyDateTo)
  }

  const clearFilters = () => {
    setHistoryAgentFilter('')
    setHistoryDateFrom('')
    setHistoryDateTo('')
    setExpandedHistory(null)
    loadHistory(0)
  }

  // Project data from API
  const [project, setProject] = useState<ProjectResponse | null>(null)
  const [projectLoading, setProjectLoading] = useState(true)
  const [projectError, setProjectError] = useState<string | null>(null)
  const [approvals, setApprovals] = useState<ApprovalResponse[]>([])
  const [approvalError, setApprovalError] = useState<string | null>(null)
  const [decidingApprovalId, setDecidingApprovalId] = useState<string | null>(null)
  const [techLeadQuestion, setTechLeadQuestion] = useState('')
  const [techLeadHistory, setTechLeadHistory] = useState<
    TechLeadInteractionResponse[]
  >([])
  const [techLeadLoading, setTechLeadLoading] = useState(false)
  const [techLeadError, setTechLeadError] = useState<string | null>(null)

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

  useEffect(() => {
    listApprovals(projectId, 'PENDING')
      .then(setApprovals)
      .catch((err) =>
        setApprovalError(
          err instanceof Error ? err.message : 'Failed to load approvals',
        ),
      )
  }, [projectId])

  const handleApprovalDecision = async (
    approvalId: string,
    decision: 'approve' | 'reject',
  ) => {
    setDecidingApprovalId(approvalId)
    setApprovalError(null)
    try {
      await decideApproval(approvalId, decision)
      setApprovals((previous) =>
        previous.filter((approval) => approval.id !== approvalId),
      )
    } catch (err) {
      setApprovalError(
        err instanceof Error ? err.message : `Failed to ${decision} request`,
      )
    } finally {
      setDecidingApprovalId(null)
    }
  }

  const handleTechLeadQuery = async () => {
    const question = techLeadQuestion.trim()
    if (!question || techLeadLoading) return
    setTechLeadLoading(true)
    setTechLeadError(null)
    try {
      const interaction = await queryTechLead(projectId, question)
      setTechLeadHistory((previous) => [
        { ...interaction, question },
        ...previous,
      ])
      setTechLeadQuestion('')
    } catch (err) {
      setTechLeadError(
        err instanceof Error ? err.message : 'Tech lead query failed',
      )
    } finally {
      setTechLeadLoading(false)
    }
  }

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
      } else if (isOfflineResponse(data)) {
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
      if (isOfflineResponse(orig)) {
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
      if (isOfflineResponse(data)) {
        setRagResults([])
        setRagSearched(true)
        setRagError(
          data.detail ||
            'Local agent workstation is offline. Start `agentforge start` to enable RAG search.',
        )
        return
      }
      const results = Array.isArray(data)
        ? (data as RagResultItem[])
        : [data as RagResultItem]
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
      if (isOfflineResponse(data)) {
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

  // Poll the project's live workspace reachability and RAG stats. This keeps
  // the local-workspace status accurate on every tab and refreshes indexing
  // progress more frequently while the RAG tab is active.
  useEffect(() => {
    // A device record can be stale after a local agent disconnects. Probe the
    // project's own workspace rather than showing the header as connected
    // merely because some device is marked online in the database.
    if (project?.execution_target !== 'LOCAL') return
    const tick = async () => {
      try {
        const s = await getRagStats(projectId)
        setRagStats(s)
        setIsOffline(s.online === false)
      } catch {
        // A failed reachability probe must not leave a false "Connected"
        // status visible for a local workspace.
        setIsOffline(true)
      }
    }
    tick()
    const timer = window.setInterval(tick, activeTab === 'RAG' ? 2000 : 5000)
    return () => window.clearInterval(timer)
  }, [activeTab, project?.execution_target, projectId])

  // Refresh the chunks browser when a background index finishes so the
  // default "All Chunks" view always reflects the latest index.
  const wasIndexingRef = useRef(false)
  useEffect(() => {
    const indexing = ragStats?.indexing === true
    if (
      wasIndexingRef.current &&
      !indexing &&
      ragStats?.state === 'complete' &&
      ragView === 'chunks'
    ) {
      const offset = chunksPage * PAGE_SIZE
      const run = async () => {
        try {
          const data = await listRagChunks(projectId, offset, PAGE_SIZE)
          setRagChunks(data.chunks || [])
          setRagChunksTotal(data.total || 0)
        } catch {
          setRagChunks([])
          setRagChunksTotal(0)
        } finally {
          setRagChunksLoading(false)
        }
      }
      void run()
    }
    wasIndexingRef.current = indexing
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ragStats?.indexing, ragStats?.state, ragView, chunksPage])

  // Subscribe to SSE events
  useEffect(() => {
    return subscribeProjectEvents(
      projectId,
      (data) => {
        const time = new Date().toLocaleTimeString()

        setEvents((prev) => [
          ...prev,
          { time, text: `[${data.agent_name || 'System'}] ${data.message}` },
        ])

        if (['WAITING_APPROVAL', 'APPROVED', 'REJECTED'].includes(data.status)) {
          listApprovals(projectId, 'PENDING')
            .then(setApprovals)
            .catch((err) =>
              setApprovalError(
                err instanceof Error
                  ? err.message
                  : 'Failed to refresh approvals',
              ),
            )
        }

        const agentName = data.agent_name
        if (agentName) {
          setAgentsState((prev) =>
            prev.map((ag) => {
              if (ag.template_name === agentName) {
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
          if (data.status === 'COMPLETED' && data.data) {
            setPipelineResults((prev) => ({
              ...prev,
              [agentName]: data.data,
            }))
          }
        }

        if (
          data.agent_name === 'System' &&
          ['COMPLETED', 'FAILED', 'CANCELLED'].includes(data.status) &&
          data.instruction_id === activeInstructionIdRef.current
        ) {
          setIsRunning(false)
          setIsCancelling(false)
          setActiveInstructionId(null)
          activeInstructionIdRef.current = null
        }
      },
      (error) => {
        console.error('SSE Error:', error)
        setEvents((prev) => [
          ...prev,
          {
            time: new Date().toLocaleTimeString(),
            text: '[System] ⚠ Live event stream could not be restored.',
          },
        ])
      },
    )
  }, [projectId])

  // Sync state when tab changes
  useEffect(() => {
    if (activeTab === 'FILES') {
      if (!fileTree && !fileTreeError) {
        getProjectTree(projectId)
          .then((data: unknown) => {
            if (isOfflineResponse(data)) {
              setIsOffline(true)
              setFileTree(null)
              setFileTreeError(
                'Local agent workstation is offline — connect a device to browse files.',
              )
            } else {
              setIsOffline(false)
              setFileTree(data as FileTreeNodeData)
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
          .then((data: unknown) => {
            const offline = isOfflineResponse(data)
            setIsOffline(offline)
            setGitStatus(
              offline
                ? { ...(data as GitStatusData), offline: true }
                : ((data as GitStatusData) ?? null),
            )
          })
          .catch((err) => console.error('Failed to load git status:', err))
      }
      if (urlFile) {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- tab activation intentionally triggers file loading that sets state
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
        .then((data: unknown) => {
          const offline = isOfflineResponse(data)
          setIsOffline(offline)
          setGitStatus(
            offline
              ? { ...(data as GitStatusData), offline: true }
              : ((data as GitStatusData) ?? null),
          )
        })
        .catch((err) => console.error('Failed to load git status:', err))
      // Also fetch git log
      if (gitLog.length === 0 && !gitLogLoading) {
        setGitLogLoading(true)
        getGitLog(projectId, 10)
          .then((data: unknown) => {
            if (Array.isArray(data)) {
              setGitLog(data as GitCommitLogEntry[])
            }
          })
          .catch((err) => console.error('Failed to load git log:', err))
          .finally(() => setGitLogLoading(false))
      }
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
    if (activeTab === 'VALIDATION') {
      listVerificationRuns(projectId)
        .then(setVerificationRuns)
        .catch((err) => console.error('Failed to load verification evidence:', err))
    }
    if (activeTab === 'LEAD') {
      listTechLeadHistory(projectId)
        .then(setTechLeadHistory)
        .catch((err) =>
          setTechLeadError(
            err instanceof Error ? err.message : 'Failed to load tech lead history',
          ),
        )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load-once-per-tab; adding data deps would refetch on every data change
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

  const handleCancelPipeline = async () => {
    const instructionId = activeInstructionIdRef.current
    if (!instructionId || isCancelling) return
    setIsCancelling(true)
    try {
      const cancelled = await cancelInstruction(projectId, instructionId)
      setEvents((prev) => [
        ...prev,
        {
          time: new Date().toLocaleTimeString(),
          text: '[System] Cancellation requested.',
        },
      ])
      if (cancelled.status === 'CANCELLED') {
        setIsRunning(false)
        setIsCancelling(false)
        setActiveInstructionId(null)
        activeInstructionIdRef.current = null
      }
    } catch (error) {
      console.error('Failed to cancel instruction:', error)
      setIsCancelling(false)
    }
  }

  // Ensure all enabled agents are active before running pipeline.
  // Returns a Promise that resolves when all agents are confirmed enabled.
  const ensureAgentsEnabled = (): Promise<boolean> => {
    // Wait for agents to load if they haven't yet
    if (agentsLoading || agentsState.length === 0) {
      return Promise.resolve(true) // agents not loaded yet, proceed anyway
    }
    const disabled = agentsState.filter((a) => !a.enabled)
    if (disabled.length === 0) return Promise.resolve(true)

    return new Promise((resolve) => {
      const allIds = new Set(disabled.map((a) => a.template_id))
      // Git Agent is unchecked by default (user must opt-in)
      for (const ag of disabled) {
        if (ag.template_name === 'Git Agent') allIds.delete(ag.template_id)
      }
      setAgentEnablePrompt({
        disabled: disabled.map((a) => ({
          template_id: a.template_id,
          template_name: a.template_name,
        })),
        selectedIds: new Set(allIds),
        onConfirm: async (selectedIds: Set<string>) => {
          setAgentEnablePrompt(null)
          // Enable only the selected agents
          for (const ag of disabled) {
            if (!selectedIds.has(ag.template_id)) continue
            try {
              await configureProjectAgent(projectId, {
                template_id: ag.template_id,
                enabled: true,
              })
            } catch (err) {
              console.error(`Failed to enable ${ag.template_name}:`, err)
            }
          }
          // Update local state — mark selected agents as enabled
          setAgentsState((prev) =>
            prev.map((a) =>
              selectedIds.has(a.template_id) ? { ...a, enabled: true } : a,
            ),
          )
          resolve(true)
        },
        onSkip: () => {
          setAgentEnablePrompt(null)
          resolve(true) // proceed without enabling
        },
      })
    })
  }

  // AI FIX: open confirmation modal, then submit with error context
  const handleAiFix = (instruction: InstructionSummary) => {
    if (!instruction || isRunning) return

    // Collect errors and recommendations from failed runs
    const errors: string[] = []
    const recs: string[] = []
    const agents: string[] = []
    if (instruction.runs) {
      for (const run of instruction.runs) {
        if (run.status === 'FAILED') {
          agents.push(run.agent_name)
          if (run.metadata?.error) {
            errors.push(`[${run.agent_name}] ${run.metadata.error}`)
          }
        }
        if (run.metadata?.recommendations) {
          const r = Array.isArray(run.metadata.recommendations)
            ? run.metadata.recommendations
            : [run.metadata.recommendations]
          recs.push(...r.map((s: string) => `[${run.agent_name}] ${s}`))
        }
      }
    }

    fixInstructionRef.current = instruction
    setFixModalInfo({
      prompt: instruction.prompt,
      errors,
      recommendations: recs,
      agentNames: agents.filter((v, i, a) => a.indexOf(v) === i),
    })
    setFixModalOpen(true)
  }

  // AI FIX: confirmed — submit and close (click-and-forget)
  const handleAiFixConfirm = async () => {
    const instruction = fixInstructionRef.current
    if (!instruction) return

    // Check agents before proceeding
    const ok = await ensureAgentsEnabled()
    if (!ok) return

    setFixSubmitting(true)

    const errors: string[] = []
    const recs: string[] = []
    if (instruction.runs) {
      for (const run of instruction.runs) {
        if (run.status === 'FAILED' && run.metadata?.error) {
          errors.push(`[${run.agent_name}] ${run.metadata.error}`)
        }
        if (run.metadata?.recommendations) {
          const r = Array.isArray(run.metadata.recommendations)
            ? run.metadata.recommendations
            : [run.metadata.recommendations]
          recs.push(...r.map((s: string) => `[${run.agent_name}] ${s}`))
        }
      }
    }

    const errorBlock = errors.length > 0
      ? `\n\nErrors from previous run:\n${errors.join('\n')}`
      : ''
    const recBlock = recs.length > 0
      ? `\n\nRecommendations:\n${recs.join('\n')}`
      : ''

    const fixPrompt = `[AI FIX] The following instruction failed. Please analyze the errors and fix them.\n\nOriginal instruction: ${instruction.prompt}${errorBlock}${recBlock}\n\nFix all issues and re-run.`

    // Mark this instruction as being fixed (prevents re-click)
    setFixingIds((prev) => [...prev, instruction.id])
    setFixedIds((prev) => new Set(prev).add(instruction.id))

    // Close modal immediately (click-and-forget)
    setFixModalOpen(false)
    setFixSubmitting(false)

    // Start pipeline
    setIsRunning(true)
    setEvents((prev) => [
      ...prev,
      { time: new Date().toLocaleTimeString(), text: `[AI FIX] Fixing: ${instruction.prompt}` },
    ])
    setAgentsState((prev) =>
      prev.map((ag) =>
        ag.enabled ? { ...ag, status: 'PENDING', duration: '-' } : ag,
      ),
    )

    try {
      const submitted = await submitInstruction(projectId, fixPrompt)
      setActiveInstructionId(submitted.id)
      activeInstructionIdRef.current = submitted.id
      setPrompt('')
      setHistoryIndex(-1)
    } catch (err) {
      console.error('AI FIX submit failed:', err)
      setIsRunning(false)
    }
  }

  // Clear fixing state when pipeline completes, refresh session context
  useEffect(() => {
    if (!isRunning && fixingIds.length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- pipeline completion intentionally refreshes history + clears state
      loadHistory(historyPage, historyAgentFilter, historyDateFrom, historyDateTo)
      // Refresh session context to reflect any changes
      if (activeSessionId) {
        getSessionContext(projectId, activeSessionId)
          .then(setSessionContext)
          .catch(() => setSessionContext(null))
      }
      setFixingIds([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only reacts to pipeline completion; other deps are stable refs/state
  }, [isRunning])

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
                ? isOffline
                  ? 'Local · Offline'
                  : 'Local · Connected'
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
        <nav className="flex flex-wrap justify-end gap-2">
          {(['AGENTS', 'FILES', 'RAG', 'GIT', 'ARTIFACTS', 'TESTS', 'VALIDATION', 'LEAD', 'SETTINGS'] as const).map((tab) => {
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

      {(approvals.length > 0 || approvalError) && (
        <section
          className="rounded-xl border border-amber-500/35 bg-amber-500/10 p-5 space-y-3"
          aria-label="Pending approvals"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-bold text-foreground">
                Human approval required
              </h2>
              <p className="text-xs text-muted mt-1">
                Review the exact operation before allowing the instruction to resume.
              </p>
            </div>
            {approvals.length > 0 && (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/15 px-2.5 py-1 text-[10px] font-bold text-amber-600 dark:text-amber-400">
                {approvals.length} pending
              </span>
            )}
          </div>
          {approvalError && (
            <p role="alert" className="text-xs text-red-500">
              {approvalError}
            </p>
          )}
          {approvals.map((approval) => (
            <article
              key={approval.id}
              className="rounded-lg border border-border bg-surface-secondary p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-foreground">
                      {approval.summary}
                    </span>
                    <span className="rounded border border-red-500/30 bg-red-500/10 px-1.5 py-0.5 text-[9px] font-bold text-red-500">
                      {approval.risk_level}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-muted">
                    {approval.tool_name} · {approval.operation}
                  </p>
                  <pre className="mt-3 max-h-32 overflow-auto rounded border border-border bg-background p-2 text-[10px] text-muted whitespace-pre-wrap break-all">
                    {JSON.stringify(approval.request_payload, null, 2)}
                  </pre>
                  <p className="mt-2 text-[10px] text-muted">
                    Expires {new Date(approval.expires_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    className="btn-secondary-af !px-3 !py-1.5 !text-xs"
                    disabled={decidingApprovalId !== null}
                    onClick={() => handleApprovalDecision(approval.id, 'reject')}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    className="btn-primary-af !px-3 !py-1.5 !text-xs"
                    disabled={decidingApprovalId !== null}
                    onClick={() => handleApprovalDecision(approval.id, 'approve')}
                  >
                    {decidingApprovalId === approval.id ? 'Saving…' : 'Approve'}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </section>
      )}

      {/* Global Offline Banner — shown on all tabs when workstation is disconnected */}
      {isOffline && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-5 flex items-start gap-4">
          <span className="text-2xl flex-shrink-0">🖥</span>
          <div className="min-w-0">
            <div className="text-sm font-bold text-foreground">
              Local Agent Workstation Offline
            </div>
            <p className="text-sm text-muted mt-1 m-0">
              Local agent workstation is offline. Connect a device to use this feature.
            </p>
          </div>
        </div>
      )}

      {/* Instruction Form — only on the Agents tab */}
      {activeTab === 'AGENTS' && (
        <>
          {/* Session Selector + Context Bar */}
          <section className="card-af p-3">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-muted uppercase tracking-wider font-semibold">Session</span>
                <select
                  value={activeSessionId || ''}
                  onChange={async (e) => {
                    const val = e.target.value
                    if (val === '__new__') {
                      try {
                        const s = await createSession(projectId, { name: `Session ${sessions.length + 1}`, model_name: project?.default_model || 'deepseek-chat' })
                        setSessions((prev) => [s, ...prev])
                        setActiveSessionId(s.id)
                      } catch (err) { console.error('Failed to create session:', err) }
                    } else {
                      setActiveSessionId(val || null)
                    }
                  }}
                  className="input-af text-xs py-1 px-2 w-[170px]"
                >
                  <option value="">— None —</option>
                  {sessions.map((s) => (<option key={s.id} value={s.id}>{s.name}</option>))}
                  <option value="__new__">+ New Session</option>
                </select>
              </div>
              {effectiveSessionContext ? (
                <div className="flex-1 min-w-[200px] flex items-center gap-2">
                  <div className="flex-1 h-2.5 bg-surface-secondary rounded-full overflow-hidden border border-border/50">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        effectiveSessionContext.context_used_pct > 80 ? 'bg-red-500' : effectiveSessionContext.context_used_pct > 50 ? 'bg-amber-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(effectiveSessionContext.context_used_pct, 100)}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-muted font-mono whitespace-nowrap">
                    {(effectiveSessionContext.total_tokens_used / 1000).toFixed(0)}K / {(effectiveSessionContext.context_limit / 1000).toFixed(0)}K
                  </span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-semibold">
                    {effectiveSessionContext.model_name}
                  </span>
                </div>
              ) : (
                <span className="text-[10px] text-muted italic">Create a session to track context window usage</span>
              )}
            </div>
          </section>

          {/* Agent Enablement Prompt — shown when some agents are disabled */}
          {agentEnablePrompt && (
            <div className="bg-amber-50 dark:bg-amber-500/8 border border-amber-300 dark:border-amber-500/25 rounded-xl px-4 py-3">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-100 dark:bg-amber-500/15 grid place-items-center flex-shrink-0 mt-0.5">
                  <svg className="w-4 h-4 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-amber-800 dark:text-amber-300 mb-1">
                    Some agents are disabled
                  </div>
                  <p className="text-[11px] text-amber-700 dark:text-amber-400/80 mb-2">
                    Select which agents to enable before running:
                  </p>
                  <div className="grid grid-cols-2 gap-1.5 mb-3">
                    {agentEnablePrompt.disabled.map((ag) => {
                      const checked = agentEnablePrompt.selectedIds.has(ag.template_id)
                      const toggle = () => {
                        setAgentEnablePrompt((prev) => {
                          if (!prev) return null
                          const next = new Set(prev.selectedIds)
                          if (next.has(ag.template_id)) next.delete(ag.template_id)
                          else next.add(ag.template_id)
                          return { ...prev, selectedIds: next }
                        })
                      }
                      return (
                        <label
                          key={ag.template_id}
                          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-white dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/15 cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-500/10 transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={toggle}
                            className="w-3.5 h-3.5 rounded border-amber-400 text-primary focus:ring-primary focus:ring-offset-0 cursor-pointer"
                          />
                          <span className="text-[11px] font-semibold text-amber-900 dark:text-amber-200">
                            {ag.template_name}
                          </span>
                        </label>
                      )
                    })}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        const ids = agentEnablePrompt.selectedIds
                        if (ids.size === 0) return
                        agentEnablePrompt.onConfirm(ids)
                      }}
                      disabled={agentEnablePrompt.selectedIds.size === 0}
                      className="px-3 py-1.5 rounded-lg text-[11px] font-bold text-white bg-primary hover:bg-primary/90 shadow-sm transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      Enable Selected ({agentEnablePrompt.selectedIds.size})
                    </button>
                    <button
                      type="button"
                      onClick={agentEnablePrompt.onSkip}
                      className="px-3 py-1.5 rounded-lg text-[11px] font-semibold text-amber-700 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-500/10 transition-colors"
                    >
                      Skip
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <section className="card-af p-4"
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation() }}
          onDrop={(e) => {
            e.preventDefault()
            e.stopPropagation()
            const files = Array.from(e.dataTransfer.files || []).filter(
              (f) => f.type.startsWith('image/'),
            )
            if (files.length === 0) return
            Promise.all(
              files.map(
                (f) =>
                  new Promise<{ name: string; dataUrl: string; mimeType: string }>(
                    (resolve) => {
                      const reader = new FileReader()
                      reader.onload = () =>
                        resolve({
                          name: f.name,
                          dataUrl: reader.result as string,
                          mimeType: f.type,
                        })
                      reader.readAsDataURL(f)
                    },
                  ),
              ),
            ).then((newAttachments) => {
              setAttachments((prev) =>
                [...prev, ...newAttachments].slice(0, 3),
              )
            })
          }}
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault()
              if (!prompt.trim()) return

              // Check if any agents are disabled — prompt to enable them
              if (!agentsLoading && agentsState.length > 0) {
                try {
                  const ok = await ensureAgentsEnabled()
                  if (!ok) return
                } catch (err) {
                  console.error('Agent enable check failed:', err)
                }
              }

              setIsRunning(true)
              setEvents((prev) => [
                ...prev,
                {
                  time: new Date().toLocaleTimeString(),
                  text: `[Instruction Submitted] ${prompt}`,
                },
              ])
              setAgentsState((prev) =>
                prev.map((ag) =>
                  ag.enabled
                    ? { ...ag, status: 'PENDING', duration: '-' }
                    : ag,
                ),
              )
              // Collect base64 image data (strip data: URL prefix)
              const imageBytes = attachments.length > 0
                ? attachments[0].dataUrl.split(',')[1] || undefined
                : undefined
              const imageMimeType = attachments.length > 0
                ? attachments[0].mimeType
                : undefined
              submitInstruction(projectId, prompt, imageBytes, imageMimeType, activeSessionId || undefined)
                .then((instruction) => {
                  setActiveInstructionId(instruction.id)
                  activeInstructionIdRef.current = instruction.id
                  setAttachments([])
                  setPrompt('')
                  setHistoryIndex(-1)
                })
                .catch((err) => {
                  console.error(
                    'Failed to trigger instruction pipeline:',
                    err,
                  )
                  setIsRunning(false)
                })
            }}
            className="flex gap-3 items-start"
          >
            <div className="flex-1 space-y-2">
              <textarea
                ref={textareaRef}
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value)
                  setHistoryIndex(-1)
                  // Auto-resize
                  const el = e.target
                  el.style.height = 'auto'
                  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
                }}
                onKeyDown={(e) => {
                  const el = e.target as HTMLTextAreaElement
                  const atTop = el.selectionStart === 0
                  const atBottom =
                    el.selectionStart === el.value.length
                  if (e.key === 'ArrowUp' && atTop && historyList.length > 0) {
                    e.preventDefault()
                    const nextIdx = Math.min(
                      historyIndex + 1,
                      historyList.length - 1,
                    )
                    setHistoryIndex(nextIdx)
                    setPrompt(historyList[nextIdx])
                  } else if (
                    e.key === 'ArrowDown' &&
                    atBottom &&
                    historyIndex >= 0
                  ) {
                    e.preventDefault()
                    const prevIdx = historyIndex - 1
                    if (prevIdx < 0) {
                      setHistoryIndex(-1)
                      setPrompt('')
                    } else {
                      setHistoryIndex(prevIdx)
                      setPrompt(historyList[prevIdx])
                    }
                  } else if (e.key === 'Escape') {
                    setHistoryIndex(-1)
                    setPrompt('')
                    el.style.height = 'auto'
                  }
                  // Enter to submit (without Shift)
                  if (e.key === 'Enter' && !e.shiftKey && prompt.trim()) {
                    e.preventDefault()
                    el.form?.requestSubmit()
                  }
                }}
                onPaste={(e) => {
                  const items = e.clipboardData?.items
                  if (!items) return
                  for (let i = 0; i < items.length; i++) {
                    if (items[i].type.startsWith('image/')) {
                      e.preventDefault()
                      const blob = items[i].getAsFile()
                      if (!blob) continue
                      const reader = new FileReader()
                      reader.onload = () => {
                        setAttachments((prev) =>
                          [
                            ...prev,
                            {
                              name: 'pasted-image.png',
                              dataUrl: reader.result as string,
                              mimeType: blob.type,
                            },
                          ].slice(0, 3),
                        )
                      }
                      reader.readAsDataURL(blob)
                      break
                    }
                  }
                }}
                placeholder="e.g. Create payment management module with FastAPI endpoints, React admin table, unit tests, and git commit..."
                className="input-af flex-1 resize-none"
                rows={2}
                disabled={isRunning}
              />
              {/* Attachment thumbnails + add button */}
              <div className="flex gap-2 flex-wrap">
                {attachments.map((att, i) => (
                  <div
                    key={i}
                    className="relative group w-16 h-16 rounded-lg border border-border overflow-hidden bg-surface-secondary"
                  >
                    <Image
                      src={att.dataUrl}
                      alt={att.name}
                      width={64}
                      height={64}
                      unoptimized
                      className="w-full h-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setAttachments((prev) =>
                          prev.filter((_, j) => j !== i),
                        )
                      }
                      className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      ✕
                    </button>
                  </div>
                ))}
                {attachments.length < 3 && (
                  <label className="w-16 h-16 rounded-lg border border-dashed border-border flex items-center justify-center cursor-pointer hover:border-primary hover:bg-primary/5 transition-colors">
                    <span className="text-muted text-lg">+</span>
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      className="hidden"
                      onChange={(e) => {
                        const files = Array.from(
                          e.target.files || [],
                        ).filter((f) => f.type.startsWith('image/'))
                        if (files.length === 0) return
                        Promise.all(
                          files.map(
                            (f) =>
                              new Promise<{
                                name: string
                                dataUrl: string
                                mimeType: string
                              }>((resolve) => {
                                const reader = new FileReader()
                                reader.onload = () =>
                                  resolve({
                                    name: f.name,
                                    dataUrl: reader.result as string,
                                    mimeType: f.type,
                                  })
                                reader.readAsDataURL(f)
                              }),
                          ),
                        ).then((newAtts) => {
                          setAttachments((prev) =>
                            [...prev, ...newAtts].slice(0, 3),
                          )
                        })
                      }}
                    />
                  </label>
                )}
              </div>
            </div>
            <div className="flex flex-col items-center gap-2 flex-shrink-0 pt-0.5">
              <button
                type="submit"
                disabled={isRunning}
                className="btn-primary-af text-xs disabled:opacity-50 whitespace-nowrap"
              >
                {isRunning ? 'Running...' : 'Run Instruction'}
              </button>
            </div>
          </form>
        </section>
      </>)}

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
            <button
              type="button"
              onClick={handleCancelPipeline}
              disabled={!activeInstructionId || isCancelling}
              className="ml-auto text-[10px] rounded border border-red-500/40 px-2 py-1 text-red-500 disabled:opacity-50"
            >
              {isCancelling ? 'Cancelling…' : 'Cancel run'}
            </button>
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
              <div className="flex items-center gap-2">
                {effectiveSessionContext && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-semibold">
                    {effectiveSessionContext.context_limit >= 1000000
                      ? `${(effectiveSessionContext.context_limit / 1000000).toFixed(1)}M`
                      : `${(effectiveSessionContext.context_limit / 1000).toFixed(0)}K`} Context
                  </span>
                )}
                {agentsLoading && (
                  <span className="text-[10px] text-muted animate-pulse">Loading...</span>
                )}
              </div>
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

      {/* Instruction History — visible on AGENTS tab */}
      {activeTab === 'AGENTS' && (
        <section className="card-af p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted uppercase tracking-wider">
              Instruction History
            </h2>
            {historyLoading && (
              <span className="text-[10px] text-muted animate-pulse">Loading...</span>
            )}
          </div>

          {/* Filter Bar */}
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex flex-col gap-1 min-w-0">
              <label className="text-[10px] text-muted font-semibold uppercase tracking-wider">
                Agent
              </label>
              <select
                value={historyAgentFilter}
                onChange={(e) => setHistoryAgentFilter(e.target.value)}
                className="input-af text-xs py-1.5 px-2 w-[160px]"
              >
                <option value="">All Agents</option>
                {agentsState.map((ag) => (
                  <option key={ag.template_id} value={ag.template_name}>
                    {ag.template_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-muted font-semibold uppercase tracking-wider">
                From
              </label>
              <input
                type="date"
                value={historyDateFrom}
                onChange={(e) => setHistoryDateFrom(e.target.value)}
                className="input-af text-xs py-1.5 px-2 w-[140px]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] text-muted font-semibold uppercase tracking-wider">
                To
              </label>
              <input
                type="date"
                value={historyDateTo}
                onChange={(e) => setHistoryDateTo(e.target.value)}
                className="input-af text-xs py-1.5 px-2 w-[140px]"
              />
            </div>
            <button
              type="button"
              onClick={applyFilters}
              className="btn-primary-af text-xs !px-3 !py-1.5"
            >
              Apply
            </button>
            {(historyAgentFilter || historyDateFrom || historyDateTo) && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-[10px] text-muted hover:text-foreground px-2 py-1.5"
              >
                ✕ Clear
              </button>
            )}
          </div>

          {/* History List */}
          {!historyLoading && instructionHistory.length === 0 && (
            <p className="text-xs text-muted py-4 text-center">
              {historyAgentFilter || historyDateFrom || historyDateTo
                ? 'No instructions match your filters.'
                : 'No instructions yet. Submit your first instruction above.'}
            </p>
          )}
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {instructionHistory.map((ins) => (
              <div
                key={ins.id}
                className="border border-border rounded-[10px] overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() =>
                    setExpandedHistory(
                      expandedHistory === ins.id ? null : ins.id,
                    )
                  }
                  className="w-full flex items-center justify-between gap-3 p-3 text-left hover:bg-hover transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          ins.status === 'COMPLETED'
                            ? 'bg-emerald-500/15 text-emerald-500'
                            : ins.status === 'FAILED'
                              ? 'bg-red-500/15 text-red-500'
                              : 'bg-amber-500/15 text-amber-500'
                        }`}
                      >
                        {ins.status}
                      </span>
                      <span className="text-[10px] text-muted">
                        {ins.created_at
                          ? new Date(ins.created_at).toLocaleString()
                          : ''}
                      </span>
                    </div>
                    <p className="text-xs text-foreground truncate">
                      {ins.prompt}
                    </p>
                  </div>
                  <span className="text-muted text-sm flex-shrink-0">
                    {expandedHistory === ins.id ? '▲' : '▼'}
                  </span>
                </button>
                {expandedHistory === ins.id && (
                  <div className="border-t border-border bg-[#0f141e] p-3 font-mono text-xs space-y-1.5 max-h-[300px] overflow-y-auto">
                    <div className="text-muted mb-2">
                      [Instruction] {ins.prompt}
                    </div>
                    {ins.runs && ins.runs.length > 0 ? (
                      ins.runs.map((run: HistoryRun, ri: number) => (
                        <div key={ri} className="text-[#49e56d]">
                          <span className="text-[#7f899c]">
                            [{run.created_at
                              ? new Date(run.created_at)
                                  .toLocaleTimeString()
                              : ''}]
                          </span>{' '}
                          [{run.agent_name}] {run.status === 'COMPLETED'
                            ? `Finished in ${run.duration_seconds?.toFixed(1) || '?'}s`
                            : run.status}
                          {(() => {
                            const summary = run.metadata?.test_summary
                            const files = run.metadata?.files_generated
                            const error = run.metadata?.error
                            const filesList = Array.isArray(files)
                              ? files
                              : null
                            return (
                              <>
                                {summary && (
                                  <div className="ml-4 text-[#c8d0df]">
                                    ↳ {String(summary)}
                                  </div>
                                )}
                                {filesList && filesList.length > 0 && (
                                  <div className="ml-4 text-[#7f899c]">
                                    ↳ Generated:{' '}
                                    {filesList.map(String).join(', ')}
                                  </div>
                                )}
                                {error && (
                                  <div className="ml-4 text-red-400">
                                    ↳ Error: {String(error)}
                                  </div>
                                )}
                              </>
                            )
                          })()}
                        </div>
                      ))
                    ) : (
                      <div className="text-muted italic">
                        No agent run logs available.
                      </div>
                    )}
                    {ins.status === 'FAILED' && (
                      <div className="mt-2">
                        {fixingIds.includes(ins.id) ? (
                          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20">
                            <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                            Fixing in progress…
                          </div>
                        ) : fixedIds.has(ins.id) ? (
                          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                            Fix Submitted
                          </div>
                        ) : (
                          <button
                            type="button"
                            disabled={isRunning}
                            onClick={(e) => {
                              e.stopPropagation()
                              handleAiFix(ins)
                            }}
                            className="group mt-0.5 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold bg-primary/10 text-primary border border-primary/25 hover:bg-primary hover:text-white hover:border-primary hover:shadow-lg hover:shadow-primary/30 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 active:scale-95"
                          >
                            <svg className="w-3.5 h-3.5 transition-transform group-hover:scale-110" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                            AI FIX
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Branded Pagination */}
          {instructionHistory.length > 0 && (
            <div className="flex items-center justify-between pt-2 border-t border-border">
              <span className="text-[10px] text-muted">
                Page {historyPage + 1}
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  disabled={historyPage === 0}
                  onClick={() => {
                    const p = historyPage - 1
                    loadHistory(p, historyAgentFilter, historyDateFrom, historyDateTo)
                  }}
                  className="px-2.5 py-1 rounded-[8px] text-[11px] font-semibold border border-border
                    text-muted hover:text-foreground hover:bg-hover
                    disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  ‹ Prev
                </button>
                {historyPage > 0 && (
                  <button
                    type="button"
                    onClick={() => loadHistory(0, historyAgentFilter, historyDateFrom, historyDateTo)}
                    className="w-7 h-7 rounded-[8px] text-[11px] font-semibold border border-border
                      text-muted hover:text-foreground hover:bg-hover transition-colors"
                  >
                    1
                  </button>
                )}
                {historyPage > 1 && (
                  <span className="text-[10px] text-muted px-0.5">…</span>
                )}
                <button
                  type="button"
                  disabled
                  className="w-7 h-7 rounded-[8px] text-[11px] font-bold
                    bg-primary text-white shadow-sm"
                >
                  {historyPage + 1}
                </button>
                <button
                  type="button"
                  disabled={!historyHasMore}
                  onClick={() => {
                    const p = historyPage + 1
                    loadHistory(p, historyAgentFilter, historyDateFrom, historyDateTo)
                  }}
                  className="px-2.5 py-1 rounded-[8px] text-[11px] font-semibold border border-border
                    text-muted hover:text-foreground hover:bg-hover
                    disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Next ›
                </button>
              </div>
            </div>
          )}
        </section>
      )}

      {activeTab === 'FILES' && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1 min-h-0">
          {/* File Tree Panel */}
          <div className="md:col-span-1 card-af p-4 text-xs space-y-2 min-h-0 max-h-[calc(100vh-219px)] overflow-y-auto">
            {isOffline && (
              <p className="text-sm text-muted italic pb-2 border-b border-border mb-2">
                Refer to the offline banner above.
              </p>
            )}
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
                {(fileTree.children || []).map((node: FileTreeNodeData) => (
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
          {isOffline && (
            <p className="text-sm text-muted italic">Refer to the offline banner above.</p>
          )}
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
                            Relevance: {(Number(res.score ?? 0) * 100).toFixed(0)}%
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
            <p className="text-sm text-muted text-center py-4">
              Refer to the offline banner above.
            </p>
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
                {(() => {
                  const staged = gitStatus.staged_files
                  if (!staged || staged.length === 0) return null
                  return (
                    <div>
                      <div className="text-muted mt-2 font-sans font-semibold">
                        Staged:
                      </div>
                      {staged.map((f: string, i: number) => (
                        <div key={i} className="text-primary pl-2">
                          ● {f}
                        </div>
                      ))}
                    </div>
                  )
                })()}
                {(() => {
                  const modified = gitStatus.modified_files
                  if (!modified || modified.length === 0) return null
                  return (
                    <div>
                      <div className="text-muted mt-2 font-sans font-semibold">
                        Modified:
                      </div>
                      {modified.map((f: string, i: number) => (
                        <div key={i} className="text-amber-500 pl-2">
                          ~ {f}
                        </div>
                      ))}
                    </div>
                  )
                })()}
                {(() => {
                  const untracked = gitStatus.untracked_files
                  if (!untracked || untracked.length === 0) return null
                  return (
                    <div>
                      <div className="text-muted mt-2 font-sans font-semibold">
                        Untracked:
                      </div>
                      {untracked.map((f: string, i: number) => (
                        <div key={i} className="text-emerald-500 pl-2">
                          + {f}
                        </div>
                      ))}
                    </div>
                  )
                })()}
                {(() => {
                  const unpushed = gitStatus.unpushed_files
                  if (!unpushed || unpushed.length === 0) return null
                  return (
                    <div>
                      <div className="text-muted mt-2 font-sans font-semibold">
                        Unpushed:
                      </div>
                      {unpushed.map((f: string, i: number) => (
                        <div key={i} className="text-blue-500 pl-2">
                          ↑ {f}
                        </div>
                      ))}
                    </div>
                  )
                })()}
              </div>

              {(() => {
                const gitAgentResult = pipelineResults['Git Agent'] as
                  | AgentResultPayload
                  | undefined
                if (!gitAgentResult) return null
                return (
                  <div className="bg-surface-secondary border border-border rounded-lg p-4 space-y-2">
                    <div className="text-xs font-semibold text-foreground">
                      Last Agent Commit
                    </div>
                    <div className="font-mono text-xs">
                      <span className="text-muted">Branch: </span>
                      <span className="text-primary">
                        {gitAgentResult.branch}
                      </span>
                    </div>
                    <div className="font-mono text-xs">
                      <span className="text-muted">Message: </span>
                      <span className="text-foreground">
                        {gitAgentResult.commit_message}
                      </span>
                    </div>
                  </div>
                )
              })()}

              {/* Commit History Log */}
              <div className="bg-surface-secondary border border-border rounded-lg p-4 space-y-3">
                <div className="text-xs font-semibold text-foreground flex items-center gap-2">
                  <span>⎇ Commit History</span>
                  <span className="text-[10px] text-muted font-normal">
                    (last {gitLog.length > 0 ? gitLog.length : '—'} commits)
                  </span>
                </div>
                {gitLogLoading ? (
                  <div className="flex items-center gap-2.5 text-xs text-muted py-2">
                    <span className="h-3.5 w-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                    Loading commit log…
                  </div>
                ) : gitLog.length > 0 ? (
                  <div className="font-mono text-xs space-y-0.5 max-h-[500px] overflow-y-auto">
                    {gitLog.map((commit: GitCommitLogEntry, i: number) => {
                      const commitId = commit.hash || `commit-${i}`
                      const isExpanded = expandedHistory === commitId
                      const shortHash = commit.hash
                        ? commit.hash.substring(0, 7)
                        : '—'
                      const filesList: GitChangedFile[] =
                        commit.changed_files || []
                      const totalInsertions: number =
                        commit.insertions ||
                        filesList.reduce(
                          (s: number, f: GitChangedFile) =>
                            s + (f.insertions || 0),
                          0,
                        )
                      const totalDeletions: number =
                        commit.deletions ||
                        filesList.reduce(
                          (s: number, f: GitChangedFile) =>
                            s + (f.deletions || 0),
                          0,
                        )
                      return (
                        <div
                          key={commitId}
                          className="border-b border-border/50 last:border-0"
                        >
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedHistory(
                                isExpanded ? null : commitId,
                              )
                            }
                            className="w-full flex items-start gap-3 py-1.5 text-left hover:bg-hover/50 transition-colors rounded px-1 -mx-1"
                          >
                            <span className="flex-shrink-0 w-[58px] h-[20px] inline-flex items-center justify-center rounded-md bg-[#0d1117] dark:bg-[#161b22] border border-[#30363d] text-[11px] font-bold text-[#c9d1d9] tracking-tight">
                              {shortHash}
                            </span>
                            <span className="text-foreground flex-1 min-w-0 break-words leading-[20px]">
                              {commit.message || '—'}
                            </span>
                            <span className="text-muted flex-shrink-0 text-[10px] leading-[20px] whitespace-nowrap">
                              {commit.author || ''}
                              {commit.time
                                ? ` · ${new Date(commit.time).toLocaleDateString()}`
                                : ''}
                            </span>
                          </button>
                          {isExpanded && filesList.length > 0 && (
                            <div className="ml-[70px] mb-2 border border-[#30363d] rounded-md bg-[#0d1117] overflow-hidden">
                              <div className="px-3 py-1.5 border-b border-[#30363d]/40 flex items-center gap-2 text-[10px] text-[#8b949e] bg-[#161b22]/50">
                                <span>
                                  {filesList.length} file
                                  {filesList.length !== 1 ? 's' : ''} changed
                                </span>
                                <span className="text-emerald-400 font-semibold">
                                  +{totalInsertions}
                                </span>
                                <span className="text-red-400 font-semibold">
                                  −{totalDeletions}
                                </span>
                              </div>
                              <div className="divide-y divide-[#30363d]/30">
                                {filesList.map((f: GitChangedFile) => (
                                  <div
                                    key={f.path}
                                    className="flex items-center gap-3 px-3 py-1 text-[11px]"
                                  >
                                    <span className="text-[#c9d1d9] flex-1 truncate">
                                      {f.path}
                                    </span>
                                    <span className="flex items-center gap-1.5 flex-shrink-0">
                                      <span className="text-emerald-400 w-6 text-right tabular-nums">
                                        +{f.insertions || 0}
                                      </span>
                                      <span className="text-red-400 w-6 text-right tabular-nums">
                                        −{f.deletions || 0}
                                      </span>
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-muted py-2">
                    No commits found in this workspace.
                  </p>
                )}
              </div>
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
          {isOffline && (
            <p className="text-sm text-muted italic">Refer to the offline banner above.</p>
          )}
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
                  <pre className="mt-3 bg-[#1e1e1e] border border-[#3c3c3c] rounded-lg p-3 text-[11px] font-mono whitespace-pre-wrap overflow-x-auto max-h-[400px] overflow-y-auto">
                    {highlightJSON(art.content)}
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
          {isOffline && (
            <p className="text-sm text-muted italic">Refer to the offline banner above.</p>
          )}
          <p className="text-xs text-muted">
            Latest Test Agent run — loaded from persisted pipeline history.
          </p>
          {(() => {
            const run = runs.find(
              (r) => r.agent_name === 'Test Agent' && r.metadata,
            )
            const meta = (run?.metadata ??
              pipelineResults['Test Agent']) as TestAgentMeta | null

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
                    <p className="text-xs text-muted">
                      {String(meta.test_summary)}
                    </p>
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
                  <details className="bg-[#1e1e1e] border border-[#3c3c3c] rounded-lg overflow-hidden">
                    <summary className="text-xs font-semibold text-[#cccccc] cursor-pointer px-4 py-2.5 hover:bg-[#2a2a2a] transition-colors select-none">
                      ▸ Raw output
                    </summary>
                    <pre className="text-[11px] font-mono whitespace-pre-wrap leading-relaxed px-4 py-3 border-t border-[#3c3c3c] overflow-x-auto max-h-[400px] overflow-y-auto">
                      {highlightJSON(run.output)}
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
          {isOffline && (
            <p className="text-sm text-muted italic">Refer to the offline banner above.</p>
          )}
          <p className="text-xs text-muted">
            Latest Validation Agent run — loaded from persisted pipeline
            history.
          </p>
          {(() => {
            const run = runs.find(
              (r) => r.agent_name === 'Validation Agent' && r.metadata,
            )
            const meta = (run?.metadata ??
              pipelineResults['Validation Agent']) as ValidationAgentMeta | null

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
                    {String(meta.build_status ?? '—')}
                  </span>
                </div>
                {verificationRuns.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-foreground mb-2">
                      Durable Verification Evidence
                    </div>
                    <div className="space-y-2">
                      {verificationRuns.slice(0, 20).map((evidence) => (
                        <details
                          key={evidence.id}
                          className="rounded-lg border border-border bg-surface-secondary p-3"
                        >
                          <summary className="cursor-pointer flex items-center gap-2 text-xs">
                            <span
                              className={
                                evidence.status === 'PASSED'
                                  ? 'text-emerald-500'
                                  : 'text-red-500'
                              }
                            >
                              {evidence.status === 'PASSED' ? '✓' : '✗'}
                            </span>
                            <span className="font-semibold text-foreground uppercase">
                              {evidence.category}
                            </span>
                            <span className="font-mono text-muted">
                              {evidence.executable}
                            </span>
                            <span className="ml-auto text-[10px] text-muted">
                              {evidence.duration_seconds.toFixed(2)}s
                            </span>
                          </summary>
                          <div className="mt-2 text-[10px] font-mono text-muted break-all">
                            evidence: sha256:{evidence.output_digest}
                          </div>
                          {evidence.output_excerpt && (
                            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded border border-border bg-background p-2 text-[10px] text-muted">
                              {evidence.output_excerpt}
                            </pre>
                          )}
                        </details>
                      ))}
                    </div>
                  </div>
                )}
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
                  <details className="bg-[#1e1e1e] border border-[#3c3c3c] rounded-lg overflow-hidden">
                    <summary className="text-xs font-semibold text-[#cccccc] cursor-pointer px-4 py-2.5 hover:bg-[#2a2a2a] transition-colors select-none">
                      ▸ Raw output
                    </summary>
                    <pre className="text-[11px] font-mono whitespace-pre-wrap leading-relaxed px-4 py-3 border-t border-[#3c3c3c] overflow-x-auto max-h-[400px] overflow-y-auto">
                      {highlightJSON(run.output)}
                    </pre>
                  </details>
                )}
              </>
            )
          })()}
        </section>
      )}

      {activeTab === 'LEAD' && (
        <section className="card-af p-6 space-y-5">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Project Technical Lead
            </h2>
            <p className="text-xs text-muted mt-1">
              Ask about architecture, recent work, failures, approvals, verification,
              or AI-authored commits. Answers are grounded in bounded project records.
            </p>
          </div>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="sr-only" htmlFor="tech-lead-question">
                Question for the project technical lead
              </label>
              <textarea
                id="tech-lead-question"
                value={techLeadQuestion}
                onChange={(event) => setTechLeadQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                    event.preventDefault()
                    handleTechLeadQuery()
                  }
                }}
                rows={3}
                maxLength={4000}
                placeholder="What changed recently, and is it verified?"
                className="input-af w-full text-sm resize-y"
              />
            </div>
            <button
              type="button"
              className="btn-primary-af text-sm disabled:opacity-50"
              disabled={techLeadLoading || techLeadQuestion.trim().length < 2}
              onClick={handleTechLeadQuery}
            >
              {techLeadLoading ? 'Thinking…' : 'Ask Tech Lead'}
            </button>
          </div>
          {techLeadError && (
            <p role="alert" className="text-xs text-red-500">
              {techLeadError}
            </p>
          )}
          <div className="space-y-3">
            {techLeadHistory.length === 0 && !techLeadLoading ? (
              <p className="text-xs text-muted text-center py-8">
                No technical-lead conversations yet.
              </p>
            ) : (
              techLeadHistory.map((interaction) => (
                <article
                  key={interaction.id}
                  className="rounded-lg border border-border bg-surface-secondary p-4"
                >
                  {interaction.question && (
                    <p className="text-xs font-semibold text-foreground mb-2">
                      {interaction.question}
                    </p>
                  )}
                  <Markdown>{interaction.answer}</Markdown>
                  <div className="mt-3 flex items-center gap-3 text-[10px] text-muted">
                    <span>{interaction.model_name || 'model unavailable'}</span>
                    <span>{interaction.total_tokens} tokens</span>
                    <span>{new Date(interaction.created_at).toLocaleString()}</span>
                  </div>
                  {interaction.sources.length > 0 && (
                    <details className="mt-2 text-[10px] text-muted">
                      <summary className="cursor-pointer text-primary">
                        {interaction.sources.length} context sources
                      </summary>
                      <div className="mt-1 font-mono break-all">
                        {interaction.sources.join(' · ')}
                      </div>
                    </details>
                  )}
                </article>
              ))
            )}
          </div>
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

      {/* AI FIX Confirmation Modal */}
      <AiFixModal
        open={fixModalOpen}
        fixInfo={fixModalInfo}
        onConfirm={handleAiFixConfirm}
        onCancel={() => setFixModalOpen(false)}
        submitting={fixSubmitting}
      />
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
  const [ciGateEnabled, setCiGateEnabled] = useState(
    project?.ci_gate_enabled ?? true,
  )
  const [gitCommitTemplate, setGitCommitTemplate] = useState(
    project?.git_commit_template || '',
  )
  const [fsRead, setFsRead] = useState(project?.fs_read_enabled ?? true)
  const [fsWrite, setFsWrite] = useState(project?.fs_write_enabled ?? true)
  const [fsDelete, setFsDelete] = useState(project?.fs_delete_enabled ?? true)
  const [defaultModel, setDefaultModel] = useState(project?.default_model || '')
  const [approvalMode, setApprovalMode] = useState<'NEVER' | 'RISKY' | 'ALWAYS'>(
    project?.approval_mode || 'RISKY',
  )
  const [commandAllowlist, setCommandAllowlist] = useState(
    (project?.command_allowlist || []).join(', '),
  )
  const [maxCommandSeconds, setMaxCommandSeconds] = useState(
    project?.max_command_seconds ?? 120,
  )
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Fetch available models
  useEffect(() => {
    import('@/lib/api').then(({ getModels }) =>
      getModels().then(setAvailableModels).catch(() => {}),
    )
  }, [])

  // Sync form state when the project loads/changes. Adjusting state during
  // render (keyed on the project id) is the React-recommended pattern for
  // initializing a form from an async-loaded prop (avoids set-state-in-effect).
  const syncProjectId = project?.id ?? null
  const [prevSyncProjectId, setPrevSyncProjectId] = useState(syncProjectId)
  if (project && syncProjectId !== prevSyncProjectId) {
    setPrevSyncProjectId(syncProjectId)
    setGitEnabled(project.git_enabled ?? true)
    setBranchPatterns((project.git_branch_patterns || ['*']).join(', '))
    setGitRequirePr(project.git_require_pr ?? false)
    setCiGateEnabled(project.ci_gate_enabled ?? true)
    setGitCommitTemplate(project.git_commit_template || '')
    setFsRead(project.fs_read_enabled ?? true)
    setFsWrite(project.fs_write_enabled ?? true)
    setFsDelete(project.fs_delete_enabled ?? true)
    setDefaultModel(project.default_model || '')
    setApprovalMode(project.approval_mode || 'RISKY')
    setCommandAllowlist((project.command_allowlist || []).join(', '))
    setMaxCommandSeconds(project.max_command_seconds ?? 120)
  }

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
        ci_gate_enabled: ciGateEnabled,
        git_commit_template: gitCommitTemplate || null,
        fs_read_enabled: fsRead,
        fs_write_enabled: fsWrite,
        fs_delete_enabled: fsDelete,
        default_model: defaultModel || null,
        approval_mode: approvalMode,
        command_allowlist: commandAllowlist
          .split(',')
          .map((command) => command.trim())
          .filter(Boolean),
        max_command_seconds: maxCommandSeconds,
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
      {/* Human approval and command policy */}
      <div className="card-af p-6">
        <h2 className="text-base font-semibold text-foreground mb-4">
          🛡 Human Approval &amp; Commands
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-foreground mb-1" htmlFor="approval-mode">
              Approval mode
            </label>
            <select
              id="approval-mode"
              value={approvalMode}
              onChange={(event) =>
                setApprovalMode(event.target.value as 'NEVER' | 'RISKY' | 'ALWAYS')
              }
              className="input-af w-full max-w-[380px] text-sm"
            >
              <option value="RISKY">Risky operations only</option>
              <option value="ALWAYS">Every mutation</option>
              <option value="NEVER">Never pause for approval</option>
            </select>
            <p className="text-[11px] text-muted mt-1">
              Policy restrictions still apply when approvals are disabled.
            </p>
          </div>
          <div>
            <label className="block text-sm text-foreground mb-1" htmlFor="command-allowlist">
              Allowed command executables
            </label>
            <input
              id="command-allowlist"
              type="text"
              value={commandAllowlist}
              onChange={(event) => setCommandAllowlist(event.target.value)}
              placeholder="pytest, npm, pnpm, ruff"
              className="input-af w-full text-xs font-mono"
            />
            <p className="text-[11px] text-muted mt-1">
              Comma-separated executable names. Commands outside this list are blocked.
            </p>
          </div>
          <div>
            <label className="block text-sm text-foreground mb-1" htmlFor="command-timeout">
              Maximum command runtime (seconds)
            </label>
            <input
              id="command-timeout"
              type="number"
              min={1}
              max={300}
              value={maxCommandSeconds}
              onChange={(event) =>
                setMaxCommandSeconds(
                  Math.min(300, Math.max(1, Number(event.target.value) || 1)),
                )
              }
              className="input-af w-36 text-sm"
            />
          </div>
        </div>
      </div>

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
              Require Pull Request
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
            When enabled, AI commits are restricted to isolated agent branches;
            merging remains a reviewed Pull Request action.
          </p>

          <label className="flex items-center justify-between">
            <span className="text-sm text-foreground">
              Require passing CI verification before Git changes
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={ciGateEnabled}
              onClick={() => setCiGateEnabled(!ciGateEnabled)}
              disabled={!gitEnabled}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary ${
                ciGateEnabled ? 'bg-emerald-500' : 'bg-border'
              } ${!gitEnabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  ciGateEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </label>
          <p className="text-[11px] text-muted -mt-2">
            A real validation tool must report PASSED; estimates and unavailable
            checks remain UNVERIFIED and cannot be committed.
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

      {/* Default LLM Model */}
      <div className="card-af p-6">
        <h2 className="text-base font-semibold text-foreground mb-4">
          🤖 Default LLM Model
        </h2>
        <p className="text-[11px] text-muted mb-3">
          Select which model new sessions in this project will use by default.
          Configure API keys on the Settings page.
        </p>
        <select
          value={defaultModel}
          onChange={(e) => setDefaultModel(e.target.value)}
          className="input-af text-sm max-w-[380px]"
        >
          <option value="">Platform default (DeepSeek)</option>
          {availableModels.length > 0 ? (
            ['deepseek', 'openai', 'gemini', 'claude'].map((provider) => {
              const groupModels = availableModels.filter((m) => m.provider === provider)
              if (groupModels.length === 0) return null
              const label = provider === 'deepseek' ? 'DeepSeek' : provider === 'openai' ? 'OpenAI' : provider === 'gemini' ? 'Gemini' : 'Claude'
              return (
                <optgroup key={provider} label={label}>
                  {groupModels.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.label} ({(m.context_limit / 1000).toFixed(0)}K)
                      {m.vision ? ' 👁' : ''}
                    </option>
                  ))}
                </optgroup>
              )
            })
          ) : (
            <>
              <optgroup label="DeepSeek">
                <option value="deepseek-chat">DeepSeek-V3 (64K)</option>
                <option value="deepseek-coder">DeepSeek-Coder (128K)</option>
                <option value="deepseek-reasoner">DeepSeek-R1 (64K)</option>
              </optgroup>
              <optgroup label="OpenAI">
                <option value="gpt-4o">GPT-4o (128K) 👁</option>
                <option value="gpt-4-turbo">GPT-4 Turbo (128K) 👁</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo (16K)</option>
              </optgroup>
              <optgroup label="Gemini">
                <option value="gemini-2.5-pro">Gemini 2.5 Pro (1M) 👁</option>
                <option value="gemini-2.5-flash">Gemini 2.5 Flash (1M) 👁</option>
                <option value="gemini-1.5-pro">Gemini 1.5 Pro (2M) 👁</option>
              </optgroup>
              <optgroup label="Claude">
                <option value="claude-3.5-sonnet">Claude 3.5 Sonnet (200K) 👁</option>
                <option value="claude-3-opus">Claude 3 Opus (200K) 👁</option>
                <option value="claude-3-haiku">Claude 3 Haiku (200K) 👁</option>
              </optgroup>
            </>
          )}
        </select>
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
