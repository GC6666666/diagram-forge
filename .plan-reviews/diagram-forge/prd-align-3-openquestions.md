# PRD Open Questions Review (Round 3)

Reviewer: open-questions-resolution analyst
PRD: /home/gongchao/gastown/df/crew/gongchao/.prd-reviews/diagram-forge/prd-draft.md
Plan: /home/gongchao/gastown/df/crew/gongchao/designs/diagram-forge/design-doc.md
Design docs: /home/gongchao/gastown/df/crew/gongchao/designs/diagram-forge/

---

## Section 1: Clarifications from Human Review (Q1-Q10)

These are answered in the PRD's "Clarifications from Human Review" section.

---

**RESOLVED: Q1 (v1 scope)** -- Architecture, sequence, flowchart in v1. All three modalities ship together.
- Phased plan (design-doc.md, Phase 1-4) explicitly sequences text (P1) -> multi-format (P2) -> voice (P3) -> image (P4).
- Key decisions table: "Diagram types: Architecture, Sequence, Flowchart."
- integration.md "Per-Diagram-Type Strategy" section covers all three.

---

**RESOLVED: Q2 (diagram types)** -- Same three diagram types confirmed.
- Same references as Q1. integration.md has dedicated subsections for architecture, sequence, and flowchart element types, layout strategies, and example prompts.

---

**RESOLVED: Q3 (iteration)** -- Iteration via re-submit of full context (stateless model).
- integration.md "Iteration Flow" section (pp. 769-839) covers all three iteration modes: Image+Text, Text+Text, Excalidraw JSON+Text.
- design-doc.md: "Iteration is stateless (re-submit full context)."
- UX flow documents the iterate panel with instruction text field.

---

**DEFERRED-OK: Q4 (internal representation)** -- Deferred per PRD itself. Design doc addresses it explicitly.
- integration.md "Internal Representation (Deferred)" section (p. 842): "As specified in PRD Open Question Q4: internal representation is deferred to Phase 2. The approach is validated via prompt engineering first."
- data.md confirms v1 uses Excalidraw JSON as the canonical intermediate: "For v1, the internal representation IS the Excalidraw JSON itself."

---

**RESOLVED: Q5 (AI generation approach)** -- Prompt engineering + post-processing. No structured intermediate format in v1.
- design-doc.md Key Decisions table: "Prompt engineering + post-processing. No structured intermediate format in v1."
- integration.md "AI Prompt Strategy" section (pp. 461-536) covers prompt library, versioning, temperature strategy, and few-shot examples.

---

**RESOLVED: Q6 (Whisper)** -- OpenAI Whisper API for v1.
- design-doc.md Key Decisions table: "Whisper: OpenAI API."
- scale.md confirms `whisper-1` via OpenAI API with cost analysis.
- integration.md pipeline: "Whisper is OpenAI API only for v1 (local/deployment deferred)."

---

**RESOLVED: Q7 (CLI vs API)** -- FastAPI + Web UI + CLI wrapper. CLI wraps API.
- PRD Q7 clarification: "FastAPI + Web UI + CLI wrapper. CLI wraps the API."
- design-doc.md Key Decisions table: "FastAPI + Web UI + CLI wrapper."
- api.md section 6 covers all CLI commands; ux.md section "CLI Design" shows CLI as a thin wrapper over REST API.

---

**RESOLVED: Q8 (authentication)** -- Pre-shared API keys with X-API-Key header.
- design-doc.md Key Decisions table: "Pre-shared API key (X-API-Key header)."
- security.md has full API key model: key distribution, validation, rotation, secrets management.
- api.md section 4 details the Bearer token format, key lookup, revocation, and expiry.
- Minor inconsistency noted: api.md uses `Authorization: Bearer` while security.md uses `X-API-Key`. This should be unified in implementation but does not block PRD alignment.

---

**RESOLVED: Q9 (input limits)** -- Limits are specified and implemented.
- PRD Q9: "PNG/JPEG/WebP <=10MB, 4096x4096px max; MP3/WAV <=60s; text <=4000 chars."
- scale.md Input Size Limits table matches these exactly.
- data.md input validation section enforces all limits with specific error codes.

---

**RESOLVED: Q10 (data retention)** -- 24-hour TTL on temporary files.
- design-doc.md Key Decisions table: "Stateless, 24h TTL on temp files."
- data.md "Filesystem Lifecycle" table with TTL enforcement and cleanup implementation.
- security.md "Data Retention Enforcement" section with background cleanup task design.

---

## Section 2: Open Questions (1-10 from the original list)

These are the 10 open questions listed at the bottom of the PRD.

---

**RESOLVED: Q1 (OCR client vs server)** -- Not applicable; OCR is not a separate step.
- integration.md image pipeline (p. 206): "Claude Vision Analysis (replaces OCR + layout inference)." OCR is subsumed into the vision model call. No OCR library or client/server decision needed. The Claude vision call handles both layout understanding and text extraction in one pass.

---

**RESOLVED: Q2 (Whisper deployment)** -- OpenAI Whisper API is the choice. Local deferred.
- integration.md architecture notes: "Whisper is OpenAI API only for v1 (local/deployment deferred)."
- scale.md "Phase 5: Whisper Self-Hosting" outlines the future path with faster-whisper on GPU.
- PRD Q6 already clarified "OpenAI Whisper API. Simplest path for v1."

---

**RESOLVED: Q3 (ambiguous layouts in image->diagram)** -- Handled by the vision model approach.
- integration.md "Mode B: Image + Iteration Instruction" (p. 294): "If the modification is ambiguous, make a sensible default choice and note it." The vision prompt instructs Claude to preserve relative spatial layout and make default choices when ambiguous. No explicit multi-candidate output strategy, but the approach is pragmatic for v1.

---

**RESOLVED: Q4 (batch processing)** -- Explicitly not in scope.
- integration.md and all pipeline docs show single-input, single-output processing. No batch endpoints, no parallel image processing. PRD non-goals do not mention batch explicitly, but the stateless single-job design makes batch inherently out of scope for v1. Not addressed as a question is appropriate.

---

**RESOLVED: Q5 (CLI vs API-first)** -- API is primary; CLI is a wrapper.
- Covered by Q7 in clarifications above. The design treats the REST API as the primary interface with CLI as a thin wrapper. api.md section 6 and ux.md "CLI Design" confirm this.

---

**DEFERRED-OK: Q6 (self-hosted deployment target)** -- Docker is specified. Specific PaaS/VM choices deferred.
- design-doc.md "Deployment: Docker container, single `docker run` deployment."
- data.md Docker volume mount example.
- scale.md "Docker Resource Config" section.
- security.md "Docker Network" section.
- No specific PaaS target (Fly.io, Railway, ECS, etc.) is chosen, but Docker is explicit. This is an acceptable deferral.

---

**RESOLVED: Q7 (rate limiting / API key management)** -- Rate limiting is fully designed.
- scale.md "Rate Limiting Design" section: two-tier (IP 30/min, authenticated 100/min) with token bucket implementation.
- security.md "Rate Limiting" section: in-memory token bucket, 10 RPM default, 200/hour.
- Note: Minor inconsistency between scale.md (100/min per key) and security.md (10/min per key). Both documents address rate limiting adequately for PRD alignment purposes, but implementation must pick one value.
- API key management: covered by security.md "API Key Model" and "API Key Management" subsections.

---

**RESOLVED: Q8 (diagram storage vs fresh generation)** -- Stateless. No storage. Re-submit for iteration.
- PRD non-goals: "Diagram *hosting* or *sharing* (output files are downloaded, not stored server-side)."
- design-doc.md: "Stateless, 24h TTL on temp files."
- integration.md "Iteration Flow": "Stateless model. The user re-submits the full context (original input + modification instruction) each time. No diagram storage."
- UX doc iteration design confirms stateless re-submit model.

---

**UNRESOLVED: Q9 (SVG export -- editable vs rendered)** -- INTERNAL CONFLICT between design docs.
- data.md (p. 261): "v1 produces **rendered SVG** (single vector path tree), not **editable SVG** (grouped semantic elements). This is the simpler path... Decision deferred per PRD open question Q9."
- integration.md (p. 699-701): "**Design decision:** Generate **editable SVG** (semantic SVG with grouped elements, text, and arrows as proper SVG elements)... This aligns with the PRD's 'fully-editable industry-standard diagrams' goal."

These two design docs directly contradict each other. data.md defers the decision to rendered SVG; integration.md commits to editable SVG. This is a must-fix inconsistency.

**Suggested resolution:** Commit to editable SVG (as integration.md argues, aligning with PRD goals) and add a note in data.md that the original deferral is resolved in favor of editable SVG. Alternatively, if editable SVG is too complex for v1, explicitly defer it with a Phase 2 task.

---

**RESOLVED: Q10 (multi-page/multi-panel diagrams)** -- Not addressed; out of scope for v1.
- No design doc mentions multi-page or multi-panel diagram handling. The canvas dimensions are fixed (1200x800px architecture, 1400x600px sequence, 1000x1200px flowchart per integration.md). Large diagrams would overflow or require scrolling, not pagination. This is acceptable as an out-of-scope limitation not addressed in the plan, since v1 targets simple single-canvas diagrams.

---

## Summary

| Question | Status | Notes |
|----------|--------|-------|
| Q1 Clarifications (v1 scope) | RESOLVED | Phased plan + key decisions table |
| Q2 (diagram types) | RESOLVED | Covered in integration.md |
| Q3 (iteration) | RESOLVED | Stateless re-submit in 3 modes |
| Q4 (internal rep) | DEFERRED-OK | Explicitly deferred to Phase 2 |
| Q5 (AI approach) | RESOLVED | Prompt engineering + post-processing |
| Q6 (Whisper) | RESOLVED | OpenAI API for v1 |
| Q7 (CLI vs API) | RESOLVED | API primary, CLI wrapper |
| Q8 (auth) | RESOLVED | Pre-shared API keys |
| Q9 (input limits) | RESOLVED | All limits specified |
| Q10 (data retention) | RESOLVED | 24h TTL enforced |
| OQ1 (OCR client/server) | RESOLVED | Not applicable; replaced by vision model |
| OQ2 (Whisper deployment) | RESOLVED | OpenAI API; local deferred |
| OQ3 (ambiguous layouts) | RESOLVED | Vision model handles with defaults |
| OQ4 (batch processing) | RESOLVED | Out of scope; not addressed |
| OQ5 (CLI vs API-first) | RESOLVED | API primary, CLI wrapper |
| OQ6 (self-hosted target) | DEFERRED-OK | Docker specified; specific PaaS deferred |
| OQ7 (rate limiting) | RESOLVED | Two-tier token bucket fully designed |
| OQ8 (diagram storage) | RESOLVED | Stateless; no storage |
| OQ9 (SVG editable vs rendered) | **UNRESOLVED** | Must-fix: internal conflict between data.md and integration.md |
| OQ10 (multi-page diagrams) | RESOLVED | Out of scope for v1 |

---

## Must-Fix Issues

### 1. SVG Editability Internal Conflict (OQ9)

**Severity: MUST-FIX**

data.md says v1 produces "rendered SVG (single vector path tree)" and defers the decision. integration.md says the design decision is "Generate editable SVG (semantic SVG with grouped elements, text, and arrows as proper SVG elements)." These cannot both be true.

**Impact:** If data.md's rendered SVG approach is implemented, the PRD goal of "fully-editable industry-standard diagrams" is weakened for the SVG output format specifically. If integration.md's editable SVG is implemented, data.md must be updated to remove the deferral.

**Action required:** Pick one approach. Recommendation: editable SVG (as integration.md argues, since it aligns with the PRD's stated goal). Update data.md to remove the deferral language and reflect the decision. If editable SVG proves too complex during implementation, add an explicit Phase 2 task to implement it, rather than leaving the ambiguity.

### 2. Rate Limit Value Inconsistency

**Severity: LOW (minor)**

scale.md specifies "100 req/min per API key" (authenticated tier). security.md specifies "10 requests per minute" with "200 per hour." api.md specifies 60/min for pro tier. These three documents use different numbers.

**Impact:** Low for PRD alignment -- all three documents address rate limiting, confirming it is designed. But the implementation must pick consistent values.

**Action required:** Unify on a single rate limit value (or clearly document the tier differences) before implementation.

---

## Secondary Notes

- **Minor inconsistency in auth header format:** security.md uses `X-API-Key` header; api.md uses `Authorization: Bearer`. These should be unified to a single format in implementation.
- **Q8 in clarifications (auth) is well-resolved** across all design docs despite the header format difference.
- **Phase ordering in design-doc.md** (P1=text, P2=multi-format, P3=voice, P4=image) differs from integration.md's pipeline order. This is acceptable since design-doc.md is the consolidated summary and integration.md shows the full detail; but implementers should default to integration.md's ordering as the source of truth.
