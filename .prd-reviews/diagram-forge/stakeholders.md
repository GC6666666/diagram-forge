# Stakeholder Analysis: Diagram Forge

## Summary

The PRD focuses narrowly on end-user personas (engineers, tech leads, technical writers) but omits several critical stakeholder groups whose requirements will directly shape the architecture, deployment, security posture, and long-term viability of the product. The most significant gaps are: no DevOps/Platform Engineering representation, no security team concerns addressed, no third-party integrator strategy, and no legal/compliance input despite the privacy-sensitive nature of image and audio uploads.

## Critical Gaps (things MUST be answered before implementation)

### 1. DevOps / Platform Engineering -- NOT MENTIONED

**Who they are:** The engineers responsible for deploying, monitoring, and maintaining Diagram Forge in production.

**What they need that the PRD does not address:**

- **Claude API key management**: How are credentials injected at runtime? Env vars? Secrets manager (Vault, AWS Secrets Manager)? This is non-negotiable for production.
- **Whisper deployment model**: The PRD lists three options (local, OpenAI API, self-hosted endpoint) with no decision. This is a first-order architectural choice that affects GPU infra, cost, and latency. It cannot be deferred to "later."
- **Telemetry and observability**: No mention of logging, metrics, tracing, or alerting. How do ops teams know the service is healthy? What are the SLOs/SLAs?
- **Auto-scaling**: If multiple users upload simultaneously, how does the service scale? Whisper (especially local) is GPU-bound and expensive. This affects both the Whisper decision and the overall architecture.
- **Cost monitoring**: Claude API is per-token; Whisper (API) is per-minute; local Whisper is GPU-hours. There is no cost envelope defined.
- **Deployment specifics**: "Docker container, single `docker run`" is underspecified. What about health checks, resource limits, restart policies, rolling updates, and environment-specific configs (dev/staging/prod)?
- **Storage model for MVP**: "Temporary only" is vague. What is the retention window? Who cleans up old files? Is there a TTL mechanism? What happens if cleanup fails?

**Decision needed:** Assign Whisper deployment model and define the ops runbook scope before implementation begins.

### 2. Security Team -- NOT MENTIONED

**Who they are:** Internal security engineers responsible for application security, data handling, and access control.

**What they need that the PRD does not address:**

- **Authentication and authorization**: The PRD says "No persistent user accounts required for MVP (stateless API)." If there is no auth, the API is wide open. Who can call it? Is there an API key mechanism? Rate limiting alone is insufficient for production. This is a CRITICAL security gap.
- **Input validation and sanitization**: Images and audio are uploaded. Are there file size limits? Format validation? Malware scanning? DoS protection? The attack surface includes:
  - Malformed images designed to trigger parser bugs
  - Extremely large files to exhaust storage/disk
  - Audio files with embedded payloads (rare but possible with certain formats)
  - Prompt injection via text input (e.g., "ignore previous instructions and...")
- **Data retention and deletion**: "Uploaded images/audio are not stored long-term" is vague policy, not an enforceable technical requirement. How is this implemented? Is there a deletion log? Can users request certified deletion?
- **Claude API prompt injection**: User text/voice input becomes part of prompts sent to Claude. There is no mention of input sanitization or prompt template security. This could allow adversarial diagram descriptions to manipulate Claude's behavior.
- **Network security**: Is the API internal-only? Public? Behind a gateway? TLS required?
- **Secrets rotation**: Claude API keys, Whisper API keys -- how are these rotated without downtime?

**Decision needed:** Auth model and data retention policy must be defined before any external-facing deployment. Prompt injection defenses are required if the service accepts arbitrary user text.

### 3. Third-Party API Consumers -- NOT MENTIONED

**Who they are:** Developers who will integrate Diagram Forge into their own tools, CI/CD pipelines, documentation systems, or internal platforms.

**What they need that the PRD does not address:**

- **API contract stability**: What is the versioning strategy? Will breaking changes be announced? How many prior versions will be supported?
- **Response format and error handling**: The PRD describes output formats but not the API response envelope. What does a success response look like? An error? Are error codes standardized?
- **Async processing**: For image→diagram, processing may take 10-30 seconds. Is the API synchronous (blocking) or does it return a job ID? The current architecture implies synchronous but this may not scale.
- **Rate limiting policy for API consumers**: Open Question #7 mentions "Rate limiting / API key management for the MVP" but there is no consumer-facing policy. Will there be tiers (free/paid)?
- **Webhook or callback mechanism**: If async, how do consumers receive results?
- **SDK availability**: Will official client libraries be provided, or are consumers expected to call raw HTTP?

**Decision needed:** Define whether the API is sync or async, and establish a versioning strategy. API consumers are blocked without these.

### 4. Legal / Compliance -- NOT MENTIONED

**Who they are:** Legal counsel, compliance officers, or privacy teams.

**What they need that the PRD does not address:**

- **Data privacy for EU/international users**: If images or audio from EU users are uploaded, GDPR applies. The service likely processes PII (screen content, voice recordings). There is no Data Processing Agreement (DPA) consideration, no privacy policy requirement, no data minimization statement.
- **Data residency**: If deployed on cloud infrastructure, where does user data flow? US-only? Multi-region? This affects both the Whisper decision (local vs. API) and Claude API deployment.
- **Diagram ownership and IP**: Who owns the generated diagrams? The user who described it? The company running the service? Both? This matters for commercial use cases.
- **Audit trail**: For regulated industries (finance, healthcare, defense), any automated diagram generation from sensitive screenshots may need audit logging. Not mentioned.
- **Acceptable Use Policy**: What happens if users upload copyrighted screenshots, proprietary architecture diagrams, or other sensitive content? Is there a policy?

**Decision needed:** At minimum, a privacy impact assessment and acceptable use policy are required before any public deployment.

## Important Considerations

### 5. Conflicting Needs Between User Groups

**Technical depth vs. accessibility:** The PRD targets "engineers and technical teams" but the stated goal of "fast iteration" and "voice in meetings" implies non-technical or semi-technical users (e.g., product managers in sprint ceremonies) also want to use it. The current text-only/CLI-first approach (Open Question #5: "CLI vs API-first") directly conflicts with accessibility for less technical users. An API-first product requires a front-end wrapper to be usable by the meeting scenario.

**Privacy vs. capability (Whisper):** Local Whisper = maximum privacy, maximum infra cost, maximum maintenance burden. OpenAI Whisper API = best quality, data leaves the infrastructure. This creates a direct conflict between what security/compliance teams need (data stays local) and what users want (best quality output).

**Stateless vs. useful (Open Question #8):** The MVP's "stateless" decision conflicts with the iteration workflow (Scenario 4: "make this more modern" on an existing diagram). Without some state, iteration requires re-uploading the full original diagram every time. The PRD acknowledges this as an open question but does not explore the tradeoffs.

**Multi-format support vs. quality:** Supporting Excalidraw, Draw.io, AND SVG simultaneously means three export paths must be maintained. Each export path will have subtle differences in what shapes/labels are supported. This creates a maintenance burden and an inconsistent user experience depending on output format. Prioritization is needed.

### 6. Internal Team Dependencies

**Frontend / Product Teams:** The README mentions a web interface ("web API is primary"). If a web UI is planned, a frontend team is needed for:
- Image upload UI with drag-and-drop
- Voice recording interface
- Diagram preview before download
- Format selection UI
These are not captured in the PRD at all.

**QA / Testing Team:** No test strategy is mentioned. For a product that processes AI-generated output, testing is non-trivial:
- How to assert diagram correctness (structural validation vs. visual similarity)?
- What golden datasets are used for image→diagram regression testing?
- How to test voice input reliability across accents, languages, and audio quality?
- Chaos testing for malformed inputs.

**Data / ML Team (if local Whisper is chosen):** Local Whisper requires ongoing model maintenance (updating, fine-tuning, GPU infra management). This is a significant ongoing commitment not acknowledged in the PRD.

### 7. Unstated User Personas

**Accessibility users:** People with disabilities who may rely on voice input (already partially covered) or who need screen reader support if a web UI is built. WCAG compliance is not mentioned.

**Non-English users:** Voice input is heavily language-dependent. Whisper's quality varies by language and dialect. If the service is used internationally, non-English voice support and non-English text input (diagram labels) need consideration.

**Enterprise users with strict network policies:** Users in air-gapped environments or behind strict corporate firewalls cannot use the OpenAI Whisper API. The PRD does not consider air-gap deployment as a use case.

**CI/CD automation engineers:** Users who want to programmatically generate diagrams as part of automated documentation pipelines. They need stable API contracts, idempotent behavior, and reliable error handling -- none of which are specified.

### 8. Launch Coordination

**Who needs to be notified at launch:**
- Internal engineering teams (so they can integrate)
- Technical writing / documentation team (to document the API)
- Sales / marketing (if this is a commercial product -- no mention of this)
- InfoSec (to approve the security posture before go-live)
- Customer support (for handling user issues)
- Excalidraw / Draw.io community (potentially, as a new integration point)

### 9. Developer Experience

**API usability:** A well-designed API should be self-documenting (OpenAPI/Swagger), have example requests/responses, and provide clear error messages. None of this is mentioned.

**DX for contributors:** If this is an open-source project, contributors need: contribution guidelines, coding standards, a local dev environment setup, and dependency management. Not covered.

**Claude API prompt management:** The PRD treats the AI layer as a black box ("Claude API calls with structured prompts"). In practice, prompt engineering is an ongoing effort. There is no mention of a prompt versioning strategy, A/B testing of prompts, or a way to track prompt quality over time.

## Observations

1. **README and PRD are out of sync on OCR:** The README mentions `src/ocr/` with "GPT-4V, PaddleOCR" but the PRD only mentions Claude API for diagram generation and does not mention OCR as a separate module. The image→diagram pipeline is ambiguous -- is OCR done before AI generation? During? Are they combined? This inconsistency suggests either the README is ahead of the plan, or the plan is missing the OCR component.

2. **Data directory structure in README does not match PRD storage approach:** README shows `data/input/`, `data/output/`, `data/templates/` -- persistent directories. PRD says "Temporary only for MVP" and "Output files are downloaded, not stored server-side." These are contradictory. Persistent directories and stateless API are fundamentally incompatible.

3. **The "No persistent user accounts" decision creates downstream complexity:** While this simplifies the MVP, it eliminates personalization, history, and subscription management. If these are added later, they require a significant architectural shift. The long-term account model should be thought through even if not implemented for MVP.

4. **Claude API cost is unbounded in the current design:** Every diagram generation call costs tokens. With image→diagram, there may be additional vision API costs. There is no cost cap, no user-level budget, no free tier defined. This is a business model gap, not just a technical one.

5. **Open Question #5 (CLI vs API-first) is a strategic fork:** This choice determines the entire product direction. CLI-first = developer-focused niche tool. API-first with web UI = broader audience. These require fundamentally different architectures, teams, and timelines.

## Confidence Assessment

**Medium-Low Confidence**

Rationale: The PRD has well-defined user scenarios and a coherent high-level vision, which gives us confidence in what the product is trying to solve. However, the critical gaps identified above (auth model, Whisper decision, storage model, security posture, legal compliance, API contract) are all first-order architectural decisions that are either unresolved or entirely absent. The most concerning gap is the combination of "stateless, no auth" with "upload images/audio" and "GDPR-relevant data" -- this trio of decisions creates a product that cannot safely be deployed to production without significant additional work. Until these are resolved, implementation carries high risk of rework.

The two specific inconsistencies (README vs. PRD on OCR, README vs. PRD on storage) also reduce confidence that the PRD reflects the actual intended implementation.
