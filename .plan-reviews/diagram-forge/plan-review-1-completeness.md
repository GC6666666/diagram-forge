# Plan Review: Diagram Forge -- Completeness

**Reviewer:** Claude Code
**Date:** 2026-03-22
**Docs Reviewed:** design-doc.md, api.md, data.md, ux.md, scale.md, security.md, integration.md

---

## Cross-Doc Inconsistencies (Foundations)

Before checking task completeness, three foundational inconsistencies must be resolved, as they affect every downstream implementation task.

- **FINDING:** The API endpoint naming is inconsistent across docs.
  - `integration.md` uses `POST /v1/diagram`
  - `design-doc.md` and `api.md` use `POST /v1/generate/text` (and `/generate/image`, `/generate/voice`)
  - `ux.md` uses `POST /v1/generate` with `input_type` field
  - Severity: must-fix
  - Suggested addition: Standardize on one endpoint naming convention before Phase 1 begins. Recommended: `POST /v1/generate/text`, `POST /v1/generate/image`, `POST /v1/generate/voice` (per `api.md`) as it provides cleaner routing and separate OpenAPI schemas per modality.

- **FINDING:** The API authentication header format is inconsistent.
  - `security.md` specifies `X-API-Key` header
  - `api.md` specifies `Authorization: Bearer <token>` header
  - `ux.md` CLI examples use neither (relies on config/env), and the curl examples reference Bearer token in API developer section
  - Severity: must-fix
  - Suggested addition: Pick one. Recommended: `Authorization: Bearer <token>` (per `api.md`) as it is more standard and aligns with OpenAPI security scheme definition.

- **FINDING:** The pipeline processing model is ambiguous.
  - `design-doc.md` says "stateless, no sessions" and `api.md` says "all endpoints are version-prefixed" with sync responses
  - `api.md` says `POST /v1/generate` returns `202 Accepted` for async jobs and clients should poll
  - `integration.md` Step 5 says "Request timeout: 30s" implying sync processing
  - `ux.md` API section says "async `POST /v1/generate` + `GET /v1/status/{id}` polling"
  - Severity: must-fix
  - Suggested addition: Clarify that Phase 1 is sync (in-process job execution with background thread) and Phase 7 introduces proper async queueing. Make this distinction explicit in the phased plan.

- **FINDING:** Claude model versioning is inconsistent across docs.
  - `design-doc.md`: "Claude Sonnet 4.5"
  - `api.md`: `claude-3-5-sonnet-20241022`
  - `integration.md`: `claude-3-5-sonnet-20241022`
  - `scale.md`: "Claude Sonnet 4/4.5"
  - `security.md`: pin range `anthropic>=0.25.0,<1.0.0`
  - Severity: should-fix
  - Suggested addition: Define a `CLAUDE_MODEL_VERSION` environment variable with a pinned default (e.g., `claude-3-5-sonnet-20241022`). Document that model selection is version-pinned per environment (production vs. staging) rather than hardcoded.

---

## 1. Missing Infrastructure Setup

- **FINDING:** CI/CD pipeline is not a defined task.
  - `security.md` references `pip-audit` in Dockerfile and Trivy/Grype in CI, plus `dependabot`/`renovate` for dependency updates. `integration.md` references `scripts/lint.sh` and `scripts/test.sh` but there is no CI configuration file or workflow definition.
  - Severity: must-fix
  - Suggested addition: Add explicit Phase 0.5 task: "Define CI/CD pipeline (GitHub Actions or equivalent): lint + test + pip-audit + Trivy image scan + dependency check. Gate on all passing." Break into sub-tasks: `ci.yml` workflow file, Docker image build + push, dependency vulnerability scanning.

- **FINDING:** The phased plan omits project scaffolding as a distinct Phase 0.
  - `integration.md` Phase 1 says "Project scaffold (FastAPI, models, exporters)" as the first deliverable, but this conflates infrastructure setup with feature development. Scaffolding is a prerequisite that should be clearly scoped.
  - Severity: must-fix
  - Suggested addition: Add explicit Phase 0: "Project scaffold" with sub-tasks: `pyproject.toml` setup, `Dockerfile` (per `security.md` non-root hardening requirements), `docker-compose.yml`, `.env.example` (listing all env vars from `security.md` Section "Environment Variables"), logging configuration (`configs/logging.yaml`), static analysis config (ruff or flake8), pre-commit hooks. This must be completed before any Phase 1 code is written.

- **FINDING:** Environment variable names are not standardized.
  - `security.md` defines `DIAGRAM_FORGE_API_KEYS`; `data.md` defines `DF_DATA_ROOT`, `DF_CONFIG_DIR`, `DF_API_KEY`, `DF_OUTPUT_TTL_SECONDS`, `DF_LOG_RETENTION_DAYS`, `DF_MAX_INPUT_SIZE_BYTES`, `DF_MAX_TEXT_CHARS`; `ux.md` CLI section uses `DIAGRAM_FORGE_API_KEY`; `data.md` Docker example uses `DF_DATA_ROOT` and `DF_API_KEY`; `security.md` uses `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.
  - No single canonical env var naming convention is established.
  - Severity: should-fix
  - Suggested addition: Define a canonical env var prefix (`DF_` for all Diagram Forge config, `ANTHROPIC_` and `OPENAI_` for provider keys). Add a `config.py` / pydantic-settings module that enumerates every env var with type, default, and validation. This should be the first file created in Phase 0.

- **FINDING:** Feature flags for phased rollout are not defined.
  - The plan has 7 phases. In production, you may want to deploy Phase 1 code while Phase 2 code is in progress. There is no feature flag strategy to gate unimplemented endpoints.
  - Severity: should-fix
  - Suggested addition: Add Phase 0 task: "Define feature flags for Phase-gated endpoints." For example: `FEATURE_VOICE_INPUT`, `FEATURE_IMAGE_INPUT`, `FEATURE_ITERATION`, `FEATURE_MULTI_FORMAT_EXPORT`. Unimplemented features return `501 Not Implemented` with a helpful message. Implement via a `features.py` module.

- **FINDING:** `pyproject.toml` and dependency pinning are not explicit tasks.
  - Dependencies are listed in prose across `design-doc.md`, `security.md`, and `scale.md` with slight version discrepancies (e.g., `anthropic>=0.20` in design-doc.md vs `anthropic>=0.40` in scale.md).
  - Severity: should-fix
  - Suggested addition: Add explicit Phase 0 task: "Create `pyproject.toml` with all pinned dependencies. Verify version consistency across all design docs."

---

## 2. Missing Data Migrations / Schema Changes

- **FINDING:** The internal representation design (DiagramModel) is deferred but its eventual schema changes have no migration strategy.
  - `integration.md` says internal representation is deferred. `data.md` says "v1 the internal representation IS the Excalidraw JSON itself." But `integration.md` already defines a `DiagramModel` Pydantic schema with typed elements. When these models change, there is no migration path.
  - Severity: should-fix
  - Suggested addition: Add a "Schema Versioning" section to the plan: define that `DiagramModel` gets a `schema_version: int` field, that all exports are versioned, and that migration tasks are tracked separately from feature phases. Alternatively, note that schema changes in Phase 2+ will be backward-compatible only (adding optional fields, never breaking existing ones).

- **FINDING:** Jobs.jsonl compaction is described but not scoped as an implementation task.
  - `data.md` describes the compaction process ("a separate compaction process truncates the log to the last N entries or entries within the TTL window") but provides no implementation details and no explicit task to build it.
  - Severity: should-fix
  - Suggested addition: Add task to Phase 1 or Phase 2: "Implement `jobs.jsonl` compaction worker: truncate log to last 10,000 entries or entries from the last 7 days, whichever is larger. Run as a daily cron or startup task."

- **FINDING:** SQLite for API key management (mentioned in `data.md` for v2) has no migration path from env-var keys to DB-backed keys.
  - `data.md` says "v2+ (Out of Scope for v1): SQLite-backed key store with CRUD API". The migration from env vars to DB is uncharted.
  - Severity: should-fix (deferred)
  - Suggested addition: At minimum, add a note in the Phase 7 tasks that v1.1 will need a migration from `DIAGRAM_FORGE_API_KEYS` env var format to a JSON config file, and v2 will need a SQLite migration task. Document the upgrade path.

---

## 3. Missing Test Tasks

- **FINDING:** Phase 1 says "Basic unit tests" but does not define what those are.
  - This is too coarse-grained to be actionable. "Basic unit tests" could mean anything from 5 tests to 50.
  - Severity: must-fix
  - Suggested addition: Break Phase 1 test tasks into specific suites:
    - `tests/unit/test_models.py`: DiagramModel validation, element creation, connection validation, bounds checking.
    - `tests/unit/test_excalidraw_exporter.py`: Excalidraw JSON roundtrip, element mapping correctness, schema conformance.
    - `tests/unit/test_text_pipeline.py`: Input validation (empty, too long, whitespace), pipeline orchestration.
    - Define a minimum coverage target: Phase 1 must reach 70% line coverage before Phase 2 begins.

- **FINDING:** Phase 2 says "Full unit + integration test suite (>=80% coverage)" but no specific integration test tasks are listed.
  - Severity: must-fix
  - Suggested addition: Phase 2 test tasks should include:
    - `tests/integration/test_text_pipeline.py`: End-to-end text → all three formats, all three diagram types.
    - `tests/integration/test_drawio_exporter.py`: Excalidraw JSON → Draw.io XML → validate output opens in diagrams.net.
    - `tests/integration/test_svg_exporter.py`: Excalidraw JSON → SVG → validate well-formed SVG, check element IDs are present.
    - `tests/unit/test_json_repair.py`: Malformed JSON repair scenarios (trailing commas, JS comments, block comments, markdown fences).
    - `tests/unit/test_type_inference.py`: Keyword detection for each diagram type, confidence thresholds.

- **FINDING:** End-to-end tests are entirely absent from the phased plan.
  - No e2e tests are mentioned anywhere in the 7-phase plan. The project structure in `integration.md` has no e2e test directory.
  - Severity: must-fix
  - Suggested addition: Add Phase 2 or Phase 7 task: "Implement e2e tests (Playwright or pytest + httpx) covering critical user flows:
    1. Text input → diagram download (all 3 formats)
    2. Image upload → diagram download
    3. Voice upload → diagram download
    4. Iteration: image + instruction → modified diagram
    5. Error flows: invalid API key, rate limit, oversized input
    6. CLI: `df generate --text ...` → file output
    Run e2e tests in CI on every PR."

- **FINDING:** Whisper transcription caching is not tested.
  - `scale.md` defines a Whisper cache (SHA256 audio bytes → transcript). The cache get/set and TTL expiry are not covered by any test task.
  - Severity: should-fix
  - Suggested addition: Add Phase 3 test task: "Test Whisper cache: verify cache hit for identical audio bytes, verify cache miss for different audio, verify TTL expiry cleanup."

- **FINDING:** WebSocket SSE progress streaming is not tested.
  - `api.md` defines SSE event types (`queued`, `stage_start`, `stage_progress`, `stage_complete`, `completed`, `failed`). No test task covers this.
  - Severity: should-fix
  - Suggested addition: Add test task to Phase 2 or Phase 4: "Test WebSocket SSE stream: connect to `ws://.../ws/jobs/{id}?api_key=...`, verify correct event sequence, verify stream closes on job completion, verify reconnection logic."

---

## 4. Missing Documentation Updates

- **FINDING:** No documentation task is listed in any phase.
  - The project structure in `integration.md` mentions `README.md` and `CHANGELOG.md` but there is no task to create them. The security checklist references a "privacy disclosure" and "PRIVACY.md" but these are not scoped as implementation tasks.
  - Severity: should-fix
  - Suggested addition: Add Phase 0 task: "Create `README.md` covering installation, configuration (env vars), quick-start examples, architecture overview, and link to `/docs`." Add Phase 1 task: "Write `PRIVACY.md` covering data retention (24h TTL), which APIs process data (Anthropic Claude API, OpenAI Whisper API), and links to both privacy policies, as required by `security.md` data retention enforcement section."

- **FINDING:** The security checklist in `security.md` (Section "Security Checklist Before First Deploy") is a checklist of 10 items but is not mapped to implementation tasks.
  - Several checklist items are implementation tasks that do not appear in the phased plan: "Temp cleanup worker is verified to run on startup" (cleanup worker), "Rate limiting is enabled and tested" (already partially planned), "Privacy disclosure is visible to users" (see above).
  - Severity: should-fix
  - Suggested addition: Map each security checklist item to a specific phase/task. For example: temp cleanup worker verification = Phase 1 or Phase 2 task with a specific test. Privacy disclosure = Phase 1 task. Rate limit testing = Phase 2 integration test.

- **FINDING:** `integration.md` references a `CHANGELOG.md` for prompt versions but no task to create it.
  - Severity: should-fix
  - Suggested addition: Add Phase 2 task: "Create `src/ai/prompts/CHANGELOG.md` tracking prompt version changes per `integration.md` Prompt Versioning section."

---

## 5. Missing Error Handling / Rollback Procedures

- **FINDING:** The phased plan has no rollback or recovery procedure for failed deployments.
  - If a new version of prompts or a code change causes degraded output quality in production, there is no documented rollback procedure.
  - Severity: should-fix
  - Suggested addition: Add Phase 7 task: "Define rollback procedure: if production error rate exceeds 5% or output quality drops (measured by manual review sample), revert to previous Docker image tag. Document the rollback runbook: `docker pull diagram-forge:<previous-tag>` and restart. Add a canary deployment task: route 5% of traffic to new version, monitor for 10 minutes, promote or rollback."

- **FINDING:** Iteration completeness check (retry-once behavior) is not a tracked implementation task.
  - `integration.md` describes a "completeness check" that verifies all original elements are preserved during iteration, retrying once with a stricter prompt. This is a non-trivial implementation with error code `INCOMPLETE_ITERATION`.
  - Severity: should-fix
  - Suggested addition: Phase 5 task: "Implement iteration completeness check: after generating modified diagram, compare element IDs against original. If missing: retry once with strict preservation prompt. If still missing: return `INCOMPLETE_ITERATION` error with `retryable: true`. Add unit tests for completeness check."

- **FINDING:** The circuit breaker for Claude API is well-specified but the circuit breaker for Whisper is not defined as an implementation task.
  - `scale.md` defines circuit breaker configuration for Claude but not for Whisper. `security.md` mentions "Claude API data handling" but not Whisper-specific data handling concerns.
  - Severity: should-fix
  - Suggested addition: Phase 2 or Phase 3 task: "Implement Whisper circuit breaker: same configuration as Claude (5 failures, 30s recovery, 3 half-open probes). Add monitoring alert when Whisper circuit is open for >2 minutes."

---

## 6. Implicit Dependencies Not Called Out as Tasks

- **FINDING:** Prompt example generation is an implicit dependency with no task.
  - `integration.md` says each diagram type includes "1-2 examples in the prompt as structured JSON matching the expected output." `integration.md` also mentions `scripts/generate_examples.py` for "Tool to generate new prompt examples from Claude." But there is no task to create the initial set of examples for Phase 1. Without examples, Claude's output quality cannot reach the >70% structural accuracy entry criteria.
  - Severity: must-fix
  - Suggested addition: Phase 1 must include sub-task: "Generate initial prompt examples: create 2 example JSON pairs per diagram type (architecture, sequence, flowchart) covering typical inputs. Store in `src/ai/prompts/examples/{diagram_type}/`. Validate each example by running the pipeline and verifying Excalidraw JSON output. These examples are the primary determinant of output quality."

- **FINDING:** JSON repair function is referenced but not scoped as a task.
  - `integration.md` and `data.md` describe JSON repair logic (stripping markdown fences, removing trailing commas, removing JS comments). `integration.md` even shows `repair_json()` pseudocode. But there is no task to implement and test the JSON repair function as a standalone module.
  - Severity: should-fix
  - Suggested addition: Phase 1 task: "Implement `src/ai/parser.py`: JSON repair (`repair_json()`) + parse attempt + Pydantic validation + retry-on-failure. Test with 20+ malformed JSON variants covering: trailing commas, JS single-line comments, block comments, markdown code fences (```json ... ```), incomplete JSON, extra fields, missing required fields."

- **FINDING:** The `@excalidraw/utils` `export_to_svg()` is referenced in `data.md` as a generation strategy but the `integration.md` SVG exporter is a hand-written editable SVG generator, not using that library.
  - `data.md` Section "SVG Generation Strategy" says: "Use `@excalidraw/utils` `export_to_svg()` directly on the Excalidraw elements. No intermediate transformation."
  - `integration.md` Section "Exporter 3: SVG" says: "Design decision: Generate **editable SVG** (semantic SVG with grouped elements, text, and arrows as proper SVG elements)."
  - These are mutually exclusive approaches. The editable SVG requires hand-rolling an SVG exporter; the data.md approach requires an npm package that must be callable from Python.
  - Severity: must-fix
  - Suggested addition: Resolve this in the architecture decision section. If using `@excalidraw/utils`, add a Node.js sidecar or subprocess call. If hand-rolling editable SVG, remove the `@excalidraw/utils` dependency reference. Add a Phase 2 task for SVG exporter that matches the chosen approach.

- **FINDING:** The `idempotency_key` deduplication store is an implicit dependency.
  - `api.md` and `ux.md` both reference idempotency key deduplication ("server stores `(idempotency_key, api_key)` -> `job_id` in a TTL store"). `data.md` does not describe this store. No implementation is specified and no task covers it.
  - Severity: should-fix
  - Suggested addition: Phase 1 task: "Implement idempotency store: in-memory dict with `(idempotency_key, api_key)` -> `(job_id, response_body)` mapping, 24h TTL. For Phase 7 multi-container: document that Redis replaces this in-memory store."

---

## 7. Tasks Too Coarse-Grained to Be Actionable

- **FINDING:** Every phase in the phased plan is too coarse-grained for execution.
  - Example: Phase 1 has 5 deliverables collapsed into one line: "Project scaffold (FastAPI, models, exporters), TextPipeline with hardcoded prompts, ExcalidrawExporter only, Basic unit tests, Dockerfile."
  - A developer cannot confidently estimate work or track progress from this.
  - Severity: must-fix
  - Suggested addition: Reframe each phase into a task list with estimated effort labels. For Phase 1, expand to:
    1. Create `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.env.example` (Phase 0)
    2. Implement `config.py` with pydantic-settings (all env vars)
    3. Implement `DiagramModel` and element classes in `src/diagram_forge/models/`
    4. Implement `ExcalidrawExporter` in `src/exporters/`
    5. Implement `TextPipeline` with hardcoded prompts (no PromptRegistry yet)
    6. Implement `POST /v1/generate/text` endpoint with input validation
    7. Implement structured JSON logging
    8. Write Phase 1 unit tests (70% coverage gate)
    9. Generate initial prompt examples per diagram type
    10. End-to-end manual validation: text → all 3 diagram types → Excalidraw JSON

- **FINDING:** Phase 2 lumps "DrawioExporter, SVGExporter, PromptRegistry, Example fixtures, JSON repair, Full test suite" into one phase.
  - Any single one of these is a multi-day task. They should be tracked independently.
  - Severity: must-fix
  - Suggested addition: Split Phase 2 into sub-tasks with clear ownership and dependencies. For example, DrawioExporter and SVGExporter can be developed in parallel once ExcalidrawExporter is done and the element model is stable. JSON repair is a prerequisite for all exporters.

- **FINDING:** Phase 7 says "Operational Hardening" with 7 deliverables listed but no sub-tasks.
  - "Rate limiting with API key management, Circuit breaker with AI provider, Health/ready endpoints, Structured logging + request tracing, Cost monitoring, Staging environment" -- each of these is a substantial task.
  - Severity: should-fix
  - Suggested addition: Break Phase 7 into: rate limiter implementation (token bucket, headers), circuit breaker implementation (pybreaker config), health/ready endpoints (with dependency checks), Prometheus metrics instrumentation, alerting rules definition, staging environment setup, canary deployment procedure.

---

## Summary

| # | Category | Severity | Count |
|---|----------|----------|-------|
| 1 | Infrastructure setup | must-fix | 5 |
| 2 | Data migrations/schema | should-fix | 3 |
| 3 | Test tasks | must-fix | 5 |
| 4 | Documentation updates | should-fix | 3 |
| 5 | Error handling/rollback | should-fix | 3 |
| 6 | Implicit dependencies | must-fix | 4 |
| 7 | Coarse-grained tasks | must-fix | 3 |
| -- | Cross-doc inconsistencies | must-fix | 4 |

**Total findings: 30**

**Must-fix (before Phase 1 begins):** 14
- Resolve the 4 cross-doc inconsistencies (endpoint naming, auth header, sync/async model, Claude version)
- Define Phase 0 project scaffold as explicit tasks
- Define CI/CD pipeline
- Break Phase 1 into actionable sub-tasks (especially prompt examples, JSON repair, idempotency store)
- Add e2e test coverage task
- Add Phase 2 sub-tasks
- Clarify SVG exporter approach (data.md vs. integration.md conflict)

**Should-fix (before or during implementation):** 16
- Standardize env var naming convention
- Add feature flags for phased rollout
- Create schema versioning strategy
- Define test tasks for Whisper cache, WebSocket SSE, circuit breaker
- Add documentation tasks (README, PRIVACY, CHANGELOG)
- Add rollback/canary deployment procedure
- Break Phase 2 and Phase 7 into sub-tasks

---

*This review covers completeness against the stated criteria. It does not evaluate the technical soundness of individual design decisions, which would require separate architectural review.*
