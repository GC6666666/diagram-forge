# Scale Design: Diagram Forge

## Performance Targets

### Latency SLOs by Input Modality

All targets are end-to-end, measured from request receipt to final byte sent.

| Modality | Stage Breakdown | p50 | p95 | p99 | Notes |
|---|---|---|---|---|---|
| **Text** | Validate → Claude LLM → Parse → Exporter | 3s | 5s | 8s | Dominated by Claude API latency |
| **Voice** | Validate → Whisper → Parse text → Claude → Exporter | 6s | 10s | 15s | Whisper API on 60s audio adds ~5s; Claude adds ~3s |
| **Image** | Validate → Vision analysis → Claude → Parse → Exporter | 12s | 18s | 25s | Vision model (Claude with image) is ~8-12s; Claude generation ~3s |

### Rationale for Targets

- Text: Claude Sonnet 4/4.5 generates Excalidraw JSON in 1-3s for typical inputs. p99 of 8s covers cold-start and token-heavy prompts.
- Voice: Whisper API processes ~60s audio in 4-6s (OpenAI reports 10x realtime, so 60s audio → ~6s). With 5s Claude generation, total ~11s. p99 of 15s covers slow Whisper responses and retries.
- Image: Claude Sonnet 4 with vision support analyzes images in 5-12s depending on image complexity. p99 of 25s covers complex multi-element diagrams and slow API responses.

### Input Size Limits (from PRD Clarifications)

| Input | Limit | Rationale |
|---|---|---|
| Text | 4,000 chars | Sufficient for detailed diagram descriptions; prevents token overflow |
| Image | 10 MB, 4096x4096 px | Excalidraw/Draw.io diagrams are typically small; prevents DoS |
| Audio | 60s (MP3/WAV) | ~3x average speaking rate; covers most meeting descriptions |
| Formats | PNG, JPEG, WebP (images); MP3, WAV (audio) | Universal browser support; avoids complex codecs |

### Output Quality Targets

These are informational targets for iterative improvement, not hard SLOs:

- Structural accuracy: >80% of elements (boxes, arrows, labels) present and correctly placed, judged by human review
- Format validity: 100% of responses must parse as valid Excalidraw JSON / Draw.io XML / SVG (validated server-side before returning)
- Malformed AI output rate: Target <5% requiring retry or fallback response

---

## Concurrency Strategy

### Semaphore Architecture

Three independent semaphore pools prevent any single pipeline stage from exhausting capacity:

```
Global concurrency gate (total in-flight requests: 50)
├── /generate/text    → Claude semaphore (max 20 concurrent)
├── /generate/voice   → Whisper semaphore (max 5 concurrent)
│                     → Claude semaphore (max 20 concurrent, shared with text+image)
└── /generate/image   → Claude semaphore (max 20 concurrent, shared)
```

### Why These Numbers

| Pool | Limit | Reasoning |
|---|---|---|
| **Global** | 50 | Prevents any single client or burst from saturating all resources. At 50 concurrent requests consuming ~3-12s each, throughput is ~4-17 req/s. |
| **Claude (Sonnet 4)** | 20 | Anthropic's tier-based rate limits: Sonnet 4 supports ~2,000 requests/min at standard tier. 20 concurrent means 20 × 5s avg = 100 slots consumed/min, well within limits. Burst capacity handles spikes. |
| **Claude (Opus)** | 5 | Opus is 10x more expensive and typically slower. If Opus is used for complex generation, cap lower to prevent runaway costs. |
| **Whisper** | 5 | OpenAI Whisper API limits: ~180 requests/min at standard tier. 5 concurrent is conservative; Whisper is I/O-bound on audio duration, not concurrent request count. |

### Shared Claude Pool

Text, voice (post-Whisper), and image pipelines all share the Claude semaphore pool. This is intentional: the total Claude load is the sum of all modalities, and the pool must reflect total API capacity, not per-modality capacity.

### Implementation

Use Python's `asyncio.Semaphore` (in-memory) for v1. This is appropriate because:

1. Single-container deployment means no cross-process coordination needed
2. Semaphores are per-worker in uvicorn/gunicorn; the limit is per-container, not global
3. For multi-container scaling, migrate to Redis-backed semaphore (see Future Scaling)

```python
# diagram_forge/core/concurrency.py
from asyncio import Semaphore

# Global request gate — prevents any single client from dominating resources
GLOBAL_SEMAPHORE = Semaphore(50)

# Claude API — shared across text, voice (post-Whisper), and image pipelines
CLAUDE_SEMAPHORE = Semaphore(20)

# Whisper API — separate pool, lower limit
WHISPER_SEMAPHORE = Semaphore(5)
```

---

## Rate Limiting Design

### Two-Tier Rate Limiting

**Tier 1 — Per-IP (unauthenticated requests)**
- Algorithm: Sliding window counter
- Limit: **30 requests / minute** per IP
- Burst: 5 requests
- Response: HTTP 429 with `Retry-After` header

**Tier 2 — Per API Key (authenticated requests)**
- Algorithm: Token bucket
- Limit: **100 requests / minute** per API key
- Burst: 20 requests
- Response: HTTP 429 with `Retry-After` and `X-RateLimit-Limit` headers

### Why Two Tiers

Unauthenticated users get a lower limit to prevent abuse. Authenticated users (with pre-shared API keys per PRD Clarification Q8) get higher limits reflecting their provisioned capacity. Both tiers protect the Claude API from runaway load.

### Implementation

For single-container v1, use an in-memory token bucket with per-IP and per-key tracking:

```python
# diagram_forge/core/rate_limiter.py
from collections import defaultdict
from time import time
import threading

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate          # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> tuple[bool, float]:
        """Returns (allowed, retry_after_seconds)"""
        with self._lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            retry_after = (tokens - self.tokens) / self.rate
            return False, retry_after

    def _refill(self):
        now = time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

# Global state
_ip_buckets: dict[str, TokenBucket] = defaultdict(
    lambda: TokenBucket(rate=0.5, capacity=5)   # 30/min with burst of 5
)
_key_buckets: dict[str, TokenBucket] = defaultdict(
    lambda: TokenBucket(rate=1.67, capacity=20) # 100/min with burst of 20
)
_rate_limit_lock = threading.Lock()
```

### Key Header Response Format

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1742644800
Retry-After: 3
```

### Future: Redis-Backed Rate Limiting

When scaling to multiple containers, move rate limit state to Redis:
- Key pattern: `rl:ip:{ip_address}` and `rl:key:{api_key}`
- TTL: 60 seconds (window size)
- Use `INCR` + `EXPIRE` for sliding window
- Rate: ~1ms per Redis round-trip is acceptable given request overhead

---

## Circuit Breaker

### Purpose

The Claude API (and Whisper API) will experience outages, degradation, or elevated error rates. A circuit breaker prevents the service from hammering a failing API, wasting resources, and compounding failures.

### Configuration

| Parameter | Value | Rationale |
|---|---|---|
| **Failure threshold** | 5 consecutive failures | Enough to confirm a real issue, not so many that a brief spike trips the breaker |
| **Recovery timeout** | 30 seconds | Short enough for quick recovery, long enough to let the API stabilize |
| **Half-open requests** | 3 | Probe the API with limited traffic before fully closing |
| **Success threshold** | 2 successes in half-open | Confirms the API is healthy before fully closing the circuit |
| **Failure rate threshold** | 50% | Also trip on sustained high error rate, not just consecutive failures |

### States

```
CLOSED (normal) → [5 consecutive failures OR 50% error rate over 10 requests]
    ↓
OPEN (failing fast)
    ↓ [30s elapsed]
HALF-OPEN (probing)
    ↓ [2 successes]
CLOSED
    ↓ [1 failure in half-open]
OPEN
```

### Implementation

Use `pybreaker` library — battle-tested circuit breaker for Python:

```python
# diagram_forge/core/circuit_breaker.py
import pybreaker

claude_circuit = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    half_open_max_calls=3,
    exclude=[httpx.HTTPStatusError],  # Let 4xx passthrough without tripping
)
# Configure listeners for alerting (see Monitoring section)
```

### Error Classification

Not all API errors should trip the circuit breaker:

| Error | Behavior | Trip Circuit? |
|---|---|---|
| HTTP 400 (Bad Request) | Return 400 to client | No — client error |
| HTTP 401/403 (Auth) | Return 401/403 to client | No — credential issue |
| HTTP 429 (Rate Limited) | Retry with backoff (see below) | No — throttling, not failure |
| HTTP 500/502/503 (Server Error) | Return 500 to client | **Yes** |
| HTTP 504 (Gateway Timeout) | Return 504 to client | **Yes** |
| Timeout (request timeout) | Return 504 to client | **Yes** |
| Network error (connection refused, DNS) | Return 503 to client | **Yes** |

### Retry Strategy for HTTP 429 (Claude API Rate Limits)

```
Attempt 1: Immediate
Attempt 2: Wait 5 seconds + jitter (±1s)
Attempt 3: Wait 15 seconds + jitter (±3s)
Attempt 4: Return 429 to client with Retry-After
```

Total retry budget: ~25 seconds. Combined with the overall request timeout, this stays within the 60s ceiling.

---

## Timeout Strategy

### Per-Stage Timeouts

Timeouts are cumulative — each stage must complete within its budget before the next begins.

| Stage | Timeout | Rationale |
|---|---|---|
| **Input validation** | 2s | File format, size, and dimension checks are fast |
| **Image preprocessing** | 3s | Resize, normalize, strip EXIF — CPU-intensive but bounded |
| **Whisper API call** | 30s | For 60s audio file; OpenAI Whisper API typically returns in 4-6s; 30s is generous headroom |
| **Claude API call (text-only)** | 20s | Anthropic API p95 is ~10s for text; 20s covers cold starts and complex prompts |
| **Claude API call (with image)** | 35s | Vision models are slower; p95 ~20s, so 35s is generous |
| **Output parsing** | 3s | JSON/XML parsing and validation |
| **Format export** | 3s | Converting internal representation to Excalidraw/Draw.io/SVG |
| **Response serialization** | 2s | JSON encoding and streaming to client |

### Total Request Timeout Ceiling

| Modality | Sum of stages | Ceiling | Notes |
|---|---|---|---|
| Text | 2+0+20+3+3+2 | **30s** | Well within p99 target of 8s; ceiling is generous |
| Voice | 2+0+30+20+3+3+2 | **60s** | Covers slow Whisper + slow Claude |
| Image | 2+3+0+35+3+3+2 | **48s** | Covers slow vision analysis |

### Implementation

Use `asyncio.timeout` (Python 3.11+) for deadline enforcement:

```python
# diagram_forge/core/timeout.py
from asyncio import timeout as asyncio_timeout, TimeoutError

async def with_timeout(coro, seconds: float, stage: str):
    """Wraps a coroutine with a deadline. Raises TimeoutError on breach."""
    try:
        async with asyncio_timeout(seconds):
            return await coro
    except TimeoutError:
        raise DiagramForgeTimeout(f"{stage} exceeded {seconds}s")
```

### Client Disconnect Handling

When a client disconnects mid-request (e.g., user closes browser), the server should stop processing immediately:

```python
# In FastAPI route:
async def generate_diagram(request: Request):
    async def do_work():
        # ... full pipeline
    try:
        return await request.app.state.executor(do_work, request)
    except asyncio.CancelledError:
        # Pipeline cancelled — clean up resources, stop API calls
        log.info("Request cancelled by client", extra={"request_id": request.state.request_id})
        raise
```

---

## Caching Strategy

### Can We Cache?

Diagram generation is inherently non-idempotent: the same text prompt today may produce a different (improved) diagram tomorrow as prompts evolve. However, some layers are cacheable:

| Layer | Cacheable? | Strategy |
|---|---|---|
| Input validation result | No | Validation is trivial; caching adds complexity |
| Whisper transcription | **Yes, partially** | SHA256(audio_bytes) → transcript. Audio files are deterministic input. TTL: 24h (matches temp file TTL). |
| Claude API response | No | Non-deterministic; prompt changes would stale cache |
| Output format conversion | No | Depends on upstream AI output |
| Static assets | Yes | Exporter templates, prompt libraries — cache forever |

### Whisper Cache

Transcription is the most expensive voice stage and the most cache-friendly:

```python
# diagram_forge/core/cache.py
import hashlib, json, os
from pathlib import Path

CACHE_DIR = Path("/tmp/diagram_forge/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def cache_key(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def get_whisper_cache(audio_bytes: bytes) -> str | None:
    key = cache_key(audio_bytes)
    path = CACHE_DIR / f"whisper_{key}.json"
    if path.exists():
        return json.loads(path.read_text())["transcript"]
    return None

def set_whisper_cache(audio_bytes: bytes, transcript: str, ttl_hours: int = 24):
    key = cache_key(audio_bytes)
    path = CACHE_DIR / f"whisper_{key}.json"
    path.write_text(json.dumps({
        "transcript": transcript,
        "cached_at": time.time(),
        "expires_at": time.time() + ttl_hours * 3600,
    }))
    # Background task: clean expired entries
```

### Cache Hit Rates

Realistic cache hit rates for the voice modality:
- Unique audio: 0% hit (first pass)
- Re-submitted same audio: 100% hit (within TTL)
- Retry of failed request with same audio: ~30% hit (depending on failure timing)

### What NOT to Cache

- Text-to-diagram responses: Cache key ambiguity (similar prompts produce different diagrams), prompt versioning complexity, and low replay value make caching counterproductive.
- Image-to-diagram responses: Images are large, cache keys are expensive to compute, and responses are highly variable.

---

## Cost Estimation

### Per-Request Token Costs

**Text modality** (typical architecture diagram description, ~200 words):

| Component | Input Tokens | Output Tokens | Cost @ Sonnet 4.5 |
|---|---|---|---|
| System prompt (diagram rules) | 800 | — | — |
| User prompt (description) | 600 | — | — |
| Claude response (Excalidraw JSON) | — | 1,500 | — |
| **Total** | 1,400 | 1,500 | **$0.0018** |

**Voice modality** (60s audio → transcribed → diagram):

| Component | Cost |
|---|---|
| Whisper API (60s audio) | **$0.006** ($0.006/15s = $0.024/min → $0.024 for 60s) |
| Transcription text tokens (~150 words) | Included in Claude call below |
| Claude Sonnet 4.5 (smaller prompt, ~600 in, ~1500 out) | **$0.0014** |
| **Total** | **$0.0074** |

**Image modality** (4096x4096 JPEG, ~10MB):

| Component | Input Tokens | Output Tokens | Cost @ Sonnet 4.5 |
|---|---|---|---|
| System prompt | 800 | — | — |
| Image (encoded) | ~8,000 | — | — (vision adds ~8K tokens) |
| User instruction | 100 | — | — |
| Claude response (Excalidraw JSON) | — | 1,500 | — |
| **Total** | 8,900 | 1,500 | **$0.033** |

### Monthly Cost Scenarios

Assumptions: 8 hours/day active, 5 days/week, avg 2 req/user/day.

| Scenario | Users | Req/Day | Text% | Voice% | Image% | Monthly API Cost |
|---|---|---|---|---|---|---|
| Solo dev | 1 | 10 | 80% | 15% | 5% | **$1.80** |
| Small team | 10 | 100 | 70% | 20% | 10% | **$21** |
| Team (+ API overhead, retries) | 10 | 100 | 70% | 20% | 10% | **$35** (w/ 1.5x retry factor) |
| Growing | 50 | 500 | 60% | 25% | 15% | **$165** |
| Productive | 200 | 2,000 | 50% | 30% | 20% | **$680** |

### Cost Controls

1. **Semaphore prevents runaway concurrent calls**: At most 20 concurrent Claude calls, each costing ≤$0.033. Worst-case concurrent spend: 20 × $0.033 = **$0.66/second** (bounded by semaphore).
2. **Token budgets on prompts**: Cap system prompt at 1,000 tokens. Cap user input at 4,000 chars (~1,000 tokens). Cap output at 2,000 tokens.
3. **Model selection**: Use Sonnet 4.5 for standard generation; reserve Opus for complex multi-element diagrams only.
4. **Whisper model**: Use `whisper-1` via OpenAI API (no GPU cost, consistent quality, no maintenance).

---

## Docker Resource Config

### Container Resource Limits

```yaml
# docker-compose.yml (or Dockerfile CMD args)
services:
  diagram-forge:
    image: diagram-forge:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'        # 2 CPU cores — sufficient for image processing + Whisper parsing
          memory: 4G         # 4 GB RAM — image decode, Excalidraw JSON serialization
        reservations:
          cpus: '0.5'
          memory: 1G
    # uvicorn workers: 2 per core = 4 workers
    # Each worker handles requests via asyncio (not threading)
```

### Why 2 CPUs, 4 GB

- **CPU**: Image preprocessing (resize, normalize, encode) is CPU-bound. 2 cores handles ~2-4 concurrent image pipelines before queuing. At 50 global semaphore slots, most requests are I/O-bound (waiting on API responses), so CPU is not the bottleneck.
- **Memory**: Largest memory consumer is image buffer during preprocessing. A 10MB JPEG decoded into a 4096x4096 RGBA array = ~64MB. Processing 10 concurrent images = ~640MB. Plus Python runtime, uvicorn workers, and OS overhead = ~3GB. 4GB is tight but adequate for v1. Monitor with `memory_usage` metric.

### uvicorn Configuration

```bash
# Start command
uvicorn diagram_forge.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --limit-concurrency 50 \
  --timeout-keep-alive 60 \
  --limit-max-requests 1000  # Restart worker after 1000 requests (memory leak prevention)
```

- `--workers 2`: Two processes. Each gets 2 CPUs and 2 GB (implicit, based on total). Avoid 1 worker (no CPU parallelism). 4+ workers would over-subscribe the CPU.
- `--limit-concurrency 50`: Matches global semaphore. Surplus requests queue at the uvicorn level.
- `--limit-max-requests 1000`: Worker recycling prevents memory leaks from accumulating in long-running processes.

### FastAPI Request Size Limits

```python
# diagram_forge/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Enforce payload size limits at the FastAPI level
@app.middleware("http")
async def payload_size_limit(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 15 * 1024 * 1024:  # 15 MB
        return JSONResponse(
            status_code=413,
            content={"error": "PAYLOAD_TOO_LARGE", "message": "Maximum request size is 15 MB"}
        )
    return await call_next(request)
```

15 MB limit = 10 MB (actual image/audio) + 5 MB HTTP overhead (headers, multipart framing).

---

## Future Scaling Considerations

### Phase 2: Multi-Container Deployment

Stateless design makes horizontal scaling straightforward:

1. **Add a Redis-backed semaphore**: Replace in-memory `asyncio.Semaphore` with Redis `SETNX` + `EXPIRE` for distributed concurrency control.
2. **Add a Redis-backed rate limiter**: Move from per-process token buckets to Redis-based sliding window.
3. **Add a job queue** (Redis or SQS): For voice/image requests that may exceed the timeout budget. Return a job ID; client polls for completion.
4. **Load balancer**: nginx or cloud LB in front of multiple container instances.

### Phase 3: Cost Optimization

- **Prompt caching**: Cache the system prompt compilation. The dynamic part (user description) still goes to Claude, but the static rules/template portion can be pre-cached.
- **Response caching**: For identical text inputs (deterministic), cache the Excalidraw JSON response. Use `MD5(text + system_prompt_version)` as cache key.
- **Model tiering**: Route simple descriptions to Haiku 4 (fast, cheap), complex diagrams to Sonnet 4.5, ambiguous cases to Opus.
- **Whisper batching**: If multiple audio requests arrive within a short window, batch them into a single API call (OpenAI Whisper API supports this via multipart).

### Phase 4: Auto-Scaling

Target metrics for auto-scaling decisions:

| Metric | Scale Up | Scale Down | Cooldown |
|---|---|---|---|
| CPU utilization > 70% for 2 min | +1 container | — | 3 min |
| Memory utilization > 80% for 2 min | +1 container | — | 3 min |
| Claude semaphore utilization > 80% | +1 container | — | 3 min |
| Request queue depth > 20 | +2 containers | — | 3 min |
| CPU utilization < 20% for 10 min | — | -1 container | 5 min |
| Active connections < 5 | — | -1 container | 5 min |

### Phase 5: Whisper Self-Hosting (Cost Reduction)

If Whisper API costs become prohibitive at scale:

- Deploy `faster-whisper` (CTranslate2-optimized) on a GPU instance (e.g., NVIDIA T4)
- Throughput: ~100x realtime on T4 → 60s audio → ~0.6s processing
- Cost: ~$0.30/hr GPU time vs $0.024/min via API → breakeven at ~750 minutes/month
- Tradeoff: Adds deployment complexity, GPU cost, and maintenance burden

---

## Implementation Notes

### Key Dependencies

```toml
# pyproject.toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "httpx>=0.27",
    "anthropic>=0.40",
    "pybreaker>=1.0",
    "pillow>=10.0",
    "pydantic>=2.0",
    "python-multipart>=0.0.9",
    "structlog>=24.0",
    "prometheus-client>=0.20",
]
```

### Metrics to Expose (Prometheus)

```
# Request latency
diagram_forge_request_duration_seconds{modality="text|voice|image", stage="total|whisper|claude|export", quantile="0.5|0.95|0.99"}

# Throughput
diagram_forge_requests_total{modality="text|voice|image", status="success|error|timeout"}

# Concurrency
diagram_forge_semaphore_available{name="global|claude|whisper"}
diagram_forge_semaphore_total{name="global|claude|whisper"}

# Circuit breaker
diagram_forge_circuit_breaker_state{name="claude|whisper", state="closed|open|half_open"}

# Rate limiting
diagram_forge_rate_limit_rejected_total{type="ip|key"}

# Cost proxy
diagram_forge_claude_tokens_total{type="input|output"}
diagram_forge_whisper_audio_seconds_total
```

### Health Endpoint

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "circuit_breaker": {
            "claude": claude_circuit.current_state,
            "whisper": whisper_circuit.current_state,
        },
        "semaphores": {
            "global_available": GLOBAL_SEMAPHORE._value,
            "claude_available": CLAUDE_SEMAPHORE._value,
            "whisper_available": WHISPER_SEMAPHORE._value,
        },
    }

@app.get("/ready")
async def ready():
    # Returns 503 if circuit breakers are open
    if claude_circuit.current_state == pybreaker.STATE_OPEN:
        raise HTTPException(503, "Claude API circuit breaker is open")
    return {"ready": True}
```

### Observability Integration Points

- **Structured logging**: Use `structlog` with request IDs, modality, stage timing, and error classification.
- **Distributed tracing**: Add OpenTelemetry spans per pipeline stage for detailed latency breakdown.
- **Alerting**: Alert on circuit breaker open (>5 min), error rate >5%, p95 latency >2x target, and Claude API cost spike >$100/day.

### File to Create

```
diagram_forge/
├── core/
│   ├── concurrency.py      # Semaphore pools (GLOBAL, CLAUDE, WHISPER)
│   ├── circuit_breaker.py  # Claude and Whisper circuit breakers
│   ├── rate_limiter.py     # Per-IP and per-API-key token buckets
│   ├── timeout.py           # Per-stage timeout wrappers
│   ├── cache.py             # Whisper transcription cache
│   └── metrics.py           # Prometheus metric definitions
```
