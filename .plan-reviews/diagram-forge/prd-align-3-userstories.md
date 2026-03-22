# PRD Alignment Review: User Stories Coverage (Round 3)

**Analyst:** user-stories-coverage
**Reviewing:** PRD scenarios against design-doc.md (phases), api.md, ux.md, integration.md, data.md
**Date:** 2026-03-22

---

## Summary

4 user stories reviewed. 2 COVERED, 1 PARTIAL, 1 PARTIAL. **3 MUST-FIX issues** and **7 SHOULD-FIX issues** identified across cross-document conflicts, missing fields, and missing plan tasks.

---

## Scenario 1: Hand-drawn sketch to clean diagram

> Alice sketches an architecture on a whiteboard, takes a photo with her phone, uploads it. Within seconds she downloads an Excalidraw JSON file with clean boxes, arrows, and labels.

**User journey steps:**
1. Upload photo (PNG/JPEG/WebP, max 10MB, 4096x4096px)
2. System auto-detects diagram type (shown as a chip)
3. User confirms/edits diagram type
4. User selects output format (default: Excalidraw)
5. System analyzes image (Claude vision)
6. System generates diagram
7. User downloads Excalidraw JSON file

**Trace:**

| Step | Coverage | Plan Task |
|------|----------|-----------|
| Upload image | COVERED | Integration.md: ImagePipeline Mode A, Step 1 (validation: Content-Type, file size, dimensions, readability) |
| Auto-detect diagram type | GAP | UX.md Flow 1 step 3 describes "auto-detect likely diagram type (shown as a chip: 'Detected: Architecture diagram?')" but the ImagePipeline Mode A in integration.md does NOT include a diagram type detection step. The plan only has Claude vision parse the diagram and output JSON—the type is inferred from the output JSON's `diagram_type` field, not proactively surfaced before generation. |
| Confirm/edit type | DEPENDS | Depends on auto-detect being implemented first |
| Select output format | COVERED | Integration.md: Step 8 Export (for each requested format); ExcalidrawExporter is P1 deliverable |
| Analyze image (Claude vision) | COVERED | Integration.md: Mode A, Step 2 (Claude Vision Analysis: encode image as base64, vision prompt, outputs DiagramModel) |
| Generate diagram | COVERED | Integration.md: Mode A, Steps 2-3 (Claude vision call + output parsing/validation) |
| Download Excalidraw JSON | COVERED | api.md: GET /v1/jobs/{job_id}/download/{format} endpoint; Content-Type: application/json with Content-Disposition attachment header |

**Result: PARTIAL**

- **STEP 2 MISSING PLAN TASK**: Auto-detection of diagram type from uploaded image is described in UX Flow 1 but has no corresponding plan task in the ImagePipeline. The UX explicitly shows "Detected: Architecture diagram?" as a chip the user can confirm or override, but the integration design skips this step and relies on the AI's output type. This is a **must-fix** gap.

- **UX detail not planned**: The UX (Image Tab) also describes an optional "Adjust bounds" cropper UI for trimming edges. This is not present in any plan task. (Should-fix, since UX iteration mentions re-uploading a refined sketch as an alternative to text iteration, but no cropper is planned.)

---

## Scenario 2: Voice to sequence diagram

> Bob is in a meeting, describes an API flow verbally: "The client sends a request to the gateway, which authenticates with OAuth, then calls the user service..." — within seconds, a sequence diagram is ready.

**User journey steps:**
1. User records or uploads audio (max 60s, MP3/WAV)
2. Audio waveform visualizes during recording; timer shows elapsed time
3. On stop, transcription appears as editable text below the waveform
4. User edits transcription if needed
5. User confirms diagram type (auto-detected from transcript or manually set)
6. User selects output format
7. System generates diagram
8. User downloads diagram

**Trace:**

| Step | Coverage | Plan Task |
|------|----------|-----------|
| Record/upload audio | COVERED | Integration.md: VoicePipeline Step 1 (Audio Validation: Content-Type, size, duration, corrupt check) |
| Waveform visualization | UX-ONLY | UX.md Flow 2 step 2 (wavesurfer.js) — this is a client-side UX concern, not a backend plan task |
| Transcription appears | COVERED | Integration.md: VoicePipeline Step 2 (Whisper API Transcription: whisper-1 model, verbose_json response) |
| User edits transcription | COVERED | UX.md Flow 2 step 4; integration design routes edited transcript into the text pipeline identically to a text input |
| Confirm diagram type | COVERED | Integration.md: Step 3 (Diagram Type Inference from text keywords; confidence scoring < 0.7 → ask user) |
| Select output format | COVERED | Integration.md: Step 8 (Export); api.md POST /v1/generate/voice with output_formats |
| Generate diagram | COVERED | Integration.md: Step 4 onward (merge with Text Pipeline: type inference, prompt construction, Claude call, parsing, export) |
| Download diagram | COVERED | api.md: GET /v1/jobs/{job_id}/download/{format} |

**Result: COVERED**

All steps traceable to plan tasks. Two notes:
- **Should-fix**: The UX Flow 2 describes a "df transcript" CLI command (`df transcript --audio ./recording.mp3`) as a standalone convenience tool that outputs only the transcription without generating a diagram. This command is not exposed as a standalone API endpoint in the plan (only as part of the voice generation pipeline). The UX says "This transcribes audio without generating a diagram" — the plan should include a `POST /v1/transcribe` endpoint or clarify this is CLI-only.
- The `language_hint` field in the API design (api.md) is used for transcription but the integration design (integration.md) specifies "language: auto-detect" by default. The plan should clarify whether `language_hint` is respected for Whisper or always auto-detected.

---

## Scenario 3: Text description to architecture diagram

> Charlie writes: "Microservices with API Gateway, Auth Service, User Service, Order Service, Payment Service, Database. Gateway routes to services, services communicate via async messaging." → Clean architecture diagram generated.

**User journey steps:**
1. User types or pastes description (max 4000 chars)
2. Character counter shows remaining capacity
3. User selects diagram type (Architecture / Sequence / Flowchart)
4. User selects output format (Excalidraw / Draw.io / SVG)
5. User clicks Generate
6. System generates diagram
7. User downloads diagram

**Trace:**

| Step | Coverage | Plan Task |
|------|----------|-----------|
| Type/paste description | COVERED | Integration.md: TextPipeline Step 1 (Input Validation: type, length, content check) + Step 2 (Preprocessing: strip, normalize whitespace) |
| Character counter | UX-ONLY | UX.md Text Tab (client-side display of "240 / 4000") |
| Select diagram type | COVERED | Integration.md: Step 3 (Diagram Type Inference if not specified); api.md: diagram_type enum field in request |
| Select output format | COVERED | Integration.md: Step 8 (Export for each requested format); api.md: output_formats array field |
| Generate diagram | COVERED | Integration.md: Steps 4-7 (Prompt construction, Claude API call, response parsing, post-generation validation) |
| Download diagram | COVERED | api.md: GET /v1/jobs/{job_id}/download/{format} |

**Result: COVERED**

All steps traceable. One cross-document conflict noted: the UX default output format is SVG (to show a preview without requiring a tool), but the plan's default is Excalidraw JSON (Phase 1 only has ExcalidrawExporter). SVGExporter is a Phase 2 deliverable. This is a UX/plan mismatch — the UX preview experience assumes SVG is available immediately, but Phase 1 only ships Excalidraw.

---

## Scenario 4: Iterating on existing diagrams

> Diana pastes an existing diagram screenshot and says "make this more modern" or "add a cache layer" → Updated diagram returned.

**User journey steps (from UX "Unified Iteration Flow"):**
1. User uploads original diagram image
2. User types modification instruction (e.g., "add a cache layer" or "make this more modern")
3. System parses existing diagram and applies modification
4. System returns complete updated diagram

**Trace (two sub-scenarios):**

Sub-scenario A: "add a cache layer" (element addition):

| Step | Coverage | Plan Task |
|------|----------|-----------|
| Upload image + instruction | COVERED | Integration.md: Iteration Option A (Image + Text Instruction), ImagePipeline Mode B (vision + iteration) — validates both inputs, sends image + modification text to Claude vision |
| Parse + apply modification | COVERED | Integration.md: Mode B Step 2 (Vision + Modification Analysis: Claude vision parses current diagram AND applies modification in one pass, outputs complete new DiagramModel) |
| Return updated diagram | COVERED | Integration.md: Mode B Step 3 (Post-Generation Validation + Export) |

Sub-scenario B: "make this more modern" (style-only change):

| Step | Coverage | Plan Task |
|------|----------|-----------|
| Upload image + instruction | COVERED | Same Mode B input validation |
| Parse + apply style modification | GAP | Mode B's vision prompt says "Apply ONLY the requested change while preserving everything else" and "If the modification is ambiguous, make a sensible default choice." A "make this modern" instruction is ambiguous — it could mean color palette, shape roundness, font size, or line thickness. The prompt doesn't specify how to handle aesthetic/style-only changes. This is a **should-fix**: add style-change handling guidance to the Mode B prompt or document the expected behavior. |

**Iteration field naming conflict (MUST-FIX):**

- **UX.md** (Unified Iteration Flow): The iteration panel has a text field with placeholder "How should I change this?" and the CLI iteration command uses `--instruction "add a Redis cache layer"`.
- **UX.md** (Iteration API): Sends an `instruction` field: `instruction: "add a Redis cache layer between the gateway and user service"`.
- **api.md** (ImageGenerateRequest): The image generation request uses `iteration_context` (max 2000 chars): `iteration_context: "add a cache layer"`.
- **Plan (integration.md)**: Uses `instruction` in the iteration prompt template but the API parameter name is `iteration_context`.

**Fix:** Rename `iteration_context` in the API schema to `instruction` to match the UX/plan terminology, or rename the UX field to `iteration_context`.

**Result: PARTIAL (must-fix for naming; should-fix for style-only changes)**

---

## Cross-Cutting Issues (Not Tied to a Single Scenario)

### MUST-FIX

1. **SVG export design conflict** (integration.md vs data.md):
   - `integration.md` (Integration Design): Explicitly states "Design decision: Generate **editable SVG** (semantic SVG with grouped elements, text, and arrows as proper SVG elements)." The spec includes semantic `<g>` groups, `<text>` elements, CSS classes, and markers.
   - `data.md` (Data Design): States "v1 produces **rendered SVG** (single vector path tree)" and recommends `@excalidraw/utils export_to_svg()`. "Rendered SVG: all shapes become `<path>` elements with no semantic grouping."
   - These are fundamentally incompatible. Editable SVG has semantic structure; rendered SVG is rasterized vector. The PRD says "fully-editable industry-standard diagrams" and "SVG" as an output format — but rendered SVG is not editable.
   - **Fix**: Choose one direction and ensure all downstream decisions (exporter implementation, UX preview, test strategy) are consistent. The integration.md design is more aligned with the PRD's "editable" goal.

2. **Endpoint routing conflict** (integration.md vs api.md):
   - `integration.md` (Project Structure, routes.py): Single endpoint `POST /v1/diagram` with mode dispatching in the route handler (if/elif for image/voice/text).
   - `api.md` (Endpoint Overview): Three separate endpoints `POST /v1/generate/text`, `POST /v1/generate/image`, `POST /v1/generate/voice`.
   - These are mutually exclusive. A single `/v1/diagram` endpoint cannot coexist with three `/v1/generate/*` endpoints. **Fix**: Decide on the routing strategy (single unified endpoint vs. separate endpoints) and ensure all plan tasks (route handlers, schemas, test cases, CLI commands, WebSocket auth) are consistent with the chosen approach.

3. **Iteration field naming mismatch** (api.md vs ux.md + integration.md):
   - API uses `iteration_context`; UX and plan use `instruction`.
   - **Fix**: Standardize on `instruction` across all documents.

### SHOULD-FIX

4. **Auto-detect diagram type from image** (UX Flow 1 not in plan): UX step 3 shows "Detected: Architecture diagram?" chip for image input. The integration design's ImagePipeline Mode A does not include a type detection step — the type is whatever Claude infers and puts in the output JSON. For a good UX, the type should be surfaced (and confirmable) before generation starts.
   - **Fix**: Add a plan task for diagram type detection from image content (similar to the text type inference in Step 3 of the text pipeline), or clarify that the UX will show the type only after the first generation completes.

5. **Optional image cropper** (UX not planned): UX Image Tab describes "Optional cropper toggle: 'Adjust bounds' — opens a crop/trim UI." This is not present in the ImagePipeline plan. Cropping before upload could improve analysis quality for photos with distracting edges.
   - **Fix**: Add cropper as a Phase 4 UX enhancement, or explicitly defer it.

6. **`df transcript` CLI command not in API plan**: UX describes `df transcript --audio ./recording.mp3` as a standalone command that outputs only transcription. This requires either a `POST /v1/transcribe` endpoint (not present in api.md, though it appears in the UX "API Developer Experience" section) or it must be documented as CLI-only (client-side Whisper call).
   - **Fix**: Add `POST /v1/transcribe` to the API plan, or clarify in the UX that `df transcript` is a client-side convenience using the Whisper API directly.

7. **Storage design conflict** (integration.md vs data.md):
   - `data.md`: Uses `$DF_DATA_ROOT/` with subdirs `input/`, `output/`, `tmp/`, `logs/`, `state/`.
   - `integration.md` (Implementation Note 5): Uses `/tmp/diagram-forge/` with TTL cleanup.
   - `integration.md` (Project Structure): References `storage.py` but no `$DF_DATA_ROOT` environment variable.
   - These must be reconciled. The data.md design is more production-ready (configurable path, separate state directory).
   - **Fix**: Adopt data.md's storage architecture throughout.

8. **`estimated_duration_seconds` not in job model**: UX Flow descriptions and the API response design (api.md GenerateResponse) include `estimated_duration_seconds`. The job record in data.md has timing fields (`whisper_duration_ms`, `ai_generation_duration_ms`, `export_duration_ms`, `total_duration_ms`) but no `estimated_duration_seconds` field. This field needs to be defined: how is it computed? From historical averages? Static per-modality?
   - **Fix**: Add `estimated_duration_seconds` computation logic to the plan (e.g., use p50 latency from the scale design: text=3s, voice=6s, image=12s).

9. **WebSocket `progress_percent` missing from REST polling response**: The UX polling section says "Each poll updates the progress bar and message" and shows a `percent` field in the status response. The api.md job status response includes `progress.stage_progress_percent` in the WebSocket design but the REST `/v1/jobs/{job_id}` response (for polling fallback) does not explicitly show a percent field in the response schema. The UX relies on this for the progress bar.
   - **Fix**: Ensure the REST polling response schema explicitly includes `progress_percent: int | None` so the UX can render the progress bar consistently.

10. **Default output format mismatch (UX vs Phase 1)**: UX says "SVG selected by default because it shows a preview without requiring a tool." Phase 1 only has ExcalidrawExporter. SVGExporter is Phase 2. This means the UX's SVG-preview-first experience is not available in Phase 1.
    - **Fix**: Either change the UX default to Excalidraw for v1, or clarify that the SVG preview UX is Phase 2+.

---

## Verdict

| Scenario | Result | Priority |
|----------|--------|----------|
| S1: Sketch → Excalidraw | PARTIAL | Must-fix (auto-detect not planned) + should-fix (cropper) |
| S2: Voice → Sequence | COVERED | Should-fix (transcribe endpoint, language_hint) |
| S3: Text → Architecture | COVERED | Should-fix (SVG default vs Phase 1, estimated_duration) |
| S4: Iterate diagrams | PARTIAL | Must-fix (field naming) + should-fix (style-only changes) |

**Critical blockers before implementation:**
1. Resolve SVG export conflict (rendered vs editable)
2. Resolve endpoint routing conflict (/v1/diagram vs /v1/generate/*)
3. Standardize iteration field naming (`instruction` vs `iteration_context`)
4. Add diagram type auto-detection task to ImagePipeline plan
