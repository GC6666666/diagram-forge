# Plan Review: Diagram Forge -- Sequencing Analysis

Cross-referenced: design-doc.md, integration.md, scale.md, api.md, security.md, data.md, ux.md.

---

## Critical Path

Longest serial chain: **P1 -> P2 -> P5 -> P6** (4 phases).
Second longest: **P1 -> P2 -> P3 -> P4 -> P5 -> P6** (6 phases) if Phases 3 and 4 are done sequentially rather than in parallel.

---

## MUST-FIX: Sequencing Issues

### FINDING: Concurrency primitives (semaphores) deferred to Phase 7
Severity: must-fix

The scale design specifies `GLOBAL_SEMAPHORE` (max 50 concurrent), `CLAUDE_SEMAPHORE` (max 20), and `WHISPER_SEMAPHORE` (max 5) as foundational concurrency infrastructure to prevent any single request burst from exhausting AI provider capacity.

The phased plan defers semaphores to Phase 7 ("Operational hardening").

**Impact if deferred:** A burst of requests can exhaust the Claude API rate limit within seconds, causing cascading 429s and 500s. Without semaphores, there is no back-pressure mechanism. The `uvicorn --limit-concurrency 50` flag partially mitigates this but does not enforce per-API-key fairness or per-modality concurrency budgets.

**Suggested reorder:** Move semaphore implementation to Phase 1. Add as part of the FastAPI skeleton, alongside API auth.

---

### FINDING: Rate limiting deferred to Phase 7
Severity: must-fix

The scale design, security design, and API design all specify rate limiting as a first-class protection mechanism:
- Scale: 30 req/min per IP (unauthenticated), 100 req/min per API key (authenticated)
- Security: 10 req/min per key, 200 req/hr per key
- API: Token bucket per key with configurable tiers (free/pro/enterprise)

None of these appear in any phase's deliverable list. The only mention is "Rate limiting with API key management" in Phase 7 (integration.md) and "Operational hardening" in Phase 7 (design-doc.md).

**Impact if deferred:** The Phase 1 API key auth layer will validate keys but never enforce per-key quotas. Any authenticated user can make unlimited requests, directly draining the Claude API budget. The security design threat model explicitly lists "Free-tier abuse" as a threat.

**Suggested reorder:** Rate limiting belongs in Phase 1, not Phase 7. Implement per-IP sliding-window (30/min) for unauthenticated requests and per-key token bucket (100/min) for authenticated requests alongside the API key middleware.

---

### FINDING: Circuit breaker deferred to Phase 7
Severity: must-fix

The scale design specifies circuit breakers on both Claude API (5 consecutive failures, 50% error rate over 60s, 30s recovery) and Whisper API. The retry strategy for 429s is explicitly defined. This is foundational infrastructure -- a single Claude API outage causes 100% of in-flight requests to fail and retry indefinitely without a circuit breaker.

The phased plan defers circuit breakers to Phase 7 ("Circuit breaker with AI provider").

**Impact if deferred:** During a Claude API outage, all Phase 1-6 requests will retry 4 times with escalating backoff (5s + jitter, 15s + jitter) per the retry strategy, consuming API quota with no recovery benefit. The circuit breaker should trip after 5 failures and fail-fast.

**Suggested reorder:** Move circuit breaker implementation to Phase 1. Implement alongside API client initialization.

**Hidden dependency:** The circuit breaker must protect Whisper (used in Phase 3 Voice), not only Claude. The scale design includes both but the phased plan only mentions "Claude API circuit breaker" in Phase 7. Phase 3 (Voice) does not mention circuit breaker at all, yet it depends on Whisper being protected.

---

### FINDING: Health and readiness endpoints deferred to Phase 7
Severity: must-fix

The scale design exposes `/health` and `/ready` endpoints with semaphore availability, circuit breaker state, and dependency checks. The data design includes a detailed `/health` response schema with disk space, active jobs, and uptime. The API design defines both endpoints. The Docker healthcheck in the data design uses `curl -f http://localhost:8000/health` for container orchestration.

None of these appear as Phase 1-6 deliverables. Phase 7 (integration.md) lists "Health/ready endpoints" as a deliverable.

**Impact if deferred:** Kubernetes cannot perform rolling deployments or liveness checks without `/health` and `/ready`. The Docker container healthcheck will always report healthy (or require a custom TCP check), making deployment orchestration unreliable from the start.

**Suggested reorder:** Implement `/health` and `/ready` in Phase 1 as part of the FastAPI skeleton. The readiness check can start simple (just "ok") and gain dependency checks later.

---

## SHOULD-FIX: Hidden Dependencies

### FINDING: Input validation (magic bytes, dimension checks) missing from all phases
Severity: should-fix

The security design specifies magic-byte validation for images (PNG `89 50 4E 47...`, JPEG `FF D8 FF`, WebP `52 49 46 46...57 45 42 50`) and audio (MP3 `49 44 33`, WAV `52 49 46 46...57 41 56 45`). Image dimension checks (PIL decode, reject >4096x4096) and audio duration checks (mutagen, reject >60s) are explicitly defined. This is the first line of defense against file-based exploits.

The phased plan does not list input validation as a deliverable in any phase. The integration design mentions "Input validation layer" in Phase 2, but the security design's magic-byte requirements apply to Phase 1 images and audio as well.

**Suggested reorder:** Add input validation as a Phase 1 deliverable. The FastAPI skeleton in Phase 1 should include `UploadFile` size enforcement and content-type checks at minimum. Magic-byte validation and dimension probing belong in Phase 2 alongside the other validation hardening.

---

### FINDING: Temp file cleanup (24h TTL) missing from all phases
Severity: should-fix

The data design specifies a background cleanup process for temporary files with a 24h TTL (enforced via `mtime` checks every 5-10 minutes). The security design explicitly requires this for data retention compliance. The PRD mandates 24h TTL.

The phased plan never mentions the temp file cleanup worker as a deliverable.

**Suggested reorder:** Add temp file cleanup as a Phase 1 deliverable. At minimum, implement lazy cleanup-on-access (check `mtime` when serving a download, return 410 if expired). A background periodic cleanup can be added later.

---

### FINDING: Structured logging missing from all phases
Severity: should-fix

The scale design specifies Prometheus metrics and `structlog` JSON logging to stdout. The data design specifies detailed log schemas with `timestamp`, `level`, `request_id`, `api_key_name`, `duration_ms`, etc. The security design specifies audit logging with `API key name` (not value), request correlation via `request_id`, and exact log levels per event type.

None of these appear in the phased plan until Phase 7.

**Suggested reorder:** Implement basic structured logging (request_id injection, JSON to stdout) in Phase 1. This is critical for debugging Phase 1 AI generation failures. Add Prometheus metrics in Phase 2 when the metrics library is available.

---

### FINDING: Excalidraw JSON Parser dependency not accounted for
Severity: should-fix

The iteration plan (Phase 5: Image + iteration Mode B) specifies "vision + modification" where Claude parses an existing diagram image and applies changes. The integration design says Mode B "parses current diagram AND applies modification in one pass" -- it does not depend on the Excalidraw JSON Parser.

However, Phase 6's "Excalidraw JSON Parser" (parse Excalidraw JSON back to DiagramModel for precise iteration) is described as "Deferred to Phase 3" in the integration design, yet appears as Phase 6 in the phased plan. This creates ambiguity: is Mode B (image + iteration) usable without the Excalidraw JSON Parser?

The integration design Iteration Option C is explicitly deferred to Phase 6. But Phase 5's Mode B (image + text iteration) is a separate feature that does NOT require the parser.

**Suggested reorder:** Clarify that Phase 5 Mode B (vision-based image iteration) does NOT require the Excalidraw JSON Parser and is independent. Phase 6 is ONLY for iteration Option C (Excalidraw JSON upload).

---

## SHOULD-FIX: Cross-Document Conflicts

### FINDING: API endpoint naming conflict between design-doc/integration and api.md
Severity: should-fix

The integration design (lines 12-14, 877, 1080) uses a single unified endpoint `POST /v1/diagram` with routing logic inside the handler to dispatch based on which field is present.

The API design uses three separate endpoints: `POST /v1/generate/text`, `POST /v1/generate/image`, `POST /v1/generate/voice`.

These are fundamentally different API contracts. Any implementation following one design will break clients of the other.

**Resolution needed:** Decide on a single endpoint strategy. The separate-endpoint approach is cleaner for API versioning, load balancing, and documentation. The unified-endpoint approach is simpler for clients but requires more complex server-side routing.

---

### FINDING: SVG export strategy conflict between data.md and integration.md
Severity: should-fix

The data design (lines 259-269) says: "v1 produces rendered SVG (single vector path tree), not editable SVG... Use `@excalidraw/utils` `export_to_svg()` directly on the Excalidraw elements." This defers editable SVG.

The integration design (lines 697-765) specifies a hand-crafted `SVGExporter` generating semantic SVG with `<g>` groups, proper `<text>` elements, and CSS classes for re-theming. This is explicitly "editable SVG."

These are two different engineering efforts. The semantic SVG exporter (integration.md) requires custom polygon math, arrow marker definitions, and layout logic. The rendered approach (data.md) requires a single `export_to_svg()` call.

**Resolution needed:** Decide on one SVG strategy. Rendered SVG via `@excalidraw/utils` is much simpler for Phase 2. Editable semantic SVG is more valuable but significantly more engineering work.

---

### FINDING: Internal representation conflict between data.md and integration.md
Severity: should-fix

The data design (lines 96-101) says explicitly: "For v1, the internal representation IS the Excalidraw JSON. Future phases will introduce a canonical model if/when format conversion requires it." The pipeline is: Input -> AI Generation (prompt) -> Excalidraw JSON -> Exporter -> other formats.

The integration design (lines 25-26) shows a `DiagramModel (pydantic)` as the AI layer output, with exporters reading from `DiagramModel`. The integration design also says (line 844): "internal representation is deferred to Phase 2."

These are contradictory. If `DiagramModel` is the internal representation (integration.md), then Phase 1 needs a `DiagramModel` pydantic schema and a JSON-to-DiagramModel parser. If Excalidraw JSON is the internal representation (data.md), then no separate `DiagramModel` is needed in Phase 1.

**Resolution needed:** Decide on one representation. The data design's approach (Excalidraw JSON as canonical) is simpler for Phase 1 MVP. The integration design's approach (DiagramModel as canonical) is cleaner architecturally but requires more schema design upfront.

---

### FINDING: Rate limiting numbers conflict between scale.md and security.md
Severity: should-fix

| Parameter | scale.md | security.md |
|-----------|----------|------------|
| Authenticated (per key) | 100 req/min | 10 req/min |
| Burst | 20 req | 3 req |
| Unauthenticated (per IP) | 30 req/min | (not specified) |

These are very different numbers. 100 req/min vs 10 req/min is a 10x difference. The API design's tiered rate limits (free: 10, pro: 60, enterprise: 300) differ from both.

**Resolution needed:** Reconcile to a single set of numbers across all design documents.

---

## SHOULD-FIX: Parallelization Opportunities

### FINDING: Voice (Phase 3) and Image (Phase 4) can run in parallel
Severity: should-fix

Phases 3 (Voice: Whisper API + text pipeline) and 4 (Image: Claude vision + pipeline) share no code dependencies. Both depend only on:
- Phase 2's `PromptRegistry` and multi-format exporters
- The shared `ClaudeAPIClient`

These could be implemented in parallel by two developers after Phase 2 is complete, reducing the critical path from 6 phases to 4 phases (P1 -> P2 -> P3+P4 -> P5 -> P6).

**Suggested reorder:** Mark Phase 3 and Phase 4 as parallelizable in the plan. Define a "Phase 2 complete" gate that both tracks must pass before Phase 3 and Phase 4 begin.

---

## SHOULD-FIX: Phase 1 Scope Ambiguity

### FINDING: Phase 1 deliverable list is inconsistent across design-doc.md and integration.md
Severity: should-fix

design-doc.md Phase 1 says: "Text->Excalidraw MVP; FastAPI skeleton; API auth; CLI"

integration.md Phase 1 says: "Project scaffold (FastAPI, models, exporters); TextPipeline with hardcoded prompts; ExcalidrawExporter only; Basic unit tests; Dockerfile"

The design-doc.md version includes "CLI" but integration.md does not. The integration.md version is more specific and realistic. The design-doc.md version mentions "API auth" which creates a false impression that rate limiting comes with it.

**Suggested reorder:** Consolidate Phase 1 deliverables to match integration.md's explicit list. Move CLI to Phase 2 or beyond. Confirm that Phase 1 explicitly excludes: multi-format exporters, prompt library, rate limiting, circuit breakers, health endpoints, structured logging.

---

## Summary Table

| # | Finding | Severity | Critical Path Impact | Suggested Fix |
|---|---------|----------|---------------------|---------------|
| 1 | Semaphores in Phase 7 | must-fix | No (deferred infrastructure) | Move to Phase 1 |
| 2 | Rate limiting in Phase 7 | must-fix | No (deferred infrastructure) | Move to Phase 1 |
| 3 | Circuit breaker in Phase 7 | must-fix | No (deferred infrastructure) | Move to Phase 1 |
| 4 | Health/ready in Phase 7 | must-fix | No (deferred infrastructure) | Move to Phase 1 |
| 5 | Input validation missing | should-fix | No | Add to Phase 1-2 |
| 6 | Temp file cleanup missing | should-fix | No | Add to Phase 1 |
| 7 | Structured logging missing | should-fix | No | Add to Phase 1 |
| 8 | Excalidraw parser dependency unclear | should-fix | No | Clarify Phase 5 vs Phase 6 scope |
| 9 | API endpoint naming conflict | should-fix | No | Reconcile integration.md vs api.md |
| 10 | SVG export strategy conflict | should-fix | No | Reconcile data.md vs integration.md |
| 11 | Internal representation conflict | should-fix | No | Reconcile data.md vs integration.md |
| 12 | Rate limiting numbers conflict | should-fix | No | Reconcile scale.md vs security.md |
| 13 | P3 and P4 parallelizable | should-fix | **Yes** (4 phases vs 6 phases) | Mark as parallelizable |
| 14 | Phase 1 scope ambiguity | should-fix | No | Consolidate deliverable lists |

**Root cause of most issues:** The scale design, security design, and data design each describe infrastructure that is foundational (Phase 1 level), but the phased implementation plan in design-doc.md and integration.md places infrastructure in Phase 7 ("Operational hardening"). The plans correctly identify these as necessary but incorrectly sequence them last.

**Corrected phase 1 should include:** FastAPI skeleton, ExcalidrawExporter, TextPipeline, API key auth, per-IP rate limiting, per-key rate limiting, circuit breakers (Claude + Whisper), `/health` and `/ready` endpoints, structured JSON logging, request ID injection, temp file cleanup (lazy on-access), and basic unit tests.

**Corrected phase 7 would then contain:** Multi-container deployment orchestration, Redis-backed rate limiting and semaphores (if scaling beyond single container), staged environment setup, cost monitoring dashboards, and penetration testing.
