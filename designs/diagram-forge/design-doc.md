# Design Doc: Diagram Forge

Consolidated from 6 parallel design dimensions, refined through 6 rounds of review. Full details in sibling docs.

## Architecture Overview

```
FastAPI Service (stateless, Docker container)
├── REST API Layer (/v1/)
│   ├── POST /v1/generate/text    — text → diagram
│   ├── POST /v1/generate/voice  — audio → diagram (Whisper API)
│   ├── POST /v1/generate/image   — image → diagram (Claude vision)
│   ├── GET  /v1/jobs/{id}       — polling for job status
│   ├── GET  /v1/jobs/{id}/download/{format} — download result
│   ├── GET  /v1/health          — liveness probe
│   └── GET  /v1/ready           — readiness probe
├── Input Handlers (text, voice, image)
├── AI Layer (Claude Sonnet 4.5)
└── Exporters (Excalidraw JSON, Draw.io XML, SVG)
```

All 3 modalities converge on **Excalidraw JSON** → exporters. Iteration is stateless (re-submit full context).

## Key Decisions (canonical)

| Decision | Choice | Source |
|----------|--------|--------|
| Input modalities | Text, Voice (Whisper API), Image (Claude vision) | PRD |
| Output formats | Excalidraw JSON, Draw.io XML, SVG (rendered) | SVG = rendered, not editable |
| Diagram types | Architecture, Sequence, Flowchart | PRD |
| Authentication | Pre-shared API key, `X-API-Key` header | PRD Q8 |
| Rate limits | 100 req/min (authenticated), 30 req/min (IP) | Unified |
| Storage | Stateless, `$DF_DATA_ROOT/tmp/`, 24h TTL | PRD |
| Claude model | Claude Sonnet 4.5 (vision for images) | Integration |
| Whisper | OpenAI API (MP3/WAV only, ≤60s, ≤10MB) | PRD |
| SVG export | Rendered via `@excalidraw/utils export_to_svg()` | Deferred editable |
| Internal representation | Excalidraw JSON as canonical (DiagramModel deferred) | MVP simplification |
| Audio formats | MP3, WAV only (no OGG/M4A) | PRD Q9 |
| Image limits | ≤10MB, ≤4096×4096px, PNG/JPEG/WebP | PRD Q9 |
| Text limit | ≤4000 chars | PRD Q9 |

## Performance Targets

| Modality | p50 | p95 | p99 | Max |
|---------|-----|-----|-----|-----|
| Text | 3s | 5s | 8s | 30s |
| Voice | 6s | 10s | 15s | 60s |
| Image | 12s | 18s | 25s | 48s |

## Phased Implementation Plan

### Phase 0: Spike (MUST execute before Phase 1)
**Validate Claude → Excalidraw JSON feasibility.**
- Write 5 example prompts per diagram type (architecture, sequence, flowchart)
- Call Claude Sonnet 4.5 with each prompt
- Parse output as Excalidraw JSON — verify schema validity
- Test with Excalidraw app (open generated JSON in editor)
- Measure output quality (structural accuracy, not visual similarity)
- **Exit criteria**: ≥70% of outputs parse as valid Excalidraw JSON and are structurally correct
- If spike fails: pivot to 2-step approach (generate description → generate Excalidraw JSON)

### Phase 1: MVP Core (text → Excalidraw, web UI, CLI)
**Project scaffold + text pipeline + API + basic web UI**

Sub-tasks:
1. Project scaffold: `pyproject.toml`, Docker setup, `src/diagram_forge/` layout
2. FastAPI app: app skeleton, `/v1/health`, `/v1/ready`
3. API key auth middleware (`X-API-Key` header, `DF_API_KEY` env var)
4. Rate limiter: 100 req/min (authenticated), 30 req/min (IP), token bucket
5. Circuit breaker on Claude API (trip after 5 failures, 30s recovery)
6. Semaphore pools: global(50), Claude(20), Whisper(5)
7. Text pipeline: input validation → prompt construction → Claude call → JSON parse → Excalidraw export
8. `POST /v1/generate/text`, `GET /v1/jobs/{id}`, `GET /v1/jobs/{id}/download/{format}`
9. Basic web UI: single HTML page, text input, format selector, download button
10. CLI: `df generate --text`, `df generate --type`, `df generate --format`
11. Temp file cleanup: background thread, 24h TTL
12. Structured JSON logging (structlog → stdout jsonl)
13. Unit tests: input validation, pipeline steps, exporter
14. Integration test: end-to-end text → Excalidraw flow
15. Privacy disclosure: response headers (`X-Data-Retention: 24h`)
16. **Prompt library**: 5 architecture + 5 sequence + 5 flowchart example prompts (from Phase 0)

### Phase 2: Multi-format Export + Voice Input
**Add Draw.io XML, SVG exporters + Whisper pipeline**

Sub-tasks:
1. Draw.io XML exporter: `mxGraphModel` structure, shapes, edges, labels
2. SVG exporter: `@excalidraw/utils export_to_svg()` (rendered, not semantic)
3. `POST /v1/generate/voice`: audio upload → Whisper API → transcript → text pipeline
4. Voice pipeline: audio validation (MP3/WAV ≤10MB ≤60s) → Whisper → text pipeline
5. Circuit breaker on Whisper API
6. Whisper transcription cache (SHA256 of audio bytes, 24h TTL)
7. Unit + integration tests for new exporters and voice pipeline

*Phase 2 can start when: Phase 1 MVP works end-to-end.*

### Phase 3: Image Input
**Add Claude vision pipeline for image → diagram**

Sub-tasks:
1. Image pipeline: image validation (PNG/JPEG/WebP ≤10MB ≤4096px) → Claude Sonnet 4.5 Vision
2. `POST /v1/generate/image`: multipart upload → image pipeline → export
3. Image auto-type detection (keyword matching: Flowchart > Sequence > Architecture)
4. Unit + integration tests for image pipeline

*Phase 3 can run in parallel with Phase 2 after Phase 1 is stable.*

### Phase 4: Iteration on Existing Diagrams
**Support modification of existing diagrams (stateless: re-submit full context)**

Sub-tasks:
1. Iteration API: accept image + modification instruction text
2. Claude prompt: parse existing diagram → apply modification → regenerate
3. CLI: `df iterate --image <file> --instruction "..."`
4. Iteration acceptance criteria:
   - Given image + instruction → returns valid Excalidraw JSON
   - Modified diagram preserves unmodified elements
   - Handles "add X", "remove Y", "change Z" instructions
5. Unit + integration tests for iteration

*Phase 4 after Phases 2+3 are stable.*

### Phase 5: Operational Hardening
**Production readiness**

Sub-tasks:
1. Docker healthcheck (`/v1/health`)
2. Prometheus metrics (latency, error rate, token costs)
3. Graceful degradation when Claude API is unavailable
4. Worker recycling (uvicorn `--worker-connections 1000`)
5. End-to-end test suite (full user flow validation)
6. API documentation (OpenAPI at `/docs`)
7. Deployment runbook (env vars, Docker run command, health check)

*Phase 5 can overlap with Phase 4 implementation.*

### Phase 6+: Future Work (not in current scope)
- Precise iteration (Excalidraw JSON parser for modification diff)
- Editable SVG exporter (semantic SVG with `<g>` groups, not rendered)
- Multi-container deployment (Redis-backed rate limiting)
- Self-hosted Whisper (GPU infrastructure)
- Generated SDKs (TypeScript, Go)
- Enterprise features (team keys, admin dashboard)

## Acceptance Criteria Per Phase

| Phase | What "done" means |
|-------|-------------------|
| Phase 0 | Claude produces valid Excalidraw JSON for ≥70% of test prompts |
| Phase 1 | `POST /v1/generate/text` returns valid Excalidraw JSON; web UI can upload text and download diagram; CLI works; rate limiter enforced |
| Phase 2 | All 3 output formats work; voice input produces correct diagram |
| Phase 3 | Image upload produces correct diagram for clean screenshots |
| Phase 4 | "Add a cache layer" on an architecture diagram produces updated diagram |
| Phase 5 | Service runs in Docker, passes health check, metrics visible |

## Dependencies

```
fastapi>=0.109
uvicorn[standard]>=0.27
anthropic>=0.20
openai>=1.12
pydantic>=2.6
python-multipart>=0.0.6
httpx>=0.27
tenacity>=8.2
structlog>=24.1
```

## Project Structure

```
src/diagram_forge/
├── __init__.py
├── main.py              # FastAPI app entry
├── api/
│   ├── __init__.py
│   ├── routes.py        # /v1/ endpoints
│   ├── schemas.py       # Pydantic models
│   ├── auth.py          # API key middleware
│   └── errors.py        # Error taxonomy
├── pipeline/
│   ├── __init__.py
│   ├── text.py          # Text → Excalidraw pipeline
│   ├── voice.py         # Audio → Whisper → text pipeline
│   ├── image.py         # Image → Claude vision → Excalidraw
│   └── iter.py          # Iteration pipeline
├── ai/
│   ├── __init__.py
│   └── client.py        # Claude API client + circuit breaker
├── exporters/
│   ├── __init__.py
│   ├── excalidraw.py    # → Excalidraw JSON
│   ├── drawio.py        # → Draw.io XML
│   └── svg.py           # → SVG (rendered)
├── models/
│   ├── __init__.py
│   └── job.py           # Job state dataclass
├── services/
│   ├── __init__.py
│   ├── storage.py       # Temp file management, 24h TTL
│   ├── rate_limiter.py  # Token bucket
│   └── whisper.py       # Whisper API client
├── utils/
│   ├── __init__.py
│   ├── prompts.py       # Prompt library per diagram type
│   └── logging.py       # Structured JSON logging
├── cli/
│   ├── __init__.py
│   └── main.py          # CLI commands
tests/
├── unit/
├── integration/
└── e2e/
Dockerfile
docker-compose.yml  # dev only
pyproject.toml
.env.example
PRIVACY.md
```

## Detailed Design Docs

- [API Design](./api.md) — endpoints, schemas, error codes
- [Data Design](./data.md) — storage layout, job model, logging schema
- [UX Design](./ux.md) — web UI, CLI commands, user flows
- [Scale Design](./scale.md) — latency targets, semaphores, circuit breaker, costs
- [Security Design](./security.md) — API keys, input validation, prompt injection defense
- [Integration Design](./integration.md) — full pipeline, exporters, project structure
- [Review Summary](./.plan-reviews/diagram-forge/review-summary.md) — 6-round review findings
