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
  return fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    ...options,
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

/** Client-side logout — clears stored tokens. */
export function logout(): void {
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
  git_commit_template?: string | null
  // Filesystem access
  fs_read_enabled?: boolean
  fs_write_enabled?: boolean
  fs_delete_enabled?: boolean
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

/** GET /api/v1/settings */
export function getSettings(): Promise<{
  deepseek_api_key_masked: string
  deepseek_base_url: string
  chat_model: string
  coder_model: string
  max_agent_steps: number
  agent_timeout: number
  rag_top_k: number
  rag_chunk_size: number
  rag_chunk_overlap: number
  rag_similarity_threshold: number
  context_window_budget: string
  allowed_commands: string
  has_key: boolean
}> {
  return request('GET', '/api/v1/settings')
}

/** PUT /api/v1/settings */
export function updateSettings(data: {
  deepseek_api_key?: string
  deepseek_base_url?: string
  chat_model?: string
  coder_model?: string
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
    git_commit_template?: string | null
    // Filesystem access
    fs_read_enabled?: boolean
    fs_write_enabled?: boolean
    fs_delete_enabled?: boolean
  },
): Promise<ProjectResponse> {
  return request<ProjectResponse>(
    'PATCH',
    `/api/v1/projects/${encodeURIComponent(id)}`,
    data,
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
): Promise<{ id: string; project_id: string; prompt: string; status: string }> {
  return request<{ id: string; project_id: string; prompt: string; status: string }>(
    'POST',
    `/api/v1/projects/${encodeURIComponent(id)}/instructions`,
    { prompt },
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

/** Build SSE EventSource URL for a project */
export function buildSSEUrl(projectId: string): string {
  return `${API_BASE}/api/v1/projects/${encodeURIComponent(projectId)}/stream`
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
  created_at: string | null
}

/** GET /api/v1/users */
export function listUsers(): Promise<UserResponse[]> {
  return request<UserResponse[]>('GET', '/api/v1/users')
}

/** PATCH /api/v1/users/:id */
export function updateUser(
  id: string,
  data: { full_name?: string; role?: string },
): Promise<UserResponse> {
  return request<UserResponse>('PATCH', `/api/v1/users/${encodeURIComponent(id)}`, data)
}

/** DELETE /api/v1/users/:id */
export function deleteUser(id: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>('DELETE', `/api/v1/users/${encodeURIComponent(id)}`)
}
