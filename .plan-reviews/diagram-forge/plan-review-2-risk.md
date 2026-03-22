# Plan Risk Review: Diagram Forge

## Executive Summary

The implementation plan spans 7 phases from a text-to-Excalidraw MVP through operational hardening. The core premise -- using Claude to generate Excalidraw JSON from natural language -- is sound but unproven. The most critical risks are the absence of any spike or POC to validate that premise, cross-document inconsistencies that will cause implementation confusion, and an underspecified rate-limiting architecture that allows clients to triple their effective limits.

---

## Risk Register

### RISK-01: Claude JSON Generation Reliability (Core Assumption Untested)
**Description:** The entire system rests on Claude Sonnet 4.5 consistently producing valid, schema-compliant Excalidraw JSON. The Excalidraw element schema is large (50+ fields per element, strict types, required bindings for arrows). The plan sets a target of "<5% malformed output" but provides no evidence this is achievable. The plan mentions "JSON repair" and "1 retry" as mitigation but does not quantify expected success rates.

The integration design (Step 5, Step 7) relies on `response_format: { type: "json_object" }` which constrains output to valid JSON but does not enforce the Excalidraw element schema. Claude can return structurally valid JSON that fails Excalidraw validation (wrong element types, missing required fields, invalid version numbers, incorrect arrow bindings, bad fractional indices).

**Impact:** HIGH -- A high malformed-output rate means users experience repeated failures and have a poor impression of the product. This is existential for Phase 1.

**Likelihood:** MEDIUM -- Claude Sonnet 4.5 is a strong model but the Excalidraw schema is complex. Few-shot examples may not be sufficient to guarantee schema compliance across all diagram types.

**Mitigation:** must-fix

**Suggested action:** Add a Phase 0 spike: generate 100+ test diagrams (30 architecture, 30 sequence, 30 flowchart, 10 edge cases) with the current prompt approach and measure actual malformed-output rate. Set the acceptable threshold and only proceed to Phase 1 implementation if the rate is below 5%. If the rate exceeds 5%, iterate on the prompt strategy before writing pipeline code. Consider adding a JSON schema validation layer in the prompt ("Here is the exact schema your JSON must match: ...") which often improves compliance significantly.

---

### RISK-02: Cross-Document Specification Conflicts
**Description:** All 6 sibling design docs were produced in parallel and contain numerous conflicting specifications:

**Authentication:**
- design-doc.md, data.md, scale.md: `X-API-Key` header
- api.md: `Authorization: Bearer` header
- data.md: `DF_API_KEY` env var (single key)
- security.md, ux.md: `DIAGRAM_FORGE_API_KEYS` env var (`name:secret` format)
- api.md: `X-API-Key` in curl examples

**Rate limits (authenticated):**
- design-doc.md: 100 req/min
- scale.md: 100 req/min (token bucket, 20 burst)
- api.md: 60 req/min (pro tier), 10 req/min (free tier)
- security.md: 10 req/min, 200 req/hour, 3 burst

**Key structure:**
- data.md: `{ key, name, created_at, rate_limit_rpm, enabled }`
- security.md: `name:secret` pairs with `name` as stable identifier
- api.md: `{ key_id, key_hash (sha256:...), owner, tier, expires_at, rate_limit: {...} }`

**Retry behavior:**
- integration.md: circuit breaker trips at 5 consecutive failures, 60s recovery
- scale.md: circuit breaker trips at 5 consecutive failures OR 50% error rate over 10 requests, 30s recovery
- api.md: 50% error rate in 60s window, 30s cooldown

**SVG generation strategy:**
- data.md: Use `@excalidraw/utils` `export_to_svg()` (rendered, non-editable)
- integration.md: Generate editable SVG from scratch with semantic SVG elements (proper `<g>`, `<rect>`, `<text>`)

**Impact:** HIGH -- These conflicts will cause implementation confusion, lead to inconsistent behavior, and require significant cross-doc reconciliation before coding begins. Every team member reading different docs will reach different conclusions.

**Likelihood:** HIGH -- The conflicts are not subtle; they represent fundamentally different design choices documented simultaneously.

**Mitigation:** must-fix

**Suggested action:** Before any code is written, produce a single `SPEC.md` that resolves every conflict explicitly. The "winner" for each conflict should be decided and stated. The 6 sibling docs can remain as detailed rationale, but SPEC.md is the canonical source of truth.

---

### RISK-03: Per-Worker Rate Limiting Bypasses Limits on Restart
**Description:** The rate limiter (both security.md and scale.md) uses in-memory token buckets. With 2 uvicorn workers, each worker maintains its own independent rate limit state. A client sending 60 requests/min to a 2-worker deployment can effectively get 120 req/min by distributing requests across workers, since neither worker sees more than ~30 req/min.

Additionally, restarting the container (planned via `--limit-max-requests 1000` for memory leak prevention) resets all rate limit counters to full capacity, allowing a burst well beyond the intended limits.

The scale.md notes "v1 is single-instance, so an in-memory store is acceptable" but does not address the multi-worker bypass vector or the restart reset vector.

**Impact:** HIGH -- Rate limiting is a key cost control and abuse prevention mechanism. Bypasses could lead to runaway costs or quota exhaustion.

**Likelihood:** MEDIUM -- Any user who notices the behavior (or intentionally exploits it) can triple their effective rate limit.

**Mitigation:** must-fix

**Suggested action:** Either (a) use a single shared rate limiter backed by a lightweight store (SQLite file, Redis) so state is consistent across workers and survives restarts, or (b) document this as a known v1 limitation with explicit monitoring: alert if any single API key exceeds 2x the configured rate limit in a sliding window.

---

### RISK-04: Missing Spike for AI Diagram Generation Feasibility
**Description:** The plan has no Phase 0 or spike task to validate the core technical assumptions. Specifically, there is no evidence that:

1. Claude can reliably produce valid Excalidraw JSON for architecture, sequence, and flowchart diagrams with low error rates.
2. The Excalidraw JSON produced by Claude loads correctly in the Excalidraw editor (bindings, IDs, version compatibility).
3. The Draw.io exporter produces valid, renderable XML from arbitrary Excalidraw JSON (Draw.io is notoriously strict about XML format).
4. The SVG exporter (whichever strategy is chosen) produces valid, renderable SVG.
5. Claude's vision analysis can extract meaningful diagram structure from real-world sketches.
6. Iteration mode (re-generating a modified diagram) preserves enough detail to be useful across multiple iterations.

These are all open research questions. The plan treats them as implementation details.

**Impact:** HIGH -- If items 1, 2, 3, or 4 fail at >5% rate, the product is not viable. Discovering this after Phase 1-3 are implemented means significant rework.

**Likelihood:** HIGH -- This is the most likely source of project failure.

**Mitigation:** must-fix

**Suggested action:** Add a Phase 0 spike with these tasks:
- Spike A: Test Claude with 100 prompts across 3 diagram types. Measure JSON validity rate, Excalidraw schema compliance rate, and visual quality score (manual review). Target: >95% valid, >80% correct.
- Spike B: Test Excalidraw-to-Draw.io conversion on 50 generated Excalidraw JSON files. Measure XML validity rate and Draw.io render success rate.
- Spike C: Test Claude vision on 20 real sketch images. Measure element extraction accuracy.
- Spike D: Test 3-round iteration on 10 diagrams. Measure element preservation rate.

Do not proceed to Phase 1 implementation until all spikes pass their thresholds.

---

### RISK-05: Tight Memory Budget Under Concurrent Load
**Description:** The Docker container is configured with 4 GB RAM and 2 CPUs. The plan estimates that a single 4096x4096 RGBA image decodes to ~64 MB. At 4 concurrent image-processing jobs, that's 256 MB just for decoded images. Adding Python runtime overhead, uvicorn workers (2x), Excalidraw JSON serialization, Draw.io XML generation, SVG generation, and OS overhead brings total consumption to ~3 GB, leaving only 1 GB of headroom.

The plan explicitly states "4GB is tight but adequate for v1. Monitor with `memory_usage` metric." There is no mechanism specified to handle memory exhaustion. An OOM kill would terminate in-flight jobs with no graceful degradation.

Additionally, the plan specifies `--limit-max-requests 1000` for worker recycling, but does not address that OOM kills happen before that limit.

**Impact:** MEDIUM -- OOM kills cause job failures and require client retries. Under moderate concurrent load (e.g., 5+ image jobs simultaneously), memory pressure is significant.

**Likelihood:** MEDIUM -- Likely to manifest under real usage, not just extreme edge cases.

**Mitigation:** should-fix

**Suggested action:** (a) Increase the memory limit to 6 GB as a safety buffer. (b) Add an async job queue (Redis or in-process with background tasks) so image processing jobs are serialized rather than parallelized within a worker, preventing concurrent image decode. (c) Add memory monitoring to the `/health` endpoint and set the global semaphore to reduce concurrency when memory is elevated.

---

### RISK-06: SVG Generation Strategy Is Internally Contradictory
**Description:** Two different sections of the plan describe fundamentally different SVG generation approaches:

- data.md says: "Use `@excalidraw/utils` `export_to_svg()` directly on the Excalidraw elements. No intermediate transformation." The output is described as "rendered SVG (single vector path tree), not editable SVG."
- integration.md says: Generate "editable SVG" with semantic `<g>` groups, proper `<rect>`, `<text>`, `<line>`, and arrow `<marker>` definitions. This is architecturally a full SVG exporter equivalent in complexity to the Draw.io exporter.

"Rendered SVG" (Excalidraw utility) and "editable SVG" (manual SVG construction) are not the same thing. The former takes minutes to implement; the latter is a substantial engineering effort. The UX goal ("fully-editable industry-standard diagrams") strongly implies the editable SVG path, but the data design says otherwise.

**Impact:** MEDIUM -- The wrong choice (rendered SVG) fails the product requirement. The right choice (editable SVG) is a substantial additional effort not accounted for in phase estimates.

**Likelihood:** MEDIUM -- The contradiction will cause implementation confusion.

**Mitigation:** should-fix

**Suggested action:** Decide the SVG strategy explicitly in SPEC.md. If editable SVG is required (strongly recommended for UX quality), this is a full exporter implementation equivalent to Draw.io, not a library call. Allocate additional time in Phase 2. If rendered SVG is acceptable as a v1 fallback, implement the Excalidraw utility approach first and defer editable SVG to a future phase.

---

### RISK-07: Vision Prompt Incompatibility with JSON Object Mode
**Description:** The integration design's vision prompt (sketch-to-diagram mode, step 2) instructs Claude to "Output ONLY a valid JSON object matching this schema" and lists the full schema in the prompt. However, the recommended API call uses `response_format: { type: "json_object" }` which already constrains Claude to output valid JSON and typically does not include markdown fences.

The prompt also says "Output valid JSON only, no markdown, no explanation" and lists schema rules like "Every element referenced in connections must exist in elements." These rules are natural language constraints embedded in the prompt, but `response_format: { type: "json_object" }` does not enforce schema compliance -- it only ensures the output is valid JSON.

If the vision model outputs valid JSON that violates the element-ID consistency rules or uses element types not mapped in the exporter, the pipeline silently succeeds but produces invalid output.

**Impact:** MEDIUM -- Schema violations in vision output can lead to diagram elements being dropped, misconnected, or mislabeled. Users may not notice immediately.

**Likelihood:** MEDIUM -- The schema complexity for vision output (diagram_type, elements array, connections array with cross-references) is higher than text-only output.

**Mitigation:** should-fix

**Suggested action:** Add a post-generation validation step that specifically checks: (a) all element IDs in `connections[].from_id/to_id` reference valid `elements[].id`, (b) all element types are among the supported set, (c) all coordinates are within canvas bounds. This is a superset of the existing "completeness check" mentioned for iteration.

---

### RISK-08: Incomplete Dependency Specifications
**Description:** Several libraries referenced in code examples and design docs are missing from the declared dependency list in design-doc.md:

| Library | Referenced In | In Dependency List |
|---------|---------------|-------------------|
| `tenacity>=8.2` | design-doc.md | Yes |
| `pybreaker>=1.0` | scale.md (code examples) | No |
| `slowapi>=0.1.9` | security.md (code examples) | No |
| `structlog>=24.1` | design-doc.md, scale.md | No |
| `tenacity` | scale.md code uses `pybreaker`, not `tenacity` | N/A -- inconsistency |
| `pillow>=10.0` | scale.md, security.md | No |
| `mutagen` | security.md | No (replaced by pydub in some docs) |

The `pydub` vs `mutagen` discrepancy is also a concern: security.md recommends `mutagen` for metadata extraction (safer for untrusted files) while other docs reference `pydub`.

**Impact:** MEDIUM -- Missing dependency declarations will cause implementation delays when the code references libraries that haven't been added to the project.

**Likelihood:** HIGH -- The inconsistencies are already present in the design documents.

**Mitigation:** should-fix

**Suggested action:** Produce a canonical `pyproject.toml` or `requirements.txt` before Phase 1 implementation begins. Resolve the pydub/mutagen choice explicitly (recommendation: use `mutagen` per security.md guidance since it handles untrusted files more safely). Remove `tenacity` if `pybreaker` is used instead, or vice versa.

---

### RISK-09: Excalidraw Schema Version Stability and Compatibility
**Description:** The plan references Excalidraw schema v2 but does not specify:
- How schema version changes in Excalidraw will be detected and handled
- Whether the output Excalidraw JSON will be forward-compatible with future Excalidraw releases
- What happens when the Excalidraw schema changes and generated diagrams stop loading in the Excalidraw editor

The api.md says the schema is "pinned to v2" but provides no mechanism for handling schema evolution.

**Impact:** MEDIUM -- Schema mismatches can cause silent failures where diagrams load incorrectly or not at all in Excalidraw. This undermines the core value proposition.

**Likelihood:** LOW -- Excalidraw v2 has been stable. Schema changes are infrequent. But when they occur, they can be breaking.

**Mitigation:** should-fix

**Suggested action:** (a) Pin to a specific Excalidraw npm version (e.g., `@excalidraw/excalidraw@0.17.0`) rather than `latest`. (b) Add a regression test suite that opens generated Excalidraw JSON in the Excalidraw editor (headless) and verifies it loads without errors. (c) Monitor Excalidraw release notes for schema changes.

---

### RISK-10: Iteration Mode Completeness Not Guaranteed
**Description:** The iteration flow (sketch + modification text -> vision + iteration prompt -> new diagram) instructs Claude to "preserve all unmodified elements" and "output the complete updated diagram." However, there is no guarantee Claude will not inadvertently modify, reposition, or drop elements during iteration.

The integration design mentions a "completeness check" post-generation (verify all expected elements are present) but:
- It is only mentioned in the integration design, not in the phase plan
- It is not a committed task in any phase
- The threshold for "acceptable" element preservation is not defined

The plan also uses a single API call for both parsing the existing diagram AND applying the modification, which couples two complex operations. If either fails, the whole iteration fails.

**Impact:** MEDIUM -- Degraded iteration quality (elements disappearing or shifting) will erode user trust in the iteration feature. This is a key differentiator in the UX design.

**Likelihood:** MEDIUM -- Claude's instruction-following for "preserve everything except X" degrades with complexity (more elements, more subtle modifications).

**Mitigation:** should-fix

**Suggested action:** (a) Make the completeness check a committed part of Phase 4 (iteration feature). (b) Define a minimum acceptable element preservation rate (e.g., >95% of non-removed elements must be preserved). (c) If completeness check fails after 1 retry, return `INCOMPLETE_ITERATION` error with specific guidance to the user.

---

### RISK-11: Whisper Cache Uses Ephemeral Filesystem
**Description:** The Whisper transcription cache stores files at `CACHE_DIR = Path("/tmp/diagram_forge/cache")` with a 24-hour TTL. `/tmp` is an in-memory tmpfs on many systems and is cleared on every container restart. Cache entries survive minutes to hours at most.

The plan also stores the cache in the same `/tmp/diagram_forge/` path as transient upload staging files, which creates a security concern (cache files should not be in the same directory as potentially untrusted upload files).

**Impact:** LOW -- Whisper cache misses add latency (5-10s per voice job) but do not cause failures. Cache misses are expected on first use.

**Likelihood:** HIGH -- Cache misses are effectively 100% on every restart.

**Mitigation:** should-fix

**Suggested action:** Move the Whisper cache to the persistent `$DF_DATA_ROOT/cache/` directory alongside the output directory, not `/tmp/`. Add TTL cleanup for the cache directory (separate from the 24-hour temp file cleanup).

---

### RISK-12: Concurrency Model Ambiguity for Async Jobs
**Description:** There is a fundamental ambiguity about how async jobs work:
- The API design uses 202 responses with job IDs, polling, and WebSocket progress streams (implying a job queue)
- The integration design describes a synchronous pipeline (step-by-step processing)
- The main design doc says "stateless" with "iteration is stateless (re-submit full context)"
- scale.md mentions a job queue as a "future scaling" consideration (Phase 2)

If jobs are processed synchronously within the HTTP request handler, the timeout ceiling (30s text, 60s voice, 48s image) is enforced by the server. If the timeout is exceeded, the client gets a timeout error and the job is lost.

If jobs are queued asynchronously (using FastAPI background tasks or a task queue), the architecture is significantly more complex (job state management, dead-letter queue, result persistence, WebSocket fan-out).

The plan is ambiguous about which model is used in Phase 1.

**Impact:** MEDIUM -- The wrong model chosen late in implementation leads to significant rework. A synchronous model limits scalability; an async model adds complexity.

**Likelihood:** MEDIUM -- The 202 + polling API strongly implies async processing, but the integration pipeline is described synchronously.

**Mitigation:** should-fix

**Suggested action:** Explicitly decide in SPEC.md: Phase 1 uses FastAPI `BackgroundTasks` (in-process async, single-container) for the MVP. This provides the 202 + polling API without requiring a separate task queue. Document this as a migration path to a Redis/SQS-backed queue in Phase 2.

---

### RISK-13: Circuit Breaker 30-Second Timeout May Be Too Short
**Description:** The circuit breaker recovery timeout is set to 30 seconds in scale.md. Anthropic API incidents have historically lasted longer than 30 seconds (typically 2-10 minutes for significant outages). A 30-second recovery timeout means the circuit opens, 30 seconds pass, then 3 probe requests are sent. If the API is still degraded, the circuit reopens immediately and the 30-second cycle repeats.

This creates a pattern of probing that: (a) continues to generate API costs during degraded periods, (b) adds latency for legitimate users, and (c) may mask the severity of an ongoing incident by showing intermittent 503s.

**Impact:** MEDIUM -- Repeated circuit trips extend outage windows and generate unnecessary API costs.

**Likelihood:** MEDIUM -- Anthropic API has had multi-minute incidents in the past.

**Mitigation:** should-fix

**Suggested action:** Increase the recovery timeout to 60 seconds. Also consider adding a circuit-breaker alerting rule: alert if the circuit opens more than 3 times in 10 minutes, as this indicates a sustained issue rather than a transient spike.

---

### RISK-14: Async File Deletion Without Confirmation
**Description:** Input files are deleted "immediately after pipeline consumption" and temp files are deleted "immediately after the job completes." These deletions are asynchronous (fire-and-forget). If the process crashes between consumption and deletion (or between completion and deletion), files remain on disk past their intended TTL.

This is compounded by the fact that the cleanup worker runs every 5-10 minutes, so the maximum lag between a crash and cleanup is 10 minutes for staging files and 24 hours for output files (lazy cleanup on access).

**Impact:** LOW -- This is a data retention violation (files exceeding their TTL) but not a security breach if the 24-hour limit is eventually enforced.

**Likelihood:** LOW -- Process crashes are infrequent but not rare.

**Mitigation:** should-fix

**Suggested action:** Use synchronous (blocking) deletion for input and temp files immediately after processing. The 24-hour TTL cleanup is acceptable as an async background task since its purpose is convenience, not security.

---

### RISK-15: No Rollback Plan for Phase 1 Failure
**Description:** The plan has 7 sequential phases with dependencies (Phase N depends on Phase N-1 being complete). If Phase 1 (Text->Excalidraw MVP) fails critically -- for example, the AI generation reliability spike reveals that Claude produces valid Excalidraw JSON only 60% of the time -- there is no defined recovery path.

The plan does not specify: what constitutes "Phase 1 complete," how to measure success, what the exit criteria are, or what the fallback plan is if Phase 1 fails its quality gates.

**Impact:** MEDIUM -- Without clear success criteria and a fallback plan, a Phase 1 failure leads to scope creep (attempting to fix the core approach within Phase 1) or project abandonment (no clear path forward).

**Likelihood:** LOW -- The risk is in the planning gap, not in the technical outcome.

**Mitigation:** should-fix

**Suggested action:** Define explicit Phase 1 exit criteria: (a) >95% of test prompts produce valid Excalidraw JSON, (b) >95% of generated diagrams render correctly in the Excalidraw editor, (c) p50 latency < 5s, p95 < 10s for text modality. If these are not met after the spike + Phase 1 implementation, the fallback plan is: pivot to a template-based approach (pre-defined diagram templates that Claude populates with structured data) rather than free-form generation.

---

## Summary by Mitigation Priority

### must-fix (resolve before Phase 1 begins)
1. **RISK-01**: Add Phase 0 spike to validate Claude JSON generation reliability
2. **RISK-02**: Produce canonical SPEC.md resolving all cross-document conflicts
3. **RISK-03**: Fix per-worker rate limiting (shared store or documented limitation)
4. **RISK-04**: Add spikes for Excalidraw JSON validity, Draw.io export, vision, iteration

### should-fix (resolve during Phase 1 or early Phase 2)
5. **RISK-05**: Increase memory budget or add concurrency controls
6. **RISK-06**: Decide SVG strategy (editable vs. rendered) and account for effort
7. **RISK-07**: Add post-generation schema validation for vision output
8. **RISK-08**: Produce canonical `pyproject.toml` before implementation
9. **RISK-09**: Pin Excalidraw to a specific npm version
10. **RISK-10**: Make completeness check a committed iteration feature task
11. **RISK-11**: Move Whisper cache to persistent storage
12. **RISK-12**: Decide async job architecture explicitly
13. **RISK-13**: Increase circuit breaker timeout to 60 seconds
14. **RISK-14**: Use synchronous deletion for input/temp files
15. **RISK-15**: Define Phase 1 exit criteria and fallback plan

## Open Questions

1. Which SVG strategy should be used for v1: rendered (fast, low value) or editable (slow, high value)?
2. Should `pybreaker` or `tenacity` be used for retries/circuit breaking? These are different libraries with different use cases.
3. Should `pydub` or `mutagen` be used for audio metadata extraction?
4. Is a template-based fallback plan acceptable if Claude JSON generation is unreliable?
5. What is the maximum acceptable malformed-output rate for the product to be viable? (The plan says 5% but this should be validated with users.)
