Below is the prompt I recommend giving directly to your **VS Code coding agent**. It is deliberately written as an **upgrade/refactor prompt**, not a greenfield-build prompt, because the agent must first understand what is already implemented and preserve working functionality.

The current prototype clearly contains the visual foundation you want, including Dashboard, New Project, Live Workspace, RAG Manager, Git History, Observability, Architecture, and Settings.  However, several parts are explicitly still mock-driven: the live pipeline says “mock SSE stream,” Observability says “Mock operational metrics,” Settings says prototype values, and project creation currently creates a project directly in browser memory without performing real project-directory validation.

Use this prompt:

````markdown
# MASTER IMPLEMENTATION PROMPT
# AgentForge — Convert Existing Prototype Into Pixel-Perfect, Fully Functional Real Application

You are working on an EXISTING project.

This is NOT a new project.

A significant amount of UI, backend, architecture, project structure, and functionality may already have been implemented.

Your first responsibility is to fully inspect, understand, and document the CURRENT CODEBASE before changing anything.

Do not rebuild the application blindly.
Do not replace working implementations unnecessarily.
Do not create duplicate components or duplicate services.
Do not reset the project.
Do not delete existing functionality just because you would implement it differently.

The objective is to complete and correct the existing implementation.

---

# 1. PRIMARY OBJECTIVE

We have an AgentForge / AI Agent Framework application.

There is an approved prototype/reference design.

I need the real application to match that prototype as closely as technically possible:

## PIXEL-PERFECT DESIGN

The real application must reproduce the approved prototype UI:

- same layout
- same sidebar
- same navigation structure
- same header
- same card dimensions
- same spacing
- same typography hierarchy
- same backgrounds
- same borders
- same border radius
- same shadows
- same colors
- same status indicators
- same badges
- same buttons
- same forms
- same tables
- same agent execution layout
- same RAG UI
- same Git history UI
- same file browser
- same observability layout
- same architecture page
- same settings layout
- same responsive behaviour
- same visual hierarchy

Treat the existing approved prototype as the DESIGN SOURCE OF TRUTH.

Do not redesign it according to your own preference.

Do not "improve" the visual design unless absolutely required for functionality.

Do not substitute a generic shadcn dashboard.

Do not simplify the interface.

Do not change branding.

We want the REAL application to look like the prototype.

---

# 2. VERY IMPORTANT — FIRST UNDERSTAND CURRENT IMPLEMENTATION

Before writing or changing code, inspect the COMPLETE repository.

You MUST determine:

- what is already implemented
- what is partially implemented
- what is mock
- what is real
- what is broken
- which API endpoints already exist
- which frontend pages already exist
- which components already exist
- which database tables already exist
- which migrations already exist
- whether Redis is implemented
- whether Qdrant is implemented
- whether CrewAI is implemented
- whether DeepSeek/model integration exists
- whether SSE/WebSocket/event streaming exists
- whether filesystem integration exists
- whether Git integration exists
- whether RAG indexing exists
- whether workers/background jobs exist
- what project directory validation currently does
- why "Check Project Folder" is not working correctly
- how configuration/environment variables currently work

Inspect, at minimum:

- README
- docs/
- frontend/
- backend/
- API routes
- database models
- migrations
- services
- repositories
- agents
- tools
- workers
- RAG implementation
- filesystem implementation
- Git implementation
- environment files/examples
- Docker configuration
- package.json
- pyproject.toml / requirements files
- existing tests

Also SEARCH the entire repository for:

```text
mock
dummy
sample
fake
hardcoded
setTimeout
Math.random
demo
placeholder
TODO
FIXME
simulate
simulation
prototype
localStorage
sessionStorage
````

Do not assume every occurrence must be removed.

Classify each one first.

---

# 3. CREATE A CURRENT-STATE AUDIT FIRST

Before major implementation changes, create:

```text
docs/CURRENT_IMPLEMENTATION_AUDIT.md
```

It must contain:

## Existing and Working

List everything already implemented and working.

## Existing but Partial

List incomplete implementations.

## Mock Implementations

List every frontend/backend feature currently using mock data or simulated behaviour.

## Missing

List functionality required by the approved system that does not yet exist.

## Broken

List known broken functionality.

Specifically investigate:

```text
Check Project Folder
```

## Integration Map

Document:

Frontend
→ API
→ Services
→ Workers
→ Agents
→ RAG
→ Filesystem
→ Git
→ PostgreSQL / Redis / Qdrant

## Reuse Plan

Clearly identify code/components/services that must be preserved.

---

# 4. APPROVED REFERENCE UI

There is an existing AgentForge prototype/reference implementation.

The approved design contains:

### Main Navigation

* Dashboard
* New Project
* Live Workspace
* RAG Manager
* Git History
* Observability
* Architecture
* Settings

### Main UI structure

Dark left sidebar.

White sticky top header.

Light application background.

Professional compact SaaS/developer-platform styling.

The following visual identity must remain consistent throughout the application.

Example reference tokens:

```css
--bg: #f6f8fc;
--panel: #ffffff;
--text: #121827;
--muted: #687386;
--line: #e3e8f1;

--nav: #111a33;
--nav2: #172342;

--purple: #6f35c8;
--purple2: #8a5ade;
--blue: #1976d2;
--teal: #0e8b92;
--green: #238636;
--orange: #dd7a00;
--red: #d6263b;
```

Do not randomly replace these colors.

Extract the exact approved styling from the reference prototype and convert it into proper reusable design tokens/components.

---

# 5. DO NOT KEEP THE PROTOTYPE AS ONE HTML FILE

The prototype may currently exist as static HTML/CSS/JS.

Do NOT simply continue building production functionality inside one static HTML file.

Use the prototype as the visual specification.

Implement the real UI using the existing application framework.

If the frontend is Next.js, create reusable production components.

For example:

```text
frontend/
  app/
  components/
  features/
  hooks/
  services/
  lib/
  types/
```

Possible reusable components:

```text
AppSidebar
TopHeader
PageHeader
StatCard
StatusBadge
ProjectCard
AgentPipeline
AgentRow
LiveEventStream
ExecutionContext
CurrentChanges
ProjectFileTree
CodeViewer
DiffViewer
ArtifactList
TestSummary
ValidationReport
GitCommitList
RAGResult
RAGStatusCard
MetricCard
ConfirmationDialog
ToastProvider
```

But BEFORE creating a component, search the repository to determine whether an equivalent already exists.

Reuse before creating.

---

# 6. REMOVE MOCK BEHAVIOUR FROM PRODUCTION PATH

The approved prototype currently demonstrates the expected UX through simulated behaviour.

The production application must use REAL DATA.

Replace mock/simulated behaviour with real service integrations.

Examples that must NOT remain as simulated production logic:

```text
setTimeout-based agent simulation
fake progress percentages
hardcoded project counts
hardcoded files generated counts
hardcoded test counts
hardcoded RAG results
fake Git commits
fake rollback
fake service-health statuses
fake API cost
fake model usage
fake test output
fake coverage
fake Qdrant indexing numbers
hardcoded generated file contents
fake "semantic search completed"
fake re-index progress
fake SSE events
```

Mock mode may remain ONLY if explicitly isolated behind:

```env
APP_MODE=mock
```

Production mode must never silently fall back to mock data.

---

# 7. REAL PROJECT DATA

Dashboard values must come from backend/database.

For example:

```text
Total Projects
Agent Runs
Files Generated
Tests Passed
Success Rate
Last Activity
Pipeline Status
```

These values must be calculated from real persisted records.

Project cards must come from:

```text
GET /api/projects
```

or the project's existing equivalent endpoint.

No hardcoded project array in production.

---

# 8. CRITICAL ISSUE — FIX "CHECK PROJECT FOLDER"

This is currently not working as expected.

Treat this as a HIGH PRIORITY issue.

Do not apply a superficial frontend-only validation.

First trace the COMPLETE existing flow.

Search for:

```text
check project folder
validate project path
project path
project root
PROJECT_ROOT
PROJECT_ROOT_PATH
PROJECT_ROOT_BASE
validate_path
directory exists
filesystem
path validation
```

Determine:

* whether a backend endpoint exists
* whether frontend is actually calling it
* whether the request payload is correct
* whether Windows paths work
* whether Linux paths work
* whether Docker path mapping is involved
* whether application server can see the user's path
* whether project runs locally or remotely
* whether permissions are checked
* whether symlinks are handled
* whether path normalization exists
* whether security confinement exists

Then implement the correct behaviour.

---

# 9. IMPORTANT PROJECT PATH ARCHITECTURE

Do NOT confuse:

```text
Browser path
Application server path
Docker container path
Host-machine path
```

These are not automatically the same.

The application must correctly understand where the selected project actually exists.

If AgentForge is running locally:

```text
User Machine
    ↓
AgentForge
    ↓
Local Project Directory
```

the backend can validate the local filesystem directory directly.

If AgentForge backend runs in Docker:

the host project folder must be mounted into the backend/worker containers.

If AgentForge runs remotely/cloud-hosted:

a browser cannot simply send something such as:

```text
C:\xampp\htdocs\project
```

and expect a remote server to access it.

The architecture must explicitly support the deployment mode.

---

# 10. PROJECT FOLDER VALIDATION REQUIREMENTS

Implement a real project-folder validation endpoint if it does not already exist.

Suggested:

```http
POST /api/projects/validate-path
```

Request:

```json
{
  "path": "..."
}
```

Response example:

```json
{
  "valid": true,
  "exists": true,
  "is_directory": true,
  "readable": true,
  "writable": true,
  "git_repository": true,
  "detected_stack": [
    "Python",
    "FastAPI",
    "Next.js"
  ],
  "project_name": "my-project",
  "files_count": 428,
  "directories_count": 67,
  "warnings": []
}
```

If invalid:

```json
{
  "valid": false,
  "exists": false,
  "is_directory": false,
  "readable": false,
  "writable": false,
  "warnings": [
    "The directory cannot be accessed by the AgentForge backend."
  ]
}
```

---

# 11. CHECK PROJECT FOLDER UI

On New Project page, provide:

```text
Project Root Path
[____________________________________] [Check Folder]
```

When checking:

```text
Checking...
```

Then display an inline result.

Success:

```text
✓ Folder found
✓ Read permission
✓ Write permission
✓ Git repository detected
✓ 428 files
✓ Technology detected: Python, FastAPI, Next.js, PostgreSQL
```

Warnings:

```text
⚠ Git repository not found
⚠ Node modules ignored
```

Failure:

```text
✕ Project folder cannot be accessed
```

Show the ACTUAL backend error.

Do not return generic "Something went wrong".

Do not allow project creation until path validation succeeds, unless the selected project mode intentionally does not require filesystem access.

---

# 12. PATH SECURITY

Every project path must be normalized.

Use platform-safe path handling.

Python example conceptually:

```python
Path(path).expanduser().resolve()
```

But implement it according to the current architecture.

Protect against:

```text
../
../../
symlink escape
unauthorized root directories
system directories
```

The selected path must fall inside configured allowed project roots where that security policy applies.

Do not expose `.env`, keys, credentials, or secrets unnecessarily.

---

# 13. PROJECT CREATION MUST BE REAL

Current production flow should be:

```text
User enters project information
        ↓
Check Project Folder
        ↓
Backend validates folder
        ↓
Detect project stack
        ↓
User confirms
        ↓
POST /api/projects
        ↓
Persist project in PostgreSQL
        ↓
Initialize/inspect Git repository
        ↓
Queue RAG indexing
        ↓
Return real project ID
        ↓
Navigate to Project Workspace
        ↓
Show real indexing status
```

Do NOT simply add the project to frontend memory.

---

# 14. TECHNOLOGY DETECTION

When checking the project folder, inspect real files.

Examples:

```text
package.json
next.config.*
tsconfig.json
requirements.txt
pyproject.toml
manage.py
composer.json
version.php
docker-compose.yml
Dockerfile
alembic.ini
```

Detect technologies such as:

```text
Python
FastAPI
Django
Next.js
React
Node.js
TypeScript
PHP
Moodle
PostgreSQL
MySQL
Redis
Docker
```

Return detected technologies to UI.

Allow user to edit them after automatic detection.

---

# 15. REAL RAG INDEXING

After project creation:

```text
Project
 ↓
File Scanner
 ↓
Ignore rules
 ↓
Code-aware chunking
 ↓
Embedding
 ↓
Qdrant
 ↓
Index metadata persisted
```

Display REAL progress.

For example:

```text
Scanning project...     18%
Parsing files...        34%
Generating embeddings.. 67%
Writing Qdrant index... 91%
Completed              100%
```

Progress must come from backend events.

Do not generate random percentages.

---

# 16. LIVE WORKSPACE MUST USE REAL PIPELINE DATA

The approved layout must remain pixel-perfect.

But replace the mock agent state with real pipeline state.

The main pipeline must display actual agents.

For the current project architecture, determine which agents already exist.

Do not blindly duplicate agents.

Possible desired final architecture:

```text
Planning Agent
Architecture Agent
UI/UX Agent
Documentation Agent
Frontend Agent
Backend Agent
Database Agent
Test Agent
Validation Agent
Git Agent
```

However:

IF the current repository intentionally still uses the existing six-agent system:

```text
Planning
Documentation
Code
Test
Validation
Git
```

first understand that architecture.

Do not introduce breaking architecture changes purely for visual reasons.

Create a migration/refactoring plan if expanding the agent system is required.

---

# 17. REAL AGENT EXECUTION EVENTS

Frontend must receive real events from backend.

Use the existing implementation if SSE/WebSocket already exists.

Do not create a competing mechanism.

Expected events include:

```text
pipeline_started

agent_started
agent_progress
agent_completed
agent_failed

rag_search_started
rag_search_completed

file_read
file_created
file_updated
file_deleted

tool_started
tool_completed

test_started
test_result

validation_started
validation_completed

confirmation_required

git_commit_created

pipeline_completed
pipeline_failed
```

The UI must react to these events.

---

# 18. NEVER DISPLAY PRIVATE CHAIN-OF-THOUGHT

The Live Event Stream should show operational information such as:

```text
Planning Agent started
Retrieved 5 files from RAG
Analyzed 3 existing modules
Created implementation plan
Code Agent created payments/models.py
Validation completed
```

Do NOT attempt to expose hidden model reasoning or internal chain-of-thought.

---

# 19. REAL FILE TREE

The Files tab must display the selected project's ACTUAL files.

Use backend filesystem APIs.

Requirements:

* folder expansion
* folder collapse
* lazy loading where useful
* file icons
* modified state
* created state
* deleted state
* last modifying agent
* file content
* syntax highlighting
* diff view

The code viewer must display actual file contents.

No hardcoded `codeContent`.

---

# 20. REAL FILE DIFF

The Diff button must work.

Use real Git diff / filesystem diff.

Support:

```text
current vs previous commit
working tree vs HEAD
commit vs commit
```

Clearly show:

```text
added lines
removed lines
modified lines
```

---

# 21. REAL RAG MANAGER

Preserve the approved visual design.

Replace static values with real values:

```text
Files Indexed
Chunks
Coverage
Last Index
Embedding Model
Vector DB status
```

The semantic search box must query the actual RAG backend.

Result:

```text
file path
line range
similarity score
content preview
collection
```

No hardcoded RAG results.

---

# 22. REAL RE-INDEX

The Re-index Project button must:

1. call backend
2. start a real re-index job
3. receive job ID
4. subscribe to progress
5. show real percentage
6. update index statistics
7. handle failures
8. allow retry

---

# 23. REAL GIT HISTORY

The Git History screen must use the selected project's actual repository.

Display:

```text
commit hash
message
author/agent
timestamp
files changed
branch
```

Actions:

```text
View Diff
Rollback
Compare
```

No hardcoded commit list.

---

# 24. REAL ROLLBACK

Rollback is destructive.

Must show confirmation dialog.

Flow:

```text
User selects rollback
 ↓
Load commit information
 ↓
Display affected files
 ↓
User confirms
 ↓
Backend performs rollback
 ↓
RAG affected files re-indexed
 ↓
UI refreshes
```

Do NOT use JavaScript `confirm()` in final production UI.

Use the approved application modal.

---

# 25. REAL TEST RESULTS

Tests screen must come from real execution artifacts.

Show:

```text
Total
Passed
Failed
Skipped
Coverage
Duration
```

Allow users to inspect:

```text
test file
test name
failure
trace
duration
```

Do not hardcode:

```text
28 passed
87% coverage
```

---

# 26. REAL VALIDATION

Validation screen must use actual results.

Backend validation could include:

```text
Ruff
mypy
pytest
Bandit
ESLint
TypeScript
Next.js build
Prettier
```

Only display tools relevant to the project's technology stack.

Example:

Moodle/PHP project should not display mypy unless Python components exist.

---

# 27. REAL OBSERVABILITY

Remove static mock metrics.

Display real persisted/aggregated data:

```text
Agent duration
Pipeline success rate
Average pipeline duration
RAG latency
Model errors
Queue depth
Prompt tokens
Completion tokens
Estimated cost
Infrastructure health
```

If some measurements are not implemented yet:

show:

```text
Not available
```

Do not fabricate values.

---

# 28. REAL HEALTH CHECKS

Infrastructure section must call the backend health endpoint.

Check:

```text
FastAPI
PostgreSQL
Redis
Qdrant
Celery workers
LLM provider if configured
```

Do not always display "Healthy".

---

# 29. SETTINGS MUST BE REAL

Settings page must load and save actual configuration.

Never expose raw secrets back to the browser.

For API keys:

```text
••••••••••••••••
```

Support:

```text
configured
not configured
replace key
remove key
test connection
```

Add real connection testing.

Example:

```text
Test DeepSeek Connection
```

The server validates the key without returning it to browser.

---

# 30. LOADING / EMPTY / ERROR STATES

Every real-data component must have:

```text
loading
success
empty
warning
error
retry
```

Examples:

Projects:

```text
Loading projects...
No projects yet
Could not load projects
Retry
```

RAG:

```text
Index has not been created yet
```

Git:

```text
This directory is not a Git repository
```

Tests:

```text
No test run exists for this project
```

Do not use fake data to avoid empty states.

---

# 31. PIXEL-PERFECT RESPONSIVENESS

The approved desktop design must remain the primary reference.

Verify at least:

```text
1920 × 1080
1600 × 900
1440 × 900
1366 × 768
1280 × 800
1024 × 768
768 × 1024
390 × 844
```

At each breakpoint check:

* sidebar
* page header
* forms
* project cards
* statistics
* pipeline
* file tree
* code viewer
* tabs
* RAG
* Git
* modal
* live logs

No horizontal overflow unless intentional for code/diff content.

---

# 32. VISUAL VALIDATION

Do not claim "pixel perfect" purely because CSS looks similar.

Run the frontend.

Capture/reference the actual rendered pages.

Compare against the approved prototype.

Check:

```text
position
width
height
padding
margin
font size
font weight
line height
border
radius
shadow
colors
alignment
overflow
responsive behaviour
```

Fix visible differences.

Repeat until the application is visually faithful.

---

# 33. DO NOT BREAK EXISTING WORK

Critical rule:

If an existing implementation already works:

PRESERVE IT.

Refactor only where necessary.

Before replacing a service:

1. inspect who calls it
2. inspect tests
3. inspect API contracts
4. inspect database dependencies
5. inspect workers
6. inspect frontend integrations

Do not cause regressions.

---

# 34. DATABASE / API COMPATIBILITY

Do not randomly rename:

* tables
* columns
* endpoints
* request schemas
* response schemas

If a change is necessary:

* provide migration
* maintain compatibility where reasonable
* update all consumers
* update tests
* document it

---

# 35. NO SILENT MOCK FALLBACK

This is critical.

Never implement:

```javascript
try {
    return await api();
} catch {
    return mockData;
}
```

That hides real failures.

Instead:

```text
API failure
→ real error state
→ retry option
```

Mock mode must be explicit.

---

# 36. ERROR REPORTING

Backend errors must use structured responses.

Example:

```json
{
  "error": {
    "code": "PROJECT_PATH_NOT_ACCESSIBLE",
    "message": "The configured backend cannot access this project folder.",
    "details": {
      "path": "...",
      "reason": "Permission denied"
    }
  }
}
```

Frontend displays a useful user message.

---

# 37. TEST THE "CHECK PROJECT FOLDER" ISSUE THOROUGHLY

Add tests for:

### Valid directory

Expected:

```text
valid = true
```

### Missing directory

```text
exists = false
```

### File instead of folder

```text
is_directory = false
```

### Permission denied

Appropriate error.

### Empty project directory

Valid with warning.

### Git project

Git detected.

### Non-Git directory

Valid with warning.

### Windows path

When supported.

Examples:

```text
C:\projects\my-app
D:\Development\project
```

### Linux path

```text
/home/user/projects/app
```

### WSL path where applicable

### Docker mounted path

Correct mapping.

### Path traversal

Reject.

### Symlink escape

Reject where security policy requires.

---

# 38. END-TO-END PROJECT CREATION TEST

Test this entire real workflow:

```text
Open New Project
↓
Enter project path
↓
Click Check Project Folder
↓
Backend validates path
↓
Frontend shows project metadata
↓
Create Project
↓
Database row created
↓
Git status inspected
↓
RAG indexing starts
↓
Real progress shown
↓
Index completes
↓
Project Workspace opens
↓
Actual files displayed
↓
RAG search returns actual code
↓
User submits instruction
↓
Real agent pipeline starts
↓
Live events appear
↓
Files are modified
↓
Tests run
↓
Validation runs
↓
Git commit created
↓
UI updates
```

This workflow is a core acceptance test.

---

# 39. TEST UI PAGE GENERATION

After the system is functional, use this test instruction:

```text
Analyze the existing project's UI design system and create a new
Payments Dashboard page.

Requirements:
- Follow the existing layout and theme exactly.
- Reuse existing components where available.
- KPI cards.
- Payment transactions table.
- Search and filters.
- Payment status badges.
- Refund action with confirmation.
- Loading, empty, error and success states.
- Fully responsive.
- Connect to the real backend APIs.
- Generate tests.
- Run validation.
- Commit the changes.
```

Verify that the agents:

```text
inspect existing project
query RAG
reuse design system
create real page
create real files
connect actual data
run tests
validate
commit
```

---

# 40. DEVELOPMENT WORKFLOW

Work in this exact sequence.

## Step 1 — Audit

Do not modify major code yet.

Understand repository.

Create:

```text
docs/CURRENT_IMPLEMENTATION_AUDIT.md
```

---

## Step 2 — Gap Analysis

Create:

```text
docs/IMPLEMENTATION_GAP_ANALYSIS.md
```

For every feature mark:

```text
COMPLETE
PARTIAL
MOCK
BROKEN
MISSING
```

---

## Step 3 — Implementation Plan

Create:

```text
docs/REAL_DATA_IMPLEMENTATION_PLAN.md
```

Prioritize:

### P0

```text
Check Project Folder
Project creation
Project persistence
Filesystem integration
```

### P1

```text
Real project dashboard
Real project workspace
Real file browser
Real SSE events
```

### P2

```text
RAG
Git
Tests
Validation
```

### P3

```text
Observability
Settings
Architecture runtime status
```

---

# 41. IMPLEMENT IN SMALL SAFE BATCHES

For each batch:

```text
Analyze
↓
Implement
↓
Run tests
↓
Run lint
↓
Run type check
↓
Run build
↓
Inspect UI
↓
Fix
↓
Document
```

Do not implement 100 unrelated files and test only at the end.

---

# 42. AFTER EACH MAJOR FEATURE

Report:

```text
What existed
What was wrong
Root cause
What was changed
Files changed
API changes
Database changes
Tests added
Tests passed
Remaining issues
```

---

# 43. FINAL ACCEPTANCE CRITERIA

Do not call this complete until:

* Existing repository was understood first
* Existing working functionality was preserved
* Approved design is reproduced accurately
* Dashboard uses real data
* New Project uses real APIs
* Check Project Folder works correctly
* Path validation is secure
* Project creation persists to DB
* Stack detection works
* RAG indexing is real
* RAG search is real
* Live workspace uses real events
* Agent statuses are real
* Files tab shows real files
* File contents are real
* Diff works
* Artifacts are real
* Tests are real
* Validation results are real
* Git history is real
* Rollback is real
* Observability uses real metrics
* Infrastructure health is real
* Settings are persisted
* API secrets are protected
* Loading states work
* Empty states work
* Error states work
* Responsive design works
* Production build passes
* Backend tests pass
* Frontend tests pass
* No unintended mock production data remains
* No major console errors exist
* No major backend errors remain

---

# 44. MOST IMPORTANT RULES

## RULE 1

DO NOT START FROM SCRATCH.

Understand and continue the current implementation.

## RULE 2

DO NOT CHANGE THE APPROVED UI DESIGN.

Make the real implementation match it pixel-perfectly.

## RULE 3

DO NOT USE MOCK DATA IN PRODUCTION.

All visible operational data must come from real services.

## RULE 4

FIX "CHECK PROJECT FOLDER" PROPERLY.

Trace frontend → backend → filesystem → Docker/host path mapping.

Do not fake validation.

## RULE 5

DO NOT DESTROY WORKING CODE.

Reuse and extend.

## RULE 6

DO NOT CLAIM SUCCESS WITHOUT TESTING IT.

Run the application and verify the complete workflow.

---

# 45. START NOW

Begin ONLY with repository analysis.

Do the following now:

1. Inspect the complete repository.
2. Read all project documentation.
3. Inspect frontend structure.
4. Inspect backend structure.
5. Inspect database/migrations.
6. Inspect APIs.
7. Inspect agents.
8. Inspect RAG.
9. Inspect filesystem tools.
10. Inspect Git tools.
11. Inspect SSE/event implementation.
12. Inspect project creation flow.
13. Trace "Check Project Folder" from UI to backend.
14. Search for all mock/simulated/hardcoded production data.
15. Compare current real UI against the approved prototype.
16. Create `docs/CURRENT_IMPLEMENTATION_AUDIT.md`.
17. Create `docs/IMPLEMENTATION_GAP_ANALYSIS.md`.
18. Create `docs/REAL_DATA_IMPLEMENTATION_PLAN.md`.

THEN begin implementation with the highest-priority broken feature:

"Check Project Folder"

Do not ask me to repeat information that can be discovered from the repository.

Do not create a new parallel application.

Work on the existing application and bring it to production quality.

````

### One point I would emphasize to the VS Code agent

The **project-folder issue is architectural**, not merely a button bug. In the current prototype, the project path field is simply accepted and then inserted into the workspace when the user clicks Create; there is no real directory check in that flow. :contentReference[oaicite:3]{index=3} :contentReference[oaicite:4]{index=4}

So the agent should not implement something fake like:

```javascript
if (path.length > 3) {
   showSuccess();
}
````

It needs to verify whether the **backend process can actually access that folder**, determine whether you're running locally, through Docker, or eventually from a cloud-hosted backend, and then use the correct filesystem/mount architecture.

Also, the current reference uses browser arrays for projects, agents, files, Git commits, and RAG results.  Those are useful as the approved **visual/interaction specification**, but the production frontend should preserve that UI while sourcing everything from the real backend.
