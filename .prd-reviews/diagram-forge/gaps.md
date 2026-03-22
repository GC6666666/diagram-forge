# Missing Requirements: Diagram Forge PRD Gap Analysis

## Summary

The PRD draft covers the happy path for converting images, voice, and text into diagrams. It omits cross-cutting concerns around security, operations, reliability, and lifecycle management that are essential for any production system. Most critically, the document assumes a stateless, unauthenticated MVP forever — a choice that will create significant friction when real users, real usage, and real operational needs arrive.

## Critical Gaps (MUST be answered before implementation)

### 1. Authentication and Authorization

The PRD explicitly states "No persistent user accounts required for MVP (stateless API)" but never defines who can access the API, how they prove their identity, or how access is revoked.

- How do users authenticate? API keys? OAuth tokens? No auth at all?
- If no auth: is the API public? What prevents open abuse?
- If API keys: how are they provisioned, rotated, and revoked?
- Are there permission tiers (e.g., free vs. paid)? Different rate limits per tier?
- The PRD mentions "teams in meetings" as actors — does every team member need their own key, or is there a team-level credential?
- What happens to a user's API key if they leave an organization?

### 2. Rate Limiting and Abuse Prevention

Open Question #7 flags this but provides no answer. For a stateless, potentially unauthenticated API:

- What are the rate limits? Per-IP? Per-API-key? Per-tenant?
- What happens when limits are exceeded? HTTP 429 with Retry-After? Token bucket? Leaky bucket?
- Is there a circuit breaker on AI provider calls to prevent runaway costs?
- What is the retry strategy for transient failures (AI provider downtime, network issues)?
- Is there protection against prompt injection or malicious input designed to produce harmful content?
- Are there input size limits? A 50MB image or a 10-minute audio file could DoS the service cheaply.

### 3. Data Retention and Privacy (beyond "not stored long-term")

"Uploaded images/audio are not stored long-term" is vague and likely legally insufficient.

- What does "long-term" mean? Minutes? Hours? Days?
- Is there a defined retention window for temporary storage (e.g., logs, temp files, failed-job artifacts)?
- Are uploaded files shared with the AI provider (Claude)? Does that constitute a data processing agreement?
- For audio: does Whisper (local or API) retain recordings? Under what jurisdiction?
- Is there a data deletion / right-to-erasure mechanism? If a user sends an image and later asks for it to be deleted, can we comply?
- What logging occurs? Do logs contain any portion of user input (text descriptions, image filenames)?
- Is there a privacy policy or terms of service document users must agree to?

### 4. Backwards Compatibility and API Versioning

As a FastAPI service, the API will evolve. The PRD does not address:

- How are breaking changes to the API handled? URL versioning (/v1/, /v2/)? Header-based? Query param?
- What is the deprecation policy? How long are old versions supported?
- For output formats: Excalidraw JSON schema evolves. Draw.io XML schema evolves. How do we maintain compatibility with newer versions of these tools?
- When we change internal representation, do existing exports break? Is there a migration path?
- Is there a changelog or migration guide for API consumers?

### 5. Concurrent Access and Request Management

Multiple simultaneous users hitting the service simultaneously:

- Is there a maximum queue depth? What happens when the queue is full?
- Are AI provider calls made concurrently, or is there a semaphore limiting concurrency to prevent rate limit exhaustion?
- If a request is cancelled (client disconnects mid-stream), does work continue server-side wastefully?
- Is there a request timeout? Who sets it — the server, the client, or the AI provider?
- Are there request IDs for tracing? Can a user or operator correlate logs to a specific request?

### 6. Admin Tooling and Operational Visibility

No operations tooling is defined:

- How do operators debug a failing request? Is there structured logging (JSON logs)?
- Is there a health endpoint (/health, /ready, /metrics)?
- Are there Prometheus/OTel metrics? What is monitored (latency, error rate, AI provider costs)?
- Is there a way to inspect in-flight or recent requests for debugging without direct database access?
- If the service fails, what is the recovery procedure? Is there a runbook?
- Are there environment-specific configs (dev, staging, prod) or is it one-size-fits-all?
- How is the service deployed? Restarted? Logs accessed? (The PRD says "single docker run" but doesn't cover ongoing operations.)

### 7. Error Handling and User Feedback

The PRD covers the happy path but not failure modes:

- What does a user get back when the AI provider fails? A generic 500? A structured error with a code?
- Are there user-actionable error messages (e.g., "image too large", "audio too long", "diagram too complex")?
- Is there a taxonomy of error codes that API consumers can programmatically handle?
- What is the SLA / availability target? Is this documented anywhere?

## Important Considerations (should be addressed but aren't blockers)

### 8. Multi-Tenancy

Even for a stateless API, multi-tenancy matters:

- Are there shared resources (AI provider quotas, file storage) that tenants could starve each other of?
- Is there isolation between tenants' processing? Can one tenant's image appear in another tenant's logs?
- Do different tenants have different rate limits or feature access?
- If multi-tenancy is added later, what changes are needed? (Designing for multi-tenancy from day one is much cheaper than retrofitting.)

### 9. Data Migration

Mildly relevant given the "consider S3-compatible for future" storage note:

- If storage is introduced in a later phase, what is the migration path from temporary-only to persistent?
- If the internal diagram representation changes, can older generated diagrams be re-exported in new formats?
- Is there any existing data (diagrams, preferences) that needs migration from a prior system?

### 10. Audit Logging and Compliance

- Are API calls logged? For how long? In what format?
- For regulated industries (healthcare, finance, government): can customers request audit logs of their diagram generation?
- Is there any PII in logs that needs to be handled under GDPR, CCPA, or similar?
- Is there a data processing agreement (DPA) template for enterprise customers?

### 11. Internationalization and Localization

- The PRD assumes English ("plain English" inputs). Is multilingual input supported?
- Are error messages localized? API error strings in multiple languages?
- Date, time, and number formatting in any exported metadata?
- RTL language support for exported SVG/Draw.io content?

### 12. Accessibility Requirements

- Is the API documentation accessible (WCAG-compliant docs site)?
- For any web-based UI (even minimal): keyboard navigation, screen reader support?
- Are SVG exports accessible (aria labels, semantic structure)?
- Is there a plain-text alternative for generated diagrams (for screen readers)?

### 13. Edge Cases: Empty, Null, and Zero States

Multiple scenarios are unhandled:

- Empty image (white/transparent file): what is returned?
- Empty audio (silence): what is returned?
- Empty text input ("", just whitespace): HTTP 400? Empty diagram? Silent rejection?
- Audio with no speech detected (just noise): error, empty diagram, or something else?
- Image that is not a diagram (e.g., a photo of a cat): does the AI hallucinate a diagram, or return a specific error?
- Text describing something that cannot be diagrammed (e.g., "blue"): what is returned?
- Extremely large inputs (long audio, very complex text description): timeout behavior?
- Non-image file uploaded as "image": graceful rejection?
- Corrupt or unreadable image file: graceful rejection?

### 14. Deprecation and Cleanup

- Open Question #3 ("ambiguous layouts") and Open Question #9 ("SVG fully editable") suggest that early design decisions will need to change. What is the process for deprecating output formats or changing the internal representation?
- When a feature is removed, how are API consumers notified?
- Is there a sunset period for deprecated endpoints?
- How are old Docker images cleaned up in CI/CD?

### 15. Input Validation and Sanitization

Closely related to edge cases but worth calling out separately:

- What image formats are accepted? PNG, JPEG, WebP, HEIC from phones?
- What audio formats? MP3, WAV, OGG, M4A?
- Maximum file sizes for each input type?
- Maximum text input length?
- Are there restrictions on output diagram complexity (e.g., maximum number of nodes, arrows)?
- Is there content filtering on text inputs (profanity, harmful content)?

### 16. Dependency Management and Supply Chain Security

Not mentioned at all:

- How are Python dependencies pinned and updated? requirements.txt? Poetry? pyproject.toml?
- Is there a lock file to ensure reproducible builds?
- Are there known CVEs in dependencies? Is there a scanning process?
- Is the Docker base image pinned? Updated regularly?
- Are AI provider API clients pinned to a specific version with known behavior?

### 17. Testing Strategy

The PRD mentions no testing requirements:

- What kinds of tests are required? Unit? Integration? E2E?
- Is there a test coverage threshold?
- How are AI provider outputs tested? They are non-deterministic. Are golden files or fuzzy matching used?
- Is there a staging environment that mirrors production for integration testing?
- Are there load tests? What throughput target must be met?

## Observations

1. **The MVP scope is underspecified as a long-term constraint vs. a short-term deferral.** Stating "no persistent user accounts" and "temporary only storage" as features rather than phase-1 deferrals locks the team into a stateless model that will be expensive to change later. This is the single most consequential gap — it shapes every other decision.

2. **Open Question #7 (rate limiting / API key management) is both a critical gap and a blocker.** You cannot ship even an MVP without some form of access control and abuse prevention. Even a simple pre-shared key model requires key distribution, rotation, and revocation infrastructure.

3. **The AI provider (Claude API) is a single point of failure with no fallback.** If Claude is unavailable or returns errors, the entire service is down. There is no mention of fallback behavior, retry logic, or alternative providers.

4. **Cost modeling is absent.** AI provider calls are not free. The PRD does not discuss cost management, budget caps, cost-per-request, or how costs are allocated across tenants. This is essential for pricing and for preventing runaway bills.

5. **The "Output files are opened in the respective tools" assumption is fragile.** Excalidraw and Draw.io have their own format quirks, version differences, and rendering behaviors. The PRD does not address format version compatibility or what happens when a newer Excalidraw release breaks an older JSON export.

6. **Scenario 4 ("make this more modern") implies context continuity that a stateless model cannot support.** Iterating on an existing diagram requires either storing the prior version or re-sending the entire context. Neither is addressed.

## Confidence Assessment

**Medium** — The PRD provides a clear problem statement and happy-path user scenarios. The modular pipeline architecture is sensible. However, the document lacks depth on cross-cutting concerns, and many "Open Questions" are not questions but decisions that must be made before implementation. The two most significant gaps (authentication and rate limiting) are acknowledged as open questions but not answered, which suggests the PRD is still in a very early draft stage. The confidence is not Low because the core value proposition and technical approach are coherent; it is not High because the missing sections represent real production requirements that will delay or derail implementation if deferred.
