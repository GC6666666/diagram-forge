# Plan Review: PRD Alignment — Non-Goals Enforcement (Round 2)

**Reviewer:** Non-goals-enforcement analyst
**PRD:** `.prd-reviews/diagram-forge/prd-draft.md`
**Plan:** `designs/diagram-forge/design-doc.md` + 6 design docs
**Non-goals (5):**

1. Real-time collaborative editing (handled by Excalidraw/Draw.io themselves)
2. Direct browser-based editing (output files are opened in the respective tools)
3. Support for non-computer-industry diagram types (e.g., infographics, marketing graphics)
4. Mobile-native experience (web API is primary; CLI is secondary)
5. Diagram *hosting* or *sharing* (output files are downloaded, not stored server-side)

---

## Result: CLEAN

All plan sections stay within the five non-goal boundaries. No scope creep detected.

---

## Detailed Analysis by Non-Goal

### Non-Goal 1: Real-time collaborative editing

**Plan sections examined:**
- `design-doc.md` (Architecture Overview, phased plan)
- `api.md` (WebSocket endpoint, job state machine)
- `integration.md` (pipeline architecture)
- `ux.md` (iteration UX, Web UI design)

CLEAN. The plan uses Excalidraw JSON and Draw.io XML as export-only formats. The WebSocket (`WSS /v1/ws/jobs/{job_id}`) streams job progress events — not diagram state. There is no collaboration layer, no operational transform, no shared cursor. Iteration (Phase 5-6) is a re-submit flow, not a shared editing session.

### Non-Goal 2: Direct browser-based editing

**Plan sections examined:**
- `ux.md` (Web UI: SVG preview, JSON/XML viewer, "Open in Excalidraw/Draw.io")
- `api.md` (download endpoints, `GET /v1/jobs/{job_id}/download/{format}`)
- `integration.md` (exporters)

CLEAN. The Web UI provides viewing/preview capabilities (SVG rendering with pan/zoom, JSON/XML syntax highlighting) and download links. The "Open in Excalidraw" / "Open in Draw.io" actions launch the respective external tools with the output — exactly as the non-goal prescribes. No in-browser diagram editor is designed.

One borderline-adjacent detail: `ux.md` mentions "pan/zoom overlay" for SVG preview and "Open in Excalidraw" generates a shareable URL. Neither constitutes editing. Both are viewing/launching affordances, which the non-goal explicitly accommodates (the concern is editing-in-browser, not viewing-in-browser).

### Non-Goal 3: Non-computer-industry diagram types

**Plan sections examined:**
- `design-doc.md` (diagram types table: Architecture, Sequence, Flowchart)
- `api.md` (`DiagramType` enum: `ARCHITECTURE`, `SEQUENCE`, `FLOWCHART`)
- `ux.md` (diagram type selector pills, example prompts)
- `scale.md` (latency targets, cost estimation — all scoped to the three types)
- `integration.md` (prompt library per diagram type)

CLEAN. The plan defines exactly three diagram types throughout: architecture/block diagrams, sequence diagrams, and flowcharts. All prompt templates, latency targets, cost estimates, and API schemas are scoped to these three. No mention of infographics, marketing graphics, UML class diagrams, ER diagrams, or any other non-computer-industry type.

### Non-Goal 4: Mobile-native experience

**Plan sections examined:**
- `design-doc.md` (phased plan: "Web API is primary; CLI is secondary")
- `ux.md` (responsive design: "works on desktop (max-width: 720px) and tablet. Mobile is functional but not optimized (non-goal).")
- `api.md` (REST API, CLI commands, Swagger UI at `/ui/docs`)

CLEAN. The plan designates the REST API as the primary interface, the CLI as secondary, and the Web UI as functional but not mobile-optimized. `ux.md` explicitly acknowledges the mobile non-goal. No mobile-specific design, native mobile SDK, or mobile-first UI is planned.

### Non-Goal 5: Diagram hosting or sharing

**Plan sections examined:**
- `design-doc.md` (stateless API, 24h TTL on temp files)
- `data.md` (storage architecture: `output/{job_id}/` TTL 24h, lazy cleanup on access, immediate delete after download)
- `api.md` (download URLs expire after 24h, `JOB_EXPIRED` error code, `410 Gone` for expired jobs)
- `security.md` (data retention enforcement, cleanup workers)

CLEAN. The plan implements strict ephemeral storage: input files deleted immediately, output files with 24h TTL, no persistent diagram store, no sharing URLs, no diagram history. The download endpoint returns files that must be stored client-side. No hosting layer, no sharing links, no diagram gallery.

---

## Summary Table

| Plan Section | Non-Goal | Verdict |
|---|---|---|
| WebSocket (progress streaming) | #1 Real-time collab | CLEAN |
| Iteration (Phase 5-6, re-submit) | #1 Real-time collab | CLEAN |
| Web UI (SVG preview, pan/zoom) | #2 Browser editing | CLEAN |
| "Open in Excalidraw/Draw.io" | #2 Browser editing | CLEAN |
| Three diagram types (architecture/sequence/flowchart) | #3 Non-CI types | CLEAN |
| Web API primary, CLI secondary | #4 Mobile-native | CLEAN |
| Web UI "functional but not optimized" for mobile | #4 Mobile-native | CLEAN |
| 24h TTL temp files, stateless API | #5 Hosting/sharing | CLEAN |
| Download-only, no diagram store | #5 Hosting/sharing | CLEAN |

---

## Notable Design Decisions That Are Correctly Scoped

These are worth highlighting as they could be mistaken for scope creep but are not:

- **Whisper transcription cache** (`scale.md`): SHA256(audio) -> transcript in `/tmp/diagram_forge/cache/`. This is ephemeral server-side caching (within the 24h TTL), not diagram hosting. Correctly scoped.

- **Idempotency keys** (`api.md`): `(idempotency_key, api_key)` -> `job_id` mapping for 24h. This is deduplication of API requests, not diagram storage. Correctly scoped.

- **Admin key management endpoints** (`api.md`: `POST/GET/DELETE/PATCH /admin/keys`): Operates on API key metadata, not diagram data. Infrastructure for the pre-shared key auth model (PRD Q8). Correctly scoped.

- **Phase 6 "Precise iteration (Excalidraw JSON parser)"**: Parses the Excalidraw JSON structure to inform a more targeted re-generation prompt. This is a prompt-engineering input — the actual editing still happens in Excalidraw/Draw.io. Correctly scoped under the iteration goal (PRD Scenario 4).

---

## Conclusion

No scope creep found. The implementation plan is fully compliant with all five PRD non-goals across all seven phases and six design dimensions.
