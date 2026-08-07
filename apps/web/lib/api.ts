/**
 * AgentForge API Client — typed fetch wrappers for all Cloud Control Plane endpoints.
 *
 * All functions return the parsed JSON response or throw a structured ApiError.
 * Base URL is configurable via NEXT_PUBLIC_API_URL env var (defaults to localhost:8000).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  })

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

// ── Types ──────────────────────────────────────────────────────────────────

export interface ProjectResponse {
  id: string
  name: string
  description: string | null
  execution_target: string
  tech_stack?: Record<string, boolean> | null
  status: string
  created_at?: string | null
  updated_at?: string | null
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
    tech_stack?: string[]
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

/** GET /api/v1/projects/:id/git/status */
export function getGitStatus(id: string): Promise<unknown> {
  return request<unknown>('GET', `/api/v1/projects/${encodeURIComponent(id)}/git/status`)
}

/** GET /api/v1/projects/:id/git/log */
export function getGitLog(id: string, maxCount = 20): Promise<unknown[]> {
  return request<unknown[]>('GET', `/api/v1/projects/${encodeURIComponent(id)}/git/log?max_count=${maxCount}`)
}

/** GET /api/v1/projects/:id/rag/stats */
export function getRagStats(id: string): Promise<{ files_indexed: number; chunks: number; last_index: string | null }> {
  return request('GET', `/api/v1/projects/${encodeURIComponent(id)}/rag/stats`)
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

/** GET /api/v1/devices */
export function listDevices(): Promise<DeviceResponse[]> {
  return request<DeviceResponse[]>('GET', '/api/v1/devices')
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
