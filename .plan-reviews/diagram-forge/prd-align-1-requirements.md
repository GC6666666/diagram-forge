# PRD Alignment Review: Diagram Forge

**Reviewer**: requirements-coverage analyst
**Date**: 2026-03-22
**PRD**: `.prd-reviews/diagram-forge/prd-draft.md`
**Plan**: `designs/diagram-forge/design-doc.md`
**Integration**: `designs/diagram-forge/integration.md`
**Supporting**: `api.md`, `security.md`, `ux.md`, `scale.md`, `data.md`

---

## Summary

The plan addresses the vast majority of PRD requirements. The most significant gap is a **contradiction** between the PRD's Q1 clarification (all 3 modalities ship together in v1) and the plan's sequential phase structure (text first, voice second, image third). Several supporting requirements (web UI, privacy disclosure, specific API endpoint layout) are addressed in sibling design docs but not tracked as named phases or tasks in the phased plan itself.

---

## Requirement Coverage

### Goals (PRD Section: Goals)

**COVERED: Goal 1 -- Image → Diagram (upload screenshot/sketch, get clean Excalidraw/Draw.io)**
- Plan Phase 4 (Image input + Claude vision) directly addresses this.
- Integration design: full "Mode A: Sketch-to-Diagram" pipeline with Claude Vision analysis, image validation (10MB/4096x4096px), base64 JPEG encoding, and output parsing.
- Security design: magic byte validation, EXIF stripping, PIL re-save to clean buffer.
- Scale design: 12s p50 / 18s p95 / 25s p99 latency targets for image modality.

**COVERED: Goal 2 -- Voice → Diagram (dictate flow, get sequence diagram)**
- Plan Phase 3 (Voice input + Whisper API) directly addresses this.
- Integration design: full "Pipeline: Voice → Diagram" with Whisper API transcription (OpenAI Whisper-1, verbose_json), transcript validation, and merge with text pipeline steps 3 onward.
- Scale design: 6s p50 / 10s p95 / 15s p99 latency targets for voice modality.
- UX design: microphone button, waveform visualizer, editable transcript preview, `df transcript` CLI command.

**COVERED: Goal 3 -- Text → Diagram (plain English description, get diagram)**
- Plan Phase 1 (Text→Excalidraw MVP) directly addresses this as the blocker.
- Integration design: full "Pipeline: Text → Diagram" with 8 steps (validation → preprocessing → type inference → prompt construction → Claude call → response parsing → post-generation validation → export).
- Scale design: 3s p50 / 5s p95 / 8s p99 latency targets for text modality.

**COVERED: Goal 4 -- Multi-format export (Excalidraw JSON, Draw.io XML, SVG)**
- Plan Phase 2 (Multi-format export: +Draw.io, +SVG) directly addresses this.
- Integration design: three exporter implementations with full element mapping tables for each format.
- Excalidraw exporter: v2 schema, arrow binding for editability, labeled arrows via midpoint text elements.
- Draw.io exporter: `mxGraphModel` structure, per-diagram-type style constants, edge labels.
- SVG exporter: semantic/structural SVG (not raster-like), `<g>` groups with descriptive IDs, proper `<text>` elements for editability, CSS class styling.

**COVERED: Goal 5 -- Fast iteration (seconds, not minutes)**
- Plan Phase 5 (Iteration on existing diagrams) and Phase 6 (Precise iteration via Excalidraw JSON parser) address this.
- Integration design: three iteration modes (image+text, text+text, Excalidraw JSON+text).
- Stateless model confirmed: full context re-submitted each time. Completeness check post-generation with retry on element loss.
- UX design: "Iterate" panel with instruction field, `df iterate` CLI command.
- Scale design: Whisper transcription cache (SHA256 audio → transcript, 24h TTL) for voice iteration speed.

---

### Non-Goals (PRD Section: Non-Goals)

**COVERED: Real-time collaborative editing** -- not in plan.
**COVERED: Direct browser-based editing** -- output files opened in respective tools, not in-browser editing planned.
**COVERED: Non-computer-industry diagram types (infographics, marketing)** -- only architecture, sequence, and flowchart in scope.
**COVERED: Mobile-native experience** -- web API is primary, CLI is secondary.
**COVERED: Diagram hosting/sharing** -- stateless, no persistent storage, files downloaded only.

---

### User Scenarios (PRD Section: User Stories / Scenarios)

**COVERED: Scenario 1 -- Hand-drawn sketch to clean diagram (Alice)**
- Image pipeline Mode A (sketch-to-diagram) covers this end-to-end.

**COVERED: Scenario 2 -- Voice to sequence diagram (Bob)**
- Voice pipeline + diagram type inference (sequence mode) covers this.

**COVERED: Scenario 3 -- Text description to architecture diagram (Charlie)**
- Text pipeline + default architecture type inference covers this.

**COVERED: Scenario 4 -- Iterating on existing diagrams (Diana)**
- Iteration flows (all three modes) cover this. Specifically: image + modification text (Mode B in image pipeline) and text + modification text (Iteration Option B).

**GAP: Actor identification** -- The PRD lists 4 actor types (software engineers, tech leads, meeting teams, technical writers) but the plan does not explicitly map requirements or UX decisions to these actor segments. The UX design implicitly serves all four, but this is not documented. No fix needed for MVP; this is a clarification/documentation gap.

---

### Constraints (PRD Section: Constraints)

**COVERED: Language -- Python 3.11+**
- All design docs use Python 3.11+ throughout.
- `python:3.11-slim` Docker base image in integration and security designs.
- Dependencies pin `>=3.11`.

**COVERED: AI Provider -- Claude API (Anthropic)**
- `claude-3-5-sonnet-20241022` in integration design.
- Claude API key via `ANTHROPIC_API_KEY` env var, validated at startup (security design).

**COVERED: Speech-to-Text -- Whisper (local or API)**
- PRD says "Whisper (local or API)". Q6 clarifies: "OpenAI Whisper API. Simplest path for v1."
- Plan uses OpenAI API only; local/self-hosted is a future consideration in scale design Phase 5.
- Integration design: Whisper-1 API call example with `aiohttp`.

**COVERED: No persistent user accounts for MVP (stateless API)**
- Plan: "Stateless, 24h TTL on temp files" confirmed throughout.

**COVERED: Output formats -- Excalidraw JSON, Draw.io XML, SVG**
- Covered in plan Phase 2 and integration design exporters.

**COVERED: Privacy -- uploaded images/audio not stored long-term**
- Security design: 24h TTL cleanup worker, immediate deletion on success/failure, memory-based processing preferred for <5MB inputs.
- Data design: input files deleted immediately after pipeline consumption.
- Audit logging excludes file content.

---

### Clarifications from Human Review (PRD Section: Clarifications)

**COVERED: Q1 -- All three input modalities (text, voice, image) ship together in v1**
- Three diagram types (architecture, sequence, flowchart) in v1: confirmed.

**GAP (must-fix): Q1 -- "All three input modalities (text, voice, image) ship together, but only these three diagram types"**
- The PRD is explicit: all three modalities ship together in v1.
- The plan's phase structure is sequential: Phase 1 (text) → Phase 2 (format) → Phase 3 (voice) → Phase 4 (image).
- This contradiction means Phase 3 and Phase 4 cannot be separate sequential milestones if all three must ship together. The plan must either (a) merge Phases 1-4 into a single "all modalities" phase, or (b) clarify that the phases represent internal development order but the release is a single v1 with all three modalities.
- Suggested fix: Rename Phase 1 to "All-modality MVP" with text, voice, and image all in scope. Subdivide internally by pipeline complexity, but do not represent them as sequential release gates.

**COVERED: Q2 -- Architecture/Block, Sequence, Flowchart diagrams in v1**
- All three covered in integration design "Per-Diagram-Type Strategy" section with element types, connection types, layout strategies, layout dimensions, and example system prompts.

**COVERED: Q3 -- Iteration on existing diagrams needed, stateless model**
- Iteration flows in integration design. Stateless model confirmed. Re-submit full context each time.

**COVERED: Q4 -- Internal representation deferred, validate via prompt engineering first**
- "Internal Representation (Deferred)" section in integration design confirms this. DiagramModel pydantic class as in-memory representation for v1.

**COVERED: Q5 -- Prompt engineering + post-processing, no structured intermediate format in v1**
- Confirmed throughout: DiagramModel as the sole intermediate, generated directly by Claude JSON output, then exported.

**COVERED: Q6 -- OpenAI Whisper API for v1**
- Confirmed in integration design and scale design.

**GAP (should-fix): Q7 -- "FastAPI + Web UI + CLI wrapper. CLI wraps the API."**
- CLI wrapper: covered in Phase 1 as a blocker.
- FastAPI: covered in Phase 1.
- Web UI: NOT explicitly included as a phase or tracked deliverable in the plan. The UX design and API design documents cover the web UI extensively (React/Svelte SPA, API key modal, 3-tab layout, output panel, iteration UX), but the plan phases do not mention the web UI as a named deliverable.
- The architecture overview mentions "Web UI" but it is absent from the phased plan table.
- Suggested fix: Add a "Web UI" column to the phased plan, or add a Phase 1b "Web UI shell" sub-phase alongside the API skeleton.

**COVERED: Q8 -- Pre-shared API keys for v1. Pre-shared key-based access control**
- API key authentication in Phase 1 blocker.
- Full API key model in security design: `X-API-Key` header, constant-time lookup, `name:secret` format, 32-byte entropy, 90-day rotation, key enumeration prevention.

**COVERED: Q9 -- Input limits (PNG/JPEG/WebP ≤10MB, 4096x4096px; MP3/WAV ≤60s; text ≤4000 chars)**
- All limits specified and enforced at multiple layers (API validation, pipeline validation, security validation, scale design).

**COVERED: Q10 -- 24-hour TTL on temporary files**
- 24h TTL in plan (Key Decisions table), confirmed in security design (cleanup worker, enforcement code) and data design (filesystem lifecycle table).

---

### Open Questions (PRD Section: Open Questions)

Items Q1-Q10 have been answered above. The remaining open questions (OCR client/server, Whisper deployment choice, ambiguous layouts, batch processing, CLI vs API-first, self-hosted deployment, rate limiting/API key management, diagram storage, SVG editability, multi-page diagrams) are implementation details appropriately deferred. No requirement gap.

---

### Additional Requirements from Sibling Design Docs

These are requirements that appear in the PRD's "Rough Approach" or are implied by the PRD's constraints, but are not explicitly mapped as tasks in the phased plan:

**GAP (should-fix): Privacy disclosure / data retention enforcement in implementation**
- The PRD specifies no long-term storage and Q10 specifies 24h TTL. The security design has a detailed privacy disclosure section including response headers (`X-Data-Retention`, `X-Data-Processing`) and a `PRIVACY.md` requirement. The data design specifies the cleanup worker.
- None of these appear as named tasks or deliverables in the phased plan. The 24h TTL is listed as a "Key Decision" but is not a phase or task.
- Suggested fix: Add a "Privacy & data retention enforcement" task to Phase 1 or a pre-phase "Foundational" section, ensuring the cleanup worker, response headers, and privacy disclosure are built and verified.

**GAP (should-fix): API endpoint inconsistency between design docs**
- The plan architecture overview lists 9 endpoints including separate `POST /v1/generate/text`, `POST /v1/generate/image`, `POST /v1/generate/voice`, `GET /v1/jobs/{id}`, `GET /v1/jobs/{id}/download/{format}`, `WS /v1/ws/jobs/{id}`, `GET /v1/health`, `GET /v1/ready`.
- The integration design has a single unified `POST /v1/diagram` endpoint with modality routing internally (if image... elif audio... else text...).
- The API design doc has separate `POST /v1/generate/text`, `POST /v1/generate/image`, `POST /v1/generate/voice` endpoints.
- The UX design doc references `POST /v1/generate` with an `input_type` field and async `202 Accepted` + polling.
- These three API surface definitions are mutually incompatible. The plan must choose one and propagate it consistently across all design docs.
- Suggested fix: Decide on unified vs. separate endpoints (likely unified for cleaner API surface) and update the plan architecture overview, integration design routing code, and API design doc accordingly.

**GAP (should-fix): WebSocket / SSE progress endpoint**
- The plan architecture overview and API design doc both include `WS /v1/ws/jobs/{id}` for SSE progress streaming.
- The integration design does not mention WebSocket or SSE -- it describes only the REST polling path.
- The UX design mentions "Progress SSE (optional enhancement)" as a future improvement, but the API design treats it as a primary feature.
- Suggested fix: Either remove WebSocket from the Phase 1 scope (if it's deferred) or ensure the integration design describes the SSE pipeline.

**PARTIAL: Actor segmentation not traced to requirements**
- The PRD identifies 4 actor types (software engineers, tech leads, meeting teams, technical writers) but the plan does not trace requirements or UX decisions to these segments. No fix strictly needed for MVP; the UX covers all actors implicitly. Should-fix if the plan is used for sprint planning or user story derivation.

---

## Priority Summary

### Must-Fix

| # | Gap | Description |
|---|-----|-------------|
| 1 | Q1 contradiction | Plan phases are sequential (text→voice→image) but PRD Q1 requires all 3 modalities to ship together in v1. Phases must be reconciled to reflect a single unified v1 release. |

### Should-Fix

| # | Gap | Description |
|---|-----|-------------|
| 2 | Q7 Web UI missing from plan | Web UI is explicitly listed in PRD Q7 but does not appear as a named phase or deliverable in the phased plan. |
| 3 | Privacy disclosure not in plan | 24h TTL enforcement, response headers, and PRIVACY.md are in security/data designs but not mapped to implementation tasks. |
| 4 | API endpoint inconsistency | Three incompatible API surface definitions across plan, integration, and API design docs. Must unify. |
| 5 | WebSocket/SSE gap | `WS /v1/ws/jobs/{id}` in plan and API design, absent from integration design. Scope unclear. |

### Not Applicable

| # | Item | Notes |
|---|------|-------|
| A | Actor segmentation | PRD lists actors but this is a documentation gap, not a missing feature. |
| B | Rough Approach consistency | The "Rough Approach" in the PRD is at a higher level of abstraction than the plan; the plan refines it correctly. |

---

## Verdict

The plan is substantively complete. All 5 goals, all 3 diagram types, all 3 input modalities, all 3 output formats, iteration, authentication, rate limiting, input validation, and deployment are covered. The single must-fix is the Q1 contradiction between the sequential phase structure and the PRD's explicit requirement that all modalities ship together. The four should-fix items are gaps between sibling design docs and the main plan, not missing features.
