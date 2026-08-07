# AgentForge — Real Data Implementation Plan

**Date:** 2026-08-07
**Strategy:** Small safe batches — implement, test, verify, then move to next batch.

---

## Batch 0: Foundation — Database Wiring (P0)

### 0.1: Alembic Migrations Setup
- Initialize Alembic in `apps/api/`
- Create initial migration for all 10 models
- Test: `alembic upgrade head` creates all tables

### 0.2: Database-Backed Project CRUD
- Replace `MOCK_PROJECTS` in `endpoints/projects.py` with real DB queries
- `GET /projects` → query all projects
- `POST /projects` → insert into DB
- `GET /projects/{id}` → query by ID
- Add `project_repository.py` in `app/repositories/`

### 0.3: Project Path Validation Endpoint
- Create `POST /api/v1/projects/validate-path`
- Accepts `{path: string}`
- Validates: exists, is_directory, readable, writable, git_repository
- Detects technology stack from files
- Returns structured response with warnings
- Path security: normalize, block traversal, apply PathGuard

### 0.4: Database-Backed Device CRUD
- Replace `MOCK_DEVICES` with real DB queries
- `GET /devices` → query all devices
- Persist pairing codes

---

## Batch 1: Frontend — Real Data Connection (P1)

### 1.1: API Client Helper
- Create `apps/web/lib/api.ts` with base URL config
- Typed fetch wrappers for all endpoints
- Error handling with structured error responses

### 1.2: Dashboard → Real Data
- Fetch projects from `GET /api/v1/projects`
- Fetch devices from `GET /api/v1/devices`
- Calculate real KPIs from data
- Keep prototype visual design

### 1.3: Devices Page → Real Data
- Fetch device list from API
- Dynamic table rows
- Remove hardcoded device row

### 1.4: Workspace Header → Real Data
- Fetch project details from `GET /api/v1/projects/{id}`
- Dynamic project name, device, path, status

### 1.5: New Project → Check Folder + Stack Detection
- Add "Check Project Folder" button
- Call `POST /api/v1/projects/validate-path`
- Show result inline (success/warning/error)
- Add technology stack tag selector
- Auto-detect stack on validation

---

## Batch 2: Workspace — Complete Tabs (P1/P2)

### 2.1: Add Missing Workspace Tabs
- Artifacts tab
- Tests tab
- Validation tab
- Git History tab (commits list)
- RAG Status tab

### 2.2: Real Diff Baseline
- Fetch original file content from git (HEAD version)
- Pass as `originalCode` to DiffViewer

### 2.3: Execution Context Panel
- Show model name, RAG context size, branch name
- Show safety gate status
- Show estimated API cost

### 2.4: Current Changes Panel
- Track created/modified/deleted file counts during pipeline
- Live test count and coverage updates

---

## Batch 3: Real Agent Implementations (P2)

### 3.1: ArchitectureAgent → Real
- Call LLM with system prompt for architecture analysis
- Return structured architectural decisions

### 3.2: BackendAgent → Real
- Call LLM with code generation prompt
- Write generated files via ToolGateway

### 3.3: FrontendAgent → Real
- Call LLM with UI generation prompt
- Write generated files via ToolGateway

### 3.4: DatabaseAgent → Real
- Call LLM for model/migration generation
- Write generated files via ToolGateway

### 3.5: DocumentationAgent → Real
- Call LLM for doc generation
- Write generated docs via ToolGateway

### 3.6: TestAgent → Real
- Call LLM for test generation
- Write tests via ToolGateway
- Execute tests via ToolGateway (run_command)
- Parse real results

### 3.7: ValidationAgent → Real
- Execute linters via ToolGateway (run_command)
- Execute type checkers via ToolGateway
- Execute security scan via ToolGateway
- Parse real results

### 3.8: GitAgent → Real
- Create branch via ToolGateway
- Stage and commit via ToolGateway
- Return real commit hash

### 3.9: UIUXAgent → Real
- Call LLM with UI/UX analysis prompt
- Return structured UI specification

### 3.10: VisualAnalysisAgent → Real
- Wire real vision model call (if available)
- Or use LLM with image description

---

## Batch 4: New Pages (P2/P3)

### 4.1: RAG Manager Page
- RAG stats cards (from API)
- Semantic search box
- Search results list
- Re-index button with progress
- Indexed files list

### 4.2: Git History Page
- Commit list from API
- Branch selector
- Rollback action per commit
- Confirmation modal

### 4.3: Observability Page
- Agent duration metrics
- Pipeline health stats
- LLM usage charts
- Infrastructure health checks

### 4.4: Architecture Page
- System architecture diagram
- Layer visualization

### 4.5: Settings Page
- Load current settings
- Save settings
- API key masking
- Connection test button

---

## Batch 5: Observability & Metrics (P3)

### 5.1: Metrics Aggregation Endpoint
- `GET /api/v1/observability/metrics`
- Aggregate from agent_runs, llm_usage, git_commits tables

### 5.2: Health Check Endpoint
- `GET /api/v1/health/full`
- Check DB, Redis, Qdrant, LLM connectivity

### 5.3: Settings CRUD Endpoint
- `GET /api/v1/settings`
- `PUT /api/v1/settings`
- Secure API key handling

---

## Batch 6: Pixel-Perfect Visual Matching (P3)

### 6.1: Design Tokens
- Extract exact colors from prototype CSS
- Create Tailwind config extensions
- Apply to layout, sidebar, cards, buttons

### 6.2: Sidebar Layout
- Match prototype: dark sidebar, light content area
- Navigation items matching prototype structure
- Status footer

### 6.3: Page Layouts
- Dashboard: stat cards, project cards grid
- New Project: form layout, stack tags
- Workspace: pipeline layout, agent rows
- All other pages

### 6.4: Responsive Design
- Match prototype breakpoints
- Test at all specified viewport sizes

---

## Batch 7: Polish (P3)

### 7.1: Loading States
- Skeleton loaders for all data-dependent components
- Spinner for async operations

### 7.2: Empty States
- "No projects yet" message
- "No devices connected" message
- "No test runs" message
- etc.

### 7.3: Error States
- Structured error display
- Retry buttons
- Never silent fallback to mock data

### 7.4: TypeScript Types
- Create shared API types
- Type all API responses

---

## Implementation Order

```
Batch 0 (Foundation)
  ├── 0.1 Alembic setup
  ├── 0.2 DB-backed project CRUD
  ├── 0.3 Project path validation
  └── 0.4 DB-backed device CRUD

Batch 1 (Frontend real data)
  ├── 1.1 API client helper
  ├── 1.2 Dashboard real data
  ├── 1.3 Devices page real data
  ├── 1.4 Workspace header real data
  └── 1.5 Check Folder + stack detection

Batch 2 (Workspace tabs)
  ├── 2.1 Missing tabs
  ├── 2.2 Real diff baseline
  ├── 2.3 Execution context panel
  └── 2.4 Current changes panel

Batch 3 (Real agents)
  └── 3.1-3.10 All stub agents → real

Batch 4 (New pages)
  └── 4.1-4.5 All missing pages

Batch 5 (Observability)
  └── 5.1-5.3 Metrics, health, settings endpoints

Batch 6 (Visual matching)
  └── 6.1-6.4 Design system, responsive

Batch 7 (Polish)
  └── 7.1-7.4 Loading, empty, error states, types
```
