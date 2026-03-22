# PRD Alignment Review: Diagram Forge

**Reviewer:** goals-alignment analyst
**Date:** 2026-03-22
**PRD:** `/home/gongchao/gastown/df/crew/gongchao/.prd-reviews/diagram-forge/prd-draft.md`
**Plan:** `/home/gongchao/gastown/df/crew/gongchao/designs/diagram-forge/design-doc.md`
**Design Docs Reviewed:** api.md, data.md, ux.md, scale.md, security.md, integration.md

---

## Executive Summary

All 5 PRD goals are addressed by the implementation plan. However, there are **3 critical cross-document inconsistencies** that, if not resolved, will produce conflicting implementations. Additionally, Goal 4 (multi-format export) carries a partial gap around SVG editability.

---

## Goal-by-Goal Alignment

### GOAL 1: Image to Diagram

> "Upload a screenshot or photo of a hand-drawn/sketched diagram → get a clean, editable version in Excalidraw/Draw.io"

**Status: ALIGNED**

The plan delivers image input in **Phase 4** via `ImagePipeline` Mode A (sketch-to-diagram) using Claude vision. The pipeline (integration.md, lines 206-246) describes:
- Image validation (size, dimensions, format)
- Claude vision analysis (image encoded as base64 JPEG, vision-enabled model)
- Vision prompt instructing Claude to output a `DiagramModel` JSON
- Post-generation validation
- Export to requested formats

**Iteration support** (Phase 5, Mode B) handles the "fast iteration on existing diagrams" scenario from Scenario 4 (PRD), where a user uploads an existing diagram with modification text (e.g., "add a cache layer"). The vision prompt (integration.md, lines 304-322) instructs Claude to parse the current diagram and apply the modification in one pass, outputting a complete updated diagram.

**Potential concern:** Phase 4 is the last sequential phase before iteration. Users who want image input AND iteration must wait for both phases. This is acceptable but not explicitly called out in the plan's priority rationale.

---

### GOAL 2: Voice to Diagram

> "Dictate 'user logs in, then calls API, API hits database' → generates a sequence diagram"

**Status: ALIGNED**

The plan delivers voice input in **Phase 3** via `VoicePipeline`. The pipeline (integration.md, lines 143-178) describes:
- Audio validation (format, size, duration)
- Whisper API transcription (OpenAI Whisper API, `whisper-1` model)
- Transcript validation
- Merged into text pipeline (diagram type inference, prompt construction, Claude call, export)

The PRD clarification (Q6) confirms OpenAI Whisper API as the approach. The plan follows this exactly.

**Diagrams generated from voice** will be in Excalidraw/Draw.io/SVG formats per the multi-format export (Phase 2). Sequence diagrams are explicitly supported as one of the three diagram types (PRD Q1/Q2, confirmed in integration.md line 377+).

---

### GOAL 3: Text to Diagram

> "Describe in plain English → generates the diagram"

**Status: ALIGNED**

The plan delivers text input in **Phase 1** (the MVP baseline). The text pipeline (integration.md, lines 48-128) describes:
- Input validation (type, length, content)
- Preprocessing (whitespace normalization)
- Diagram type inference (keyword matching, confidence scoring)
- Prompt construction via `PromptRegistry` per diagram type
- Claude API call with `response_format: { type: "json_object" }`
- Response parsing with JSON repair
- Post-generation validation
- Export

All three diagram types (architecture, sequence, flowchart) are supported per PRD Q1/Q2.

---

### GOAL 4: Multi-format Export

> "Output to Excalidraw (JSON), Draw.io (XML), and SVG"

**Status: PARTIAL**

Excalidraw and Draw.io export are fully addressed. The SVG export carries an unresolved conflict between the integration doc (editable SVG) and the data doc (rendered SVG).

**Excalidraw export (Phase 1, refined in Phase 2):** Fully aligned. The `ExcalidrawExporter` (integration.md, lines 588-640) generates valid Excalidraw JSON v2 with element-to-element mapping, arrow bindings, and proper schema. This satisfies "clean, editable version" for Excalidraw.

**Draw.io export (Phase 2):** Fully aligned. The `DrawioExporter` (integration.md, lines 642-694) generates valid `mxGraphModel` XML with element mapping and style constants per diagram type.

**SVG export (Phase 2):** **Partially aligned.** There is a direct conflict:

- **integration.md line 699**: "Design decision: Generate editable SVG (semantic SVG with grouped elements, text, and arrows as proper SVG elements)"
- **data.md line 261**: "v1 produces rendered SVG (single vector path tree), not editable SVG (grouped semantic elements)"

The integration doc's editable SVG approach is more ambitious and aligns better with the PRD's "fully-editable" framing, but the data doc explicitly defers it. The integration doc's own implementation notes (line 996) say "The direct generation path is preferred for v1" — but this contradicts the earlier stated design decision.

The actual implementation approach from the data doc (using `@excalidraw/utils` `export_to_svg()`) produces a rendered SVG where shapes become `<path>` elements with no semantic grouping — this is **not editable** in a meaningful sense (you cannot select and modify individual shapes, labels, or arrows in a text editor).

**Gap:** The plan does not clearly resolve whether v1 SVG output is editable or rendered. This matters because "SVG" as a user-visible output format will set expectations that may not be met.

---

### GOAL 5: Fast Iteration

> "Convert and iterate on diagrams in seconds, not minutes"

**Status: ALIGNED (execution risk on image modality)**

The plan enables fast iteration through two mechanisms:

1. **Async responses with job polling** (all phases): All generation endpoints return `202 Accepted` + `job_id` immediately. Clients poll `GET /v1/jobs/{id}` or subscribe to `WSS /v1/ws/jobs/{id}`. This is streaming-iteration-friendly — the user sees progress in seconds.

2. **Stateless re-submission** (Phase 5+): Iteration is achieved by re-submitting the full context (image + text instruction, or new text). No session state, no version history needed. This is architecturally clean and supports rapid cycling.

**Latency targets from scale.md:**

| Modality | p50 | p95 | p99 | Goal 5 Satisfied? |
|---|---|---|---|---|
| Text | 3s | 5s | 8s | Yes — "seconds" |
| Voice | 6s | 10s | 15s | Yes — "seconds" |
| Image | 12s | 18s | 25s | Marginal — "seconds" for p50, "minutes" territory at p95 |

The p50 targets for text and voice clearly satisfy "seconds, not minutes." Image at 12s p50 is technically seconds but enters minute-territory at p95 (18s) and p99 (25s). The latency targets are reasonable for v1 given vision model overhead, but the "fast iteration" promise for the image modality is ambitious.

**Concurrency gating** (scale.md, lines 44-87): Three semaphore pools (global: 50, Claude: 20, Whisper: 5) prevent queue buildup that could extend iteration times under load. This is well-designed.

---

## Cross-Document Inconsistencies (Must-Fix)

These are not goal-alignment failures but implementation blockers: multiple design docs specify different values for the same parameter. An implementer cannot resolve these by choosing one doc over another — a decision must be made and propagated.

### INC-1: Rate Limit Numbers (Critical — 3 conflicting specs)

| Doc | Authenticated | Unauthenticated |
|-----|---------------|-----------------|
| api.md §5.1 | Tiered: free=10, pro=60, enterprise=300 RPM | 1 RPM (1/10th free) |
| scale.md §2 | 100 req/min per API key | 30 req/min per IP |
| security.md §3 | 10 req/min, 200 req/hour | (no unauthenticated tier defined) |

The API doc also introduces a "concurrent jobs" dimension (2/5/20 per tier) not present in the other two docs. These must be reconciled to a single authoritative spec before implementation. **Classification: must-fix** — implementing the wrong rate limit affects API stability and cost control.

### INC-2: API Key Format (Critical — 2 conflicting specs)

| Doc | Format |
|-----|--------|
| api.md §4.1 | `Authorization: Bearer <base64url-encoded 43-char token>` |
| security.md §2 | `X-API-Key` header, `name:secret` format in env var |
| design-doc.md table | `X-API-Key` header |

The PRD (Q8) says "Pre-shared API keys" with "simple key-based access control" — neither format contradicts the PRD, but the design docs must agree. The integration doc (§6.7) uses `Authorization: Bearer` in curl examples, implying API doc is authoritative there, but the main routes and security doc use `X-API-Key`. **Classification: must-fix** — auth middleware cannot be implemented until this is resolved.

### INC-3: SVG Export Approach (Must-Resolve)

See Goal 4 PARTIAL analysis above. integration.md and data.md make irreconcilable claims about SVG output being editable vs. rendered. One approach must be chosen and documented consistently. **Classification: must-fix** — this directly affects what users receive as an output format.

---

## Additional Observations (Should-Fix)

### OBS-1: Model Version Inconsistency

| Doc | Model Specified |
|-----|-----------------|
| design-doc.md | Claude Sonnet 4.5 (vision for images) |
| integration.md | claude-3-5-sonnet-20241022 |
| scale.md | Claude Sonnet 4/4.5 |
| api.md §9.1 | claude-sonnet-4-20250514 |

Sonnet 4.5 vs Sonnet 3.5 are different model families. The API doc's specific dated version (20250514) appears fictional or future-dated. This should be standardized to a single model identifier. **Classification: should-fix** — causes confusion during implementation and could affect cost/quality estimates.

### OBS-2: API Path Prefix Inconsistency

| Doc | Path |
|-----|------|
| design-doc.md | `/v1/` prefix on all endpoints |
| integration.md | `/v1/diagram` (single endpoint, routing via request body) |
| api.md | `/generate/text`, `/generate/image`, `/generate/voice` (separate endpoints) |

The integration doc proposes a single unified `POST /v1/diagram` endpoint that routes internally based on request body fields. The API doc proposes separate `POST /v1/generate/text`, `/generate/image`, `/generate/voice` endpoints. These are architecturally different approaches. The API doc's separate-endpoint approach is cleaner for OpenAPI documentation and type safety. **Classification: should-fix** — the routing strategy must be decided before the API layer is scaffolded.

### OBS-3: Async Response Pattern Inconsistency

The API doc consistently returns `202 Accepted` + `job_id` for async processing, with polling on `GET /v1/jobs/{id}`. The integration doc's pipeline examples (lines 127, 178, 246) show synchronous response objects with embedded `files: { format: base64 }`. The integration doc's implementation notes (§8, lines 1039-1050) show a synchronous `DiagramResponse` with embedded files. The actual deployment will be async (per design-doc.md architecture and the async nature of AI calls), but the integration doc's example code does not reflect this. **Classification: should-fix** — example code in the integration doc should match the async architecture.

### OBS-4: PRD Q9 Input Limits Not Fully Incorporated

PRD clarification Q9 states: PNG/JPEG/WebP ≤10MB, 4096x4096px; MP3/WAV ≤60s; text ≤4000 chars. These are in the PRD but:
- The scale doc (§1.2) covers all limits correctly
- The data doc covers all limits correctly
- The integration doc covers text (4000 chars) and audio (60s) correctly, but the image pipeline doc says ≤10MB and ≤4096x4096px implicitly rather than explicitly referencing the PRD limits
- The security doc references 10MB for images and audio

This is mostly consistent but worth auditing to ensure the `DF_MAX_INPUT_SIZE_BYTES`, `DF_MAX_TEXT_CHARS`, `DF_MAX_AUDIO_SECONDS` constants are set from a single canonical source.

---

## Summary Table

| Goal | Status | Phase | Classification |
|------|--------|-------|----------------|
| 1. Image → Diagram | ALIGNED | P4 | — |
| 2. Voice → Diagram | ALIGNED | P3 | — |
| 3. Text → Diagram | ALIGNED | P1 | — |
| 4. Multi-format Export | PARTIAL | P2 | Gap: SVG editability unresolved |
| 5. Fast Iteration | ALIGNED | P1-P6 | Concern: image p95 at 18s |

| Issue | Type | Priority |
|-------|------|----------|
| Rate limit numbers (3-way conflict: api/scale/security) | Must-Fix | Blocking |
| API key format (X-API-Key vs Bearer token) | Must-Fix | Blocking |
| SVG export approach (editable vs rendered) | Must-Fix | Blocking |
| Model version identifier | Should-Fix | Pre-implementation |
| API path strategy (unified vs separate endpoints) | Should-Fix | Pre-scaffolding |
| Async response in integration doc example code | Should-Fix | Pre-implementation |

---

## Recommendation

The plan achieves all 5 PRD goals. Before implementation begins, resolve the 3 must-fix inconsistencies by producing a single **Implementation Parameters** document that locks down: (1) the authoritative rate limit numbers, (2) the API key format and header name, and (3) the SVG export approach. Propagate the chosen values to all 6 design docs as a cleanup step.
