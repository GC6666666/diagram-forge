# UX Design: Diagram Forge

## Overview

Diagram Forge has three input modalities (image, voice, text) producing three diagram types (architecture, sequence, flowchart) in three output formats (Excalidraw JSON, Draw.io XML, SVG). The UX is designed around a single guiding principle: **the user should spend their cognitive energy describing what they want, not figuring out how to use the tool**.

The interface is minimal by default — a single-column layout with three stacked panels that collapse to icons when not in use. The user starts at the top (input) and moves downward (output). The page never feels busy because only the active step is expanded.

---

## User Flows (per Modality)

### Flow 1: Image → Diagram

```
[Upload image] → [Auto-detect diagram type?] → [Confirm/edit type] → [Select output format] → [Generate] → [Download]
```

1. User drops or selects an image (PNG/JPEG/WebP, max 10MB)
2. Image preview appears in a draggable cropper if user wants to trim edges
3. System auto-detects likely diagram type (shown as a chip: "Detected: Architecture diagram?") — user can override with a dropdown
4. User selects output format (Excalidraw / Draw.io / SVG) — defaults to Excalidraw
5. User clicks "Generate" — progress indicator shows "Analyzing image... Generating diagram..."
6. Preview appears inline (SVG rendered; JSON/XML shown as formatted code)
7. User clicks "Download" or "Open in [Excalidraw / Draw.io]"

**Iteration**: User re-uploads the generated diagram image and/or types a modification instruction. The iteration input is the original image + the new instruction text.

### Flow 2: Voice → Diagram

```
[Record / Upload audio] → [Transcription preview] → [Confirm type] → [Select output format] → [Generate] → [Download]
```

1. User clicks the microphone button to record (max 60s) or uploads an MP3/WAV
2. Audio waveform visualizes during recording; timer shows elapsed time
3. On stop, transcription appears as editable text below the waveform
4. User edits transcription if needed (e.g., fix names that Whisper misheard)
5. Same type selection and output format steps as image flow
6. Generate and download

**Iteration**: User re-records or re-uploads audio, or types modification text alongside the original transcription.

### Flow 3: Text → Diagram

```
[Type / paste description] → [Select diagram type] → [Select output format] → [Generate] → [Download]
```

1. User types or pastes a description into the main text area (max 4000 chars)
2. Character counter shows remaining capacity
3. Diagram type selector (Architecture / Sequence / Flowchart) — defaults to Architecture
4. Output format selector — defaults to Excalidraw
5. Generate and download

**Iteration**: User modifies the text description and re-submits, or uploads an existing diagram image with text instructions like "add a cache layer."

### Unified Iteration Flow

All three flows support an "Iterate" action after generation:

```
[Generate] → [Preview] → [Iterate panel expands]
  - Add instruction: "make the arrows curved"
  - OR re-upload image: "use this refined sketch instead"
  - OR re-record voice: "actually, the auth happens first"
  - [Re-generate] → [New preview replaces old]
```

Iteration is stateless: the full new input (image + text instruction, or new audio + instruction, or new text alone) is sent to the API. No session ID, no stored history. This keeps the MVP simple and privacy-friendly.

---

## Web UI Design

### Layout

Single-page application. No navigation. No sidebar. Three vertical panels:

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo: Diagram Forge]               [API Keys] [Docs] [?] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  [Image]  [Voice]  [Text]        ← tab strip        │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │                                                     │    │
│  │  INPUT PANEL (active tab content)                  │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Architecture  Sequence  Flowchart                  │    │
│  │  Diagram Type   [radio pills]                        │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │  Excalidraw    Draw.io    SVG                        │    │
│  │  Output Format [radio pills]                         │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │              [ Generate Diagram ]                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  OUTPUT PANEL                                       │    │
│  │  - SVG preview (rendered inline)                   │    │
│  │  - JSON/XML toggle to view source                  │    │
│  │  - [Download] [Open in Excalidraw] [Open in Draw.io]│    │
│  │  - [Iterate] ← expands input panel with new content │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Input Panel (Image Tab)

- Large drop zone: dashed border, icon, "Drop image or click to browse"
- Supported formats badge: PNG, JPEG, WebP (max 10MB)
- After upload: image thumbnail with filename, size, "Remove" button
- Optional cropper toggle: "Adjust bounds" — opens a crop/trim UI
- Detected type chip: "Detected: Architecture diagram" (auto-inferred from image content)
- "Not right? Change type below" link to the diagram type selector

### Input Panel (Voice Tab)

- Large microphone button with pulsing ring animation when ready
- Timer display: "0:00 / 1:00" (max 60s)
- Waveform visualizer during recording (animated bars)
- After recording/upload: audio player with waveform, transcript below (editable textarea)
- "Re-record" and "Upload instead" links
- Character limit for transcript editing: same as text input (4000 chars)

### Input Panel (Text Tab)

- Textarea with placeholder: "Describe your system... e.g., 'User authenticates via OAuth, then the gateway routes requests to three microservices that communicate over Kafka.'"
- Live character counter: "240 / 4000" with color shift at 90% usage (amber), hard stop at limit
- "Paste from clipboard" button for easy pasting from docs or Slack
- Example prompt chips below: "Architecture from scratch", "API sequence", "Add component to existing" (opens image tab with text pre-filled)

### Control Panel (shared)

- Diagram Type: three pill buttons (Architecture | Sequence | Flowchart). Selected pill has filled background. Icons next to labels (server-stack, arrow-right-left, flowchart).
- Output Format: three pill buttons (Excalidraw | Draw.io | SVG). SVG selected by default because it shows a preview without requiring a tool.
- Generate button: large, full-width in this section, primary color. Shows spinner and "Generating..." text during processing.

### Output Panel

- **Empty state**: subtle icon, "Your diagram will appear here"
- **Loading state**: skeleton preview matching the output format's aspect ratio, animated shimmer
- **Success state**:
  - SVG: inline rendered preview (pan/zoom on hover)
  - JSON/XML: syntax-highlighted code block with a "Preview as SVG" tab
  - "Download" button (format-appropriate extension)
  - "Open in Excalidraw" / "Open in Draw.io" buttons (generates a shareable URL or copies the JSON/XML to clipboard with instructions)
  - "Iterate" button: secondary style, expands the input panel with "Add changes:" text field and the current input (image/thumb or text) still visible
- **Error state**: see Error States section

### Header

- Left: Logo mark + "Diagram Forge" wordmark
- Right: "API Keys" link → modal for entering/validating API key, "Docs" link (opens /docs), "?" link (opens quick-start guide overlay)

### API Key Modal

- Simple: one input field, "Save" button
- Key stored in localStorage (not a server account — this is stateless)
- Shows masked key with "••••••ab12" if set, and a "Remove" button
- "Get an API key" link → opens a tab to the pricing/registration page
- Validation on save: calls a lightweight `/v1/ping` endpoint to verify the key works

### Color & Typography

- Background: `#0F0F0F` (near-black) — dark theme matches developer tooling
- Surface: `#1A1A1A` (card backgrounds)
- Border: `#2A2A2A`
- Primary accent: `#7C5CFF` (purple — used for Generate button, active states)
- Secondary accent: `#00D4AA` (teal — used for success states, download button)
- Text primary: `#FAFAFA`
- Text secondary: `#888888`
- Error: `#FF5C5C`
- Warning: `#FFB347`
- Font: `Inter` for UI, `JetBrains Mono` for code blocks
- Border radius: 8px for cards, 6px for buttons, 4px for inputs

---

## CLI Design

The CLI is a thin wrapper around the REST API. The user sets their API key once via environment variable or config file; subsequent commands do not repeat it.

### Installation

```bash
pip install diagram-forge
# or
brew install diagram-forge
```

### Configuration

```bash
# Option 1: environment variable
export DIAGRAM_FORGE_API_KEY="df_live_..."

# Option 2: config file (~/.config/diagram-forge/config.toml)
api_key = "df_live_..."

# Option 3: per-command flag
df generate --api-key "df_live_..." ...
```

`df` is the CLI binary name. `df help` shows the top-level help.

### Commands

#### `df generate` (primary command)

```bash
# Text input
df generate \
  --text "Microservices: API Gateway, Auth Service, User Service. Gateway routes to services." \
  --type architecture \
  --format excalidraw \
  --output ./my-diagram.excalidraw

# Image input
df generate \
  --image ./sketch.png \
  --type architecture \
  --format drawio \
  --output ./my-diagram.drawio

# Voice input (file)
df generate \
  --audio ./recording.mp3 \
  --type sequence \
  --format svg \
  --output ./my-diagram.svg

# Text with output to stdout
df generate --text "..." --format svg --stdout
```

**Flags:**

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--text` | `-t` | string | — | Text description (max 4000 chars) |
| `--image` | `-i` | path | — | Image file (PNG/JPEG/WebP, max 10MB) |
| `--audio` | `-a` | path | — | Audio file (MP3/WAV, max 60s) |
| `--type` | | enum | `architecture` | Diagram type: `architecture`, `sequence`, `flowchart` |
| `--format` | `-f` | enum | `svg` | Output format: `excalidraw`, `drawio`, `svg` |
| `--output` | `-o` | path | stdout | Output file path |
| `--stdout` | | flag | false | Write output to stdout instead of file |
| `--api-url` | | URL | API URL | Override the API endpoint (for self-hosted) |
| `--api-key` | | string | config/env | API key |

**Exactly one of `--text`, `--image`, or `--audio` is required.**

**Behavior:**
- On success: writes the output file (or outputs to stdout), prints a one-line confirmation to stderr: `Generated: ./my-diagram.svg (2.1s)`
- On error: prints a human-readable message to stderr, exits non-zero
- Progress: streams status updates to stderr (not stdout, so piping remains clean): `Analyzing image...`, `Generating diagram...`, `Done.`

#### `df iterate`

```bash
df iterate \
  --image ./sketch.png \
  --instruction "add a Redis cache layer between API Gateway and User Service" \
  --format excalidraw \
  --output ./my-diagram-v2.excalidraw
```

**Flags:**

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--image` | `-i` | path | — | Image file to iterate on |
| `--instruction` | | string | — | Text instruction for the change |
| `--format` | `-f` | enum | `svg` | Output format |
| `--output` | `-o` | path | stdout | Output file path |

#### `df transcript` (voice-only convenience)

```bash
df transcript --audio ./recording.mp3
# Outputs: "The client sends a request to the gateway, which authenticates..."
```

This transcribes audio without generating a diagram — useful for checking what Whisper heard before committing to generation.

#### `df ping`

```bash
df ping
# Output: "Connected to Diagram Forge API (v1.2.0). Key: df_live_...ab12. Status: OK."
```

Validates the API key and prints server version and status.

#### `df docs`

Opens the API documentation in a browser: `df docs --format restclient` opens curl examples, `df docs --format openapi` downloads the OpenAPI spec.

### Tab Completion

Bash/Zsh/Fish completions are generated via `df completion --shell bash > /etc/bash_completion.d/df`. Completion suggests `--type` and `--format` enum values.

### Error Output

CLI errors are printed to stderr in a consistent format:

```
Error: input too large (image is 14.2 MB, maximum is 10 MB)
Hint: compress the image or crop it to reduce file size
```

```
Error: generation failed (diagram_type_unsupported)
Detail: Sequence diagrams do not support more than 20 participants
Hint: reduce the number of participants in your description
```

```
Error: authentication failed (invalid_api_key)
Hint: check your API key with 'df ping' or update it via df config --api-key "..."
```

Exit codes: 1 for general errors, 2 for validation errors, 3 for auth errors.

---

## API Developer Experience

### Overview

The API is REST over HTTPS, JSON request/response. Stateless — no sessions, no accounts, no stored diagrams. Authentication via `X-API-Key` header or `Authorization: Bearer` header.

**Base URL:** `https://api.diagramforge.ai/v1` (self-hosted users replace with their own URL)

### Endpoints

#### `POST /v1/generate`

Primary generation endpoint. Accepts image, audio, or text input.

**Request (multipart form):**

```
POST /v1/generate
X-API-Key: df_live_...
Content-Type: multipart/form-data

diagram_type: "architecture"
output_format: "excalidraw"
input_type: "image"  | "audio" | "text"
```

With one of:
- `image`: binary file upload (PNG/JPEG/WebP, max 10MB)
- `audio`: binary file upload (MP3/WAV, max 60s)
- `text`: plain text string (max 4000 chars)

**Response (200 OK):**

```json
{
  "id": "gen_01j8xyz",
  "status": "completed",
  "diagram_type": "architecture",
  "output_format": "excalidraw",
  "content": "{ ... Excalidraw JSON ... }",
  "content_encoding": "base64",
  "metadata": {
    "generation_time_ms": 1840,
    "input_chars": 240,
    "model": "claude-sonnet-4-20250514"
  },
  "created_at": "2026-03-22T10:30:00Z"
}
```

For SVG output, `content` is the SVG string directly (not base64 encoded, since it's text). For Excalidraw JSON and Draw.io XML, `content_encoding` is always `base64`.

**Response (async / processing):**

If generation takes more than a few seconds, the API returns `202 Accepted`:

```json
{
  "id": "gen_01j8xyz",
  "status": "processing",
  "poll_url": "/v1/status/gen_01j8xyz",
  "message": "Image analysis in progress..."
}
```

The client polls `/v1/status/{id}` until `status` becomes `completed` or `failed`.

#### `GET /v1/status/{id}`

Poll for async job status.

**Response:**

```json
{
  "id": "gen_01j8xyz",
  "status": "processing" | "completed" | "failed",
  "progress": {
    "step": "generating_diagram",
    "message": "Generating diagram from parsed structure...",
    "percent": 65
  },
  "result": { ...same as generate response... },
  "error": null
}
```

#### `POST /v1/transcribe`

Audio-only transcription (Whisper). Useful for previewing transcription before generating.

**Request:** `audio` file upload (multipart)

**Response:**

```json
{
  "text": "The client sends a request to the gateway, which authenticates with OAuth...",
  "language": "en",
  "duration_seconds": 34.2
}
```

#### `GET /v1/ping`

Lightweight auth check. Returns server version, key status, and current rate limit quota.

```json
{
  "status": "ok",
  "version": "1.2.0",
  "key_status": "valid",
  "key_prefix": "df_live_...ab12",
  "rate_limit": {
    "requests_remaining": 47,
    "reset_at": "2026-03-22T11:00:00Z"
  }
}
```

### OpenAPI / Swagger

The API ships with self-hosted OpenAPI 3.1 documentation at:
- **Swagger UI**: `GET /docs` — interactive API explorer
- **ReDoc**: `GET /redoc` — cleaner reference documentation
- **OpenAPI JSON**: `GET /openapi.json` — spec file for code generation
- **OpenAPI YAML**: `GET /openapi.yaml` — spec file for Postman, Insomnia

The Swagger UI is the primary developer onboarding surface. It should:
1. Load with an `Authorize` button pre-populated if `DF_API_KEY` env var is set (via a script that reads the env var and sets the auth header in the Swagger UI)
2. Show realistic example requests for each endpoint
3. Include a "Try it out" button that works with the real API (or a sandbox)

### SDKs / Client Libraries

The CLI doubles as the reference client library for Python:

```python
from diagram_forge import DiagramForge

client = DiagramForge(api_key="df_live_...")
result = client.generate(
    text="Microservices architecture with API Gateway and three services",
    diagram_type="architecture",
    output_format="excalidraw"
)
print(result.content)
```

Generated SDKs for TypeScript/JavaScript and Go are produced from the OpenAPI spec via `openapi-generator` and published to npm and pkg.go.dev.

### Developer Onboarding

1. User lands on `https://diagramforge.ai` → "Get API Key" CTA
2. After signup, lands on a quick-start page with:
   - API key (masked, copyable)
   - `curl` example for the simplest call
   - `pip install diagram-forge` + `df generate --text "..."` example
   - Link to `/docs` (Swagger UI)
3. SDK documentation lives at `https://diagramforge.ai/docs` alongside the Swagger UI

---

## Error States

### User-Facing Errors (Web UI)

Errors appear inline in the Output Panel, replacing the empty state or the previous result. A dismissible error card with a distinctive red left border:

```
┌──────────────────────────────────────────┐
│ ⚠ Something went wrong                   │
│                                          │
│ Image is too large (14.2 MB). Maximum    │
│ size is 10 MB.                          │
│                                          │
│ [Compress image]  [Retry]  [✕ Dismiss]   │
└──────────────────────────────────────────┘
```

**Error types and recovery actions:**

| Error Code | Message | Recovery Action |
|------------|---------|----------------|
| `input_too_large` | "Image exceeds 10 MB limit" | "Compress image" → links to a client-side compressor using browser Canvas API |
| `input_too_long` | "Text exceeds 4000 character limit" | Input textarea highlights excess; user trims |
| `audio_too_long` | "Audio exceeds 60 second limit" | Timer turns red when approaching limit |
| `invalid_file_type` | "Unsupported file type. Use PNG, JPEG, WebP, MP3, or WAV." | File picker reopens with type filter set |
| `invalid_api_key` | "API key is invalid or expired" | "Add API Key" button opens the key modal |
| `rate_limit_exceeded` | "Rate limit reached. Try again in X minutes." | Countdown timer showing reset time |
| `generation_failed` | "Diagram generation failed. [Retry]" | Retry button; if it recurs, "Contact support" link |
| `unsupported_diagram_type` | "That diagram type isn't supported for this input" | Type selector re-highlights with available options |
| `parse_error` | "Couldn't understand the input. Try rephrasing." | Focus moves to input panel with suggestions |

**Network errors** (offline, timeout) show a different card:

```
┌──────────────────────────────────────────┐
│ ⚠ Connection lost                        │
│                                          │
│ Check your internet connection and       │
│ try again.                               │
│                                          │
│ [Retry]                                  │
└──────────────────────────────────────────┘
```

All errors are logged to the browser console with a correlation ID. The correlation ID is shown in error cards so users can report it: "Error ID: df_err_01j8xyz".

### API Error Responses

All error responses follow a consistent shape:

```json
{
  "error": {
    "code": "generation_failed",
    "message": "Diagram generation failed",
    "detail": "Claude API returned an empty response",
    "correlation_id": "df_err_01j8xyz",
    "docs_url": "https://diagramforge.ai/docs/errors/generation_failed"
  }
}
```

HTTP status codes: 400 (validation), 401 (auth), 403 (forbidden/quota), 413 (payload too large), 422 (unprocessable input), 429 (rate limited), 500 (server error).

### CLI Error Output

Consistent format to stderr (see CLI Design section). Never print stack traces to the user. Write full traces to a log file (`~/.local/share/diagram-forge/logs/`).

---

## Loading / Progress States

### Web UI

The Generate button transitions through labeled states:

1. **Idle**: Button shows "Generate Diagram" with a wand icon
2. **Analyzing** (image/audio only): Button shows spinner + "Analyzing..." — subtitle shows step: "Parsing image...", "Transcribing audio...", "Understanding diagram structure..."
3. **Generating**: Button shows spinner + "Generating..." — subtitle: "Building Excalidraw diagram..."
4. **Done**: Button briefly flashes teal with checkmark, then resets to "Generate Diagram" (the output panel now shows the result)

The Output Panel shows a **skeleton loader** during all three phases (analyzing and generating share the same loader):

```
┌─────────────────────────────────────────┐
│  ┌────────────────────────────────────┐  │
│  │  ████████████████  (shimmer)      │  │
│  │  ██████████                       │  │
│  │                                    │  │
│  │  ████████████  ██████  ████████  │  │
│  │  ████████  ██████████████         │  │
│  └────────────────────────────────────┘  │
│                                         │
│  Analyzing...  ·  Generating...         │
│  ████████████░░░░░░░░░  62%            │
└─────────────────────────────────────────┘
```

The skeleton matches the aspect ratio of the expected output (detected from diagram type: architecture ~16:9, sequence ~4:3 tall, flowchart ~1:1 or variable).

### Polling (Async Jobs)

For long-running jobs (>5s), the page polls `GET /v1/status/{id}` every 2 seconds. Each poll updates the progress bar and message. A timeout after 60s triggers a "This is taking longer than expected" banner with options to "Wait" (continue polling) or "Cancel and retry."

### CLI Progress

Streaming status lines written to stderr (not stdout):

```
$ df generate --image ./sketch.png --format excalidraw --output out.excalidraw
Analyzing image...          [=========================>                 ]  45%
Generating diagram...       [============>                              ]  20%
Done. Wrote 42.1 KB to out.excalidraw (3.2s)
```

The progress bar uses ASCII characters so it works in all terminals. When stdout is piped (`df generate ... > out.excalidraw`), progress is still streamed to stderr and the piped output is the clean file content.

---

## Iteration UX

Iteration is the key differentiator for the "fast iteration" goal. The design prioritizes friction-free iteration over any notion of version history.

### Web UI Iteration

After a diagram is generated:

1. The Output Panel gains an **"Iterate"** button below the download actions
2. Clicking "Iterate" causes the Input Panel to expand upward (smooth animation, 300ms) without losing the current input (image thumbnail or text stays visible)
3. A new field appears: **"How should I change this?"** — a text input with placeholder: "e.g., 'add a Redis cache layer' or 'use curved arrows' or 'change the auth to JWT'"
4. The current input context is visually grouped with the new instruction:
   ```
   ┌─ Current input ──────────────────────────────┐
   │ [thumbnail of sketch.png]                    │
   │ Detected: Architecture diagram                │
   └─────────────────────────────────────────────┘
   ┌─ Change request ─────────────────────────────┐
   │ How should I change this?                     │
   │ [add a Redis cache layer between gateway...]  │
   └─────────────────────────────────────────────┘
   ```
5. "Regenerate" button (same style as Generate, but teal-accented to indicate it's an update)
6. On submit, the Output Panel clears and shows the skeleton loader; the new result replaces the old
7. "Iterate" remains available for subsequent rounds

**Image + Text iteration**: If the user wants to iterate on an image but also clarify with text, both are shown together. The image upload area shows the current image with a "Replace" button.

**Keyboard shortcut**: `Ctrl+I` (or `Cmd+I`) opens the iterate panel from anywhere on the page.

### CLI Iteration

```bash
df iterate --image ./sketch.png --instruction "add a Redis cache layer" --format excalidraw --output v2.excalidraw
```

Or pipe the instruction:

```bash
echo "add a Redis cache layer" | df iterate --image ./sketch.png --format svg --stdout > v2.svg
```

### API Iteration

Send the original image (or text) plus a new `instruction` field:

```
POST /v1/generate
X-API-Key: df_live_...

diagram_type: "architecture"
output_format: "excalidraw"
input_type: "image"
instruction: "add a Redis cache layer between the gateway and user service"
```

The `instruction` field is the new addition for iteration. It's optional; if omitted, the behavior is a fresh generation.

---

## Implementation Notes

### Web UI Technical Decisions

- **Framework**: Single-page app in React or Svelte (server-rendered shell with client-side interactivity). No SSR needed since the app is fully client-driven after initial load.
- **State management**: Simple local state per panel. No global state library needed for v1.
- **API key storage**: `localStorage` with the key `df_api_key`. No cookie-based storage since there is no session.
- **Image preview**: Use `URL.createObjectURL()` for client-side preview before upload, revoke on cleanup.
- **File validation**: Check file type by magic bytes (not just extension) on the client side to prevent wrong uploads from hitting the API. File size checked client-side before upload.
- **Audio recording**: Web Audio API + MediaRecorder. Graceful degradation on browsers that don't support recording (show upload-only mode).
- **Waveform visualization**: `wavesurfer.js` for audio waveform rendering — both for the recording view and playback of uploaded audio.
- **Progress streaming**: For the web UI, switch from sync `POST /v1/generate` to async `POST /v1/generate` + `GET /v1/status/{id}` polling. Show the `percent` field from the status response in the progress bar.
- **SVG preview**: Render SVG inline via an `<object>` or directly in the DOM. Use `pointer-events: none` on the SVG container to prevent accidental text selection. Add a pan/zoom overlay (e.g., `panzoom` library) on hover.
- **Keyboard navigation**: Full keyboard accessibility. Tab order: tabs → input area → controls → generate button → output panel actions. Enter submits. Escape cancels/closes modals.
- **Responsive**: The layout works on desktop (max-width: 720px centered) and tablet. Mobile is functional but not optimized (non-goal).

### CLI Technical Decisions

- **Language**: Python (matches the backend). Packaged via `pyproject.toml` / `pip install`.
- **HTTP client**: `httpx` for async support and streaming responses.
- **Streaming output**: Use httpx's streaming to receive SSE or chunked progress updates from the API, print them to stderr.
- **Config file**: TOML at `~/.config/diagram-forge/config.toml` using `tomllib` (Python 3.11+).
- **Completion**: Generated via `argparse` + `shtab` or `argcomplete`.
- **Binary distribution**: PyInstaller or `uv` + ` maturin`-style cross-platform build. Also publish to Homebrew.
- **API key priority**: CLI flag `--api-key` > environment variable `DIAGRAM_FORGE_API_KEY` > config file > `~/.config/diagram-forge/config.toml`.

### API Technical Decisions

- **Async generation**: Any generation call that exceeds 3s server-side processing time returns `202 Accepted` with a `poll_url`. The server processes the job asynchronously (e.g., using a task queue or background threads). Clients are expected to poll.
- **Progress SSE** (optional enhancement): Instead of polling, clients can request `Accept: text/event-stream` and receive server-sent events for progress updates. Fallback to polling for clients that don't support SSE.
- **Rate limiting**: Token bucket per API key. Default: 60 requests/minute. Return `Retry-After` header on 429.
- **CORS**: Allow all origins (`Access-Control-Allow-Origin: *`) for the public API since it's expected to be called from browser-based tools.
- **Upload handling**: Use streaming multipart parsing (`python-multipart` with `Starlette`) so large file uploads don't fill memory. Stream the file directly to the AI provider where possible.
- **API versioning**: URL-based (`/v1/`, `/v2/`). Breaking changes increment the version. Old versions supported for 12 months after a new version ships.
- **Request IDs**: Every response includes an `X-Request-ID` header. Logs are indexed by request ID for debugging.
- **OpenAPI spec quality**: Use Pydantic models as the single source of truth for both runtime validation and OpenAPI schema generation (via `starlette-openapi` or `fastapi-utils`). This ensures the Swagger docs always match the actual API behavior.
