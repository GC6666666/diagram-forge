# Plan Review: Scope Creep Analysis
**Project:** Diagram Forge
**Review:** Implementation plan vs. PRD scope
**Reviewer:** Plan Review Agent
**Date:** 2026-03-22

## Summary

The implementation plan contains significant scope creep across API design, storage, security, observability, and infrastructure. The MVP scope per the PRD is: text/voice/image input modalities, Excalidraw-only export, FastAPI + CLI wrapper, simple pre-shared API key auth, and stateless operation. The plan expands this into a multi-tier SaaS product before validating the core AI pipeline.

The PRD's phased plan (P1-P7) contradicts the PRD clarifications (Q1 says all three modalities ship together in v1). Assuming the PRD clarifications take precedence, the scope creep items below apply to the currently defined phases.

---

## CUT Items (Remove Entirely for MVP)

### 1. Admin API key management endpoints (`POST /admin/keys`, `GET /admin/keys/{id}`, `DELETE /admin/keys/{id}`, `PATCH /admin/keys/{id}`)
**Classification:** MUST-FIX

The PRD explicitly states "Pre-shared API keys for v1. Simple key-based access control." and Q8 says "Pre-shared API keys... Simple key-based access control." The API design (section 4) and integration design define a full CRUD API for key management, API key metadata schemas with tiers/owner/rate limits, and the data design defines a SQLite-backed key store for v2+. None of this belongs in v1.

**Action:** Remove all admin endpoints. Implement key validation via `X-API-Key` header lookup against an env-var-based list. Key metadata (name, tier, owner) is v2+ material.

---

### 2. WebSocket/SSE progress streaming (`WSS /v1/ws/jobs/{job_id}`)
**Classification:** MUST-FIX

The PRD non-goals mention nothing about real-time streaming. The user stories describe submit-and-download flows. The UX design (section 6.7) describes `job watch` as opening a live WebSocket progress view, but the core value proposition (fast iteration, diagram download) works fine with HTTP polling. The API design (section 2.6) defines an entire SSE event taxonomy with 7 event types.

**Simpler approach:** HTTP polling via `GET /v1/jobs/{job_id}` with a `progress` field in the response. This is already defined in the API. Remove the WebSocket entirely.

---

### 3. Idempotency key support (`idempotency_key` field, `POST /v1/generate` deduplication)
**Classification:** MUST-FIX

The PRD does not mention idempotency. Implementing it requires a TTL store (Redis or SQLite) keyed by `(idempotency_key, api_key)`, a `Idempotency-Replayed` header, and deduplication logic. This is non-trivial infrastructure for a v1 that should focus on validating diagram generation quality.

**Action:** Remove `idempotency_key` from all request schemas and all deduplication logic.

---

### 4. Multiple API key tiers (free/pro/enterprise rate limit tiers)
**Classification:** MUST-FIX

The PRD says "Pre-shared API keys for v1. Simple key-based access control." and Q8 says "Simple key-based access control." The API design (section 5.1) defines free/pro/enterprise tiers with RPM/RPD/concurrent-job limits and burst allowances. The security design (section "Rate Limiting") defines per-key rate limits at 10 RPM.

A single flat rate limit (e.g., 30 RPM per key) is sufficient for v1. Tiered limits with per-day rolling windows and concurrent-job tracking add significant complexity without validating the core feature first.

**Action:** Implement a single rate limit tier (e.g., 30 RPM per key). Remove the tier schema and all tier-related logic.

---

### 5. Generated SDKs (TypeScript/JavaScript SDK via openapi-generator, Go SDK)
**Classification:** MUST-FIX

The UX design (section "SDKs / Client Libraries") plans generated SDKs for TypeScript/JavaScript and Go published to npm and pkg.go.dev. The PRD non-goals state "Mobile-native experience (web API is primary; CLI is secondary)." Generating, testing, and publishing SDKs for two ecosystems before validating the API is premature.

**Action:** Remove SDK generation and publication from the plan. The CLI (Python) is the reference client. OpenAPI spec at `/openapi.json` enables manual code generation by consumers if needed.

---

### 6. Whisper transcription caching (SHA256 audio cache)
**Classification:** SHOULD-FIX

The scale design (section "Caching Strategy") defines a Whisper transcription cache using SHA256(audio_bytes) as key with 24h TTL. While the analysis is correct that audio transcription is deterministic and cacheable, this adds a caching layer (directory creation, TTL cleanup, cache key computation) before validating that Whisper transcription quality is sufficient. If cache misses are common in practice, the cache becomes dead weight.

**Simpler approach:** Defer caching. If Whisper costs or latency become problematic post-launch, add the cache then. The cache key (audio bytes) is known at the start of the pipeline, so adding it later is straightforward.

---

### 7. Multi-container scaling design (Redis-backed semaphores, Redis-backed rate limiting, job queues, load balancer, auto-scaling metrics)
**Classification:** MUST-FIX

The scale design (section "Future Scaling Considerations") defines Phase 2 multi-container deployment with Redis-backed distributed semaphores, Redis-backed sliding window rate limiting, SQS job queues, and nginx load balancing. Phase 4 defines auto-scaling with per-metric thresholds. Phase 5 defines self-hosted Whisper.

This is a complete architectural roadmap for a scaled SaaS product. The PRD says "single `docker run` deployment." The cost estimation section projects monthly costs for 1, 10, 50, and 200 users -- all of which are trivially handled by a single container. There is no evidence that scaling will be needed in the relevant timeframe.

**Action:** Remove all multi-container scaling design. Implement the single-container architecture with in-memory semaphores and rate limiting. Add Redis-backed infrastructure only when a single container is demonstrably insufficient.

---

### 8. Prometheus metrics + OpenTelemetry tracing
**Classification:** SHOULD-FIX

The scale design (section "Implementation Notes / Metrics to Expose") defines 7 Prometheus metric families with labels, and section "Observability Integration Points" plans OpenTelemetry spans per pipeline stage. The API design (section 9) also defines request ID propagation with OpenTelemetry trace headers forwarded to the AI provider.

This is premature. The MVP does not need per-stage latency breakdowns indexed by modality, quantile, and stage. A single endpoint-level request duration log line per job is sufficient for debugging.

**Simpler approach:** Use the existing structured JSON logging (already designed in the data design) for observability. Add Prometheus metrics when the service reaches a scale where logs are insufficient for debugging. Add OpenTelemetry when distributed tracing is actually needed (multi-container).

---

### 9. SBOM generation, pip-audit in Dockerfile, dependabot/renovate
**Classification:** SHOULD-FIX

The security design (section "Dependency Security / Python Package Scanning") plans pip-audit in the Dockerfile build step, Trivy/Grype scanning in CI/CD, and weekly automated dependency update PRs. The "Future Security Work" section also plans SBOM generation and signed releases.

For a v1 MVP where the primary risk is Claude API failures and bad diagram output (not supply chain attacks), these add CI/CD complexity before validating core functionality.

**Simpler approach:** Pin dependencies in requirements.txt with version ranges. Run pip-audit in CI periodically (e.g., weekly) rather than blocking every build. Add SBOM and signing when the service is publicly deployed.

---

### 10. Full Web UI (React/Svelte SPA with all planned features)
**Classification:** SHOULD-FIX

The UX design defines a complete single-page application with image cropper, waveform visualization, dark theme with specific color palette, keyboard navigation, responsive layout, and iteration UX. The PRD says "Mobile-native experience (web API is primary; CLI is secondary)." The PRD non-goals say "Real-time collaborative editing" and "Direct browser-based editing" are handled by Excalidraw/Draw.io.

The PRD Q7 says "FastAPI + Web UI + CLI wrapper. CLI wraps the API." -- so a Web UI IS planned. But the current design is a feature-complete SPA. The MVP web UI could be a much simpler server-rendered HTML form that posts to the API and displays the result.

**Simpler approach:** Implement a minimal server-rendered web form (Jinja2 template served by FastAPI) for v1. Add the SPA features (cropper, waveform, dark theme, keyboard shortcuts) in v2.

---

### 11. Auto-scaling Phase 4 design (CPU/memory/semaphore/request-queue scaling triggers)
**Classification:** MUST-FIX

Already covered by item 7 (multi-container scaling). The scale design defines Phase 4 auto-scaling with 7 specific metric triggers and cooldowns. This is a complete Kubernetes/HPA configuration design for a service that has not yet validated its user base.

**Action:** Remove. Add Kubernetes HPA/vpa manifests only when deploying to K8s and only after measuring actual resource utilization.

---

### 12. Self-hosted Whisper (Phase 5: faster-whisper on GPU T4)
**Classification:** MUST-FIX

Already covered by item 7. The scale design plans self-hosted Whisper as a cost optimization when API costs become prohibitive. This adds GPU infrastructure, faster-whisper deployment, CUDA setup, and a deployment complexity the PRD does not mention.

**Action:** Remove. Use OpenAI Whisper API for the foreseeable future. Monitor Whisper API costs as part of normal cost tracking.

---

### 13. Constant-time key lookup
**Classification:** SHOULD-FIX

The security design (section "API Key Model") specifies "constant-time lookup against the registered key list." For an MVP with a small list of pre-shared keys (likely <10), a simple `==` comparison is sufficient. Constant-time comparison (`secrets.compare_digest`) is appropriate for cryptographic secrets (where timing attacks matter for HMAC verification), but API keys stored as random tokens with `sk-df-` prefixes are not vulnerable to timing attacks in a practical sense at v1 scale.

**Simpler approach:** Use `secrets.compare_digest` only if the implementation uses HMAC-based key validation. If keys are stored as random tokens with a simple `if key in key_list` check, the timing difference for small lists is negligible. Defer constant-time optimization until there is a proven threat model requiring it.

---

## SIMPLIFY Items (Reduce Scope)

### 14. Storage directory structure (6 subdirectories with separate TTL policies)
**Classification:** SHOULD-FIX

The data design defines 6 top-level storage directories (`input/`, `output/`, `tmp/`, `logs/`, `state/`, `cleanup.lock`) with separate TTL policies, a background compaction process for `jobs.jsonl`, and log rotation with 7-day retention. For v1 MVP, this is over-engineered.

**Simpler approach:**
- `input/`: single temp directory, files deleted immediately after pipeline consumption (no subdirs, no `_staging/`)
- `output/`: single directory per job, TTL enforced lazily on download access (return 410 Gone if mtime > 24h)
- `tmp/`: do not persist at all -- process entirely in memory/BytesIO
- `logs/`: write to stdout (Docker captures this); no disk-based log files
- `state/`: do not persist job state to disk at all; in-memory only

This reduces storage to 1 directory (`output/`) with a single cleanup mechanism. No background processes, no logrotate, no compaction.

---

### 15. Rate limit values inconsistency (10 RPM vs 100 RPM)
**Classification:** MUST-FIX

The PRD clarifications (Q7) say "100 req/min (authenticated)". The security design (section "Rate Limiting") specifies 10 RPM per API key with a token bucket. The API design (section 5.1) defines 60 RPM for "pro" tier.

These three documents have three different numbers. The PRD takes precedence.

**Action:** Standardize on 100 RPM per authenticated API key. Align the security design and API design. Remove per-tier differentiation.

---

### 16. API versioning lifecycle (12-month deprecation window, sunset headers, migration guides)
**Classification:** SHOULD-FIX

The API design (section 8.2) defines a full API versioning lifecycle with 12-month deprecation windows, `X-API-Deprecated` and `X-API-Sunset` headers, monthly emails, and a sunset date response. This is appropriate for a public API with many consumers. For an MVP where the team is still validating the AI generation quality, designing deprecation policies for a hypothetical v2 is premature.

**Simpler approach:** Ship v1. When v2 is actually planned, design the versioning strategy at that time based on what changed and who the consumers are.

---

### 17. Job cancellation (`DELETE /v1/jobs/{job_id}`, `QUEUED -> CANCELLED` state)
**Classification:** SHOULD-FIX

The API design (section 9.3 / Job State Machine) includes a `CANCELLED` state and a `DELETE /v1/jobs/{job_id}` endpoint for client-initiated job cancellation. The state machine shows `QUEUED -> CANCELLED (if client disconnects before processing)`.

For v1, client-initiated cancellation adds complexity (a DELETE endpoint, cancellation flag propagation through the pipeline, a terminal state that is neither success nor failure). Most clients will simply stop polling.

**Simpler approach:** Remove the DELETE endpoint. If a client disconnects, let the job reach its natural terminal state. No client will need to explicitly cancel.

---

### 18. Docker network hardening (`internal: true`, bind to `127.0.0.1`)
**Classification:** SHOULD-FIX

The security design (section "Docker Network") specifies `internal: true` (no external egress), binding to `127.0.0.1:8000`, and `internal: true` on the bridge network. The security checklist says "Service binds to 127.0.0.1:8000, not 0.0.0.0."

For a single-container self-hosted deployment, `internal: true` would block outbound calls to the Claude API and Whisper API, which are critical dependencies. The service MUST be able to make outbound HTTPS connections. Binding to `127.0.0.1` also prevents external access even for self-hosted users who want to expose the service.

**Simpler approach:** Remove `internal: true`. Bind to `0.0.0.0:8000` with TLS termination expected at the ingress layer. Network egress must be allowed for Claude API and Whisper API calls.

---

### 19. UUIDv7 request ID (time-ordered UUIDs)
**Classification:** SHOULD-FIX

The API design (section 9.7) specifies "Every request gets a `request_id` (UUIDv7, time-ordered)" for OpenTelemetry compatibility. UUIDv7 is a relatively recent standard (2024). Python's standard library does not include a UUIDv7 generator; it requires a third-party library. For v1, a simple `uuid.uuid4()` is sufficient and already available.

**Simpler approach:** Use `uuid.uuid4()` for request IDs. If OpenTelemetry integration is added later, migrate to UUIDv7 at that time.

---

### 20. OpenAPI specification quality requirements (Pydantic-as-Schema, API versioning)
**Classification:** SHOULD-FIX

The UX design (section "API Technical Decisions") plans "Pydantic models as single source of truth for both runtime validation and OpenAPI schema generation" and "FastAPI auto-generates the OpenAPI 3.1 spec at `/openapi.json`". The API design (section 8) defines URL-based versioning with `/v1/` prefix. The UX design says "Breaking changes increment the version."

While FastAPI auto-generates OpenAPI from Pydantic models, the specific requirement for schema-to-runtime consistency and the 12-month deprecation policy are v2 concerns. The automatic OpenAPI generation is already a FastAPI feature -- no additional work is needed.

**Simpler approach:** Rely on FastAPI's built-in OpenAPI generation. Remove the explicit requirement for schema-to-runtime consistency enforcement beyond what FastAPI provides natively. Remove the deprecation policy.

---

## DEFER Items (Not Needed for MVP, Move to Follow-up)

### 21. Precise iteration via Excalidraw JSON parser (Phase 6)
**Classification:** SHOULD-FIX

The phased plan (Phase 6: "Precise iteration (Excalidraw JSON parser)") plans to parse the user's exported Excalidraw JSON back into the internal representation, allowing targeted modifications. The PRD Q4 explicitly deferred internal representation design. The PRD Q3 says "iteration on existing diagrams is needed. Users re-upload full context (stateless model)."

Re-uploading full context (the current stateless approach) satisfies the iteration requirement. A dedicated Excalidraw JSON parser for precise iteration is v2+ material.

**Action:** Remove Phase 6. Implement iteration via re-submission of full context (text + image + instruction). Add a dedicated JSON parser when the stateless approach proves insufficient.

---

### 22. Prompt library with versioning and changelog
**Classification:** SHOULD-FIX

The integration design (section "Prompt Library Structure") plans a prompt registry with version fields (`version: str`, `model: str`), a prompt changelog, few-shot examples with separate JSON files, and a `PromptRegistry` class. The prompt versioning section plans structured prompts in a directory with CHANGELOG.md.

For v1, prompts will be validated and iterated on frequently as the team learns what produces good diagrams. A formal versioning system with changelog and example files adds overhead before the prompt strategy is validated.

**Simpler approach:** Store prompts as constants in Python modules. Version them via git history. Add a formal registry and changelog when prompt versions need to be tracked independently of source control.

---

### 23. Per-key metadata (key_name, key_hash, owner, tier, created_at, expires_at)
**Classification:** SHOULD-FIX

The API design (section 4.1 / API key structure) defines a key metadata schema with 11 fields including `key_id`, `key_hash`, `owner`, `tier`, `created_at`, `expires_at`, rate limit config, and allowed input/output lists. The data design (section "API Key Management / v1.1") also defines a JSON config file format with this metadata.

For v1 MVP, pre-shared keys from an environment variable need zero metadata. The `key_name` (from `name:secret` in the env var) is the only identifier needed.

**Simpler approach:** Env var `DIAGRAM_FORGE_API_KEYS` with format `name:secret,name2:secret2`. Store nothing on disk. No key metadata, no JSON config file, no SQLite store.

---

### 24. Client-side file validation (magic bytes, size checks) before upload
**Classification:** SHOULD-FIX

The UX design (section "Implementation Notes / Web UI Technical Decisions") plans client-side validation of file types via magic bytes and client-side file size checks. This duplicates server-side validation and adds JavaScript code to implement a feature that the server already handles.

**Simpler approach:** Remove client-side validation. The server rejects invalid uploads with descriptive error messages (already designed). Client-side validation adds code with no benefit since the server is the source of truth.

---

## Summary Table

| Item | Recommendation | Severity | Type |
|------|---------------|----------|------|
| Admin key CRUD endpoints | CUT | MUST-FIX | Gold-plating |
| WebSocket/SSE streaming | CUT | MUST-FIX | Nice-to-have |
| Idempotency keys | CUT | MUST-FIX | Nice-to-have |
| Multi key tiers | CUT | MUST-FIX | Over-engineering |
| Generated SDKs (TS/Go) | CUT | MUST-FIX | Nice-to-have |
| Multi-container scaling design | CUT | MUST-FIX | Premature optimization |
| Auto-scaling Phase 4 design | CUT | MUST-FIX | Premature optimization |
| Self-hosted Whisper Phase 5 | CUT | MUST-FIX | Premature optimization |
| Whisper caching | SIMPLIFY (defer) | SHOULD-FIX | Premature optimization |
| Prometheus + OpenTelemetry | SIMPLIFY (defer) | SHOULD-FIX | Premature optimization |
| pip-audit in Dockerfile, SBOM, dependabot | SIMPLIFY (defer) | SHOULD-FIX | Over-engineering |
| Full Web UI SPA | SIMPLIFY (minimal form) | SHOULD-FIX | Over-engineering |
| Storage: 6 directories, cleanup processes | SIMPLIFY (1 directory) | SHOULD-FIX | Over-engineering |
| Rate limit inconsistency (10 vs 100 RPM) | SIMPLIFY (fix to 100) | MUST-FIX | Inconsistency |
| API versioning lifecycle | SIMPLIFY (defer) | SHOULD-FIX | Gold-plating |
| Job cancellation endpoint | SIMPLIFY (remove) | SHOULD-FIX | Nice-to-have |
| Docker internal network | SIMPLIFY (remove) | SHOULD-FIX | Bug/design error |
| UUIDv7 request IDs | SIMPLIFY (use uuid4) | SHOULD-FIX | Premature optimization |
| OpenAPI schema enforcement | SIMPLIFY (use FastAPI) | SHOULD-FIX | Over-engineering |
| Precise iteration (Phase 6) | DEFER | SHOULD-FIX | Not MVP requirement |
| Prompt library with versioning | DEFER | SHOULD-FIX | Over-engineering |
| Per-key metadata (11 fields) | DEFER | SHOULD-FIX | Over-engineering |
| Client-side file validation | DEFER | SHOULD-FIX | Redundant |

**Total items: 24**
- MUST-FIX: 8 (items 1-4, 7, 11-12, 15)
- SHOULD-FIX: 16

The core theme: the plan treats this as a production SaaS product with multi-tenant billing, distributed infrastructure, and comprehensive observability before validating that the AI pipeline produces good diagrams. The MVP should be a single FastAPI container that accepts text/voice/image, calls Claude/Whisper, and returns an Excalidraw JSON file. Everything else can be added incrementally.
