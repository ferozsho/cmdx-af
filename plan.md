ChatGPT Plus





1.png
2.png
3.png

AI_Agent_Framework_Project_Document.docx
Document
Create a prototype with mockup data start to end complete

Worked for 3m 24s
I created a complete start-to-end interactive prototype with mock data based on your three reference designs and the uploaded AI Agent Framework specification.

The prototype follows the documented architecture: DeepSeek API + CrewAI, six sequential agents, project-aware RAG, filesystem/tool operations, FastAPI orchestration, PostgreSQL/Redis/Qdrant, SSE-style live updates, Git versioning, testing, validation, and rollback.

 The execution flow follows Planning → Documentation → Code → Tests → Validation → Git, including RAG lookup before generation and real-time frontend progress.


Included in the prototype
Dashboard with project cards and statistics

Complete Create Project workflow

Technology stack selection

Initial instruction submission

Live project workspace

Six Agent execution panels

Animated mock agent execution from start to finish

SSE-style live event console

Planning Agent output

Documentation Agent activity

Code Agent file generation

Test Agent with 28/28 passing tests

Mock 87% code coverage

Validation Agent with Ruff, mypy and Bandit results

Git Agent commits and version tag

Generated project file tree

Code viewer

Artifacts tab

Tests tab

Validation report

Git history

Rollback interactions

RAG status

Dedicated RAG Manager

Semantic search with Top-5 retrieved files

Similarity scores

Re-index simulation

Indexed files view

Observability dashboard

DeepSeek usage/cost mock metrics

Infrastructure/service health

Architecture visualization

Framework Settings screen

Delete/confirmation safety workflow

Responsive desktop/tablet/mobile layout

These frontend capabilities directly map to the specification's Dashboard, Project Creation, Project Detail, File Tree Viewer, Git History, RAG Manager, SSE event handling, and confirmation workflow.


Download the complete prototype
Download AI Agent Framework Complete Prototype — ZIP

You can also directly open the main prototype file:

Open / Download Prototype index.html

No installation is required. Extract the ZIP and open index.html in Chrome/Edge.

The entire application is currently mock-data driven, so DeepSeek, CrewAI, FastAPI, PostgreSQL, Redis, Qdrant, Git, filesystem changes, pytest, Ruff, mypy, Bandit, and SSE events are simulated. This makes it suitable for validating the complete product UX before replacing each mock service with the real backend. The production specification already defines the corresponding APIs for projects, instructions, files, Git, artifacts, health checks, and SSE streaming.




index.html
HTML


can this also create UI pages ?

Yes. The framework can also create complete UI pages, not only backend code.

Your current design already supports this because the Code Generation Agent is defined as a full-stack engineer covering Next.js/React-style frontend development, and the project specification explicitly includes Next.js modules, page components, hooks, TypeScript interfaces, and frontend features.


For example, you could give an instruction such as:

Create a modern project analytics dashboard with a sidebar, KPI cards, charts, recent agent executions, activity feed, responsive mobile layout, and dark mode. Follow the existing project's design system and reuse existing components.

Then the pipeline could work like this:

Planning Agent analyzes the existing UI, routes, components, branding, and design patterns.

RAG retrieves existing layouts, buttons, cards, typography, colors, forms, and component conventions.

Documentation Agent updates page/component documentation if required.

Code Agent creates the actual UI files such as:

app/dashboard/page.tsx

components/dashboard/stat-card.tsx

components/dashboard/activity-feed.tsx

components/charts/usage-chart.tsx

hooks/use-dashboard.ts

responsive Tailwind styles

Test Agent creates component/page tests.

Validation Agent runs TypeScript, ESLint, build validation, accessibility checks, etc.

Git Agent commits all generated UI files.

The specification already states that the frontend includes project dashboards, live agent monitoring, file browsing, Git history, RAG management, confirmation dialogs, and real-time updates.


More importantly, I would extend the product beyond a generic Code Agent and make UI generation a first-class capability.

A stronger agent structure would be:

Planning Agent

Architecture Agent

UI/UX Agent

Frontend Agent

Backend Agent

Database Agent

Documentation Agent

Test Agent

Validation Agent

Git Agent

The UI/UX Agent would be responsible for:

page structure

visual hierarchy

design-system selection

responsive layouts

accessibility

component reuse

colors/spacing/typography

interaction states

loading/empty/error states

Then the Frontend Agent converts that design specification into actual Next.js/React code.

It can also support instructions such as:

Create a login page.
Create an admin dashboard similar to the attached screenshot.
Redesign the existing users page but keep all current functionality.
Create a responsive LMS course dashboard using our existing theme branding.
Create the UI from this Figma design.
Create this screenshot as a pixel-close Next.js page.
Create a complete SaaS frontend including login, dashboard,
projects, settings, billing, users and reports.
And because RAG understands the existing repository, it can avoid creating isolated pages that don't match the application. It can inspect the existing design system and reuse things like Button, Card, Modal, Sidebar, layout wrappers, fonts, theme tokens, API hooks, and routing conventions before generating anything. That project-aware behavior is one of the core purposes of the framework's RAG layer.


I would add one major feature: Visual UI Generation
The workflow should become:

Prompt / Screenshot / Figma → UI Analysis → UI Specification → Component Plan → Code Generation → Browser Preview → Visual Validation → Auto-fix → Tests → Git

That would make the platform much closer to Cursor + Lovable + v0 + Claude Code + multi-agent development in one product.

For example:

User
  ↓
"Create this dashboard"
+ Screenshot / Figma
  ↓
UI/UX Agent
  ├─ Understand layout
  ├─ Identify components
  ├─ Extract spacing
  ├─ Understand typography
  └─ Define responsive behavior
  ↓
RAG
  ├─ Existing components
  ├─ Existing theme
  ├─ Existing routes
  └─ Existing coding patterns
  ↓
Frontend Agent
  ├─ Generate page
  ├─ Generate components
  ├─ Generate hooks
  └─ Connect APIs
  ↓
Browser Preview
  ↓
Visual Validation Agent
  ├─ Compare screenshot
  ├─ Detect spacing issues
  ├─ Detect overflow
  ├─ Detect responsive issues
  └─ Auto-correct
  ↓
Test Agent
  ↓
Git Agent
So yes—the system should absolutely create UI pages, and I would make UI generation, screenshot-to-code, existing-page redesign, and full frontend generation core features of the framework, rather than treating them as just another coding task.


Yes. For VS Code/Copilot/Codex/Claude Code, I would give it a single master build prompt that tells the agent to create the project systematically, not just start coding random screens.

Use this as your main project-generation prompt:

# AI Agent Framework — Full Project Build Prompt

You are a senior software architect, full-stack engineer, AI/ML engineer, DevOps engineer, QA engineer, and UI/UX engineer working as one coordinated development team.

Your task is to build a complete production-ready **AI Agent Framework / Agentic Code Generation Platform** from scratch.

The system must allow a user to connect or register a software project, submit natural-language development instructions, and have multiple specialized AI agents collaboratively analyze the existing codebase, plan changes, create/update files, generate UI pages, write tests, validate code, execute safe commands, and commit changes to Git.

The project must be designed as a real extensible product, not as a demo.

---

# 1. NON-NEGOTIABLE DEVELOPMENT RULES

Before writing any code:

1. Inspect the entire repository.
2. Read all existing README, architecture, configuration, package, environment, and coding-standard files.
3. Understand the existing folder structure.
4. Do not overwrite existing functionality unnecessarily.
5. Reuse existing components, utilities, patterns, themes, and services wherever possible.
6. Do not create duplicate functionality.
7. Keep frontend, backend, agents, tools, RAG, infrastructure, tests, and shared contracts modular.
8. Use strong typing.
9. Never hardcode secrets.
10. Never run destructive commands without explicit safety checks.
11. All filesystem access must remain inside the configured project root.
12. Every implementation phase must be independently testable.
13. After every major phase:
   - run tests
   - run linting
   - run type checking
   - fix issues
   - summarize changes
14. Do not leave placeholder implementation, TODO logic, mock APIs, or fake service calls in the production code unless explicitly marked as demo/mock mode.
15. If something cannot be completed correctly, report it clearly instead of silently faking it.

---

# 2. TARGET PRODUCT

Build an:

## AI-Powered Multi-Agent Software Development Platform

Primary capabilities:

- Create/manage development projects
- Point the framework to an existing repository/project directory
- Understand an existing codebase using RAG
- Accept natural-language instructions
- Plan implementation automatically
- Generate backend code
- Generate frontend/UI pages
- Modify existing pages
- Generate new modules
- Generate documentation
- Generate database changes
- Generate automated tests
- Run tests
- Run linting
- Run formatting
- Run type checking
- Run security scanning
- Perform Git commits
- Support rollback
- Stream agent activity live to the UI
- Maintain artifacts and audit history
- Search the indexed project using RAG
- Show generated files and diffs
- Support safe user confirmation for destructive operations

---

# 3. CORE TECHNOLOGY STACK

Use the following architecture unless the repository already contains an intentional equivalent.

## Frontend

- Next.js latest stable App Router
- TypeScript
- React
- Tailwind CSS
- shadcn/ui
- Lucide icons
- TanStack Query
- Server-Sent Events for live agent activity
- Monaco Editor or equivalent for file/code preview

## Backend

- Python 3.11+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Celery

## Agent Orchestration

- CrewAI

Build the system so the LLM provider is abstracted.

Initial provider:

- DeepSeek API

Models:

- reasoning/general agent model
- code-generation model

Do NOT tightly couple business logic directly to DeepSeek.

Create a provider interface so future providers can include:

- OpenAI
- Anthropic
- Gemini
- local models
- OpenRouter
- Ollama

---

# 4. LLM PROVIDER ARCHITECTURE

Create:

backend/app/llm/

Suggested structure:

backend/app/llm/
├── base.py
├── registry.py
├── deepseek.py
├── schemas.py
├── errors.py
└── usage.py

The base provider must support:

- chat completion
- streaming if supported
- structured output
- model configuration
- retry
- timeout
- token usage
- cost tracking
- provider errors

Never expose provider-specific implementation throughout the system.

Agents should request logical model capabilities such as:

- reasoning
- coding
- documentation
- validation

The Model Router chooses the configured provider/model.

---

# 5. MULTI-AGENT SYSTEM

Implement specialized agents.

At minimum:

1. Planning Agent
2. Architecture Agent
3. UI/UX Agent
4. Documentation Agent
5. Frontend Agent
6. Backend Agent
7. Database Agent
8. Test Agent
9. Validation Agent
10. Git Agent

Design agents so they can be enabled/disabled dynamically.

---

# 6. PLANNING AGENT

Responsibilities:

- Analyze user instruction
- Inspect existing repository
- Query RAG
- Identify affected modules
- Determine files to create
- Determine files to update
- Determine files potentially requiring deletion
- Determine dependencies
- Determine database changes
- Determine frontend/backend impact
- Estimate complexity
- Produce structured implementation plan

Return validated JSON.

Suggested output:

{
  "summary": "",
  "complexity": "low|medium|high",
  "modules_to_create": [],
  "files_to_create": [],
  "files_to_update": [],
  "files_to_delete": [],
  "dependencies_to_add": [],
  "database_changes": [],
  "frontend_changes": [],
  "backend_changes": [],
  "testing_strategy": [],
  "risks": []
}
# 7. ARCHITECTURE AGENT

Responsibilities:

- Verify architectural consistency
- Identify existing architectural patterns
- Decide service/module boundaries
- Prevent unnecessary coupling
- Define contracts
- Recommend reusable abstractions
- Detect duplication
- Ensure changes integrate with existing codebase

It must use RAG before proposing architecture.

---

# 8. UI/UX AGENT

This is a first-class agent.

It must support:

- New page generation
- Existing page redesign
- Dashboard creation
- Admin interfaces
- CRUD pages
- Forms
- Tables
- Modals
- Navigation
- Responsive design
- Mobile layouts
- Empty states
- Loading states
- Error states
- Accessibility states
- Design-system consistency

Before creating UI:

1. Search the existing project.
2. Find:
   - layout components
   - typography
   - colors
   - spacing
   - cards
   - forms
   - tables
   - buttons
   - modals
   - navigation
   - existing page patterns
3. Reuse existing UI system.

The UI/UX Agent produces a structured UI specification before Frontend Agent implementation.

Suggested result:

{
  "page": "",
  "route": "",
  "layout": "",
  "components": [],
  "reused_components": [],
  "new_components": [],
  "responsive_rules": [],
  "interaction_states": [],
  "accessibility_requirements": [],
  "design_tokens": {}
}

---

# 9. SCREENSHOT-TO-UI SUPPORT

Create architecture for future screenshot/image-based generation.

Workflow:

User Image / Screenshot
↓
Visual Analysis
↓
UI Specification
↓
Existing Design-System Retrieval
↓
Frontend Code Generation
↓
Browser Preview
↓
Visual Comparison
↓
Auto-fix
↓
Validation

Create interfaces for this workflow even if visual-model integration is initially optional.

Do not hardcode screenshot generation into the Frontend Agent.

Create a dedicated visual-analysis service abstraction.

---

# 10. FRONTEND AGENT

Responsibilities:

- Generate Next.js pages
- Generate React components
- Generate layouts
- Generate TypeScript interfaces
- Generate hooks
- Generate forms
- Generate API integrations
- Implement responsive behavior
- Reuse design system
- Maintain accessibility

Example generated structure:

app/
components/
features/
hooks/
lib/
types/

Do not create monolithic pages.

Split components logically.

Use TypeScript strictly.

Avoid `any`.

---

# 11. BACKEND AGENT

Responsibilities:

- FastAPI routes
- services
- domain logic
- repositories
- schemas
- validation
- exception handling
- background jobs
- integrations

Use layered architecture.

Suggested:

app/
├── api/
├── services/
├── repositories/
├── models/
├── schemas/
├── agents/
├── tools/
├── rag/
├── llm/
├── core/
└── workers/

Do not place business logic directly in route handlers.

---

# 12. DATABASE AGENT

Responsibilities:

- SQLAlchemy models
- schema design
- Alembic migrations
- indexes
- relationships
- transactions
- seed data
- safe migration strategy

Never modify production schema without a migration.

---

# 13. DOCUMENTATION AGENT

Maintain:

- README.md
- ARCHITECTURE.md
- API.md
- DATABASE.md
- MODULES.md
- CONTRIBUTING.md
- CHANGELOG.md

Only update documentation relevant to the current change.

---

# 14. TEST AGENT

Generate tests for all modified functionality.

Backend:

- pytest
- API tests
- service tests
- repository tests
- integration tests

Frontend:

- React component tests
- route/page tests
- utility tests

Include:

- happy path
- validation errors
- missing data
- edge cases
- failure cases

Target at least 80% coverage where practical.

---

# 15. VALIDATION AGENT

Run:

Python:
- syntax validation
- Ruff
- mypy
- pytest
- Bandit

Frontend:
- TypeScript compiler
- ESLint
- formatter
- frontend tests
- Next.js production build

Validation output must include:

{
  "overall_status": "",
  "syntax_errors": [],
  "lint_issues": [],
  "type_errors": [],
  "security_issues": [],
  "test_results": {},
  "coverage": 0,
  "build_status": ""
}

Automatically fix safe issues.

Do not hide unresolved failures.

---

# 16. GIT AGENT

Every task runs on a dedicated branch.

Format:

agent/{instruction_id}

Capabilities:

- status
- diff
- stage
- commit
- branch
- rollback
- merge
- history
- tags

Commit convention:

[Plan] ...
[Architecture] ...
[UI] ...
[Frontend] ...
[Backend] ...
[Database] ...
[Docs] ...
[Tests] ...
[Validation] ...
[Release] ...

Never make automated changes directly on main/master.

---

# 17. FILESYSTEM TOOL SYSTEM

Implement safe tools:

read_file
write_file
update_file
delete_file
create_folder
delete_folder
list_files
get_project_tree
move_file
search_in_files
get_file_diff

Every path MUST resolve inside PROJECT_ROOT_PATH.

Block:

- path traversal
- system directories
- .env secrets
- private keys
- .git internals

Write/update operations must be logged.

Update operations should support:

- full replacement
- section replacement
- append

Create backups before updates where appropriate.

Deletion always requires confirmation.

---

# 18. EXECUTION TOOLS

Implement:

run_command
run_tests
run_linter
run_formatter
run_security_scan
run_type_check
run_build

Commands must use a strict whitelist.

Never permit arbitrary shell execution.

Block dangerous commands including:

rm
del
format
shutdown
reboot
drop
truncate

Execution should happen in a sandbox/container where possible.

---

# 19. RAG SYSTEM

Use:

- Qdrant
- sentence-transformers
- CodeBERT or an equivalent code embedding model
- MiniLM or equivalent documentation embedding model

Maintain separate collections for:

- code
- documentation

RAG metadata:

- project_id
- file_path
- chunk_index
- start_line
- end_line
- language
- last_modified

Implement:

rag_search
rag_index_file
rag_update_file
rag_delete_file
rag_index_project

Agents must use RAG before generating project-specific implementation.

Top-K default:

5

Include similarity score.

Use project-level filtering.

---

# 20. SMART INDEXING

Index:

.py
.js
.jsx
.ts
.tsx
.php
.sql
.md
.txt
.rst
.json
.yaml
.yml
.toml

Ignore:

node_modules
.git
.next
dist
build
coverage
venv
.venv
cache directories
binary assets

Implement file watcher.

On:

create → index
update → reindex
delete → delete vector
rename → update metadata

Debounce bulk changes.

---

# 21. DATABASE SCHEMA

Create at minimum:

projects
instructions
agent_runs
artifacts
file_operations
git_commits
rag_index_log
llm_usage
pipeline_events
confirmations

Use UUIDs.

Include timestamps.

Maintain relationships and useful indexes.

---

# 22. CORE API

Implement at minimum:

POST /api/projects
GET /api/projects
GET /api/projects/{id}

POST /api/projects/{id}/instructions

GET /api/projects/{id}/instructions/{instruction_id}/status

GET /api/projects/{id}/stream

GET /api/projects/{id}/files

GET /api/projects/{id}/files/content

GET /api/projects/{id}/artifacts

GET /api/projects/{id}/git/log

POST /api/projects/{id}/git/rollback

GET /api/projects/{id}/rag/status

POST /api/projects/{id}/rag/reindex

POST /api/projects/{id}/rag/search

GET /api/health

Implement proper schemas and error responses.

---

# 23. SERVER-SENT EVENTS

Use Redis Pub/Sub between workers and FastAPI.

Support events:

pipeline_started

agent_started
agent_progress
agent_completed
agent_failed

rag_search_started
rag_search_completed

file_created
file_updated
file_deleted

command_started
command_completed

test_started
test_result

validation_started
validation_completed

confirmation_required

git_commit_created

pipeline_completed
pipeline_failed

Frontend must update live without page refresh.

---

# 24. FRONTEND APPLICATION

Create a polished SaaS-style development platform.

Required pages:

## Dashboard

Show:

- total projects
- active pipelines
- completed runs
- generated files
- tests passed
- recent activity

Project cards:

- name
- description
- stack
- status
- last activity

---

## New Project

Fields:

- Project Name
- Description
- Project Root Path
- Tech Stack
- Git Repository
- Default Branch
- LLM Provider
- Models
- Initial Instruction

Validate project path.

---

## Project Workspace

This is the main screen.

Layout suggestion:

Left sidebar:
- project navigation
- files
- agents
- RAG
- Git
- tests
- settings

Main center:
- instruction/chat interface
- live agent execution
- generated output
- code/diff views

Right panel:
- current task
- pipeline status
- agent details
- context/RAG results

---

# 25. LIVE AGENT EXECUTION UI

Show each agent as a pipeline.

Example:

Planning Agent        Done
Architecture Agent    Done
UI/UX Agent           Done
Frontend Agent        Running
Backend Agent          Waiting
Database Agent         Waiting
Test Agent             Waiting
Validation Agent       Waiting
Git Agent              Waiting

Clicking an agent shows:

- status
- duration
- model
- task
- tool calls
- retrieved RAG context
- files affected
- generated artifacts
- errors

Do not expose hidden model chain-of-thought.

Only display safe execution/activity summaries.

---

# 26. LIVE EVENT CONSOLE

Provide developer-style event stream.

Example:

10:15:21 [Planning Agent] Started
10:15:22 [RAG] Retrieved 5 relevant files
10:15:30 [Planning Agent] Plan created
10:15:32 [UI Agent] Started
10:15:38 [Frontend Agent] Created app/dashboard/page.tsx
10:15:39 [Frontend Agent] Updated components/sidebar.tsx
10:15:44 [Test Agent] Running tests
10:15:51 [Test Agent] 28/28 passed
10:15:55 [Validation Agent] Ruff passed
10:15:56 [Validation Agent] TypeScript passed
10:15:59 [Git Agent] Commit created

---

# 27. FILE TREE VIEWER

Provide:

- expandable folders
- file icons
- modification state
- last modifying agent
- code viewer
- diff viewer

States:

new
modified
deleted
unchanged

---

# 28. RAG MANAGER

Show:

- index status
- files indexed
- chunks
- coverage %
- last indexing time
- embedding models
- Qdrant status

Provide:

- Re-index project
- Clear/rebuild index
- Include/exclude paths
- Test semantic search

Search result should show:

- file path
- line range
- relevance %
- code/content preview

---

# 29. GIT HISTORY

Show:

- branch
- hash
- agent
- commit message
- timestamp
- changed files

Capabilities:

- view diff
- rollback
- compare commits

Confirmation is required before rollback.

---

# 30. TESTING SCREEN

Show:

- test suites
- passed
- failed
- skipped
- coverage
- duration

Allow inspection of failures.

---

# 31. VALIDATION SCREEN

Show:

- lint
- formatting
- type checking
- security scan
- tests
- frontend build
- backend validation

Use status cards:

Passed
Warning
Failed

---

# 32. SETTINGS

Provide sections:

LLM Providers
Agent Configuration
RAG
Execution
Git
Security
Appearance

DeepSeek configuration:

- API Key
- API Base URL
- Chat Model
- Coding Model

Mask secret fields.

Support BYOK.

---

# 33. MOCK MODE

For initial development, support:

APP_MODE=mock

Mock mode must simulate:

- agent pipeline
- file changes
- RAG retrieval
- SSE
- tests
- validation
- Git commits
- usage metrics

But mock mode must use the SAME interfaces as production mode.

Do not duplicate frontend code for mock mode.

Service adapters should determine mock vs real implementation.

---

# 34. DEMO PROJECT

Seed a project:

Name:
Commerce Platform

Stack:
Next.js
FastAPI
PostgreSQL
Redis

Example instruction:

"Create a complete payment module with payment API endpoints, database models, admin UI, transaction table, refund workflow, tests and documentation."

Simulate all agents operating on this project.

---

# 35. UI QUALITY

The design must feel like a professional developer platform.

Reference style:

- modern SaaS
- clean
- strong hierarchy
- compact information density
- professional cards
- clear live status
- code editor experience
- GitHub/Cursor/Linear/Vercel style quality

Avoid:

- oversized UI
- unnecessary gradients
- excessive rounded cards
- childish icons
- inconsistent spacing
- low-contrast text

Use one consistent design system.

Include responsive desktop/tablet/mobile behavior.

---

# 36. SECURITY

Implement:

- API authentication
- secret protection
- project path isolation
- safe command whitelist
- destructive-action confirmation
- rate limits
- sandboxed command execution
- audit logs
- masked secrets
- permission checks

Generated code must never automatically execute arbitrary user-provided shell content.

---

# 37. OBSERVABILITY

Track:

- pipeline duration
- agent duration
- agent failure rate
- LLM usage
- LLM cost
- RAG latency
- test duration
- tool invocation duration
- generated files
- modified files

Create structured logs.

Prepare Prometheus metrics.

---

# 38. DOCKER

Provide complete Docker Compose.

Services:

frontend
backend
worker
postgres
redis
qdrant

Optional:

flower

Use persistent volumes.

Provide health checks.

---

# 39. PROJECT STRUCTURE

Use a clean monorepo.

Suggested:

ai-agent-framework/
├── frontend/
├── backend/
├── docs/
├── infrastructure/
├── scripts/
├── docker-compose.yml
├── .env.example
├── README.md
└── Makefile

Backend:

backend/app/
├── api/
├── agents/
├── crew/
├── tools/
├── rag/
├── llm/
├── models/
├── schemas/
├── services/
├── repositories/
├── workers/
└── core/

Frontend:

frontend/
├── app/
├── components/
├── features/
├── hooks/
├── lib/
├── types/
└── public/

---

# 40. ENVIRONMENT CONFIGURATION

Create `.env.example`.

Include:

APP_ENV=
APP_MODE=

DATABASE_URL=
REDIS_URL=

QDRANT_HOST=
QDRANT_PORT=
QDRANT_API_KEY=

# DeepSeek settings (API key / base URL / models) are managed via
# the Settings page → saved to runtime_settings.json, NOT .env.

PROJECT_ROOT_BASE=

MAX_AGENT_STEPS=
AGENT_TIMEOUT_SECONDS=

# RAG settings (top K / chunk size / overlap) are managed via the
# Settings page → saved to runtime_settings.json, NOT .env.

ENABLE_CONFIRMATION_BEFORE_DELETE=

GIT_AUTHOR_NAME=
GIT_AUTHOR_EMAIL=

Never commit real secrets.

---

# 41. DEVELOPMENT PHASES

Do NOT attempt everything blindly in one uncontrolled pass.

Implement sequentially.

## Phase 0 — Repository Analysis

Inspect repository.

Create:

docs/IMPLEMENTATION_PLAN.md

Document:

- current repository state
- architecture
- proposed structure
- dependencies
- implementation phases
- risks

Stop and ensure the plan is internally consistent.

---

## Phase 1 — Foundation

Build:

- monorepo
- Docker
- FastAPI
- PostgreSQL
- Redis
- Qdrant
- Celery
- Next.js
- health checks

Verify everything starts.

---

## Phase 2 — Database

Build:

- models
- Alembic
- repositories
- schemas
- seed data

Run migrations and tests.

---

## Phase 3 — RAG

Build:

- scanner
- chunker
- embeddings
- Qdrant
- semantic search
- indexing
- watcher

Test retrieval quality.

---

## Phase 4 — Tool Layer

Build:

- filesystem
- execution
- Git

Test every tool independently.

Test all safety restrictions.

---

## Phase 5 — LLM Provider Layer

Build provider abstraction.

Implement DeepSeek provider.

Test with mocks first.

Then support real API configuration.

---

## Phase 6 — Agents

Build agents individually.

Test structured outputs.

Do not build Crew orchestration until individual agents work.

---

## Phase 7 — Pipeline

Build sequential orchestration.

Add:

- retries
- errors
- checkpoints
- safety
- confirmations

---

## Phase 8 — SSE

Build real-time event infrastructure.

Test browser reconnect.

---

## Phase 9 — Frontend

Implement:

- dashboard
- project creation
- workspace
- live agents
- files
- RAG
- Git
- tests
- validation
- settings

Initially use mock adapter.

Then connect production APIs.

---

## Phase 10 — UI Generation Capability

Implement:

- UI/UX Agent
- Frontend Agent
- design-system retrieval
- page generation
- page modification

Test instruction:

"Create a modern analytics dashboard using the existing application design system."

Verify real files are created.

---

## Phase 11 — Full End-to-End

Test:

User instruction
→ Planning
→ Architecture
→ RAG
→ UI/Frontend/Backend
→ Tests
→ Validation
→ Git
→ UI completion

---

## Phase 12 — Hardening

Run:

- security audit
- unit tests
- integration tests
- frontend production build
- backend tests
- Docker build
- performance review

Fix all high-priority issues.

---

# 42. FIRST DEMONSTRATION WORKFLOW

After the foundation is functional, demonstrate this exact workflow.

User instruction:

"Create a payment management module. Add backend payment models and FastAPI endpoints, create a responsive payments admin page with KPI cards, transaction table, status badges and refund action, create automated tests, update documentation and commit all changes."

Expected execution:

Planning Agent
↓
Architecture Agent
↓
RAG Retrieval
↓
UI/UX Agent
↓
Documentation Agent
↓
Frontend Agent
↓
Backend Agent
↓
Database Agent
↓
Test Agent
↓
Validation Agent
↓
Git Agent

The live UI must show every stage.

---

# 43. ACCEPTANCE CRITERIA

The project is NOT considered complete merely because pages render.

Minimum acceptance criteria:

- Docker stack starts successfully
- Backend health check works
- PostgreSQL works
- Redis works
- Qdrant works
- Celery worker works
- frontend works
- project can be created
- project files can be indexed
- semantic RAG search works
- instruction can be submitted
- agent pipeline can execute
- filesystem tools operate safely
- files can be generated
- UI page can be generated
- tests execute
- validation executes
- Git commit is created
- live events appear in frontend
- generated files can be browsed
- Git history can be viewed
- rollback works
- no destructive operation happens without required confirmation
- DeepSeek can be enabled through configuration
- mock mode can run without paid APIs

---

# 44. IMPLEMENTATION BEHAVIOR

You are operating as an autonomous coding agent.

For every phase:

1. Analyze.
2. Plan.
3. Implement.
4. Run tests.
5. Inspect errors.
6. Fix errors.
7. Re-run validation.
8. Update documentation.
9. Summarize exactly what changed.

Do not repeatedly ask me obvious implementation questions.

Make sensible engineering decisions consistent with this specification.

Ask me only when a decision is genuinely impossible to infer or could cause destructive/irreversible consequences.

---

# 45. START NOW

Start with **Phase 0 — Repository Analysis**.

Do not immediately generate the entire project.

First:

1. Inspect the current repository completely.
2. Identify what already exists.
3. Identify reusable code.
4. Identify missing components.
5. Create `docs/IMPLEMENTATION_PLAN.md`.
6. Create the proposed repository tree.
7. Create a phase-by-phase implementation checklist.
8. Show me the analysis and plan before making large architectural changes.

After completing Phase 0, continue into Phase 1 unless there is a genuine blocker.
This prompt aligns with your attached framework document, which defines the platform as an agentic coding system with real file operations, RAG-aware agents, testing, validation, Git versioning, and a Next.js/FastAPI stack.

 It also preserves the documented sequential agent flow and project-aware RAG behavior.


One important change from your original specification is intentional: I expanded the original six-agent model into dedicated Architecture, UI/UX, Frontend, Backend, and Database agents. That will make the project much stronger for the UI-generation capability you just asked for; your document already supports frontend page/component generation, but these dedicated responsibilities make it a first-class workflow rather than leaving everything inside one Code Agent.

I recommend pasting this into VS Code as the master instruction, then letting the coding agent complete Phase 0 first. Do not tell it simply “build everything”; the phased approach will give you much better code quality and reduce architectural drift.

Branched from Prototype with Mock Data


can you tell me how it going to work on my local pc projects and this app will be on cloud hosting

Yes. If the AI Agent Framework web application is hosted in the cloud, but the projects you want it to modify are on your local Windows PC, we should change the architecture slightly from the original document.

The cloud server cannot directly access folders such as:

D:\Projects\moodle
D:\Projects\my-nextjs-app
C:\xampp\htdocs\project
Instead, we install a small Local Agent / Desktop Bridge on your PC. That local agent becomes the secure connection between the cloud application and your local projects.

Your original document currently assumes that the FastAPI/backend has access to PROJECT_ROOT_PATH, including a Docker volume mount for the project directory.

 It also describes the project root entered in the frontend as a directory on the server.

 For your cloud + local-PC requirement, I recommend changing that part to the following architecture.

Recommended architecture
                    INTERNET / CLOUD
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│               AI AGENT FRAMEWORK CLOUD                       │
│                                                              │
│  ┌───────────────────┐                                       │
│  │ Next.js Web App   │                                       │
│  │                   │                                       │
│  │ Dashboard         │                                       │
│  │ Projects          │                                       │
│  │ Instructions      │                                       │
│  │ Live Agents       │                                       │
│  │ Files / Diff      │                                       │
│  │ Git History       │                                       │
│  └─────────┬─────────┘                                       │
│            │                                                 │
│            ▼                                                 │
│  ┌───────────────────┐                                       │
│  │ FastAPI Backend   │                                       │
│  │                   │                                       │
│  │ Authentication    │                                       │
│  │ Agent orchestration│                                      │
│  │ Task management   │                                       │
│  │ SSE events        │                                       │
│  └──────┬─────┬──────┘                                       │
│         │     │                                              │
│         │     ├──────── PostgreSQL                           │
│         │     ├──────── Redis                                │
│         │     └──────── Optional Cloud Qdrant                │
│         │                                                    │
│         │ Secure WSS/HTTPS                                   │
└─────────┼────────────────────────────────────────────────────┘
          │
          │
          │ Encrypted connection
          │ initiated FROM your PC
          │
══════════╪════════════════ INTERNET ═══════════════════════════
          │
          ▼
┌──────────────────────────────────────────────────────────────┐
│                    YOUR LOCAL WINDOWS PC                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │             AgentForge Local Agent                   │    │
│  │                                                      │    │
│  │  Project Manager                                     │    │
│  │  Filesystem Tools                                    │    │
│  │  Git Tools                                           │    │
│  │  Terminal / Command Runner                           │    │
│  │  Test Runner                                         │    │
│  │  RAG Indexer                                         │    │
│  │  Security / Permission Layer                         │    │
│  └───────────────┬──────────────────────────────────────┘    │
│                  │                                           │
│        ┌─────────┼──────────┬─────────────┐                  │
│        ▼         ▼          ▼             ▼                  │
│                                                              │
│   D:\Projects  C:\xampp   D:\Moodle    D:\NextJS             │
│                                                              │
│   Project A    Project B  Project C    Project D             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
The important principle
Cloud = brain/control plane.

Your PC = hands/execution plane.

The actual source files do not need to exist on your cloud server.

How you would use it
Suppose your project is:

D:\Projects\cmdx-framework
You install our local application once:

AgentForge Local Agent
It could run as either a Windows tray application or Windows background service.

When started it displays:

AgentForge Local Agent

Status:
● Connected to cloud

Computer:
FEROZ-PC

Registered Projects:
✓ D:\Projects\cmdx-framework
✓ D:\Projects\xplms
✓ D:\Projects\maid-pro

Local RAG:
● Running

Git:
● Available

Docker:
● Available
You do not expose D:\Projects to the Internet.

The local agent itself makes an outbound encrypted connection to your cloud server.

First time: connect PC
You open your cloud application:

https://agentforge.yourdomain.com
Go to:

Settings
    ↓
Local Machines
    ↓
Connect New Machine
The cloud might generate:

Device Code

AGF-84K2-JP7D

Expires in 10 minutes
On your PC:

agentforge connect
Enter:

AGF-84K2-JP7D
Now:

Cloud
   ↕
FEROZ-PC
become linked.

The cloud might then display:

LOCAL MACHINES

FEROZ-PC
Windows 11

● Online

Agent Version
1.0.0

Git
Available

Docker
Available

Node
22.x

Python
3.12

Projects
7
Adding your local project
From the cloud UI:

Create Project
Instead of entering a server filesystem path, you would select:

Execution Location

○ Cloud Workspace
● Local Machine
Then:

Machine
FEROZ-PC

Project Directory
D:\Projects\cmdx-framework
Better still, the local application can provide a directory picker:

Select Project

D:\Projects\
    ├── cmdx-framework
    ├── xplms
    ├── maid-pro
    └── openxpertz-api
Select:

D:\Projects\cmdx-framework
Then AgentForge registers something like:

Project ID:
prj_a83fd2

Device:
FEROZ-PC

Local path:
D:\Projects\cmdx-framework

Git:
main

Languages:
Python
TypeScript
What happens when you give an instruction?
Imagine you're sitting somewhere else and open the cloud app from a laptop.

You write:

Create a new analytics dashboard. Follow the current application's UI design, reuse our existing components, make it responsive, add tests and commit the changes.

The flow becomes:

YOU
 │
 │ Browser
 ▼
Cloud Next.js Application
 │
 ▼
Cloud FastAPI
 │
 ▼
Planning Agent
 │
 │
 │ "I need information about this project"
 │
 ▼
Secure Local-Agent Connection
 │
 ▼
Your PC
D:\Projects\cmdx-framework
The system first asks the local worker:

get_project_tree
Your local PC returns something like:

src/
  components/
  modules/
  layouts/

app/
  dashboard/
  settings/

package.json
tsconfig.json
...
That is consistent with the project's intended design: agents need to read existing files and understand the codebase before making modifications.


RAG becomes especially important
Your local agent can index:

D:\Projects\cmdx-framework
into a local Qdrant instance.

For example:

AgentForge Local Agent

          │
          ▼

Local File Scanner

          │
          ▼

Code Chunker

          │
          ▼

Local Embedding Model

          │
          ▼

Local Qdrant

          │
          ▼

Project Knowledge Base
Your document already specifies project-aware indexing with local sentence-transformer/CodeBERT-style embeddings and Qdrant.


This is actually a very good fit for a local-worker architecture.

Example RAG query
Planning Agent needs to know:

How does this project implement dashboards?
Cloud sends:

rag_search
project_id = CMDX
query = "existing dashboard architecture,
        components, layout and styling"
top_k = 5
Your PC's local RAG might return:

1. src/components/dashboard/DashboardLayout.tsx
   Score: 0.94

2. src/components/cards/StatCard.tsx
   Score: 0.91

3. src/styles/dashboard.css
   Score: 0.88

4. app/admin/dashboard/page.tsx
   Score: 0.86

5. src/components/navigation/Sidebar.tsx
   Score: 0.84
Only those relevant pieces need to be supplied as context to the agent.

The specification already requires RAG to return file path, line range and similarity score, with project-level filtering.


Then the UI Agent analyzes it
With the extended framework we've discussed:

Planning Agent
      ↓
Architecture Agent
      ↓
UI/UX Agent
UI/UX Agent determines:

Existing font:
Plus Jakarta Sans

Existing sidebar:
src/components/layout/AppSidebar.tsx

Existing card:
src/components/ui/Card.tsx

Existing button:
src/components/ui/Button.tsx

Brand colors:
existing theme tokens

Dashboard grid:
12-column responsive
So instead of producing some unrelated AI-looking page, it can say:

REUSE

AppSidebar
AppHeader
StatCard
Button
DataTable
Badge
Dialog

CREATE

AnalyticsSummary
UsageChart
RecentActivity
Frontend Agent then modifies your PC
It requests:

create_folder
Local Agent executes:

D:\Projects\cmdx-framework\
    app\
      analytics\
Then:

write_file
creates:

app/analytics/page.tsx
and:

components/analytics/
    AnalyticsStats.tsx
    UsageChart.tsx
    RecentActivity.tsx
Your original specification explicitly gives agents real filesystem CRUD tools and requires path protection around the project root.


Nothing is being written to the cloud copy.

It is writing to:

YOUR ACTUAL PC
        ↓
D:\Projects\cmdx-framework
Then it can run your local project
For example:

npm install
npm run lint
npm run typecheck
npm test
npm run build
These execute on your PC, inside:

D:\Projects\cmdx-framework
not on the cloud server.

The design already includes test, lint, formatter, security-scan and type-check execution tools.


What will you see in the cloud UI?
Even though execution happens locally, the browser can show:

LIVE AGENT EXECUTION

✓ Planning Agent
  Completed

✓ Architecture Agent
  Completed

✓ UI/UX Agent
  Completed

● Frontend Agent
  Running...

  + Created
    app/analytics/page.tsx

  + Created
    components/analytics/UsageChart.tsx

  ~ Modified
    components/layout/Sidebar.tsx

○ Test Agent
  Waiting

○ Validation Agent
  Waiting

○ Git Agent
  Waiting
Because your local agent sends events:

Local PC
   │
   │ WSS
   ▼
Cloud Backend
   │
   │ SSE
   ▼
Browser
The existing design already expects SSE-style live events from the backend to the frontend; we'd simply introduce the local worker before that cloud event pipeline.


Git also remains local
This is important.

If:

D:\Projects\cmdx-framework
already has Git:

.git/
AgentForge uses that repository.

For every instruction:

main
 │
 └── agent/ins_a72841
The AI works on:

agent/ins_a72841
and commits:

[Plan] Analytics dashboard

[UI] Define analytics dashboard UI

[Frontend] Add analytics dashboard

[Tests] Add analytics dashboard tests

[Validation] Fix linting issues
Then you see it in the cloud.

This follows the document's branch-per-instruction approach and keeps automated work off main/master.


You can review before merging
Cloud UI could show:

PIPELINE COMPLETE

Files Created       4
Files Modified      3
Files Deleted       0

Tests
48 / 48 passed

Coverage
89%

TypeScript
Passed

ESLint
Passed

Build
Passed

Git Branch
agent/ins_a72841
Then:

[ View Changes ]

[ Reject ]

[ Rollback ]

[ Approve & Merge ]
If you choose:

Approve & Merge
the command goes back to your PC:

FEROZ-PC
    ↓
Git merge
    ↓
main
What if you close your PC?
Then cloud simply shows:

FEROZ-PC

○ Offline
Your projects remain registered, but the cloud cannot modify them while the PC is offline.

A task could show:

Payments Dashboard

Waiting for device

FEROZ-PC is currently offline.
Execution will resume when the device reconnects.
Once your PC starts:

AgentForge Local Agent
        ↓
Reconnects automatically
        ↓
Cloud sees PC online
        ↓
Job resumes
What should run locally vs cloud?
I recommend this split:

Component	Cloud	Local PC
Next.js application	✅
Authentication	✅
FastAPI Control Plane	✅
PostgreSQL metadata	✅
Redis queue	✅
Crew/Workflow management	✅
Dashboard	✅
User/Organization management	✅
Billing	✅
DeepSeek API routing	✅
Source code		✅
Filesystem operations		✅
Git repository		✅
npm / Python commands		✅
Docker commands for project		✅
Tests		✅
Build		✅
Local server		✅
File watcher		✅
Code embeddings	preferably	✅
Local Qdrant	preferably	✅
This architecture gives you much better isolation.

Very important privacy point
There are actually three possible privacy modes worth designing.

Mode 1 — Cloud AI
Local project
    ↓
RAG selects relevant code
    ↓
Relevant snippets sent to cloud
    ↓
DeepSeek API
Fastest and simplest.

But relevant source-code context leaves your PC.

Mode 2 — Private RAG + Cloud AI
Source code
    ↓
Local RAG
    ↓
Only required snippets
    ↓
Cloud DeepSeek
Better.

This is what I would initially implement.

Mode 3 — Fully private/local AI
Later:

Project
   ↓
Local RAG
   ↓
Ollama / vLLM
   ↓
Local Llama / Qwen / DeepSeek model
Then:

SOURCE CODE NEVER LEAVES YOUR PC
Your cloud platform just controls jobs and receives sanitized status/results.

This is why the provider abstraction in the master prompt is valuable.

One Local Agent can handle many projects
You do not install one agent per project.

Install once:

AgentForge Local Agent
Then register:

FEROZ-PC

Projects

├── D:\Projects\cmdx-framework
├── D:\Projects\xplms
├── D:\Projects\maid-pro
├── D:\Projects\openxpertz-api
├── D:\Projects\website
└── C:\xampp\htdocs\client-project
The Local Agent keeps each project isolated:

Project A
    ↓
Sandbox A

Project B
    ↓
Sandbox B

Project C
    ↓
Sandbox C
No agent working on Project A should have permission to touch Project B.

Security: don't expose your PC
I would not do this:

Cloud
   ↓
Public IP
   ↓
Your PC port 8000
And definitely don't require users to configure:

Port forwarding
Router NAT
Public Windows port
Instead:

LOCAL AGENT
    │
    │ outbound HTTPS/WSS :443
    │
    ▼
CLOUD
Your PC initiates the connection.

Therefore normally:

No static IP required
No port forwarding
No router configuration
No public local API
That is much safer and much easier for the eventual product user.

The architecture I recommend for the actual product
I'd evolve your framework into two applications:

                     AGENTFORGE
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼

     AgentForge Cloud          AgentForge Local

     Next.js                   Go/Python/Rust daemon
     FastAPI                   Filesystem tools
     PostgreSQL                Git
     Redis                     Terminal
     Crew Manager              Tests
     User Management           Build
     Billing                   Local RAG
     Project Metadata          Qdrant
     Audit                     File watcher

            │                         │
            └──────── WSS ────────────┘
I would probably build the first version of the local worker in Python, because your entire agent/tool architecture is already Python and the specification itself is based on Python + Next.js + PostgreSQL.


Later, if you turn this into a commercial desktop product, the daemon could move to Rust or Go while retaining the Python agent runtime where needed.

Example of your real daily workflow
You could be away from your development PC and open:

https://agentforge.yourcompany.com
Choose:

CMDX Framework
which maps to:

FEROZ-PC
D:\Projects\cmdx-framework
Then say:

Redesign the model configuration page.

Follow the current application design system.

Make Agent / Ask / Plan mode selector functional.

Allow model selection.

Add BYOK.

Fix History.

Fix thumbs-up/down feedback.

Show toast notifications.

Do not break existing backend functionality.
Your cloud framework orchestrates the agents, while all actual reading, writing, testing, building and Git operations happen on your development PC.

That is the architecture I would recommend for your product.

One change to the current specification
We should add a new major component:

AGENTFORGE LOCAL WORKER / DEVICE AGENT
and change:

PROJECT_ROOT_PATH
from being a path on the cloud server into:

Device ID
+
Local Workspace ID
+
Authorized Project Path
For example:

{
  "project_id": "prj_001",
  "device_id": "dev_feroz_pc",
  "workspace_id": "ws_cmdx",
  "local_path": "D:\\Projects\\cmdx-framework"
}
That change is important enough that I recommend we update the architecture before VS Code begins implementing the framework.


yes

Yes. Before you start implementation in VS Code, I recommend changing the architecture to a Cloud Control Plane + Local Execution Agent model.

Your original document assumes that the backend directly accesses PROJECT_ROOT_PATH and mounts the project directory into the backend container.

 We should replace that assumption because your real requirement is:

AgentForge application = cloud hosted
Development projects = remain on your local PC

Add the following section to the master VS Code prompt I gave you earlier.

# CRITICAL ARCHITECTURE UPDATE
# CLOUD CONTROL PLANE + LOCAL EXECUTION AGENT

The AI Agent Framework MUST support projects stored on users' local
computers while the primary AgentForge application is hosted in the cloud.

Do NOT design the production system assuming the cloud FastAPI server
has direct filesystem access to user project directories.

The architecture must be divided into two major components:

1. AgentForge Cloud
2. AgentForge Local Agent

============================================================
1. AGENTFORGE CLOUD — CONTROL PLANE
============================================================

The cloud application is responsible for:

- Next.js web application
- Authentication
- User management
- Organization management
- Project metadata
- Device registration
- Workspace registration
- Agent orchestration
- Planning
- AI/LLM routing
- DeepSeek API integration
- Pipeline management
- Redis
- PostgreSQL
- Job scheduling
- SSE streaming to browser
- Audit logs
- Billing/usage
- Agent configuration
- Model configuration
- BYOK configuration
- Confirmation workflows
- Git/history metadata
- Observability

Cloud services:

frontend
backend
worker
postgres
redis

Optional cloud services:

qdrant
flower
prometheus
grafana

The cloud MUST NOT assume access to:

C:\Projects
D:\Projects
/home/user/projects

or any other local project path.

============================================================
2. AGENTFORGE LOCAL AGENT — EXECUTION PLANE
============================================================

Create a separate local application named:

AgentForge Local Agent

Initial implementation:

Python 3.11+

The Local Agent runs on the developer's computer and securely connects
to AgentForge Cloud.

It performs actual operations on local projects.

Responsibilities:

- Register local machine
- Maintain secure cloud connection
- Register authorized project directories
- Read project files
- Write project files
- Update project files
- Create files
- Create directories
- Delete files with confirmation
- Search project files
- Build project tree
- Run Git commands
- Run tests
- Run linters
- Run type checking
- Run security scans
- Run builds
- Execute strictly whitelisted commands
- Maintain local filesystem watcher
- Perform local RAG indexing
- Perform semantic search
- Stream operation events to cloud
- Receive agent tool requests from cloud
- Return structured tool results
- Enforce project isolation

============================================================
3. CONNECTION MODEL
============================================================

The Local Agent MUST initiate the connection to the cloud.

Use:

HTTPS + Secure WebSocket (WSS)

Port:

443

Architecture:

Local Agent
      |
      | outbound WSS/HTTPS
      |
      v
AgentForge Cloud

Do NOT require:

- Public IP on local PC
- Port forwarding
- Router configuration
- Publicly exposed local FastAPI server
- Inbound firewall rule
- Static IP

The local computer must never expose an AgentForge service directly
to the public Internet.

============================================================
4. DEVICE REGISTRATION
============================================================

Implement machine/device registration.

Database table:

devices

Suggested fields:

id UUID
user_id UUID
organization_id UUID nullable
name
hostname
platform
os_version
architecture
agent_version
status
last_seen_at
created_at
updated_at

Statuses:

online
offline
disabled
revoked

Device onboarding flow:

Cloud UI
    ↓
Connect Device
    ↓
Generate temporary pairing code
    ↓
User starts Local Agent
    ↓
Local Agent enters pairing code
    ↓
Device obtains secure device credential
    ↓
Persistent secure connection established

Pairing codes must:

- expire
- be one-time use
- be cryptographically random
- never become permanent credentials

============================================================
5. LOCAL WORKSPACE MODEL
============================================================

Do NOT store project_root_path alone as the execution reference.

Use:

device_id
workspace_id
authorized_local_path

Create table:

workspaces

Fields:

id UUID
device_id UUID
project_id UUID
display_name
local_path
git_repository
default_branch
status
created_at
updated_at

Example:

Project:
CMDX Framework

Device:
FEROZ-PC

Workspace:
CMDX Local Workspace

Local Path:
D:\Projects\cmdx-framework

Internally:

{
  "project_id": "prj_xxx",
  "device_id": "dev_xxx",
  "workspace_id": "ws_xxx"
}

The cloud should normally send workspace_id instead of arbitrary
filesystem paths.

============================================================
6. PROJECT PATH SECURITY
============================================================

The Local Agent must maintain an explicit list of authorized project roots.

Example:

D:\Projects\cmdx-framework
D:\Projects\xplms
D:\Projects\maid-pro

A job for CMDX Framework may ONLY operate inside:

D:\Projects\cmdx-framework

It MUST NOT access:

D:\Projects\xplms

even though both projects belong to the same device.

Every filesystem request must resolve:

requested_path
    ↓
canonical absolute path
    ↓
authorized workspace root validation
    ↓
allow / deny

Block:

../ traversal

.git internals

.env

*.pem
*.key

SSH keys

system directories

Windows credentials

browser profiles

other registered workspaces

unregistered directories

============================================================
7. LOCAL AGENT AUTHENTICATION
============================================================

Every Local Agent connection must authenticate using a device credential.

Do NOT store raw long-lived secrets where avoidable.

Support:

- device token rotation
- device revoke
- session expiration
- TLS
- signed requests/messages
- message IDs
- timestamps
- replay protection

Each command must include:

request_id
device_id
workspace_id
job_id
instruction_id
tool_name
parameters
issued_at

The Local Agent must validate the request before execution.

============================================================
8. CLOUD ↔ LOCAL MESSAGE PROTOCOL
============================================================

Define a structured protocol.

Example request:

{
  "type": "tool_request",
  "request_id": "req_123",
  "job_id": "job_456",
  "workspace_id": "ws_789",
  "tool": "read_file",
  "arguments": {
    "path": "src/modules/orders/service.py"
  }
}

Response:

{
  "type": "tool_result",
  "request_id": "req_123",
  "job_id": "job_456",
  "workspace_id": "ws_789",
  "success": true,
  "result": {},
  "error": null,
  "duration_ms": 32
}

Events:

device_connected
device_disconnected

job_received
job_started
job_completed
job_failed

tool_started
tool_completed
tool_failed

file_created
file_updated
file_deleted

rag_search_started
rag_search_completed

test_started
test_result

build_started
build_completed

confirmation_required

git_commit_created

pipeline_completed

pipeline_failed

============================================================
9. LOCAL TOOL SERVICE
============================================================

Move physical filesystem/execution tools to the Local Agent.

Local tools:

read_file
write_file
update_file
delete_file

create_folder
delete_folder

list_files
get_project_tree
search_in_files
get_file_diff

git_status
git_add
git_commit
git_diff
git_log
git_branch
git_rollback
git_tag
git_stash

run_command
run_tests
run_linter
run_formatter
run_security_scan
run_type_check
run_build

rag_search
rag_index_file
rag_update_file
rag_delete_file
rag_index_project

The Cloud Agent system calls them through a Tool Gateway.

============================================================
10. TOOL GATEWAY
============================================================

Implement a cloud service:

backend/app/tools/gateway/

Suggested:

gateway/
├── base.py
├── local_gateway.py
├── cloud_gateway.py
├── registry.py
├── schemas.py
└── errors.py

Agents MUST NOT care whether a project is local or cloud hosted.

Example:

agent
  ↓
ToolRegistry
  ↓
ToolGateway
  ↓
Execution Target

Target can be:

LOCAL
CLOUD
SANDBOX

This abstraction is mandatory.

============================================================
11. EXECUTION TARGET
============================================================

Add project execution_target:

LOCAL
CLOUD
SANDBOX

For initial product implementation support:

LOCAL
CLOUD

LOCAL:

Filesystem, Git, builds and tests happen on registered Local Agent.

CLOUD:

Project exists inside an isolated cloud workspace/container.

This makes AgentForge usable for both:

- local developer projects
- cloud repositories/workspaces

============================================================
12. LOCAL RAG
============================================================

For local projects, prefer RAG indexing on the Local Agent.

Local components:

File Scanner
    ↓
Chunker
    ↓
Local Embedding Model
    ↓
Qdrant
    ↓
Local Project Knowledge Base

Use:

sentence-transformers
CodeBERT
MiniLM
Qdrant

This is consistent with the project-aware RAG design.

RAG indexing must not upload the entire repository to cloud by default.

Cloud sends:

{
  "workspace_id": "...",
  "query": "...",
  "top_k": 5
}

Local Agent returns:

{
  "results": [
    {
      "file_path": "...",
      "start_line": 20,
      "end_line": 80,
      "score": 0.94,
      "content": "..."
    }
  ]
}

============================================================
13. PRIVACY MODES
============================================================

Architect three privacy modes.

MODE 1:

CLOUD_AI

Local filesystem
→ Local RAG
→ Relevant source snippets
→ Cloud AI provider

MODE 2:

RESTRICTED_CLOUD_AI

Local RAG
→ Minimized context
→ Secret filtering
→ Cloud AI provider

MODE 3:

LOCAL_AI

Local filesystem
→ Local RAG
→ Local model
→ Results

Local AI providers may later include:

Ollama
vLLM
LM Studio
local OpenAI-compatible endpoint

Do not tightly couple architecture to DeepSeek.

============================================================
14. SECRET FILTERING

Before local source content is sent to any cloud model, scan and block:

.env values

API keys

access tokens

private keys

passwords

connection strings with credentials

AWS credentials

GitHub tokens

database passwords

JWT signing secrets

SSH keys

Provide redaction:

sk-abc123...
↓
[REDACTED_API_KEY]

The system must record that redaction occurred without storing the secret.

============================================================
15. LOCAL AGENT PROCESS

The initial Local Agent can run as:

agentforge-local.exe

or during development:

python -m agentforge_local

Commands:

agentforge login

agentforge connect

agentforge status

agentforge devices

agentforge workspace add

agentforge workspace remove

agentforge workspace list

agentforge doctor

agentforge start

agentforge stop

Example:

agentforge workspace add "D:\Projects\cmdx-framework"

============================================================
16. WINDOWS SUPPORT

Windows is a first-class platform.

Support:

Windows 10+
Windows 11

Handle paths correctly:

D:\Projects\app

Do not assume Unix paths.

Use Python pathlib everywhere.

Do not concatenate filesystem paths manually.

Detect available runtimes:

Git
Python
Node.js
npm
pnpm
yarn
Docker
PHP
Composer

Return capabilities to cloud.

Example:

{
  "python": "3.12.4",
  "node": "22.10",
  "npm": "10.9",
  "git": "2.46",
  "docker": "27.1",
  "php": "8.3"
}

============================================================
17. DEVICE CAPABILITIES

Local Agent reports:

OS
CPU
RAM
available disk
Python
Node
Docker
Git
PHP
Java

and supported execution capabilities.

Do NOT send sensitive machine information unnecessarily.

Capabilities are used to determine whether a project can execute.

============================================================
18. OFFLINE HANDLING

If Local Agent disconnects:

DO NOT fail the entire project immediately.

Set job status:

WAITING_FOR_DEVICE

Cloud UI displays:

"Development machine is offline."

When device reconnects:

validate job
restore checkpoint
continue execution

Use configurable timeout.

============================================================
19. JOB QUEUE

Create:

local_jobs

Fields:

id
device_id
workspace_id
instruction_id
job_type
payload
status
priority
created_at
dispatched_at
started_at
completed_at
error

Statuses:

queued
waiting_for_device
dispatched
running
waiting_confirmation
completed
failed
cancelled

============================================================
20. LOCAL EXECUTION SAFETY

Commands execute with:

working_directory = authorized workspace root

Never:

shell=True

unless an isolated safe implementation explicitly requires it.

Prefer command arrays.

Example:

[
  "npm",
  "run",
  "build"
]

instead of:

"npm run build"

Validate executable and arguments independently.

============================================================
21. PROCESS EXECUTION

Local Agent execution service must provide:

stdout streaming
stderr streaming
return code
execution duration
timeout
cancellation

Support process tree termination.

Limit:

CPU where possible
memory where possible
execution duration

For Docker-enabled projects, allow future sandbox execution.

============================================================
22. GIT STRATEGY FOR LOCAL PROJECTS

The real repository remains local.

At instruction start:

main
  ↓
agent/{instruction_id}

All changes happen on the agent branch.

Do NOT directly modify main/master.

Agent-stage commits:

[Plan]
[Docs]
[UI]
[Frontend]
[Backend]
[Database]
[Tests]
[Validation]

After successful validation:

User chooses:

Approve & Merge
Reject
Rollback

Merge is executed locally.

============================================================
23. FILE DIFFS

Do not upload entire project history.

Local Agent computes Git diff and sends only necessary diff metadata/content.

Cloud UI displays:

created
modified
deleted
renamed

with syntax-highlighted line diffs.

============================================================
24. LOCAL FILE WATCHER

Watch authorized workspaces.

When developer manually edits files:

created
updated
deleted
renamed

Trigger local RAG update.

Do not assume every file change was made by AgentForge.

Distinguish:

agent_generated
user_generated
external_tool_generated

where possible.

============================================================
25. UI — LOCAL MACHINES PAGE

Create cloud route:

/devices

Display:

Device name
Operating system
Online/offline
Agent version
Last seen
Number of projects
Capabilities

Actions:

Connect Device
Rename
Disable
Revoke

============================================================
26. UI — DEVICE DETAIL

Route:

/devices/{device_id}

Show:

Device
Status
Agent version
OS
Capabilities
Registered workspaces
Current jobs
Recent executions
Connection history

============================================================
27. UI — CREATE PROJECT

Change Create Project flow.

Step 1:

Project Information

Step 2:

Execution Location

Options:

Local Machine
Cloud Workspace

If Local Machine:

Select Device

Example:

FEROZ-PC        Online

Then select registered workspace.

Do NOT ask the cloud server to validate the Windows path.

The Local Agent validates it.

============================================================
28. UI — LOCAL AGENT STATUS

Project page should display:

Execution Location

FEROZ-PC
● Online

Workspace

D:\Projects\cmdx-framework

Git Branch

agent/ins_xxx

RAG

Local · 1,842 chunks

This makes it clear where operations are executing.

============================================================
29. END-TO-END LOCAL WORKFLOW

The final workflow must be:

User Browser

↓ HTTPS

AgentForge Cloud

↓ Instruction

Planning Agent

↓ Need project context

Tool Gateway

↓ WSS

Local Agent

↓ Local RAG

Relevant project context

↑

Cloud Agent

↓ Implementation instructions

Local Agent

↓

Filesystem changes

↓

Tests

↓

Validation

↓

Git Commit

↓

Results/events

↑ WSS

Cloud FastAPI

↓

SSE

Browser

============================================================
30. IMPORTANT DATA OWNERSHIP RULE

Project source code should remain on the local computer unless content is
explicitly required by the selected AI provider.

Cloud database stores:

project metadata
device metadata
workspace metadata
agent runs
audit records
tool summaries
Git commit metadata
test summaries
validation summaries

Do NOT create a complete cloud mirror of local source repositories by default.

============================================================
31. REVISED MONOREPO

Use:

agentforge/
│
├── apps/
│   │
│   ├── web/
│   │
│   │   └── Next.js
│   │
│   ├── api/
│   │   │   └── FastAPI
│   │   └── local-agent/
│   │       └── Python
│   │
│   ├── workers/
│   │
│   └── ...
│
├── packages/
│   ├── contracts/
│   ├── protocol/
│   └── shared/
│
├── infrastructure/
│
├── docs/
│
├── docker-compose.yml
│
└── README.md

Suggested local agent:

apps/local-agent/
├── agentforge_local/
│   ├── auth/
│   ├── connection/
│   ├── protocol/
│   ├── filesystem/
│   ├── execution/
│   ├── git/
│   ├── rag/
│   ├── watcher/
│   ├── security/
│   ├── workspaces/
│   ├── jobs/
│   ├── telemetry/
│   └── config/
│
├── tests/
├── pyproject.toml
└── README.md

============================================================
32. IMPLEMENTATION PRIORITY CHANGE

Update implementation phases.

Phase 0
Architecture + repository analysis

Phase 1
Cloud foundation

Phase 2
Local Agent foundation

Phase 3
Secure device pairing

Phase 4
WSS command/event protocol

Phase 5
Workspace registration and security

Phase 6
Local filesystem tools

Phase 7
Local Git tools

Phase 8
Local execution tools

Phase 9
Local RAG

Phase 10
LLM provider layer

Phase 11
Agent implementation

Phase 12
Pipeline orchestration

Phase 13
Cloud UI

Phase 14
Live execution UI

Phase 15
UI generation capability

Phase 16
Testing + hardening

============================================================
33. FIRST LOCAL DEVELOPMENT ACCEPTANCE TEST

Development machine:

Windows

Example workspace:

D:\Projects\agentforge-demo

The system must demonstrate:

1. Local Agent starts.
2. Local Agent pairs with cloud.
3. Cloud shows machine online.
4. Local workspace is registered.
5. Cloud project references the local workspace.
6. User submits an instruction.
7. Planning Agent requests local project tree.
8. Local Agent returns tree.
9. Local RAG retrieves relevant source files.
10. Code Agent requests new files.
11. Files are physically created on local PC.
12. Tests execute on local PC.
13. Validation executes on local PC.
14. Git branch is created locally.
15. Git commits are created locally.
16. Cloud UI receives live events.
17. User sees file diffs.
18. User approves changes.
19. Local branch merges.
20. Project files remain on local PC.

If any of these steps are missing, the local-project architecture is not
considered complete.

============================================================
34. ARCHITECTURAL RULE

This requirement is NON-NEGOTIABLE:

The AI orchestration layer must NEVER directly assume that it has local
filesystem access.

All project operations must be requested through the Tool Gateway.

Agent
 ↓
Tool
 ↓
Tool Gateway
 ↓
Execution Target
 ↓
Local Agent / Cloud Workspace

This must be built into the architecture from the beginning.
That changes an important part of your original design. The document currently defines filesystem tools as direct Python functions that operate under the project root, with safety checks preventing access outside it.

 We keep all of those concepts, but those functions now live primarily inside the Local Agent when the project's execution target is LOCAL.

The same applies to Git. Your document already requires every instruction to get its own agent/{instruction_id} branch and prevents agents from working directly on main/master.

 With the revised architecture, those Git operations occur against the actual repository on your PC.

Final architecture
                         INTERNET
                            │
                            │ HTTPS
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                     AGENTFORGE CLOUD                         │
│                                                              │
│  Next.js                                                     │
│     │                                                        │
│     ▼                                                        │
│  FastAPI ───────── PostgreSQL                                │
│     │                                                        │
│     ├──────────── Redis                                      │
│     │                                                        │
│     ▼                                                        │
│  Agent / Crew Orchestrator                                   │
│     │                                                        │
│     ▼                                                        │
│  LLM Router ───────── DeepSeek / Claude / Gemini / etc.      │
│     │                                                        │
│     ▼                                                        │
│  Tool Gateway                                                │
│     │                                                        │
└─────┼────────────────────────────────────────────────────────┘
      │
      │ Secure WebSocket
      │ outbound connection from local machine
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│                 AGENTFORGE LOCAL AGENT                       │
│                                                              │
│ Device Authentication                                        │
│ Workspace Security                                           │
│ Job Executor                                                 │
│                                                              │
│    ┌───────────────┐                                         │
│    │ Filesystem    │                                         │
│    ├───────────────┤                                         │
│    │ Git           │                                         │
│    ├───────────────┤                                         │
│    │ Terminal      │                                         │
│    ├───────────────┤                                         │
│    │ Tests         │                                         │
│    ├───────────────┤                                         │
│    │ Build         │                                         │
│    ├───────────────┤                                         │
│    │ Local RAG     │                                         │
│    └───────┬───────┘                                         │
│            │                                                 │
│            ▼                                                 │
│                 YOUR LOCAL PC                                │
│                                                              │
│ D:\Projects\CMDX                                             │
│ D:\Projects\XPLMS                                            │
│ D:\Projects\MaidPro                                          │
│ D:\Projects\OtherProject                                     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
Your original system flow—user instruction → backend → agent pipeline → RAG → filesystem operations → Git → real-time frontend updates—still remains intact.

 We're simply separating the brain from the machine that owns and executes the source code.

One more recommendation
For the first prototype, I would not start with CrewAI or DeepSeek.

Build this first:

Cloud Web → FastAPI → WSS → Local Agent → read/write a test file → send result back to browser.

Once that works reliably, add Git, then local RAG, then execution/tests, and only after that plug in the AI agents.

That foundation is the most important part of this architecture.


