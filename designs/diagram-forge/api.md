# API Design: Diagram Forge

## 1. Endpoint Overview

Base URL: `https://api.diagramforge.dev/v1`

All endpoints are version-prefixed. The API is stateless; no sessions, no cookies. All file storage is temporary (24h TTL).

### 1.1 Endpoint Matrix

| Method | Path | Description | Sync? |
|--------|------|-------------|-------|
| `POST` | `/generate/text` | Submit text description, get diagram | Async |
| `POST` | `/generate/image` | Upload image, get diagram | Async |
| `POST` | `/generate/voice` | Upload audio, get diagram | Async |
| `GET` | `/jobs/{job_id}` | Poll job status and retrieve result | Sync |
| `GET` | `/jobs/{job_id}/download/{format}` | Download diagram in specific format | Sync |
| `WebSocket` | `/ws/jobs/{job_id}` | Stream job progress events | Async |
| `GET` | `/health` | Liveness check | Sync |
| `GET` | `/ready` | Readiness check (all deps up) | Sync |
| `GET` | `/ui/*` | Web UI static assets | Sync |

---

## 2. Request/Response Schemas

All request bodies are `multipart/form-data` or `application/json`. All responses are `application/json` unless noted.

### 2.1 Text Generation

**Endpoint:** `POST /v1/generate/text`

**Request (application/json):**

```json
{
  "description": "Microservices with API Gateway, Auth Service, User Service, Order Service, Payment Service, Database. Gateway routes to services.",
  "diagram_type": "architecture",
  "output_formats": ["excalidraw", "drawio", "svg"],
  "style_hint": "modern minimal",
  "idempotency_key": "client-uuid-v4"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `description` | string | Yes | 1-4000 chars |
| `diagram_type` | enum | Yes | `architecture`, `sequence`, `flowchart` |
| `output_formats` | string[] | No | Default: `["excalidraw"]` |
| `style_hint` | string | No | Free text, 0-200 chars |
| `idempotency_key` | string | No | Client-provided UUIDv4; dedupes requests within 24h |

**Response (202 Accepted):**

```json
{
  "job_id": "job_01J8K4N2P3Q5R6S7T8U9V0W1X2",
  "status": "queued",
  "created_at": "2026-03-22T14:30:00.000Z",
  "estimated_duration_seconds": 8,
  "status_url": "wss://api.diagramforge.dev/v1/ws/jobs/job_01J8K4N2P3Q5R6S7T8U9V0W1X2",
  "poll_url": "https://api.diagramforge.dev/v1/jobs/job_01J8K4N2P3Q5R6S7T8U9V0W1X2"
}
```

### 2.2 Image Generation

**Endpoint:** `POST /v1/generate/image`

**Request (multipart/form-data):**

```
Content-Type: multipart/form-data

image: <file upload>
diagram_type: architecture
output_formats: excalidraw,drawio
style_hint: modern minimal
idempotency_key: client-uuid-v4
iteration_context: optional prior diagram text description
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `image` | binary | Yes | PNG/JPEG/WebP, max 10MB, max 4096x4096px |
| `diagram_type` | string | No | Default: auto-detect |
| `output_formats` | string | No | Comma-separated. Default: `excalidraw` |
| `style_hint` | string | No | Free text, 0-200 chars |
| `iteration_context` | string | No | 0-2000 chars; describes modification intent |
| `idempotency_key` | string | No | Client-provided UUIDv4 |

**Response (202 Accepted):** Same shape as text generation.

### 2.3 Voice Generation

**Endpoint:** `POST /v1/generate/voice`

**Request (multipart/form-data):**

```
Content-Type: multipart/form-data

audio: <file upload>
diagram_type: sequence
output_formats: excalidraw,drawio
language_hint: en
idempotency_key: client-uuid-v4
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `audio` | binary | Yes | MP3/WAV/OGG/M4A, max 60s |
| `diagram_type` | string | No | Default: auto-detect from transcribed text |
| `output_formats` | string | No | Comma-separated. Default: `excalidraw` |
| `language_hint` | string | No | BCP-47 code (e.g., `en`, `zh`). Default: `en` |
| `idempotency_key` | string | No | Client-provided UUIDv4 |

**Response (202 Accepted):** Same shape as text generation.

### 2.4 Job Status

**Endpoint:** `GET /v1/jobs/{job_id}`

**Response (200 OK — completed):**

```json
{
  "job_id": "job_01J8K4N2P3Q5R6S7T8U9V0W1X2",
  "status": "completed",
  "created_at": "2026-03-22T14:30:00.000Z",
  "completed_at": "2026-03-22T14:30:11.000Z",
  "duration_seconds": 11,
  "input_summary": {
    "modality": "text",
    "diagram_type": "architecture",
    "description_length_chars": 187
  },
  "result": {
    "diagram_type_detected": "architecture",
    "formats": {
      "excalidraw": {
        "size_bytes": 24580,
        "download_url": "https://api.diagramforge.dev/v1/jobs/job_01J8K4N2P3Q5R6S7T8U9V0W1X2/download/excalidraw"
      },
      "drawio": {
        "size_bytes": 12840,
        "download_url": "https://api.diagramforge.dev/v1/jobs/job_01J8K4N2P3Q5R6S7T8U9V0W1X2/download/drawio"
      },
      "svg": {
        "size_bytes": 9340,
        "download_url": "https://api.diagramforge.dev/v1/jobs/job_01J8K4N2P3Q5R6S7T8U9V0W1X2/download/svg"
      }
    }
  },
  "metadata": {
    "transcription": "The client sends a request...",
    "model_used": "claude-sonnet-4-5",
    "generation_attempts": 1
  }
}
```

**Response (200 OK — failed):**

```json
{
  "job_id": "job_01J8K4N2P3Q5R6S7T8U9V0W1X2",
  "status": "failed",
  "created_at": "2026-03-22T14:30:00.000Z",
  "failed_at": "2026-03-22T14:30:08.000Z",
  "error": {
    "code": "AI_GENERATION_FAILED",
    "message": "The AI model could not produce a valid diagram for the given input.",
    "details": "Malformed Excalidraw JSON output from model. Retried 1 time.",
    "retryable": false
  }
}
```

**Response (200 OK — in-progress):**

```json
{
  "job_id": "job_01J8K4N2P3Q5R6S7T8U9V0W1X2",
  "status": "processing",
  "created_at": "2026-03-22T14:30:00.000Z",
  "progress": {
    "stage": "ai_generation",
    "stage_progress_percent": 60,
    "stages_completed": ["input_validation", "transcription"],
    "current_stage": "ai_generation",
    "message": "Generating diagram with Claude..."
  }
}
```

**Status lifecycle:** `queued` -> `processing` -> `completed` | `failed` | `cancelled`

### 2.5 Download

**Endpoint:** `GET /v1/jobs/{job_id}/download/{format}`

`format` must be one of: `excalidraw`, `drawio`, `svg`

**Response (200 OK):**

- `excalidraw`: `Content-Type: application/json`, body is Excalidraw JSON v2
- `drawio`: `Content-Type: application/xml`, body is Draw.io MXGraph XML
- `svg`: `Content-Type: image/svg+xml`, body is SVG document

**Filename headers:**

```
Content-Disposition: attachment; filename="diagram-01J8K4N2P3Q5R6S7.excalidraw"
                      attachment; filename="diagram-01J8K4N2P3Q5R6S7.drawio"
                      attachment; filename="diagram-01J8K4N2P3Q5R6S7.svg"
```

Download URLs expire after 24 hours. Re-fetch via `/jobs/{job_id}` to get fresh URLs.

### 2.6 WebSocket — Job Progress Stream

**Endpoint:** `WSS /v1/ws/jobs/{job_id}`

**Auth:** Pass `?api_key=<key>` as query param (WebSocket headers cannot carry API keys in all clients).

**Server-sent events (text frames):**

```
event: queued
data: {"stage": "queued", "message": "Job queued for processing", "timestamp": "..."}

event: stage_start
data: {"stage": "input_validation", "message": "Validating input...", "timestamp": "..."}

event: stage_progress
data: {"stage": "ai_generation", "progress_percent": 45, "message": "Generating diagram...", "timestamp": "..."}

event: stage_complete
data: {"stage": "ai_generation", "message": "Diagram generated, exporting...", "timestamp": "..."}

event: completed
data: {"status": "completed", "result_summary": {"formats": ["excalidraw", "drawio"]}, "timestamp": "..."}

event: failed
data: {"status": "failed", "error": {"code": "AI_GENERATION_FAILED", "message": "..."}, "timestamp": "..."}
```

The connection closes automatically when the job reaches a terminal state (`completed`, `failed`, `cancelled`). Clients should implement a 60-second idle timeout with reconnection logic.

### 2.7 Health & Readiness

**Endpoint:** `GET /v1/health`

```json
{"status": "ok", "version": "1.0.0", "uptime_seconds": 3600}
```

**Endpoint:** `GET /v1/ready`

```json
{
  "status": "ready",
  "checks": {
    "claude_api": "ok",
    "whisper_api": "ok",
    "storage": "ok"
  }
}
```

Returns `503 Service Unavailable` with `status: degraded` if any dependency is unhealthy.

---

## 3. Error Codes

All errors follow this envelope:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description.",
    "details": "Optional further detail.",
    "request_id": "req_01J8K4N2P3Q5R6S7T8U9V0W1X2",
    "retryable": false,
    "retry_after_seconds": null
  }
}
```

### 3.1 Error Code Taxonomy

| HTTP Status | Code | Category | Retryable | Cause |
|-------------|------|----------|-----------|-------|
| 400 | `INVALID_INPUT` | Client | No | Malformed request body |
| 400 | `INPUT_TOO_LARGE` | Client | No | File exceeds size limit |
| 400 | `INPUT_TOO_LONG` | Client | No | Text exceeds 4000 chars |
| 400 | `AUDIO_TOO_LONG` | Client | No | Audio exceeds 60s |
| 400 | `UNSUPPORTED_FORMAT` | Client | No | File type not supported |
| 400 | `INVALID_IMAGE_DIMENSIONS` | Client | No | Image exceeds 4096x4096px |
| 400 | `INVALID_DIAGRAM_TYPE` | Client | No | Unknown diagram type |
| 400 | `INVALID_OUTPUT_FORMAT` | Client | No | Unknown output format |
| 400 | `EMPTY_INPUT` | Client | No | Empty/whitespace-only input |
| 400 | `INVALID_IDEMPOTENCY_KEY` | Client | No | Malformed UUID |
| 401 | `MISSING_API_KEY` | Auth | No | No API key provided |
| 401 | `INVALID_API_KEY` | Auth | No | API key not recognized |
| 403 | `API_KEY_EXPIRED` | Auth | No | Key has passed expiry date |
| 403 | `API_KEY_REVOKED` | Auth | No | Key was manually revoked |
| 404 | `JOB_NOT_FOUND` | Client | No | Job ID does not exist |
| 404 | `FORMAT_NOT_FOUND` | Client | No | Requested output format not in job |
| 409 | `DUPLICATE_REQUEST` | Client | No | Idempotency key already used (returns original job) |
| 410 | `JOB_EXPIRED` | Client | No | Job result TTL (24h) exceeded |
| 413 | `PAYLOAD_TOO_LARGE` | Client | No | Request body too large |
| 422 | `UNPROCESSABLE_INPUT` | Client | No | Input cannot be parsed as diagram (e.g., photo of a cat) |
| 429 | `RATE_LIMIT_EXCEEDED` | Quota | Yes | Per-key rate limit hit |
| 429 | `QUOTA_EXCEEDED` | Quota | Yes | Monthly/annual quota exceeded |
| 500 | `INTERNAL_ERROR` | Server | Yes | Unexpected server error |
| 502 | `AI_PROVIDER_ERROR` | Server | Yes | Claude API returned an error |
| 502 | `WHISPER_PROVIDER_ERROR` | Server | Yes | Whisper API returned an error |
| 503 | `SERVICE_UNAVAILABLE` | Server | Yes | Service is temporarily down |
| 504 | `AI_PROVIDER_TIMEOUT` | Server | Yes | Claude API did not respond in time |

### 3.2 Rate Limit Response Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 47
X-RateLimit-Reset: 1742650800
Retry-After: 60
```

---

## 4. Authentication

### 4.1 Pre-Shared API Key Model

Each client is issued an API key: a 32-byte random token, base64url-encoded (43 characters).

**Header format:**

```
Authorization: Bearer dGhpcyBpcyBhIDQyLWJ5dGUgcmFuZG9tIHRva2Vu
```

**Validation behavior:**
1. Extract the `Authorization: Bearer <token>` header.
2. Look up the token in the key store (in-memory LRU cache backed by a DB).
3. If not found: return `401 INVALID_API_KEY`.
4. If found but revoked: return `403 API_KEY_REVOKED`.
5. If found but expired: return `403 API_KEY_EXPIRED`.
6. If valid: attach the key's associated plan/tier to the request context for rate limiting.

**API key structure (metadata, not transmitted):**

```json
{
  "key_id": "key_01J8K4N2P3Q5R6S7T8U9V0W1X2",
  "key_hash": "sha256:...",
  "owner": "team-acme-engineering",
  "tier": "pro",
  "created_at": "2026-01-01T00:00:00Z",
  "expires_at": "2027-01-01T00:00:00Z",
  "rate_limit": {
    "requests_per_minute": 60,
    "requests_per_day": 5000,
    "concurrent_jobs": 5
  },
  "allowed_inputs": ["text", "image", "voice"],
  "allowed_outputs": ["excalidraw", "drawio", "svg"]
}
```

**Key management endpoints (admin, not part of public API):**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/keys` | Issue a new API key |
| `GET` | `/admin/keys/{key_id}` | Get key metadata |
| `DELETE` | `/admin/keys/{key_id}` | Revoke a key |
| `PATCH` | `/admin/keys/{key_id}` | Update key limits/tier |

### 4.2 WebSocket Authentication

Since WebSocket upgrade requests cannot carry custom headers in many browser/server scenarios, auth is done via query parameter:

```
wss://api.diagramforge.dev/v1/ws/jobs/{job_id}?api_key=dGhpcyBpcyBh...
```

The `api_key` must match the key used to create the job.

---

## 5. Rate Limiting

### 5.1 Strategy: Token Bucket per API Key

Each API key has a token bucket with configurable refill rates. Default tiers:

| Tier | RPM | RPD | Concurrent Jobs | Burst |
|------|-----|-----|-----------------|-------|
| `free` | 10 | 100 | 2 | 5 |
| `pro` | 60 | 5,000 | 5 | 20 |
| `enterprise` | 300 | 50,000 | 20 | 100 |

- **RPM** = requests per minute (submit endpoint invocations)
- **RPD** = requests per day (rolling 24h window)
- **Concurrent Jobs** = max jobs in `queued` or `processing` state simultaneously
- **Burst** = additional tokens that can be borrowed above the refill rate

### 5.2 Enforcement Points

1. **Per-request limit (RPM/RPD):** Checked at request entry. Returns `429 RATE_LIMIT_EXCEEDED` with `Retry-After` header.
2. **Concurrent job limit:** Checked at job creation. Returns `429 RATE_LIMIT_EXCEEDED` with message `"Concurrent job limit reached"`.
3. **Circuit breaker on AI provider:** If Claude API error rate exceeds 50% in a 1-minute window, the submit endpoint returns `503 SERVICE_UNAVAILABLE` for a cooldown period of 30 seconds. Prevents runaway cost accumulation.
4. **Per-IP fallback:** If no API key is present (public endpoints only), rate limit by IP at 1/10th of the free tier.

### 5.3 Circuit Breaker

The circuit breaker protects against Claude API outages and runaway costs:

- **Closed** (normal): Requests pass through. Errors increment a counter.
- **Open** (tripped): After 5 consecutive errors OR 50% error rate in 60s, trips open. Returns `503` for 30s.
- **Half-open**: After 30s, allows 1 probe request. If it succeeds, closes. If it fails, reopens.

---

## 6. CLI Commands

The CLI wraps the REST API. Install via `pip install diagram-forge-cli` or `brew install diagram-forge`.

### 6.1 Commands

```
diagram-forge generate text [OPTIONS] [--file PATH | DESCRIPTION]

diagram-forge generate image [OPTIONS] [--file PATH | --camera]

diagram-forge generate voice [OPTIONS] [--file PATH | --record]

diagram-forge job status <job_id>

diagram-forge job download <job_id> [--format excalidraw|drawio|svg] [--output-dir .]

diagram-forge job watch <job_id>

diagram-forge configure set-api-key <key>

diagram-forge configure set-base-url <url>

diagram-forge health
```

### 6.2 `generate text`

```bash
# Direct input
diagram-forge generate text \
  --description "API Gateway, Auth Service, User Service, Database in a row"

# From file
diagram-forge generate text --file ./architecture.txt \
  --diagram-type architecture \
  --output-formats excalidraw,drawio

# Short form
df text "Frontend -> API -> DB" -d flowchart -f excalidraw
```

### 6.3 `generate image`

```bash
# From file
diagram-forge generate image --file ./sketch.jpg \
  --diagram-type architecture

# From camera (requires fswebcam or similar)
diagram-forge generate image --camera \
  --output-format excalidraw

# From clipboard (macOS)
pbpaste | diagram-forge generate image --stdin \
  --format png
```

### 6.4 `generate voice`

```bash
# From file
diagram-forge generate voice --file ./meeting.mp3 \
  --diagram-type sequence

# Record and submit
diagram-forge generate voice --record \
  --max-duration 60
```

### 6.5 `job status`

```bash
diagram-forge job status job_01J8K4N2P3Q5R6S7T8U9V0W1X2
# Output:
# Status:   processing
# Stage:    ai_generation (60%)
# Started:  2026-03-22 14:30:00 (10s ago)
```

### 6.6 `job download`

```bash
diagram-forge job download job_01J8K4N2P3Q5R6S7T8U9V0W1X2 \
  --format excalidraw \
  --output-dir ./diagrams

# Download all formats
diagram-forge job download job_01J8K4N2P3Q5R6S7T8U9V0W1X2 --all
```

### 6.7 `job watch`

Opens a live progress view using the WebSocket connection:

```bash
diagram-forge job watch job_01J8K4N2P3Q5R6S7T8U9V0W1X2
# [14:30:00] Job queued
# [14:30:01] Validating input...
# [14:30:02] Transcription complete (45s audio)
# [14:30:03] Generating diagram with Claude...
# [14:30:08] Exporting to Excalidraw...
# [14:30:11] Done. Downloaded to ./diagram-01J8K4N2.excalidraw
```

### 6.8 Configuration

```bash
# Set API key (stored in ~/.config/diagram-forge/config.toml)
diagram-forge configure set-api-key "df_live_..."

# Show current config
diagram-forge configure show

# Environment variable override (highest priority)
export DIAGRAM_FORGE_API_KEY="df_live_..."
export DIAGRAM_FORGE_BASE_URL="https://api.diagramforge.dev/v1"
```

### 6.9 curl Equivalents

```bash
# Text generation
curl -X POST https://api.diagramforge.dev/v1/generate/text \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description":"User -> API -> DB","diagram_type":"flowchart"}'

# Image generation
curl -X POST https://api.diagramforge.dev/v1/generate/image \
  -H "Authorization: Bearer $API_KEY" \
  -F "image=@sketch.png" \
  -F "diagram_type=architecture"

# Voice generation
curl -X POST https://api.diagramforge.dev/v1/generate/voice \
  -H "Authorization: Bearer $API_KEY" \
  -F "audio=@meeting.mp3"

# Poll status
curl https://api.diagramforge.dev/v1/jobs/$JOB_ID \
  -H "Authorization: Bearer $API_KEY"

# Download
curl -O -J https://api.diagramforge.dev/v1/jobs/$JOB_ID/download/excalidraw \
  -H "Authorization: Bearer $API_KEY"
```

---

## 7. Web UI Endpoints

The web UI is a single-page application served from the API server (or a CDN in production). It consumes the same REST API.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/ui` | SPA entry point (index.html + JS bundle) |
| `GET` | `/ui/*` | Static assets (JS, CSS, images) |
| `GET` | `/ui/jobs/{job_id}` | SPA loaded with job context |
| `GET` | `/ui/docs` | API documentation (Swagger UI) |
| `GET` | `/ui/docs.json` | OpenAPI 3.1 spec |

The `/ui/docs` endpoint is provided via FastAPI's built-in Swagger UI (`/docs`) and ReDoc (`/redoc`) at the API root, aliased under `/ui/docs` for consistency.

### 7.1 UI Layout (for API context)

The UI makes these API calls:

1. **Upload page** (`/ui`): POST to `/v1/generate/{text,image,voice}`
2. **Status page** (`/ui/jobs/{job_id}`): WebSocket to `/v1/ws/jobs/{job_id}` + polling fallback
3. **Result page**: GET `/v1/jobs/{job_id}` for metadata, then GET `/v1/jobs/{job_id}/download/{format}` for files
4. **API docs** (`/ui/docs`): OpenAPI spec at `/v1/openapi.json`

---

## 8. API Versioning

### 8.1 URL Path Versioning

The API is versioned via URL prefix: `/v1/`. This is the simplest and most explicit approach, preferred over header-based or query-param versioning.

```
/v1/generate/text
/v1/jobs/{job_id}
/v1/ws/jobs/{job_id}
```

### 8.2 Version Lifecycle Policy

- **Active:** The current version is fully supported.
- **Deprecated:** When v2 is released, v1 enters a 12-month deprecation window. During deprecation:
  - Responses include `X-API-Deprecated: true` and `X-API-Sunset: <date>` headers.
  - Documentation at `/ui/docs` shows deprecation notices.
  - Monthly email to API key owners with migration guide.
- **Sunset:** After 12 months, endpoints return `410 Gone` with migration instructions.

### 8.3 Output Format Compatibility

Excalidraw JSON schema is pinned to v2 (`https://excalidraw.com/schema/v2.json`) in v1 of the API. When Excalidraw releases v3, the API will either:
- Continue emitting v2 schema (stable, no change for consumers), OR
- Emit v3 schema under a new endpoint prefix (`/v2/generate/...`)

This decision is deferred until Excalidraw v3 is stable. The export schemas are independently versioned as properties of the job result, not the API itself.

---

## 9. Implementation Notes

### 9.1 FastAPI App Structure

```
src/api/
├── __init__.py
├── main.py              # FastAPI app, lifespan, middleware
├── config.py            # Settings (pydantic-settings)
├── deps.py              # Dependency injection (auth, rate limit, db)
├── routers/
│   ├── __init__.py
│   ├── generate.py      # /generate/text, /generate/image, /generate/voice
│   ├── jobs.py          # /jobs/{job_id}, /jobs/{job_id}/download/{format}
│   ├── ws.py            # /ws/jobs/{job_id}
│   └── admin.py         # /admin/keys/* (internal)
├── schemas/
│   ├── __init__.py
│   ├── generate.py      # Request/response Pydantic models
│   ├── job.py           # Job status models
│   ├── error.py         # Error envelope model
│   └── common.py        # Shared enums, pagination
├── services/
│   ├── __init__.py
│   ├── job_manager.py   # Job lifecycle, queue, TTL cleanup
│   ├── ai_generator.py  # Claude API client
│   ├── transcriber.py   # Whisper API client
│   └── storage.py       # Temporary file storage
├── middleware/
│   ├── __init__.py
│   ├── auth.py          # API key validation
│   ├── rate_limit.py    # Token bucket enforcement
│   └── request_id.py    # Inject request_id into log context
├── export/
│   ├── excalidraw.py     # -> Excalidraw JSON v2
│   ├── drawio.py         # -> Draw.io MXGraph XML
│   └── svg.py            # -> SVG
└── utils/
    ├── __init__.py
    └── validators.py     # Input size/content validation
```

### 9.2 Key Pydantic Models

**Schemas (simplified):**

```python
# schemas/common.py
class DiagramType(str, Enum):
    ARCHITECTURE = "architecture"
    SEQUENCE = "sequence"
    FLOWCHART = "flowchart"

class OutputFormat(str, Enum):
    EXCALIDRAW = "excalidraw"
    DRAWIO = "drawio"
    SVG = "svg"

class InputModality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# schemas/generate.py
class TextGenerateRequest(BaseModel):
    description: Annotated[str, StringConstraints(min_length=1, max_length=4000)]
    diagram_type: DiagramType
    output_formats: list[OutputFormat] = [OutputFormat.EXCALIDRAW]
    style_hint: Annotated[str, StringConstraints(max_length=200)] | None = None
    idempotency_key: Annotated[str, StringConstraints(pattern=r"^[0-9a-f-]{36}$")] | None = None

class ImageGenerateRequest(BaseModel):
    diagram_type: DiagramType | None = None
    output_formats: list[OutputFormat] = [OutputFormat.EXCALIDRAW]
    style_hint: Annotated[str, StringConstraints(max_length=200)] | None = None
    iteration_context: Annotated[str, StringConstraints(max_length=2000)] | None = None
    idempotency_key: str | None = None

class GenerateResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    estimated_duration_seconds: int
    status_url: HttpUrl
    poll_url: HttpUrl

# schemas/job.py
class JobError(BaseModel):
    code: str
    message: str
    details: str | None = None
    retryable: bool = False

class FormatResult(BaseModel):
    size_bytes: int
    download_url: HttpUrl

class JobResult(BaseModel):
    diagram_type_detected: DiagramType
    formats: dict[OutputFormat, FormatResult]

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    duration_seconds: int | None = None
    input_summary: dict | None = None
    result: JobResult | None = None
    error: JobError | None = None
    progress: JobProgress | None = None

# schemas/error.py
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: str | None = None
    request_id: str
    retryable: bool = False
    retry_after_seconds: int | None = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

### 9.3 Job State Machine

```
                    [submit]
                       |
                       v
                   QUEUED -----> CANCELLED (if client disconnects before processing)
                       |
                       v
                   PROCESSING
                       |
            +----------+----------+
            |          |          |
            v          v          v
        COMPLETED   FAILED     CANCELLED
```

- **QUEUED -> PROCESSING:** Worker picks up job from queue.
- **PROCESSING -> COMPLETED:** All formats exported successfully.
- **PROCESSING -> FAILED:** Unrecoverable error (AI timeout, invalid output, etc.). Returns structured error with `retryable` flag.
- **QUEUED -> CANCELLED:** Client sends DELETE `/v1/jobs/{job_id}` (optional v1 endpoint). Worker checks cancellation flag before each stage.

### 9.4 Idempotency

If a client submits with the same `idempotency_key` twice within 24h:
- The server returns `200 OK` with the **original** job response (not a new job).
- The `Idempotency-Replayed: true` header is added to indicate a replay.
- This is implemented by storing `(idempotency_key, api_key)` -> `job_id` in a TTL store.

### 9.5 File Upload Handling

- Images: validated with `Pillow` (dimensions, format, corrupt check) before queuing.
- Audio: validated with `pydub` or `mutagen` (duration, format) before queuing.
- Files are uploaded to a temporary object store (local filesystem or S3-compatible). No user data is logged.
- Files are deleted after the job completes and all downloads are served, OR after 24h TTL, whichever comes first.

### 9.6 Request Timeout Strategy

| Stage | Timeout |
|-------|---------|
| HTTP request body (upload) | 60s |
| Whisper transcription | 30s |
| Claude API call | 45s |
| Export (each format) | 15s |
| Total job time limit | 120s |

If a job exceeds the total time limit, it is marked `failed` with code `JOB_TIMEOUT`.

### 9.7 Request ID Propagation

Every request gets a `request_id` (UUIDv7, time-ordered) injected at the middleware layer. It is:
- Returned in `X-Request-ID` response header.
- Included in the error envelope.
- Attached to all log lines.
- Forwarded to the AI provider as a metadata header for tracing.

### 9.8 OpenAPI Specification

FastAPI auto-generates the OpenAPI 3.1 spec at `/openapi.json`. Key spec metadata:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Diagram Forge API",
    "version": "1.0.0",
    "description": "Convert text, image, and voice into professional editable diagrams.",
    "contact": {"email": "api@diagramforge.dev"},
    "license": {"name": "Proprietary"}
  },
  "servers": [
    {"url": "https://api.diagramforge.dev/v1", "description": "Production"},
    {"url": "https://api-staging.diagramforge.dev/v1", "description": "Staging"}
  ]
}
```

The spec includes:
- JSON schemas for all request/response bodies.
- `401`, `403`, `404`, `429`, `500`, `502`, `503`, `504` responses defined.
- Security scheme: `Bearer` auth on all endpoints except `/health` and `/ready`.
