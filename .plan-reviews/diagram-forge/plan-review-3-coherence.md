# Plan Review 3: Coherence Assessment

## Scope

This review examines the consolidated design doc plus all 6 sibling design docs (api.md, data.md, ux.md, scale.md, security.md, integration.md) for internal consistency, architecture coherence, naming uniformity, integration gaps, and residual completeness issues.

---

## CRITICAL: Unreconciled Core Design Contradictions

These issues prevent a developer from building a coherent system.

---

### ISSUE: No agreement on the fundamental API endpoint structure
Severity: must-fix

The documents contradict each other on the most basic API contract.

- **design-doc.md (consolidated):** Lists three separate endpoints: `POST /v1/generate/text`, `POST /v1/generate/image`, `POST /v1/generate/voice`
- **integration.md:** Uses a single `POST /v1/diagram` endpoint with `input_type: "image" | "audio" | "text"` field
- **api.md:** Uses `POST /v1/generate/text`, `POST /v1/generate/image`, `POST /v1/generate/voice` (matches consolidated)
- **ux.md (API section):** Uses `POST /v1/generate` with `input_type: "image" | "audio" | "text"` (matches integration, not api.md)

Suggested fix: Agree on one approach. The separate-per-modality endpoints (api.md, design-doc.md) are cleaner for API ergonomics. The unified single-endpoint approach (integration.md, ux.md) is simpler for the router code. Pick one and update all docs to match.

---

### ISSUE: No agreement on response model (inline vs. file download)
Severity: must-fix

- **data.md:** Implements file-based download: `GET /v1/jobs/{job_id}/download/{format}` returns files; completed status response has `download_url` fields pointing to download endpoints
- **api.md:** Implements inline response: `POST /v1/generate` returns `200 OK` with `"content": "{ ... Excalidraw JSON ... }"` and `"content_encoding": "base64"` directly in the response body. No download endpoint described.
- **integration.md:** API section returns `DiagramResponse` with `files: dict[str, str]` as `format -> base64-encoded file content` (matches api.md inline approach)
- **ux.md:** The SPA fetches `GET /v1/jobs/{job_id}/download/{format}` for files (matches data.md download approach)

These are fundamentally different delivery models. Inline responses work for small diagrams but are problematic for large ones and complicate streaming. Download URLs with TTL expiry require a different client UX flow.

Suggested fix: Designate one approach as canonical. If file download (data.md), remove `content`/`content_encoding` from api.md. If inline base64 (api.md/integration.md), remove the download endpoints from data.md and update ux.md SPA flow accordingly.

---

### ISSUE: SVG export strategy has two conflicting decisions
Severity: must-fix

- **data.md:** Produces **rendered SVG** (single `<path>` tree via `@excalidraw/utils export_to_svg()`, non-editable)
- **integration.md:** Produces **editable SVG** (semantic grouped elements with proper `<rect>`, `<text>`, `<marker>` elements)

These are mutually exclusive. Rendered SVG is simpler but non-editable. Editable SVG is the harder engineering path. The integration.md decision aligns with the PRD's "fully-editable industry-standard diagrams" goal.

Suggested fix: Designate editable SVG (integration.md) as the target. Add a note that editable SVG generation requires building the exporter from scratch; rendered SVG via `@excalidraw/utils` is a fallback for v1 if editable SVG is not ready.

---

### ISSUE: Internal representation is simultaneously deferred AND defined
Severity: must-fix

- **data.md:** States "internal representation IS the Excalidraw JSON" for v1; `DiagramModel` is not defined here
- **integration.md:** Defines a full `DiagramModel` Pydantic class (`models/diagram.py`, `models/elements.py`) as the internal representation
- **PRD Q4:** Explicitly defers internal representation design to validate via prompt engineering first

The integration.md model files are premature if the PRD says to defer this. Alternatively, the data.md and design-doc.md deferral claim is incorrect if integration.md already has the model.

Suggested fix: Either remove the `DiagramModel` Pydantic definitions from integration.md and truly defer to prompt engineering (Excalidraw JSON as the direct output), or formally close PRD Q4 and commit to the `DiagramModel` as the canonical intermediate format. Cannot leave both positions.

---

## HIGH SEVERITY: Naming and Terminology Inconsistencies

---

### ISSUE: Three different auth header names
Severity: must-fix

- **design-doc.md:** `X-API-Key` header
- **api.md:** `Authorization: Bearer <token>` header
- **security.md:** `X-API-Key` HTTP header

PRD Q8 specifies `X-API-Key` header for pre-shared key access control.

Suggested fix: Standardize on `X-API-Key` header per PRD. Update api.md `Authorization: Bearer` to use `X-API-Key` instead. Note: Bearer tokens imply JWT/session semantics which are not appropriate for static pre-shared keys.

---

### ISSUE: Three different rate limit values
Severity: must-fix

- **design-doc.md:** 100 req/min (authenticated), 30 req/min (IP)
- **api.md:** Tiered (free: 10/min, pro: 60/min, enterprise: 300/min)
- **scale.md:** 30/min per IP, 100/min per key (matches design-doc.md)
- **security.md:** 10 requests/min per key (v1)

Suggested fix: Pick one set of numbers and document the tiered system consistently. The api.md tiered model is the most complete but is the most ambitious for v1.

---

### ISSUE: WebSocket endpoint path inconsistent
Severity: should-fix

- **design-doc.md:** `WS /v1/ws/jobs/{id}`
- **api.md:** `WSS /v1/ws/jobs/{job_id}`
- **ux.md:** `wss://api.diagramforge.dev/v1/ws/jobs/{job_id}`

The `{id}` vs `{job_id}` path parameter naming is trivial but should be consistent. More importantly, `WS` vs `WSS` in the HTTP method column of the endpoint matrix (api.md uses `WSS`) suggests a TLS concern that should be documented.

Suggested fix: Use `WSS /v1/ws/jobs/{job_id}` everywhere with a note that the WebSocket upgrade must be over TLS.

---

### ISSUE: Duplicate field definition in Excalidraw schema
Severity: should-fix

In data.md line 138-139:
```
strokeStyle: StrokeStyle;             // "solid" | "dashed" | "dotted"
strokeStyle: StrokeStyle;             // "solid" | "dashed" | "dotted"
```
`strokeStyle` is defined twice. One is likely meant to be a different property.

Suggested fix: Remove the duplicate. Verify the intended property list.

---

### ISSUE: Cylinder and cloud shapes referenced but not defined
Severity: should-fix

integration.md's architecture diagram type mentions `cylinder` (databases) and `cloud` (cloud boundaries) as element types, but data.md's `_ExcalidrawElementBase` and concrete element types only define `rectangle`, `diamond`, `ellipse`, `text`, `arrow`, `line`. Cylinder and cloud shapes are missing from the schema.

Suggested fix: Either add `ExcalidrawCylinderElement` and `ExcalidrawCloudElement` to the schema definitions, or remove cylinder/cloud references from the integration doc and use rectangle/ellipse approximations.

---

### ISSUE: Job ID format inconsistency
Severity: should-fix

- **design-doc.md:** `job_id = uuid4()`
- **api.md:** `job_id: "job_01J8K4N2P3Q5R6S7T8U9V0W1X2"` (base62 prefix style)
- **data.md:** No explicit format

The api.md format suggests a prefixed base62 ID (similar to Stripe IDs). The design-doc.md says UUID4. These are incompatible. UUID4 is simpler and more standard.

Suggested fix: Standardize on `uuid4()` format as specified in design-doc.md. Update api.md examples to use proper UUIDs.

---

### ISSUE: Base URL domain inconsistency
Severity: should-fix

- **design-doc.md:** `https://api.diagramforge.dev/v1`
- **api.md:** `https://api.diagramforge.dev/v1` (correct)
- **ux.md:** `https://api.diagramforge.ai/v1` (different TLD: .ai instead of .dev)

Suggested fix: Use a single canonical domain. The .dev TLD is Google's gTLD for developer tools and appropriate for an API. Update ux.md references to use .dev.

---

### ISSUE: Missing env var prefix consistency
Severity: should-fix

- **design-doc.md, data.md:** Prefix `$DF_*` (e.g., `DF_DATA_ROOT`, `DF_API_KEY`)
- **security.md:** Prefix `DIAGRAM_FORGE_*` (e.g., `DIAGRAM_FORGE_API_KEYS`)
- **ux.md:** Prefix `DIAGRAM_FORGE_*` (e.g., `DIAGRAM_FORGE_API_KEY`)
- **api.md:** No env var section

PRD Q8 mentions "Pre-shared API keys" without specifying the env var format.

Suggested fix: Standardize on `$DF_*` prefix as the primary convention (design-doc.md, data.md). If backward compatibility with `DIAGRAM_FORGE_*` is needed, document aliasing explicitly.

---

### ISSUE: Project directory structure conflicts
Severity: should-fix

- **integration.md:** Project root at `diagram-forge/`, Python package at `src/diagram_forge/`, API at `src/api/`
- **api.md:** Python package at `src/api/` (not `src/diagram_forge/api/`)
- **security.md:** Uses `src/`, `src/main.py`, `src/security/`, `src/audit/`, `src/routes/`, `src/processors/` (flat, not nested under `diagram_forge`)
- **scale.md:** Uses `diagram_forge/core/` (nested under package name)

These are four incompatible project layouts.

Suggested fix: The integration.md layout (`src/diagram_forge/`) is the best structured and most scalable. All other docs should reference this layout.

---

## MODERATE: Timing and Concurrency Inconsistencies

---

### ISSUE: Timeout values differ across docs
Severity: must-fix

| Stage | design-doc.md | api.md |
|-------|--------------|--------|
| Claude (text) | 20s | 45s |
| Export (each) | 3s | 15s |
| Total job ceiling | 30s text / 60s voice / 48s image | 120s |

The scale.md has the most detailed breakdown. The api.md timeout section appears to have been written independently with different numbers.

Suggested fix: Make scale.md the single source of truth for all timeout values. Remove the duplicate timeout table from api.md section 9.6.

---

### ISSUE: Concurrency limits don't reconcile
Severity: should-fix

- **design-doc.md:** Global semaphore 50, Claude semaphore 20, Whisper semaphore 5
- **scale.md:** Same as design-doc.md (consistent)
- **api.md:** Free tier: 2 concurrent jobs, Pro: 5 concurrent jobs

The api.md concurrent job limit is per-API-key, while the semaphores are global in-process limits. These could be reconciled (per-key limits enforced at rate limiting layer, global limits enforced at semaphore layer) but the docs don't explain the relationship.

Suggested fix: Clarify that per-key concurrent job limits (api.md) are enforced at the API layer, while global semaphores (scale.md) are enforced at the process level. Document which is checked first.

---

## MODERATE: Functional Gaps

---

### ISSUE: Phase 5 iteration mentions Phase 6's deferred work
Severity: should-fix

integration.md Phase 5 describes "Iteration Option C: Excalidraw JSON + Modification Text" which requires the Excalidraw JSON parser. But integration.md Phase 6 is titled "Excalidraw JSON Parser + Precise Iteration" which defers this parser. So Phase 5 iteration Option C cannot actually be built until Phase 6.

Suggested fix: Remove "Iteration Option C" from Phase 5 until Phase 6 is completed, or promote the Excalidraw JSON parser to Phase 5.

---

### ISSUE: Audio format mismatch (OGG/M4A vs. PRD)
Severity: should-fix

- **api.md:** Lists OGG and M4A as supported audio formats for voice upload
- **PRD Q6:** Specifies OpenAI Whisper API; OpenAI Whisper API supports MP3, WAV, M4A, OGG (OpenAI docs)
- **data.md:** Lists only MP3 and WAV
- **design-doc.md:** Lists MP3 and WAV

PRD clarifications Q6 and Q9 don't mention OGG or M4A explicitly. The security.md magic bytes validation table only covers MP3 and WAV.

Suggested fix: Align audio format list across all docs. OpenAI Whisper API does support OGG and M4A, so api.md is correct. Update data.md and security.md to include OGG and M4A, or explicitly exclude them in the PRD clarifications.

---

### ISSUE: WebSocket auth inconsistency within api.md
Severity: should-fix

api.md section 2.6 says WebSocket auth is via `?api_key=<key>` query parameter. api.md section 4.2 says the same. But api.md section 9.7 says the API key is checked via the standard `Authorization: Bearer` header which is supposed to be `X-API-Key` per the earlier contradiction. The WebSocket auth section doesn't reference the auth header decision at all.

Suggested fix: Document WebSocket auth separately with its own section that explicitly states the query param approach and why (browser WebSocket limitation with custom headers).

---

### ISSUE: Job cancellation endpoint referenced but not defined
Severity: should-fix

api.md section 9.3 (job state machine) says: "QUEUED -> CANCELLED: Client sends DELETE /v1/jobs/{job_id}". This endpoint is not listed in the endpoint matrix (section 1.1), not defined with a request/response schema, and not described in the CLI or UX docs.

Suggested fix: Either add `DELETE /v1/jobs/{job_id}` to the endpoint matrix and define its behavior, or remove the CANCELLED state from the state machine in section 9.3.

---

### ISSUE: Missing DELETE endpoint from download section
Severity: should-fix

data.md describes a "lazy cleanup on access" strategy where `GET /jobs/{id}/download/{format}` returns 410 Gone for expired files. But if a user wants to explicitly delete their job result before TTL expiry (privacy concern), there is no documented delete endpoint.

Suggested fix: Add `DELETE /v1/jobs/{job_id}` to immediately remove job output files, or explicitly document that deletion before TTL is not supported.

---

## LOWER: Readability and Developer Experience Issues

---

### ISSUE: No unified "this is the source of truth" declaration
Severity: should-fix

A developer reading these docs has no way to know which doc takes precedence when they contradict. There is no "conflicts resolved in favor of X.md" statement or "authoritative source" designation.

Suggested fix: Add a header to design-doc.md stating: "This document is the authoritative source. Sibling docs (api.md, data.md, etc.) are specialized views. In case of conflict, design-doc.md takes precedence. Open questions are tracked in the PRD."

---

### ISSUE: PRD open questions are answered inconsistently
Severity: should-fix

The PRD has 10 open questions (Q1-Q10) marked for crew resolution. The design docs address these questions inconsistently:

- Q1 (v1 scope): Partially addressed (3 diagram types in v1) but PRD Q1 asks about OCR approach which no doc addresses
- Q2 (diagram types): Addressed
- Q3 (iteration): Addressed
- Q4 (internal representation): DEEPLY INCONSISTENT (simultaneously deferred AND defined - see critical issue above)
- Q5 (AI generation approach): Addressed
- Q6 (Whisper): Addressed
- Q7 (CLI vs API): INCONSISTENT (design-doc says CLI wraps API, ux.md has CLI as co-equal, api.md has CLI as reference client)
- Q8 (authentication): Addressed but with different auth header names
- Q9 (input limits): Addressed but with audio format inconsistencies
- Q10 (data retention): Addressed

Suggested fix: Add a "PRD Q&A Resolution" section to design-doc.md that explicitly states how each open question was resolved and which doc holds the authoritative answer.

---

### ISSUE: API design has a deprecated endpoint structure
Severity: should-fix

api.md section 3 describes `POST /v1/generate` with `input_type` field (matching integration.md's single-endpoint approach), but section 2 describes `POST /v1/generate/text`, `POST /v1/generate/image`, `POST /v1/generate/voice` as the primary endpoints. Section 3 should be removed or reconciled with section 2.

Suggested fix: Remove the section 3 API examples (which use the single-endpoint approach) to avoid confusing the reader about which endpoint structure is correct.

---

## Summary

| Severity | Count | Categories |
|----------|-------|------------|
| Must-fix | 8 | Core endpoint structure, response model, SVG strategy, internal representation, auth header, rate limits, timeouts |
| Should-fix | 11 | Naming conventions, project structure, phase ordering, audio formats, cancellation endpoint, auth documentation |
| Lower | 3 | Source of truth declaration, PRD Q&A tracking, deprecated API examples |

### Biggest coherence blockers (in order):

1. **Endpoint structure** (3 incompatible designs) - blocks API implementation
2. **Response model** (inline vs. file download) - blocks API and UX implementation
3. **SVG export strategy** (rendered vs. editable) - blocks exporter implementation
4. **Internal representation** (deferred vs. defined) - blocks model and pipeline implementation
5. **Auth header name** (X-API-Key vs. Bearer) - blocks security implementation

### What's genuinely good:

- The phase plan (7 phases) is coherent and well-sequenced
- The three-modality-to-single-AI-layer architecture is well-reasoned and consistent
- The per-diagram-type prompt strategy (architecture, sequence, flowchart) is detailed and plausible
- The security threat model and defense layers are thorough
- The concurrency/semaphore architecture is internally consistent within scale.md
- The exporter registry pattern is clean and well-specified

### Assessment: After 5 review rounds, the architecture is sound but the surface-level inconsistencies are pervasive. The critical issues are all contradictions in already-written decisions, not missing content. Resolving the 8 must-fix issues would produce a buildable plan.
