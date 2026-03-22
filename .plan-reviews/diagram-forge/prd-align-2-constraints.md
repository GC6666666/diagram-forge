# PRD Alignment Review: Constraints Analysis (Round 2)

**Reviewer**: constraints-compliance analyst
**Date**: 2026-03-22
**PRD**: `.prd-reviews/diagram-forge/prd-draft.md`
**Plan**: `designs/diagram-forge/design-doc.md` (+ 6 sibling design docs)
**Scope**: Every CONSTRAINT in the PRD is verified against the plan and its 6 design dimensions.

---

## Summary

**6 VIOLATIONS** (3 must-fix, 3 should-fix)
**3 UNADDRESSED** (2 must-fix, 1 should-fix)

The most critical issues are the rate-limit contradiction (security doc vs. design overview, 10x difference), the MVP phase split vs. PRD's "ship together" clarification, and the SVG editability gap (rendered-only vs. fully-editable).

---

## Constraint-by-Constraint Analysis

---

### CONSTRAINT 1: Language: Python 3.11+

**Source**: PRD, Constraints section

**RESPECTED**: The plan (design-doc.md), all 6 design docs, and all dependency listings consistently specify Python 3.11+ as the runtime. Docker base image uses `python:3.11-slim`. No other language appears in any implementation plan.

---

### CONSTRAINT 2: AI Provider: Claude API (Anthropic) for diagram generation

**Source**: PRD, Constraints section

**RESPECTED**: The plan specifies Claude Sonnet 4.5 for all generation. All design docs consistently reference the Anthropic API client (`anthropic` package), `ANTHROPIC_API_KEY` environment variable, and the Claude Messages API. No alternative AI provider is planned.

---

### CONSTRAINT 3: Speech-to-Text: Whisper (local or API)

**Source**: PRD, Constraints section; PRD Clarification Q6

**RESPECTED**: PRD Q6 clarifies "OpenAI Whisper API. Simplest path for v1." The plan and all design docs consistently use the OpenAI Whisper API (`whisper-1` model, `openai` SDK, `OPENAI_API_KEY`). The scale design (Section "Phase 5") acknowledges self-hosting `faster-whisper` as a future cost-reduction option, but not for v1.

---

### CONSTRAINT 4: No persistent user accounts required for MVP (stateless API)

**Source**: PRD, Constraints section; PRD Clarification Q3, Q8

**VIOLATED** (should-fix) — Several design components introduce statefulness that contradicts the "stateless" mandate, even if each individual piece is defensible in isolation.

**Location of violation**:

- **data.md** explicitly plans `state/jobs.jsonl` (append-only job log) and a compaction process for it. This is persistent state.
- **api.md** (Section 9.4) plans a "TTL store" for idempotency keys (`idempotency_key` -> `job_id` mapping). The security.md (Section 2.2) also references this TTL store.
- **data.md** (Section "API Key Management") plans a SQLite-backed key store for v2+, but the v1.1 JSON config file (`api_keys.json`) is already a file-based persistence mechanism.

**Risk**: "Stateless" in the PRD means no user accounts, no sessions, and no stored diagrams. The plan's use of `jobs.jsonl`, a TTL store for idempotency, and a JSON key registry introduces exactly the kind of state that makes horizontal scaling and reliability harder. The job-ID polling mechanism (api.md Section 2.4) is already stateful by nature of tracking job progress — this is acceptable. But the idempotency store and job log are additional stateful surfaces not strictly required by the API contract.

**Suggested fix**: Move idempotency key storage to the filesystem (e.g., `state/idempotency/{hash}.job_id`) with the same 24h TTL cleanup, rather than an in-memory or Redis TTL store. The `jobs.jsonl` is append-only and low-risk for a single container, but should be documented as a v1 trade-off. For v1, these are acceptable trade-offs if explicitly called out as such.

---

### CONSTRAINT 5: Output formats: Excalidraw JSON, Draw.io XML, SVG

**Source**: PRD, Constraints section

**RESPECTED** (with one sub-issue): All three formats are planned. However, there is an internal contradiction on SVG editability:

- **data.md** (Section "SVG Output Schema"): explicitly states v1 produces **rendered SVG** ("single vector path tree", "all shapes become `<path>` elements with no semantic grouping").
- **integration.md** (Section "SVG Export"): says "Excalidraw-to-SVG exporter from `@excalidraw/utils` handles this natively" (rendered).
- **PRD Non-Goal**: "Direct browser-based editing (output files are opened in the respective tools)." This implies SVG is primarily a consumption format, not an editing target.
- **integration.md SVG section** also says: "For semantic SVG (grouped elements for editing): Use semantic SVG generator from excalidraw-libraries" — this is listed as an option but the v1 path is rendered.

**Assessment**: The plan's rendered-only SVG is a reasonable interpretation of the PRD (SVG is an output format, not an editing format). However, PRD open question Q9 ("Should it be fully editable SVG or rendered raster-like SVG?") was deferred without a resolution in the plan. This is a **should-fix** gap: the plan should explicitly decide rendered vs. semantic SVG for v1 and document why.

---

### CONSTRAINT 6: Privacy — Uploaded images/audio are not stored long-term (24h TTL)

**Source**: PRD, Constraints section; PRD Clarification Q10

**VIOLATED** (must-fix) — The TTL is correctly specified at 24 hours, but the implementation uses `/tmp` which does NOT respect the 24h guarantee across process restarts or container restarts.

**Location of violation**:

- **security.md** (Section "Temporary File Lifecycle"): uses `${TMPDIR:-/tmp}/diagram-forge/` — `/tmp` survives container restarts, meaning files left behind by a crashed container persist indefinitely until the next cleanup cycle runs.
- **data.md** (Section "Storage Architecture"): uses `$DF_DATA_ROOT` (default `/var/diagram-forge`) for the structured storage layout, but **input files** are staged in `$DF_DATA_ROOT/input/{job_id}/_staging/` — this is on a persistent volume.
- **data.md** storage rules say "All paths under `$DF_DATA_ROOT` — no system `/tmp`, no `$HOME`" — this contradicts security.md's use of `/tmp`.

**Conflict within the design docs**: `data.md` mandates all storage under `$DF_DATA_ROOT` (persistent volume), while `security.md` uses `/tmp` for input staging. These two cannot both be true.

**Suggested fix**: Consolidate to a single storage strategy. Use `$DF_DATA_ROOT` (on a named Docker volume) for all input staging, with `0700` permissions and immediate deletion after pipeline consumption. The 24h TTL cleanup applies to the `output/` directory only. This ensures data lives on a managed volume that can be wiped, rather than scattered across ephemeral `/tmp`.

---

### CONSTRAINT 7 (from Clarification Q1): All three input modalities ship together in v1

**Source**: PRD Clarification Q1

**VIOLATED** (must-fix) — The phased implementation plan splits modalities across phases:

| Phase | Content |
|-------|---------|
| 1 | Text-to-Excalidraw MVP |
| 2 | Multi-format export (+Draw.io, +SVG) |
| 3 | Voice input (+Whisper API) |
| 4 | Image input (+Claude vision) |

PRD Q1 explicitly states: "All three input modalities (text, voice, image) ship together, but only these three diagram types."

The plan ships text in phase 1, voice in phase 3, and image in phase 4. This is a direct contradiction of the "ship together" clarification.

**Suggested fix**: Re-phase so that all three modalities are available from day one of the MVP, even if some are more polished than others. The MVP could limit output formats in phase 1 (Excalidraw only), with Draw.io/SVG added in phase 2. This preserves the "ship together" constraint while still having a phased output format rollout.

---

### CONSTRAINT 8 (from Clarification Q2): Only architecture/sequence/flowchart diagram types in v1

**Source**: PRD Clarification Q2

**RESPECTED**: All design docs consistently reference only these three diagram types. No other diagram types appear in any endpoint schema, prompt library, or implementation plan.

---

### CONSTRAINT 9 (from Clarification Q3): Iteration via stateless model (re-submit full context)

**Source**: PRD Clarification Q3

**RESPECTED** (with inconsistency in API design):

- **design-doc.md**: "Iteration is stateless (re-submit full context)"
- **ux.md** (Iteration UX section): "stateless: the full new input is sent to the API. No session ID, no stored history."
- **api.md**: However, the image generation endpoint has an `iteration_context` field (0-2000 chars) and the generate endpoint has an `instruction` field. These are NOT stateless by themselves — they imply the server must correlate the new instruction with a prior job.

**Sub-issue (should-fix)**: The `iteration_context` / `instruction` fields suggest a stateful iteration model where the server connects the new instruction to a prior generation. If the server stores nothing, the client must re-submit both the original input and the new instruction. The API design should clarify this: the `instruction` field is client-provided context that, combined with the original input, constitutes the "full context" for stateless re-submission. The API does not look up prior jobs by ID.

**Suggested fix**: In api.md, clarify that `instruction` is client-side context appended to the original input, not a reference to a stored job. The server performs no lookup.

---

### CONSTRAINT 10 (from Clarification Q7): Pre-shared API keys for v1 authentication

**Source**: PRD Clarification Q7

**RESPECTED** (with API key storage conflict — see Constraint 4): The authentication model is consistently pre-shared API keys across all design docs. However, there are inconsistencies in key header format:

- **design-doc.md**: `X-API-Key` header
- **api.md** (Section 4.1): `Authorization: Bearer <token>` header
- **security.md** (Section "Key Distribution"): `X-API-Key` HTTP header

The plan should pick one. Supporting both is fine for compatibility, but it should be explicit.

---

### CONSTRAINT 11 (from Clarification Q9): Input size limits — PNG/JPEG/WebP <= 10MB, 4096x4096px; MP3/WAV <= 60s; text <= 4000 chars

**Source**: PRD Clarification Q9

**RESPECTED** (with audio format discrepancy):

| Input | PRD | Design Docs | Status |
|-------|-----|-------------|--------|
| Image formats | PNG, JPEG, WebP | PNG, JPEG, WebP | MATCH |
| Image size | <= 10MB | <= 10MB | MATCH |
| Image dimensions | <= 4096x4096px | <= 4096x4096px | MATCH |
| Audio formats | MP3, WAV | api.md: MP3, WAV, OGG, M4A; security.md: MP3, WAV | PARTIAL — api.md adds OGG and M4A, which are NOT in the PRD |
| Audio duration | <= 60s | <= 60s | MATCH |
| Text | <= 4000 chars | <= 4000 chars | MATCH |

**VIOLATED** (should-fix): api.md's voice endpoint accepts OGG and M4A in addition to MP3/WAV. These formats are not specified in PRD Q9. Adding them expands the attack surface for audio parsing (more codec vulnerabilities) and deviates from the agreed-upon scope.

**Suggested fix**: Remove OGG and M4A from the API spec. If support is needed, add it in v1.1 after the PRD is updated.

---

### CONSTRAINT 12 (from Clarification Q10): 24-hour TTL on temporary files

**Source**: PRD Clarification Q10

**PARTIALLY ADDRESSED** — The TTL value is correctly specified (24h). See **Constraint 6** (Privacy) for the must-fix issue with `/tmp` persistence and the internal conflict between `data.md` and `security.md`.

Additionally: PRD Q10 says "Claude API data flow disclosed in privacy policy." The security.md (Section "Claude API data handling") mentions this disclosure and the required `X-Data-Retention` and `X-Data-Processing` response headers, but this is not reflected in any API endpoint response schema in api.md or data.md.

**Suggested fix**: Add `X-Data-Retention: 24 hours` and `X-Data-Processing` headers to all API responses, as specified in security.md.

---

## Unaddressed Open Questions from PRD

These were left as open questions in the PRD but have implementation implications. The plan does not address them:

### UNADDRESSED 1: SVG Editability (PRD Open Question Q9)

**Risk: should-fix** — PRD Q9 asks "Should SVG be fully editable SVG or rendered raster-like SVG?" The plan picks rendered SVG (data.md) without explicitly resolving this question. "Fully editable SVG" could mean grouped semantic elements (e.g., `<g class="node">`, `<text>`, `<path>`) that can be edited in vector tools. "Rendered SVG" means all elements converted to raw `<path>` elements with no structure.

**Risk**: If users expect fully editable SVG (reasonable given the PRD's "fully-editable industry-standard diagrams" claim) but receive rendered SVG, satisfaction will be low. The PRD does not clarify, and the plan does not resolve the ambiguity.

**Suggested fix**: Explicitly decide rendered vs. semantic SVG in the design doc and update the PRD's open questions to mark Q9 as resolved.

### UNADDRESSED 2: Batch Processing Support

**Risk: should-fix** — PRD Open Question Q4 asks "Should we support batch processing (multiple images to multiple diagrams)?" The plan does not address batch processing at all. This is a significant scope question: batch support would require a different API design (batch job endpoints, separate rate limiting), different job tracking, and potentially a different pricing model.

**Risk**: If batch processing is needed, the current single-image API design is insufficient. If it is not needed, the omission is fine.

**Suggested fix**: Explicitly decide batch processing as out-of-scope for v1 and document the rationale.

### UNADDRESSED 3: OCR Handling (Client vs. Server)

**Risk: should-fix** — PRD Open Question Q1 asks "Should OCR be done client-side or server-side?" The plan (data.md, integration.md) appears to use Claude's vision model for image understanding rather than traditional OCR. For the "hand-drawn sketch to clean diagram" use case (Scenario 1), this is appropriate. However, the plan does not explicitly address this decision.

**Risk**: Low. Using Claude vision is a reasonable approach that subsumes the OCR question. But the plan should explicitly state that OCR is handled by Claude's vision model, not a separate OCR step.

**Suggested fix**: Add a note in integration.md clarifying that image→diagram conversion uses Claude's vision capabilities directly, not a separate OCR pipeline.

---

## Internal Cross-Doc Contradictions (Not PRD Constraints, But Impact Implementation)

These are not direct PRD violations but are serious enough to cause implementation problems:

### CONTRADICTION A: Rate Limit Numbers (10x discrepancy)

- **design-doc.md** (Key Decisions): "Rate limits: 100 req/min (authenticated), 30 req/min (IP)"
- **security.md** (Section "Rate Limiting"): "Requests per minute: 10" per API key

100 req/min vs. 10 req/min is a 10x difference. The scale.md has yet another set: "100 requests / minute per API key" (matching design-doc.md). This is a fundamental deployment parameter that must be resolved before implementation.

**Resolution**: scale.md and design-doc.md agree (100 req/min); security.md is the outlier. The PRD itself does not specify rate limits, but PRD Q7 asks about rate limiting for the MVP. The security.md value of 10 req/min is extremely restrictive for an authenticated API generating diagrams (a human clicking "generate" every 6 seconds is already at 10 req/min). This would effectively make the service unusable.

**Must-fix**: Align security.md rate limits with scale.md. A reasonable default is 60 req/min (authenticated), 30 req/min (IP) — matching the PRD's implicit "FastAPI + CLI" primary interface where users might generate diagrams frequently.

### CONTRADICTION B: Input Storage Path (Data Root vs. /tmp)

- **data.md**: All paths under `$DF_DATA_ROOT` (default `/var/diagram-forge`), explicitly excluding `/tmp`
- **security.md**: Uses `${TMPDIR:-/tmp}/diagram-forge/` for temp file staging

**Must-fix**: These contradict each other. Consolidate to one strategy. The data.md approach (everything under `$DF_DATA_ROOT` on a named Docker volume) is better for the 24h TTL guarantee because the volume can be reliably cleaned. `/tmp` on an ephemeral container filesystem may not survive in all deployment scenarios.

### CONTRADICTION C: Audio Format Support

- **api.md** (Voice endpoint): MP3, WAV, OGG, M4A
- **security.md** (Audio Upload): MP3, WAV
- **ux.md** (Voice Tab): MP3, WAV
- **PRD Q9**: MP3, WAV only

**Must-fix**: Remove OGG and M4A from api.md to match the PRD scope.

### CONTRADICTION D: Default Output Format

- **design-doc.md** (Architecture Overview): Default not explicitly stated in the key decisions table
- **ux.md**: "SVG selected by default because it shows a preview without requiring a tool"
- **api.md**: "Default: `excalidraw`" for the schema default

**Should-fix**: Pick one and make it consistent. SVG as default in the UX (for immediate preview) with Excalidraw as default in the API schema (for better interoperability) is defensible, but should be explicitly documented as intentional.

---

## Classification Summary

### Must-Fix (blockers before implementation)

1. **Rate limit contradiction** (security.md vs. scale.md/design-doc.md: 10 vs. 100 req/min) — CONTRADICTION A
2. **Input storage path contradiction** (data.md vs. security.md: `$DF_DATA_ROOT` vs. `/tmp`) — CONTRADICTION B
3. **Audio format scope creep** (api.md adds OGG/M4A not in PRD) — CONTRADICTION C
4. **Three modalities NOT shipped together** (plan phases voice as P3, image as P4; PRD says ship together) — CONSTRAINT 7 VIOLATION
5. **24h TTL not reliably enforced** (`/tmp` survives container restarts) — CONSTRAINT 6 VIOLATION

### Should-Fix (before v1 release, but not blockers)

6. **SVG editability ambiguity** (rendered vs. semantic — PRD Q9 unresolved) — UNADDRESSED 1
7. **Statelessness tension** (`jobs.jsonl`, idempotency store add state) — CONSTRAINT 4 VIOLATION
8. **API key header format** (`X-API-Key` vs. `Authorization: Bearer` — multiple docs) — CONSTRAINT 10 INCONSISTENCY
9. **Batch processing scope** (not addressed; may be needed) — UNADDRESSED 2
10. **Default output format** (SVG in UX, Excalidraw in API schema) — CONTRADICTION D
11. **Iteration statelessness clarity** (`instruction` field semantics undefined) — CONSTRAINT 9 SUB-ISSUE
12. **OCR handling** (not explicitly addressed) — UNADDRESSED 3
