# AgentForge — Gap Completion Plan

**Date:** 2026-08-12
**Status:** Planned (nothing removed; all existing code retained)
**Source audit:** 2026-08-12 verification pass against the codebase
**Authoritative implementation status:** `docs/IMPLEMENTATION_PLAN.md` (Phases 1–11) and `docs/NEXT_PLAN.md`

---

## 0. Gap Inventory (2026-08-12)

| ID | Gap | Severity | Status |
|----|-----|----------|--------|
| G1 | API-wide rate limiting — only auth endpoints are rate-limited today | Medium | ✅ Implemented (2026-08-12) |
| G2 | `services/sse_broadcaster.py` (in-memory) is unused by the real SSE endpoint (which is DB-replay); file must be retained and integrated | Low | ⬜ Planned |
| G3 | "CI verification gate" is pipeline-internal only; no external hosted-CI integration (no `.github/workflows`) | Medium | ⬜ Planned |
| G4 | No automated tests cover container hardening config (compose + Dockerfiles) | Medium | ✅ Implemented (2026-08-12) |
| G5 | Web ESLint: 90 warnings (documented quality debt) | Low | ✅ Implemented (2026-08-12) — 0 errors / 0 warnings, tsc clean |
| G6 | Roadmap future items not yet in the plan: screenshot-to-UI generation, sandbox execution | Low | ⬜ Planned |
| G7 | Market-verdict follow-ons: PR creation from Git agent; runtime debugging/perf triage (Sentry-Seer-style) | Low | ⬜ Planned |

Constraint: **do not remove any existing file or behavior.** G2 is planned as an
integration, not a deletion.

---

## G1 — API-Wide Rate Limiting

**Current state:** `app/services/rate_limit.py` (Redis fixed-window, fail-open)
is wired only to `auth.py` (login, register, forgot-password, reset-password).
**Implemented 2026-08-12:** `api_rate_limit(scope)` dependency + structured
429 body; applied to instruction submission/cancel, project create/update/
delete, validate-path, rag search/reindex, git rollback, approval decisions,
and tech-lead queries. Config: `RATE_LIMIT_MUTATING_PER_MIN`,
`RATE_LIMIT_IP_PER_MIN`, `RATE_LIMIT_WINDOW_SECONDS` in `app/core/config.py`.
Health/readiness and SSE streams are exempt. Tests:
`tests/test_rate_limit_api.py` (6 tests, all passing).

**Target:** Defense-in-depth rate limits on all mutating tool/agent endpoints,
with per-user and per-IP keys, configurable limits, and graceful 429s.

- [x] Add a reusable FastAPI dependency `enforce_api_rate_limit(scope: str)`
  in `app/services/rate_limit.py` (keep the existing auth helper intact).
- [x] Move rate-limit config into `app/core/config.py` with env-backed defaults
  (e.g. `RATE_LIMIT_DEFAULT_PER_MIN`, `RATE_LIMIT_TOOL_PER_MIN`).
- [x] Apply to mutating endpoints: instruction submission, tool-triggering
  endpoints (rag reindex, git rollback, run_tests/run_build/run_command paths),
  approval decisions, and tech-lead queries.
- [x] Exempt health/readiness and SSE streams (no limit or high ceiling).
- [x] Return `429` with `Retry-After` and a structured `{status:"rate_limited",
  retry_after_seconds}` body; keep fail-open on Redis outage.
- [x] Tests: `tests/test_rate_limit_api.py` — per-user limits, per-IP limits,
  exemption list, 429 body shape, fail-open behavior (Redis unavailable).

**Acceptance:** mutating endpoints return 429 beyond the configured ceiling;
auth behavior is unchanged; full API suite passes. ✅ **75 passed** (69
existing + 6 new).

---

## G2 — Integrate (Retain) the In-Memory SSE Broadcaster

**Current state:** `services/sse_broadcaster.py` provides per-project
`asyncio.Queue` fan-out but the live endpoint (`sse.py`) replays
`InstructionEvent` rows from Postgres and then polls for new rows.

**Target:** Keep the file. Use the broadcaster as an **in-process fast-path**
so events produced inside the API process are delivered immediately, while
Postgres remains the durable source of truth (replay + `Last-Event-ID`).

- [ ] In `sse.py`, subscribe the client queue to the broadcaster on connect.
- [ ] Publish to the broadcaster wherever `append_instruction_event` succeeds
  in the API process (single helper, e.g. `notify_project(project_id, event)`).
- [ ] Keep the DB polling loop as the fallback: on broadcaster miss (events
  produced by the worker process), poll `InstructionEvent` as today; dedupe by
  event `id` so fast-path and replay never double-deliver.
- [ ] Tests: `tests/test_sse_fastpath.py` — in-process event is delivered
  without DB polling latency; worker-produced event still arrives via replay;
  no duplicate delivery when both paths fire.
- [ ] Update `IMPLEMENTATION_PLAN.md` §3.1 / Phase 8 wording to describe the
  hybrid (DB-replay + in-process fast-path) once implemented.

**Acceptance:** no file removed; SSE latency for API-process events drops;
replay/durability behavior is unchanged; existing SSE tests pass.

---

## G3 — External CI Verification Gate

**Current state:** `git_agent.py` blocks Git changes unless
`verification_status == "PASSED"` when `ci_gate_enabled` is set — an
in-pipeline gate only. No `.github/workflows` exists.

**Target:** Let repositories enforce the same evidence externally: a
generated workflow that runs the verification suite and fails the build when
AgentForge provenance/verification evidence is missing or digest-mismatched.

- [ ] Add `GET /projects/{id}/verification/latest` returning the latest
  `VerificationRun` summary (category, status, digests, excerpt) for an owned
  project.
- [ ] Add a templated workflow file, e.g.
  `infrastructure/ci/agentforge-ci-gate.yml` (GitHub Actions), that:
  - checks out the repo,
  - runs tests/lint/build (pytest, ruff, eslint/tsc placeholders from the
    project config),
  - compares the resulting status/digest with the API's stored evidence,
  - fails the job on mismatch (provenance tampering / stale evidence).
- [ ] Document wiring in `README.md` (env vars: API URL, token, project id).
- [ ] Tests: `tests/test_ci_gate_contract.py` — endpoint auth + response
  shape; digest-mismatch detection logic unit-tested.
- [ ] Update `IMPLEMENTATION_PLAN.md` §5.1 wording: "CI verification gates"
  = in-pipeline gate today, external hosted-CI gate shipped by this item.

**Acceptance:** a repo can enforce AgentForge verification evidence in
GitHub Actions; the in-pipeline gate remains the default.

---

## G4 — Container Hardening Tests

**Current state:** compose + Dockerfiles implement non-root users, `read_only`,
`cap_drop: ALL`, `no-new-privileges`, `init`, readiness healthchecks, 12 MB
body limit, security headers — but nothing asserts this automatically.
**Implemented 2026-08-12:** `tests/test_hardening_config.py` (11 tests, all
passing) asserts compose hardening for `api`/`worker`/`web`, the single root
exception (`api-data-init`), non-root `USER` before the final CMD/ENTRYPOINT
in both Dockerfiles, and the 12 MB body limit + security-header wiring.

- [x] Add `tests/test_hardening_config.py` (pure config parsing, no docker
  required) asserting for `infrastructure/docker-compose.yml`:
  - `api`, `worker`, `web` services set `read_only: true`,
    `cap_drop: ["ALL"]`, `security_opt: ["no-new-privileges:true"]`,
    `init: true`, and a healthcheck.
  - runtime services do not run as `user: "0:0"` (the one-shot
    `api-data-init` chown container is the documented exception).
- [x] Parse `apps/api/Dockerfile` and `apps/web/Dockerfile` and assert a
  non-root `USER` is set before the final `CMD`/`ENTRYPOINT`.
- [x] Assert `http_security.py` defaults: `max_body_bytes` ≥ 12 MB,
  security-header middleware present in `main.py`.
- [ ] Optional smoke test (tagged `docker`): build and run the API image,
  assert process UID != 0 and filesystem is read-only. *(deferred — needs a
  Docker daemon in CI; the static config tests already enforce the claims)*

**Acceptance:** `pytest tests/test_hardening_config.py` passes on CI and
locally; the hardening claims in Phase 11 become test-enforced. ✅ **11/11
passing** locally.

---

## G5 — Web ESLint Warning Cleanup (Quality Debt)

**Current state:** `eslint` passes with 0 errors, 90 warnings (recorded in
`IMPLEMENTATION_PLAN.md` Phase 10 evidence).
**Implemented 2026-08-12:** warnings reduced **90 → 0** (eslint clean, 0
errors / 0 warnings) with `tsc --noEmit` also clean. All 54 `no-explicit-any`
converted to typed interfaces or `unknown`; hydration guards refactored to
`useSyncExternalStore` (theme-provider, theme-toggle, pagination, app-shell);
data-fetch effects rewritten to async-await patterns with cancellation;
render-time state adjustment for prop-sync (ai-fix-modal, FileTreeNode,
settings panel); unused vars/imports removed; `<img>` → `next/image`;
`window.location.href` → router; three complex tab-activation effects carry
justified `eslint-disable` comments.

- [x] Run `npx eslint --format stylish` in `apps/web` and bucket warnings by
  rule (unused vars, `any`, exhaustiveness, hook deps, etc.).
- [x] Fix each bucket in the affected files (prefer typed helpers over
  `eslint-disable`; only disable with a justification comment).
- [x] Re-run `npx eslint` — target: 0 errors and a reduced warning count
  (goal ≤ 10); update the Phase 10 evidence note in `IMPLEMENTATION_PLAN.md`.
- [x] Run `tsc`/`npm run check` to confirm no type regressions.

**Acceptance:** warning count drops to ≤ 10 with no new errors; TS check
still passes. ✅ **0 errors / 0 warnings**; `tsc --noEmit` clean; web jest
suite re-run to confirm (in progress at write time).

---

## G6 — Roadmap Future Items (add to plan, framed per market verdict)

**Current state:** `plan.md` lists screenshot-to-UI generation and sandbox
execution as future work; they are not in `IMPLEMENTATION_PLAN.md`.

**Target:** add them to `IMPLEMENTATION_PLAN.md` as Phase 12 items, framed
per §5 (market verdict) — these capabilities exist in Cursor/Lovable/v0
(screenshot-to-UI) and Codespaces/CI sandboxes (execution), so they are
adoptions/completions, not novel predictions.

- [ ] **Phase 12a — Screenshot-to-UI generation.** UI/UX Agent accepts an
  image (screenshot/Figma export), uses the vision model path
  (`visual_analysis.py`) to produce a UI spec, then Frontend Agent generates
  code. Market framing: Cursor, Lovable, v0 already ship this; AgentForge
  completes it inside its governed pipeline with approval gates.
- [ ] **Phase 12b — Cloud sandbox execution.** Extend the Tool Gateway so
  tools can target a disposable cloud sandbox (container) instead of only the
  local agent, for projects with no online workstation. Market framing:
  Codespaces-style remote execution is standard; AgentForge adds its
  approval/evidence layer on top.
- [ ] Add Phase 12 sections to `IMPLEMENTATION_PLAN.md` with explicit
  "market-standard, adopt" framing and acceptance criteria.

**Acceptance:** `IMPLEMENTATION_PLAN.md` contains Phase 12a/12b with clear
scope, market framing, and no over-claiming.

---

## G7 — Market-Verdict Follow-ons

**Current state:** documented in `IMPLEMENTATION_PLAN.md` §5.1 as follow-ons
(Git agent branches + commits today; runtime triage not yet built).

- [ ] **G7a — PR creation.** Extend `git_agent.py` (or add
  `pull_request.py`) to create a PR from the isolated `agent/{instruction_id}`
  branch against the default branch, via a new `create_pull_request` local
  tool (GitHub CLI) gated by the existing approval/policy flow. UI: "Create
  PR" action on the GIT tab. Market framing: GitHub Copilot agents and Cursor
  already create PRs; this is an adoption, not a prediction.
- [ ] **G7b — Runtime debugging/perf triage.** Add a
  `diagnostics`-category verification tool that captures bounded runtime
  evidence (test timings, build output, profiler summary) and feeds it to the
  tech-lead assistant for triage answers. Market framing: Sentry Seer already
  does AI-driven debugging/perf investigation; AgentForge scopes this to the
  repository-side evidence it already stores.

**Acceptance:** PR creation works end-to-end behind approval gates; tech-lead
triage answers include runtime evidence; both items framed as market-standard
adoptions in the docs.

---

## Completion Order & Verification

1. **G1 + G4** (platform hardening, independent, no cross-dependency).
2. **G5** (quality debt, independent).
3. **G2** (SSE fast-path, touches `sse.py` + event emission).
4. **G3** (external CI gate, builds on verification evidence).
5. **G6 + G7** (feature work, largest; depend on all of the above).

Per-item verification: run the added tests, then the full suites —
`make test` (API 69 + new), `make lint`, web `npm run check`, and re-check
the deploy logs only if behavior changes at runtime. No files are removed;
G2's broadcaster is retained and integrated.

Docs to refresh as items land: `IMPLEMENTATION_PLAN.md` (Phase 8 wording for
G2, Phase 11 evidence for G4, new Phase 12 for G6, §5.1 wording for G3/G7),
`README.md` (CI gate wiring for G3), `NEXT_PLAN.md` (status table).
