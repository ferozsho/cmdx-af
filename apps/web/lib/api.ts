/**
 * AgentForge API Client — typed fetch wrappers for all Cloud Control Plane endpoints.
 *
 * All functions return the parsed JSON response or throw a structured ApiError.
 * Base URL is configurable via NEXT_PUBLIC_API_URL env var (defaults to localhost:8000).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const AUTH_TOKEN_KEY = 'agentforge_token'
const AUTH_REFRESH_KEY = 'agentforge_refresh_token'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(AUTH_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(AUTH_REFRESH_KEY)
}

export function setToken(token: string): void {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(AUTH_TOKEN_KEY, token)
  }
}

export function setTokens(access: string, refresh?: string | null): void {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(AUTH_TOKEN_KEY, access)
    if (refresh) window.localStorage.setItem(AUTH_REFRESH_KEY, refresh)
  }
}

export function clearToken(): void {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(AUTH_TOKEN_KEY)
    window.localStorage.removeItem(AUTH_REFRESH_KEY)
  }
}

export class ApiError extends Error {
  code: number
  detail: string
  constructor(code: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.code = code
    this.detail = detail
  }
}

async function rawFetch(
  method: string,
  path: string,
  body?: unknown,
  options?: RequestInit,
): Promise<Response> {
  const url = `${API_BASE}${path}`
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options?.headers,
  }
  return fetch(url, {
    method,
    body: body ? JSON.stringify(body) : undefined,
    // Spread options FIRST, then apply headers last so a caller-supplied
    // `options.headers` (e.g. Idempotency-Key on instruction submits) cannot
    // clobber the Content-Type and Authorization headers.
    ...options,
    headers,
  })
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options?: RequestInit,
): Promise<T> {
  let res = await rawFetch(method, path, body, options)

  // One-shot access-token refresh on 401 (skip the refresh endpoint itself
  // to avoid recursion). getMe/change-password etc. DO auto-refresh, so an
  // expired access token is silently replaced on page load.
  if (
    res.status === 401 &&
    getRefreshToken() &&
    !path.includes('/api/v1/auth/refresh')
  ) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      res = await rawFetch(method, path, body, options)
    }
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const errBody = await res.json()
      detail = errBody.detail || errBody.message || detail
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, detail)
  }

  return res.json() as Promise<T>
}

// Single-flight refresh: concurrent 401s share one refresh request (refresh
// tokens are single-use/rotating, so parallel refreshes would race and
// revoke each other).
let refreshInFlight: Promise<boolean> | null = null

/** Exchange the stored refresh token for a fresh pair. Returns true on success. */
async function tryRefresh(): Promise<boolean> {
  if (!getRefreshToken()) return false
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null
    })
  }
  return refreshInFlight
}

async function doRefresh(): Promise<boolean> {
  const refresh = getRefreshToken()
  if (!refresh) return false
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) {
      clearToken()
      return false
    }
    const data = (await res.json()) as AuthResponse
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    return false
  }
}

// ── Auth ───────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  role: string
  created_at?: string | null
}

export interface AuthResponse {
  access_token: string
  refresh_token?: string | null
  token_type: string
  user: AuthUser
}

/** POST /api/v1/auth/register — create an account, returns JWT + user */
export function register(
  email: string,
  password: string,
  fullName?: string,
): Promise<AuthResponse> {
  return request<AuthResponse>('POST', '/api/v1/auth/register', {
    email,
    password,
    full_name: fullName || null,
  })
}

/** POST /api/v1/auth/login — returns JWT + user */
export function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('POST', '/api/v1/auth/login', { email, password })
}

/** GET /api/v1/auth/me — current authenticated user (throws 401 if not authed) */
export function getMe(): Promise<AuthUser> {
  return request<AuthUser>('GET', '/api/v1/auth/me')
}

/** POST /api/v1/auth/change-password — verifies current, revokes old tokens */
export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<AuthResponse> {
  return request<AuthResponse>('POST', '/api/v1/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

/** POST /api/v1/auth/forgot-password — request a reset token (dev: returned) */
export function forgotPassword(
  email: string,
): Promise<{ ok: boolean; detail: string; reset_token?: string }> {
  return request('POST', '/api/v1/auth/forgot-password', { email })
}

/** POST /api/v1/auth/reset-password — set a new password with a token */
export function resetPassword(
  token: string,
  newPassword: string,
): Promise<{ ok: boolean; detail: string }> {
  return request('POST', '/api/v1/auth/reset-password', {
    token,
    new_password: newPassword,
  })
}

/** Client-side logout — clears stored tokens and notifies backend. */
export async function logout(): Promise<void> {
  const token = getToken()
  if (token) {
    // Fire-and-forget — don't block on failure
    fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {})
  }
  clearToken()
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface ProjectResponse {
  id: string
  name: string
  description: string | null
  execution_target: string
  local_path?: string | null
  tech_stack?: Record<string, boolean> | null
  status: string
  created_at?: string | null
  updated_at?: string | null
  // Git authorization
  git_enabled?: boolean
  git_branch_patterns?: string[] | null
  git_require_pr?: boolean
  ci_gate_enabled?: boolean
  git_commit_template?: string | null
  // Filesystem access
  fs_read_enabled?: boolean
  fs_write_enabled?: boolean
  fs_delete_enabled?: boolean
  default_model?: string | null
  // Human approval and command execution policy
  approval_mode?: 'NEVER' | 'RISKY' | 'ALWAYS'
  command_allowlist?: string[] | null
  max_command_seconds?: number
  // RAG readiness gate — locked until the first index completes.
  rag_gate?: {
    state: 'complete' | 'indexing_required' | 'indexing' | 'failed' | 'offline'
    locked: boolean
    indexed_at?: string | null
  }
}

export interface ApprovalResponse {
  id: string
  project_id: string
  instruction_id: string | null
  tool_name: string
  operation: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  summary: string
  request_payload: Record<string, unknown>
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CONSUMED'
  requested_at: string
  expires_at: string
  decided_at: string | null
  decision_comment: string | null
}

export interface DeviceResponse {
  id: string
  name: string
  hostname: string
  platform: string
  status: string
  agent_version: string
  os_version?: string | null
}

export interface ValidatePathResponse {
  valid: boolean
  exists: boolean
  is_directory: boolean
  readable: boolean
  writable: boolean
  git_repository: boolean
  detected_stack: string[]
  project_name: string | null
  files_count: number
  directories_count: number
  warnings: string[]
}

export interface HealthResponse {
  app_name: string
  environment: string
  mode: string
  version: string
}

export interface ComponentHealth {
  status: string
  message: string
}

export interface FullHealthResponse {
  status: string
  app_name: string
  environment: string
  mode: string
  version: string
  components: Record<string, ComponentHealth>
}

// ── API Functions ──────────────────────────────────────────────────────────

/** GET /api/v1/health */
export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('GET', '/api/v1/health')
}

/** GET /api/v1/health/full */
export function getFullHealth(): Promise<FullHealthResponse> {
  return request<FullHealthResponse>('GET', '/api/v1/health/full')
}

/** POST /api/v1/settings/test-connection/:provider */
export function testProviderConnection(
  provider: string,
): Promise<{ ok: boolean; detail?: string; error?: string }> {
  return request('POST', `/api/v1/settings/test-connection/${provider}`)
}

/** GET /api/v1/settings/models — list all LLM models with capabilities */
export function getModels(visionOnly = false): Promise<
  { name: string; provider: string; context_limit: number; vision: boolean; label: string }[]
> {
  return request('GET', `/api/v1/settings/models${visionOnly ? '?vision_only=true' : ''}`)
}

/** GET /api/v1/settings */
export function getSettings(): Promise<{
  deepseek_base_url: string
  deepseek_chat_model: string
  deepseek_max_tokens: number
  has_deepseek_key: boolean
  openai_base_url: string
  openai_chat_model: string
  openai_max_tokens: number
  has_openai_key: boolean
  gemini_chat_model: string
  has_gemini_key: boolean
  claude_chat_model: string
  has_claude_key: boolean
  max_agent_steps: number
  agent_timeout: number
  rag_top_k: number
  rag_chunk_size: number
  rag_chunk_overlap: number
  rag_similarity_threshold: number
  context_window_budget: string
  allowed_commands: string
}> {
  return request('GET', '/api/v1/settings')
}

/** PUT /api/v1/settings */
export function updateSettings(data: {
  deepseek_base_url?: string
  deepseek_chat_model?: string
  deepseek_max_tokens?: number
  openai_base_url?: string
  openai_chat_model?: string
  openai_max_tokens?: number
  gemini_chat_model?: string
  claude_chat_model?: string
  max_agent_steps?: number
  agent_timeout?: number
  rag_top_k?: number
  rag_chunk_size?: number
  rag_chunk_overlap?: number
  rag_similarity_threshold?: number
  context_window_budget?: string
  allowed_commands?: string
}): Promise<{ ok: boolean }> {
  return request('PUT', '/api/v1/settings', data)
}

/** Sentinel passed to updateApiKey to delete a provider key. */
export const REMOVE_API_KEY = '__remove__'

/**
 * PUT /api/v1/settings/keys — set, replace, or remove a provider API key.
 * Pass REMOVE_API_KEY as `apiKey` to delete the key.
 */
export function updateApiKey(
  provider: 'deepseek' | 'openai' | 'gemini' | 'claude',
  apiKey: string,
): Promise<{ ok: boolean; detail?: string; error?: string }> {
  return request('PUT', '/api/v1/settings/keys', {
    provider,
    api_key: apiKey,
  })
}

/** GET /api/v1/projects/stats/summary */
export function getProjectStats(): Promise<{
  total_projects: number
  online_devices: number
  total_devices: number
  agent_runs: number
  tests_passed: number
}> {
  return request('GET', '/api/v1/projects/stats/summary')
}

/** GET /api/v1/projects */
export function listProjects(): Promise<ProjectResponse[]> {
  return request<ProjectResponse[]>('GET', '/api/v1/projects')
}

/** GET /api/v1/projects/:id */
export function getProject(id: string): Promise<ProjectResponse> {
  return request<ProjectResponse>('GET', `/api/v1/projects/${encodeURIComponent(id)}`)
}

/** POST /api/v1/projects */
export function createProject(data: {
  name: string
  description?: string
  execution_target?: string
  local_path?: string
  tech_stack?: string[]
  initial_instruction?: string
}): Promise<ProjectResponse> {
  return request<ProjectResponse>('POST', '/api/v1/projects', data)
}

/** PATCH /api/v1/projects/:id */
export function updateProject(
  id: string,
  data: {
    name?: string
    description?: string
    execution_target?: string
    local_path?: string
    tech_stack?: string[]
    // Git authorization
    git_enabled?: boolean
    git_branch_patterns?: string[]
    git_require_pr?: boolean
    ci_gate_enabled?: boolean
    git_commit_template?: string | null
    // Filesystem access
    fs_read_enabled?: boolean
    fs_write_enabled?: boolean
    fs_delete_enabled?: boolean
    default_model?: string | null
    approval_mode?: 'NEVER' | 'RISKY' | 'ALWAYS'
    command_allowlist?: string[]
    max_command_seconds?: number
  },
): Promise<ProjectResponse> {
  return request<ProjectResponse>(
    'PATCH',
    `/api/v1/projects/${encodeURIComponent(id)}`,
    data,
  )
}

/** GET /api/v1/projects/:id/approvals */
export function listApprovals(
  projectId: string,
  status?: ApprovalResponse['status'],
): Promise<ApprovalResponse[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return request<ApprovalResponse[]>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(projectId)}/approvals${query}`,
  )
}

/** Resolve a pending, user-owned approval request. */
export function decideApproval(
  approvalId: string,
  decision: 'approve' | 'reject',
  comment?: string,
): Promise<ApprovalResponse> {
  return request<ApprovalResponse>(
    'POST',
    `/api/v1/approvals/${encodeURIComponent(approvalId)}/${decision}`,
    { comment: comment?.trim() || null },
  )
}

/** DELETE /api/v1/projects/:id */
export function deleteProject(
  id: string,
): Promise<{ ok: boolean; detail: string }> {
  return request<{ ok: boolean; detail: string }>(
    'DELETE',
    `/api/v1/projects/${encodeURIComponent(id)}`,
  )
}

/** POST /api/v1/projects/validate-path */
export function validateProjectPath(
  path: string,
): Promise<ValidatePathResponse> {
  return request<ValidatePathResponse>('POST', '/api/v1/projects/validate-path', { path })
}

/** GET /api/v1/projects/:id/tree */
export function getProjectTree(id: string): Promise<unknown> {
  return request<unknown>('GET', `/api/v1/projects/${encodeURIComponent(id)}/tree`)
}

/** GET /api/v1/projects/:id/files/content */
export function getFileContent(
  id: string,
  filePath: string,
): Promise<{ path: string; content: string }> {
  return request<{ path: string; content: string }>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/files/content?path=${encodeURIComponent(filePath)}`,
  )
}

/** POST /api/v1/projects/:id/rag/search */
export function ragSearch(
  id: string,
  query: string,
  topK = 5,
): Promise<unknown[]> {
  return request<unknown[]>('POST', `/api/v1/projects/${encodeURIComponent(id)}/rag/search`, {
    query,
    top_k: topK,
  })
}

export interface RagChunk {
  id: string
  file_path: string
  start_line: number
  end_line: number
  content: string
}

export interface RagChunksPage {
  total: number
  offset: number
  limit: number
  chunks: RagChunk[]
}

/** GET /api/v1/projects/:id/rag/chunks — paginated browse of indexed chunks */
export function listRagChunks(
  id: string,
  offset = 0,
  limit = 10,
  q = '',
): Promise<RagChunksPage> {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  })
  if (q) params.set('q', q)
  return request<RagChunksPage>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/rag/chunks?${params.toString()}`,
  )
}

/** POST /api/v1/projects/:id/rag/reindex — kicks off a background job */
export function reindexRag(
  id: string,
): Promise<{
  status: 'started' | 'running'
  job: ReindexJob | null
}> {
  return request('POST', `/api/v1/projects/${encodeURIComponent(id)}/rag/reindex`)
}

/** GET /api/v1/projects/:id/rag/reindex-status */
export function getReindexStatus(
  id: string,
): Promise<{ status: string; job: ReindexJob | null }> {
  return request('GET', `/api/v1/projects/${encodeURIComponent(id)}/rag/reindex-status`)
}

export interface ReindexJob {
  status: 'running' | 'done' | 'failed' | 'idle'
  files_indexed: number
  chunks: number
  last_index: string | null
  error: string | null
  started_at: string | null
  finished_at: string | null
}

/** GET /api/v1/projects/:id/git/status */
export function getGitStatus(id: string): Promise<unknown> {
  return request<unknown>('GET', `/api/v1/projects/${encodeURIComponent(id)}/git/status`)
}

/** GET /api/v1/projects/:id/git/log */
export function getGitLog(id: string, maxCount = 20): Promise<unknown[]> {
  return request<unknown[]>('GET', `/api/v1/projects/${encodeURIComponent(id)}/git/log?max_count=${maxCount}`)
}

export interface GitProvenanceResponse {
  id: string
  instruction_id: string
  commit_hash: string
  branch: string
  message: string
  ai_generated: boolean
  provenance_digest: string | null
  prompt_digest: string | null
  model_name: string | null
  changed_files: string[]
  commit_metadata: Record<string, unknown>
  verification_status: string
  created_at: string
}

/** GET /api/v1/projects/:id/git/provenance */
export function getGitProvenance(id: string): Promise<GitProvenanceResponse[]> {
  return request<GitProvenanceResponse[]>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/git/provenance`,
  )
}

export interface VerificationRunResponse {
  id: string
  instruction_id: string
  category: string
  executable: string
  command_digest: string
  status: 'PASSED' | 'FAILED'
  exit_code: number | null
  duration_seconds: number
  output_digest: string
  output_excerpt: string
  created_at: string
}

export interface TechLeadInteractionResponse {
  id: string
  question?: string
  answer: string
  model_name: string | null
  sources: string[]
  total_tokens: number
  created_at: string
}

/** Query the project-wide technical-lead assistant. */
export function queryTechLead(
  projectId: string,
  question: string,
  sessionId?: string,
): Promise<TechLeadInteractionResponse> {
  return request<TechLeadInteractionResponse>(
    'POST',
    `/api/v1/projects/${encodeURIComponent(projectId)}/tech-lead/query`,
    sessionId ? { question, session_id: sessionId } : { question },
  )
}

/** List audited technical-lead conversations for a project. */
export function listTechLeadHistory(
  projectId: string,
): Promise<TechLeadInteractionResponse[]> {
  return request<TechLeadInteractionResponse[]>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(projectId)}/tech-lead/history`,
  )
}

/** GET /api/v1/projects/:id/verifications */
export function listVerificationRuns(
  id: string,
  instructionId?: string,
): Promise<VerificationRunResponse[]> {
  const query = instructionId
    ? `?instruction_id=${encodeURIComponent(instructionId)}`
    : ''
  return request<VerificationRunResponse[]>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/verifications${query}`,
  )
}

/** POST /api/v1/projects/:id/git/rollback */
export function rollbackGit(
  id: string,
  commitHash: string,
): Promise<{ ok: boolean; detail: string; result: unknown }> {
  return request('POST', `/api/v1/projects/${encodeURIComponent(id)}/git/rollback`, {
    commit_hash: commitHash,
  })
}

export interface RagStats {
  online?: boolean
  state?: string
  indexing?: boolean
  progress?: number
  files_scanned?: number
  total_files?: number
  files_indexed: number
  chunks: number
  last_index: string | null
  current_file?: string | null
  started_at?: string | null
  finished_at?: string | null
}

/** GET /api/v1/projects/:id/rag/stats */
export function getRagStats(id: string): Promise<RagStats> {
  return request<RagStats>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/rag/stats`,
  )
}

export interface RagReadiness {
  state: 'complete' | 'indexing_required' | 'indexing' | 'failed' | 'offline'
  locked: boolean
  online: boolean
  indexing: boolean
  progress: number
  files_scanned: number
  total_files: number
  files_indexed: number
  chunks: number
  current_file?: string | null
  last_index?: string | null
  indexed_at?: string | null
  job?: ReindexJob | null
}

/** GET /api/v1/projects/:id/rag/readiness — RAG gate + auto re-index status */
export function getRagReadiness(id: string): Promise<RagReadiness> {
  return request<RagReadiness>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/rag/readiness`,
  )
}

/** GET /api/v1/projects/:id/files/original */
export function getFileOriginal(
  id: string,
  filePath: string,
): Promise<{ path: string; content: string }> {
  return request<{ path: string; content: string }>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/files/original?path=${encodeURIComponent(filePath)}`,
  )
}

/** GET /api/v1/projects/:id/artifacts */
export function listArtifacts(
  id: string,
): Promise<
  {
    id: string
    instruction_id: string
    title: string
    artifact_type: string
    content: string
    created_at: string | null
  }[]
> {
  return request('GET', `/api/v1/projects/${encodeURIComponent(id)}/artifacts`)
}

/** GET /api/v1/projects/:id/runs — persisted agent runs (via instructions) */
export interface AgentRun {
  id: string
  instruction_id: string
  agent_name: string
  status: string
  output: string | null
  metadata: Record<string, unknown> | null
  duration_seconds: number
  created_at: string | null
}

export function listProjectRuns(
  id: string,
  limit = 50,
): Promise<AgentRun[]> {
  return request(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/runs?limit=${limit}`,
  )
}

/** GET /api/v1/observability/agent-metrics */
export function getAgentMetrics(): Promise<{
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
}> {
  return request('GET', '/api/v1/observability/agent-metrics')
}

/** POST /api/v1/projects/:id/instructions */
export function submitInstruction(
  id: string,
  prompt: string,
  imageBytes?: string,
  imageMimeType?: string,
  sessionId?: string,
  idempotencyKey?: string,
): Promise<{ id: string; project_id: string; prompt: string; status: string }> {
  const body: Record<string, unknown> = { prompt }
  if (imageBytes) {
    body.image_bytes = imageBytes
    body.image_mime_type = imageMimeType || 'image/png'
  }
  if (sessionId) {
    body.session_id = sessionId
  }
  const requestKey =
    idempotencyKey ||
    (typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`)
  return request<{ id: string; project_id: string; prompt: string; status: string }>(
    'POST',
    `/api/v1/projects/${encodeURIComponent(id)}/instructions`,
    body,
    { headers: { 'Idempotency-Key': requestKey } },
  )
}

/** POST /api/v1/projects/:id/instructions/:instructionId/cancel */
export function cancelInstruction(
  id: string,
  instructionId: string,
): Promise<{ id: string; status: string; cancel_requested_at: string | null }> {
  return request(
    'POST',
    `/api/v1/projects/${encodeURIComponent(id)}/instructions/${encodeURIComponent(instructionId)}/cancel`,
  )
}

/** GET /api/v1/projects/:id/instructions */
export function listInstructions(
  id: string,
): Promise<
  {
    id: string
    project_id: string
    prompt: string
    status: string
    created_at: string | null
  }[]
> {
  return request('GET', `/api/v1/projects/${encodeURIComponent(id)}/instructions`)
}

/** GET /api/v1/users/me/instructions — lightweight user-wide instruction history */
export function listUserInstructions(
  limit = 50,
): Promise<{ id: string; prompt: string; project_id: string; created_at: string | null }[]> {
  return request(
    'GET',
    `/api/v1/users/me/instructions?limit=${limit}`,
  )
}

// ── Sessions ─────────────────────────────────────────────────────────────

export interface SessionResponse {
  id: string
  project_id: string
  user_id: string | null
  name: string
  model_name: string
  context_limit: number
  total_tokens_used: number
  created_at: string | null
  updated_at: string | null
}

export interface SessionContextResponse {
  session_id: string
  model_name: string
  context_limit: number
  total_tokens_used: number
  context_used_pct: number
  previous_instructions: {
    instruction_id: string
    prompt: string
    status: string
    created_at: string | null
  }[]
}

export function listSessions(
  projectId: string,
): Promise<SessionResponse[]> {
  return request('GET', `/api/v1/projects/${encodeURIComponent(projectId)}/sessions`)
}

export function createSession(
  projectId: string,
  data: { name: string; model_name: string },
): Promise<SessionResponse> {
  return request('POST', `/api/v1/projects/${encodeURIComponent(projectId)}/sessions`, data)
}

/** PATCH /api/v1/projects/:id/sessions/:sid — rename a session */
export function updateSession(
  projectId: string,
  sessionId: string,
  data: { name: string },
): Promise<{ ok: boolean; id: string; name: string }> {
  return request(
    'PATCH',
    `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}`,
    data,
  )
}

/** DELETE /api/v1/projects/:id/sessions/:sid — delete a session */
export function deleteSession(
  projectId: string,
  sessionId: string,
): Promise<{ ok: boolean }> {
  return request(
    'DELETE',
    `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}`,
  )
}

export function getSessionContext(
  projectId: string,
  sessionId: string,
): Promise<SessionContextResponse> {
  return request(
    'GET',
    `/api/v1/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(sessionId)}/context`,
  )
}

/** GET /api/v1/projects/:id/instructions/history — full history with agent runs */
export function listInstructionHistory(
  id: string,
  options?: {
    limit?: number
    offset?: number
    agent_name?: string
    date_from?: string
    date_to?: string
  },
): Promise<
  {
    id: string
    project_id: string
    user_id: string | null
    prompt: string
    status: string
    created_at: string | null
    runs: {
      agent_name: string
      status: string
      duration_seconds: number
      output: string | null
      metadata: Record<string, unknown>
      created_at: string | null
    }[]
  }[]
> {
  const params = new URLSearchParams()
  if (options?.limit) params.set('limit', String(options.limit))
  if (options?.offset) params.set('offset', String(options.offset))
  if (options?.agent_name) params.set('agent_name', options.agent_name)
  if (options?.date_from) params.set('date_from', options.date_from)
  if (options?.date_to) params.set('date_to', options.date_to)
  const qs = params.toString()
  return request(
    'GET',
    `/api/v1/projects/${encodeURIComponent(id)}/instructions/history${qs ? `?${qs}` : ''}`,
  )
}

/** GET /api/v1/devices */
export function listDevices(): Promise<DeviceResponse[]> {
  return request<DeviceResponse[]>('GET', '/api/v1/devices')
}

/** DELETE /api/v1/devices/:id */
export function revokeDevice(
  id: string,
): Promise<{ ok: boolean; detail: string }> {
  return request<{ ok: boolean; detail: string }>(
    'DELETE',
    `/api/v1/devices/${encodeURIComponent(id)}`,
  )
}

/** POST /api/v1/devices/pairing-code */
export function generatePairingCode(): Promise<{
  pairing_code: string
  expires_in_seconds: number
}> {
  return request<{ pairing_code: string; expires_in_seconds: number }>(
    'POST',
    '/api/v1/devices/pairing-code',
  )
}

export interface ProjectStreamEvent {
  event_id?: string
  instruction_id?: string
  agent_name?: string
  event_type?: string
  status: string
  message: string
  duration_seconds?: number
  data?: Record<string, unknown> & { duration_seconds?: number }
}

/**
 * Subscribe to the authenticated project event stream.
 *
 * Native EventSource cannot attach the bearer token used by this application,
 * so the stream is consumed through fetch and an AbortController.
 */
export function subscribeProjectEvents(
  projectId: string,
  onEvent: (event: ProjectStreamEvent) => void,
  onError: (error: Error) => void,
): () => void {
  const controller = new AbortController()
  const storageKey = `agentforge:project-stream:${projectId}`
  let lastEventId =
    typeof window !== 'undefined'
      ? window.sessionStorage.getItem(storageKey) || ''
      : ''
  let retryDelayMs = 500

  const waitForRetry = (delayMs: number): Promise<void> =>
    new Promise((resolve) => {
      const timer = window.setTimeout(resolve, delayMs)
      controller.signal.addEventListener(
        'abort',
        () => {
          window.clearTimeout(timer)
          resolve()
        },
        { once: true },
      )
    })

  const consumeConnection = async (): Promise<void> => {
    const after = lastEventId ? `?after=${encodeURIComponent(lastEventId)}` : ''
    const path = `/api/v1/projects/${encodeURIComponent(projectId)}/stream${after}`
    let response = await rawFetch('GET', path, undefined, {
      signal: controller.signal,
    })
    if (response.status === 401 && getRefreshToken() && (await tryRefresh())) {
      response = await rawFetch('GET', path, undefined, {
        signal: controller.signal,
      })
    }
    if (!response.ok) {
      throw new ApiError(response.status, `Event stream HTTP ${response.status}`)
    }
    if (!response.body) {
      throw new Error('Event stream response has no body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (!controller.signal.aborted) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

      let boundary = buffer.indexOf('\n\n')
      while (boundary >= 0) {
        const block = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const eventId =
          block
            .split('\n')
            .find((line) => line.startsWith('id:'))
            ?.slice(3)
            .trim() || ''
        const payload = block
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trimStart())
          .join('\n')
        if (payload) {
          const event = JSON.parse(payload) as ProjectStreamEvent
          if (eventId) {
            lastEventId = eventId
            event.event_id = eventId
            window.sessionStorage.setItem(storageKey, eventId)
          }
          onEvent(event)
        }
        boundary = buffer.indexOf('\n\n')
      }
    }
  }

  const connect = async (): Promise<void> => {
    while (!controller.signal.aborted) {
      try {
        await consumeConnection()
        retryDelayMs = 500
      } catch (error: unknown) {
        if (controller.signal.aborted) return
        if (error instanceof ApiError && [403, 404].includes(error.code)) {
          onError(error)
          return
        }
      }
      if (!controller.signal.aborted) {
        await waitForRetry(retryDelayMs)
        retryDelayMs = Math.min(retryDelayMs * 2, 10_000)
      }
    }
  }

  void connect().catch((error: unknown) => {
    if (!controller.signal.aborted) {
      onError(error instanceof Error ? error : new Error(String(error)))
    }
  })

  return () => controller.abort()
}

// ── Agent Template Types & API ────────────────────────────────────────────

export interface AgentTemplateResponse {
  id: string
  name: string
  description: string | null
  capability: string
  system_prompt: string | null
  tools: string[]
  version: number
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface AgentVersionResponse {
  id: string
  template_id: string
  version: number
  snapshot: Record<string, unknown>
  created_at: string | null
}

export interface ProjectAgentResponse {
  id: string
  project_id: string
  template_id: string
  template_name: string
  enabled: boolean
  sort_order: number
  custom_config: Record<string, unknown> | null
}

/** GET /api/v1/agents */
export function listAgents(activeOnly = false): Promise<AgentTemplateResponse[]> {
  const qs = activeOnly ? '?active_only=true' : ''
  return request<AgentTemplateResponse[]>('GET', `/api/v1/agents${qs}`)
}

/** GET /api/v1/agents/:id */
export function getAgent(id: string): Promise<AgentTemplateResponse> {
  return request<AgentTemplateResponse>('GET', `/api/v1/agents/${encodeURIComponent(id)}`)
}

/** POST /api/v1/agents */
export function createAgent(data: {
  name: string
  description?: string
  capability?: string
  system_prompt?: string
  tools?: string[]
}): Promise<AgentTemplateResponse> {
  return request<AgentTemplateResponse>('POST', '/api/v1/agents', data)
}

/** PATCH /api/v1/agents/:id */
export function updateAgent(
  id: string,
  data: {
    name?: string
    description?: string
    capability?: string
    system_prompt?: string
    tools?: string[]
  },
): Promise<AgentTemplateResponse> {
  return request<AgentTemplateResponse>(
    'PATCH',
    `/api/v1/agents/${encodeURIComponent(id)}`,
    data,
  )
}

/** DELETE /api/v1/agents/:id */
export function deleteAgent(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('DELETE', `/api/v1/agents/${encodeURIComponent(id)}`)
}

/** GET /api/v1/agents/:id/versions */
export function listAgentVersions(id: string): Promise<AgentVersionResponse[]> {
  return request<AgentVersionResponse[]>(
    'GET',
    `/api/v1/agents/${encodeURIComponent(id)}/versions`,
  )
}

/** GET /api/v1/projects/:id/agents */
export function listProjectAgents(
  projectId: string,
): Promise<ProjectAgentResponse[]> {
  return request<ProjectAgentResponse[]>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(projectId)}/agents`,
  )
}

/** POST /api/v1/projects/:id/agents */
export function configureProjectAgent(
  projectId: string,
  data: {
    template_id: string
    enabled?: boolean
    sort_order?: number
    custom_config?: Record<string, unknown>
  },
): Promise<ProjectAgentResponse> {
  return request<ProjectAgentResponse>(
    'POST',
    `/api/v1/projects/${encodeURIComponent(projectId)}/agents`,
    data,
  )
}

/** DELETE /api/v1/projects/:id/agents/:templateId */
export function removeProjectAgent(
  projectId: string,
  templateId: string,
): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(
    'DELETE',
    `/api/v1/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(templateId)}`,
  )
}

// ── Users (admin-only) ──────────────────────────────────────────────────────

export interface UserResponse {
  id: string
  email: string
  full_name: string | null
  role: string
  org_name?: string | null
  job_title?: string | null
  agent_quota?: number
  created_at: string | null
}

/** GET /api/v1/users */
export function listUsers(): Promise<UserResponse[]> {
  return request<UserResponse[]>('GET', '/api/v1/users')
}

/** POST /api/v1/users */
export function createUser(data: {
  email: string
  password: string
  full_name?: string
  role?: string
  org_name?: string
  job_title?: string
  agent_quota?: number
}): Promise<UserResponse> {
  return request<UserResponse>('POST', '/api/v1/users', data)
}

/** GET /api/v1/users/:id */
export function getUser(id: string): Promise<UserResponse> {
  return request<UserResponse>('GET', `/api/v1/users/${encodeURIComponent(id)}`)
}

/** PATCH /api/v1/users/:id */
export function updateUser(
  id: string,
  data: { full_name?: string; role?: string; org_name?: string | null; job_title?: string | null; agent_quota?: number },
): Promise<UserResponse> {
  return request<UserResponse>('PATCH', `/api/v1/users/${encodeURIComponent(id)}`, data)
}

/** DELETE /api/v1/users/:id */
export function deleteUser(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('DELETE', `/api/v1/users/${encodeURIComponent(id)}`)
}

// ── LLM Logs ───────────────────────────────────────────────────────────────

export interface LlmLogEntry {
  id: string
  instruction_id: string | null
  project_id: string | null
  provider: string
  model: string
  prompt_text: string | null
  system_prompt_text: string | null
  response_text: string | null
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost: number
  duration_ms: number
  status: string
  error_message: string | null
  request_id: string | null
  temperature: number | null
  json_mode: boolean
  created_at: string | null
}

export interface LlmLogListResponse {
  total: number
  limit: number
  offset: number
  items: LlmLogEntry[]
}

export interface LlmLogStats {
  total_calls: number
  error_count: number
  total_tokens: number
  total_cost: number
  total_duration_ms: number
  unique_models: number
  unique_providers: number
}

export interface LlmLogFilters {
  status?: string
  provider?: string
  model?: string
  sort_by?: string
  sort_order?: string
  limit?: number
  offset?: number
}

/** GET /api/v1/projects/:id/llm-logs — list LLM call logs for a project */
export function getProjectLlmLogs(
  projectId: string,
  filters: LlmLogFilters = {},
): Promise<LlmLogListResponse> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.provider) params.set('provider', filters.provider)
  if (filters.model) params.set('model', filters.model)
  if (filters.sort_by) params.set('sort_by', filters.sort_by)
  if (filters.sort_order) params.set('sort_order', filters.sort_order)
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.offset) params.set('offset', String(filters.offset))
  const qs = params.toString()
  return request<LlmLogListResponse>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(projectId)}/llm-logs${qs ? `?${qs}` : ''}`,
  )
}

/** GET /api/v1/projects/:id/llm-logs/:logId — single log detail */
export function getLlmLogDetail(
  projectId: string,
  logId: string,
): Promise<LlmLogEntry> {
  return request<LlmLogEntry>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(projectId)}/llm-logs/${encodeURIComponent(logId)}`,
  )
}

/** GET /api/v1/projects/:id/llm-logs/stats — aggregate stats for a project */
export function getLlmLogStats(projectId: string): Promise<LlmLogStats> {
  return request<LlmLogStats>(
    'GET',
    `/api/v1/projects/${encodeURIComponent(projectId)}/llm-logs/stats`,
  )
}
