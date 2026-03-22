# Plan Review: Diagram Forge -- Testability

**Reviewer:** claude-opus-4-6
**Date:** 2026-03-22
**Docs reviewed:** design-doc.md, api.md, data.md, ux.md, scale.md, security.md, integration.md
**Scope:** All 7 phases of the phased implementation plan

---

## Summary

The plan has good structural coverage (API contracts, data models, pipeline steps, error codes), but testability is uneven. Several phases lack explicit acceptance criteria or have criteria that require human judgment. Test tasks are rarely named explicitly; they are implied by the structure. The most critical gaps are in AI output quality verification and end-to-end validation.

---

## Per-Phase Analysis

### Phase 1: Text-to-Excalidraw MVP

| Check | Finding |
|-------|---------|
| Clear acceptance criteria? | Partial. The API docs define endpoints and error codes precisely, and the integration doc lists 8 pipeline steps with specific validations (length checks, schema validation, element count bounds). These are verifiable. |
| Auto-verifiable? | Partially. Input validation (4000 chars, non-empty, not whitespace-only) is trivially unit-testable. Claude output quality (does the diagram look right?) is NOT auto-verifiable. |
| Test tasks planned? | No explicit test tasks exist. The integration doc's `tests/` directory layout names test files (`test_models.py`, `test_exporters.py`, `test_json_repair.py`, etc.) but these are documentation of structure, not implementation tasks. No "add test for X" tasks appear in the plan. |
| Integration test? | Not explicitly planned. `test_text_pipeline.py` in the directory layout suggests one exists conceptually, but no task defines its scope, inputs, or pass criteria. |
| Independent verification? | Yes, approximately. The FastAPI skeleton, auth, and CLI can each be verified independently before integration. |

**VAGUE-CRITERIA (should-fix):** "Text-to-Excalidraw MVP" -- the plan never defines what "MVP" means for output quality. Does a valid Excalidraw JSON with one rectangle count as MVP success? Or is a multi-element architecture diagram required? No minimum element count, no structural requirement. **Suggested rewrite:** "Text-to-Excalidraw MVP: submit a text description of a 3+ node architecture; receive a valid Excalidraw JSON v2 containing at least 3 shape elements and at least 2 arrow connections, parseable by the Excalidraw web app."

**MISSING-TEST (should-fix):** Claude output quality for text input has no test task. The "Format validity: 100%" target in scale.md is a criterion, but there's no task to verify this across a suite of inputs. **Suggested:** "Add integration test: submit 10 diverse text descriptions, verify 100% produce valid parseable Excalidraw JSON and 80%+ contain the expected element types (verified by JSON schema + element count heuristics)."

---

### Phase 2: Multi-format export (+Draw.io, +SVG)

| Check | Finding |
|-------|---------|
| Clear acceptance criteria? | Weak. The plan names the goal ("+Draw.io, +SVG") but defines no acceptance criteria for output correctness. |
| Auto-verifiable? | Partially. Format validity (valid XML, valid SVG) is auto-verifiable. Structural correctness (does the Draw.io XML contain the right shapes?) requires either a parser or human review. |
| Test tasks planned? | No. The `test_exporters.py` file in the directory layout is noted but no task creates it. |
| Integration test? | Not explicitly planned. |

**MISSING-TEST (should-fix):** No test task for exporter correctness. Each exporter needs roundtrip or structural validation. **Suggested:** "Add unit test for each exporter: given a known DiagramModel with 3 rectangles, 2 arrows, 1 text label, verify: (1) Excalidraw JSON parses as valid JSON and validates against Excalidraw schema; (2) Draw.io XML parses as valid XML with the expected mxCell count; (3) SVG parses as valid XML and contains the expected `<rect>` and `<text>` elements."

**VAGUE-CRITERIA (must-fix):** "Prompt library" -- this is listed as part of Phase 2 but with no definition of scope. How many prompts? What counts as "complete"? No acceptance criteria. **Suggested rewrite:** "Prompt library: store at least 1 system prompt and 1 user template per diagram type (architecture, sequence, flowchart) in `/src/ai/prompts/diagram_types/`. Each prompt must produce valid Excalidraw JSON on the integration test suite (see Phase 1 test gap)."

---

### Phase 3: Voice input (+Whisper API)

| Check | Finding |
|-------|---------|
| Clear acceptance criteria? | Moderate. The voice pipeline steps are well-defined (Steps 1-7), with specific error codes (VOICE_001 through VOICE_007). Input validation (duration, format, size) is clearly specified and testable. |
| Auto-verifiable? | Partially. Input validation is auto-testable. Whisper transcription accuracy is not auto-testable. |
| Test tasks planned? | No. `test_voice_pipeline.py` is named in directory layout but no task creates it. |
| Integration test? | Not explicitly planned. |

**MISSING-TEST (should-fix):** Voice pipeline integration tests are not planned. **Suggested:** "Add `test_voice_pipeline.py`: (1) mock Whisper API to return known transcript; (2) submit audio fixture; (3) verify pipeline calls Whisper with correct params; (4) verify transcript is passed to Claude; (5) verify final diagram is produced. Also: test that corrupt audio returns VOICE_004."

**VAGUE-CRITERIA (should-fix):** "Voice input" -- no criteria for what counts as working voice input. Is a 1-second silence acceptable? Is a non-English audio acceptable? The pipeline defines what happens but not what "success" means for the phase. **Suggested rewrite:** "Voice input: submit a 30-second MP3 fixture containing a clear English technical description; pipeline transcribes via Whisper and produces a valid diagram. Verify: (1) Whisper called with correct model param, (2) transcript text is non-empty, (3) diagram JSON is valid."

---

### Phase 4: Image input (+Claude vision)

| Check | Finding |
|-------|---------|
| Clear acceptance criteria? | Moderate. Image validation steps are specific (magic bytes, dimensions, PIL decode). Error codes IMAGE_001 through IMAGE_007 are defined. But output quality (does Claude correctly interpret the image?) is subjective. |
| Auto-verifiable? | Partial. Input validation is auto-testable. Vision output quality is not. |
| Test tasks planned? | No. `test_image_pipeline.py` is named but no task creates it. |
| Integration test? | Not explicitly planned. |

**MISSING-TEST (should-fix):** Image pipeline integration tests not planned. **Suggested:** "Add `test_image_pipeline.py`: (1) fixture image of a simple flowchart; (2) mock Claude vision response to return a known valid DiagramModel; (3) verify pipeline produces diagram; (4) test each error code path (IMAGE_001 corrupt file, IMAGE_002 oversized file, IMAGE_003 oversize dimensions, IMAGE_007 empty elements)."

**UNTESTABLE (must-fix):** "Claude vision" output quality -- the plan cannot verify that Claude correctly analyzes a given image. The target ">80% structural accuracy" in scale.md is "judged by human review," meaning this criterion is not automatable. This is an inherent property of AI-based features and may be acceptable as a "should-fix" with the understanding that subjective quality cannot be fully automated. However, at minimum: **Suggested:** "Add smoke test: submit a test image fixture (generated programmatically, not hand-drawn) where the expected element count and types are known; verify the returned DiagramModel has at least N elements (where N is the known minimum from the fixture)."

---

### Phase 5: Iteration on existing diagrams (re-submit)

| Check | Finding |
|-------|---------|
| Clear acceptance criteria? | Weak. The UX doc describes the iteration flow in detail, but the plan phase just says "Iteration on existing diagrams (re-submit)." No acceptance criteria, no success definition. |
| Auto-verifiable? | No. Without knowing what "iteration" means concretely, nothing is verifiable. |
| Test tasks planned? | No. |
| Integration test? | No. |

**UNTESTABLE (must-fix):** Phase 5 has zero acceptance criteria. "Iteration on existing diagrams" could mean anything. What is the expected behavior? What inputs produce what outputs? What counts as success? **Suggested rewrite:** Define at minimum: (1) Given an image of a diagram + a text instruction, the pipeline produces a new diagram that differs from the input by the specified modification. (2) Given a text description + a text instruction, the pipeline produces a modified diagram. (3) Test that the iteration completeness check (integration.md line ~836) correctly detects missing elements and retries. Without this definition, no test can be written.

**MISSING-TEST (should-fix):** Even if criteria were defined, no test task exists. **Suggested:** "Add iteration integration tests: (1) image + instruction produces output, (2) text + instruction produces output, (3) element preservation check triggers retry on missing elements, (4) error INCOMPLETE_ITERATION returned after 2 retries."

---

### Phase 6: Precise iteration (Excalidraw JSON parser)

| Check | Finding |
|-------|---------|
| Clear acceptance criteria? | Weak. Named as a deferred task ("Excalidraw JSON → DiagramModel parser") but no acceptance criteria. The integration doc says this is needed for "most precise iteration mode." |
| Auto-verifiable? | Partially, once criteria are defined. The parser output can be validated against DiagramModel schema. |
| Test tasks planned? | No. |
| Integration test? | No. |

**UNTESTABLE (must-fix):** "Precise iteration" -- no acceptance criteria. What does "precise" mean? What is the parser expected to parse? All Excalidraw element types? Only the subset used in v1? How are unbound arrows handled? **Suggested rewrite:** "Excalidraw JSON parser: implement `parse_excalidraw_json(json: dict) -> DiagramModel` that correctly maps Excalidraw element types (rectangle, diamond, ellipse, text, arrow, line, frame) to DiagramModel elements. Test: given a fixture .excalidraw.json with known elements, verify the parser returns a DiagramModel with matching element count and correct type mapping."

---

### Phase 7: Operational hardening (metrics, alerting, multi-container)

| Check | Finding |
|-------|---------|
| Clear acceptance criteria? | Partial. Metrics to expose are listed in scale.md (Prometheus metric names). Multi-container is a structural goal. But alerting thresholds are described ("error rate >5%", "p95 latency >2x target") without specifying who receives alerts or how. |
| Auto-verifiable? | Partially. Prometheus metric exposure is verifiable via `GET /metrics`. Multi-container docker-compose is verifiable by running `docker-compose up`. |
| Test tasks planned? | No. |
| Integration test? | No. |

**MISSING-TEST (should-fix):** Operational hardening has no test tasks. **Suggested:** "Add health endpoint test: `GET /health` returns 200 with expected fields (status, version, uptime_seconds). Add readiness test: `GET /ready` returns 503 when Claude circuit breaker is open. Add Prometheus metrics test: verify `GET /metrics` contains `diagram_forge_requests_total` and `diagram_forge_request_duration_seconds` after processing a request. Add docker-compose test: `docker-compose up` starts without error, health check passes within 30s."

**VAGUE-CRITERIA (should-fix):** "Multi-container" -- is this about running 2 uvicorn workers, or deploying to Kubernetes, or something else? No definition. **Suggested rewrite:** "Multi-container readiness: verify the service runs correctly with `--workers 2` (uvicorn multi-worker) and all semaphores/rate-limiters function correctly across workers (note: in-memory limits are per-worker in this config, document this limitation)."

---

## Cross-Cutting Issues

### 1. No E2E test is ever planned

The plan describes a complete user flow (upload image/audio/text -> wait -> download diagram) but never includes an end-to-end test that exercises the full stack. The integration tests in `tests/integration/` are named but never taskified.

**Recommendation (must-fix):** Add an E2E test task before Phase 1 is considered complete: "Add E2E test: start service with mocked Claude/Whisper APIs (responses recorded or mocked), submit a text request via `POST /v1/generate/text`, poll for completion, verify download URL returns valid Excalidraw JSON. Run in CI on every PR."

### 2. AI output quality has no testable criterion

The ">80% structural accuracy" target (scale.md) is qualified as "judged by human review." This means the most important quality metric for the product cannot be verified automatically. This is an inherent AI-product risk, but it should be acknowledged and mitigated:

**Recommendation (should-fix):** Define a fixed "golden fixture" -- a set of 5-10 text descriptions with known expected outputs (element counts, types, approximate positions). This does not replace human review but provides a regression suite: if Claude starts producing diagrams with zero elements, or only 1 element when 5 are expected, the golden fixture test fails. This is not "80% accuracy" but it catches regressions.

### 3. No test coverage requirement is defined

The plan never states a coverage target. The integration doc names test files but no coverage threshold.

**Recommendation (should-fix):** State: "All code must maintain >80% line coverage per `pytest --cov`. Critical paths (input validation, error code paths, exporter roundtrips) must have 100% branch coverage."

### 4. No mention of mocking strategy

Integration tests with external APIs (Claude, Whisper) require mocking. The plan never discusses how to mock these APIs in tests. Will mocks use `responses`/`httpretty`/`aioresponses`? Will they use recorded fixtures (VCR-style)? Will they use a mock server?

**Recommendation (should-fix):** Add a task: "Set up mock API layer for integration tests: use `aioresponses` to mock Claude and Whisper HTTP calls with fixture responses. Record at least 3 response fixtures per pipeline (success, transient error, permanent error)."

### 5. Prompt library has no regression test

The prompt library (Phase 2) is central to output quality but has no test. If the architecture prompt changes, nothing verifies the change doesn't break output validity.

**Recommendation (should-fix):** "Add prompt library regression test: for each prompt (architecture, sequence, flowchart), submit the prompt + a known test description to the Claude mock; verify the response produces valid Excalidraw JSON. Run on every prompt file change."

---

## Classification Summary

| Phase | Issue | Severity |
|-------|-------|----------|
| P1 | No explicit test tasks; MVP success undefined | should-fix |
| P1 | AI output quality (>80% accuracy) is manual-only | should-fix |
| P1 | Golden fixture regression suite missing | should-fix |
| P2 | "Prompt library" has no acceptance criteria | should-fix |
| P2 | Exporter test task missing | should-fix |
| P3 | Voice pipeline integration test missing | should-fix |
| P3 | Voice success criteria vague | should-fix |
| P4 | Image pipeline integration test missing | should-fix |
| P4 | Vision output quality un-testable (AI inherent) | should-fix (mitigate with golden fixture) |
| P5 | Zero acceptance criteria | must-fix |
| P5 | Iteration test task missing | must-fix |
| P6 | "Precise iteration" acceptance undefined | must-fix |
| P7 | Health/readiness/metrics test task missing | should-fix |
| P7 | "Multi-container" definition vague | should-fix |
| All | No E2E test planned | must-fix |
| All | No test coverage target | should-fix |
| All | No mocking strategy defined | should-fix |
| All | Prompt regression suite missing | should-fix |

**Must-fix count: 4**
**Should-fix count: 13**

---

## Verdict

The plan is well-structured architecturally but under-specified for testability. The four must-fix items (Phase 5 criteria, Phase 6 criteria, E2E test, and the Phase 5/6 test tasks) are blocking: without them, Phases 5 and 6 cannot be verified, and without an E2E test, no phase can be considered complete. The 13 should-fix items are important for engineering quality but do not block progress.
