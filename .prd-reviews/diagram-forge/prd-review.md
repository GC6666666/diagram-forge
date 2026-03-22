# PRD Review: Diagram Forge

## Executive Summary

6 parallel analysts reviewed the PRD across dimensions: requirements, gaps, ambiguity, feasibility, scope, and stakeholders. Overall confidence: **LOW**. The PRD is a strong product vision with clear user value, but it lacks the engineering surface area needed to build from. 10+ unresolved open questions are blocking architectural decisions, zero quantified acceptance criteria exist, and the MVP boundary is undefined — the document reads as a feature-complete product rather than a buildable first release. Most critically, the central technical problem (LLM → structured diagram output) is unspecified, and the image→diagram pipeline is severely under-scoped as a single feature.

## Confidence Assessment

| Dimension | Score | Notes |
|-----------|-------|-------|
| Requirements completeness | LOW | No quantified metrics, no error taxonomy, no NFRs |
| Technical feasibility | LOW | Central LLM-to-diagram problem unsolved |
| Scope clarity | LOW | No MVP definition; all features implied to ship together |
| Ambiguity level | MEDIUM | Several undefined terms but overall well-written |
| Stakeholder coverage | MEDIUM | User scenarios solid; ops/security/legal missing |
| **Overall readiness** | **LOW** | Cannot implement as written |

## Before You Build: Critical Questions

These must be answered before implementation can begin.

### [Scope & MVP]

**Q1: What ships in v1?**
The PRD describes 3 input modalities, 3 output formats, 4+ diagram types — all assumed to ship together. Without an MVP definition, every developer will default to "everything ships."
- Options: (A) Text→Excalidraw only, architecture/block diagrams, one format; (B) All text/voice/image modalities but only Excalidraw output; (C) Everything in the PRD ships together
- Recommendation from reviewers: **Option A** — text→Excalidraw is the simplest path through the hardest unsolved problem.

**Q2: Which diagram types are in scope for v1?**
Sequence, architecture, flowchart, ER, class, component are all mentioned. Are all of these v1? Or only block/architecture diagrams?
- Recommended: **Architecture/block diagrams only for v1**; sequence and flowchart in phase 2; ER/class in phase 3.

**Q3: Is iteration on existing diagrams (Scenario 4) in scope?**
"Make this more modern" or "add a cache layer" on an existing diagram requires either storing prior diagrams or re-uploading everything. This conflicts with the stateless constraint. If it stays stateless, iteration means re-sending the full context every time — acceptable?
- (A) Yes, stateless iteration is fine — users re-upload; (B) No, we need minimal state to support iteration.

### [Architecture]

**Q4: What is the internal diagram representation?**
The pipeline mentions "Input → Parser → AI Generation → Exporter" with an internal representation, but this is never defined. This is arguably the most important design decision — every exporter depends on it.
- No need to design the full spec now, but we need a provisional data model before implementation starts.

**Q5: How does the AI layer generate structured diagram output?**
Claude cannot natively output Excalidraw JSON or Draw.io XML. The approach (multi-step generation? structured output? prompt engineering?) is unspecified.
- Key tradeoff: (A) Experimental — try prompt engineering first, iterate; (B) Conservative — use a structured intermediate format and convert; (C) Leverage the Excalidraw MCP tool already running in this environment.

**Q6: Voice input — which Whisper deployment?**
Options: OpenAI API (quality, cost, network dependency), local (GPU, privacy, ops burden), self-hosted endpoint (middle ground).
- Recommendation: **OpenAI Whisper API for v1** — simplest path, fastest to ship. Local if privacy is a hard requirement.

**Q7: CLI vs API-first?**
"Web API is primary; CLI is secondary" is stated but no endpoints are defined. Are we building: (A) FastAPI with a web UI; (B) FastAPI CLI tool with HTTP client; (C) Standalone CLI that calls Claude directly.
- Recommendation: **FastAPI + CLI wrapper** — CLI is `curl` wrapper around the API. Ship the API first.

### [Security & Access]

**Q8: Authentication model?**
"No persistent user accounts" is stated. But: (A) Fully open API — no auth, public, rate-limited; (B) Pre-shared API keys only — simple, no account management; (C) OAuth/OIDC — more complex but supports teams.
- Recommendation: **API key (pre-shared) for v1** — simplest thing that prevents open abuse.

**Q9: What input formats and limits?**
Images: which formats? Max file size? Max dimensions? Audio: max duration? Text: max characters?
- Need concrete limits before implementation: e.g., PNG/JPEG/WebP, max 10MB, max 4096×4096px; audio MP3/WAV max 60s; text max 4000 chars.

**Q10: What does "not stored long-term" mean exactly?**
Minutes? Hours? Until the request completes? And: do Claude API calls mean user data goes to Anthropic?
- Need a concrete retention window (e.g., 1 hour TTL) and clarity on data flow through Claude API.

## Important But Non-Blocking

These should be answered before or during v1 development, but don't block implementation start:

- **Latency targets**: "Seconds, not minutes" — what's the p95? Text/voice can hit <10s; image likely 5-15s.
- **Error taxonomy**: What happens when OCR fails, Claude returns bad JSON, image is too complex?
- **SVG export**: Fully editable SVG (paths/text groups) vs. rendered SVG (single path)? These are different engineering efforts.
- **Image→diagram pipeline**: OCR is one step; shape detection, layout inference, arrow mapping are 4+ more steps. Each is a separate research problem.
- **Prompt versioning**: How are prompts per diagram type managed, tested, and updated?
- **Observability**: Health endpoints, structured logging, metrics — at minimum for ops to debug.

## Observations

- **README and PRD are out of sync**: README shows persistent `data/` directories; PRD says stateless. These contradict each other.
- **README mentions OCR** (GPT-4V, PaddleOCR); PRD omits it entirely. Which is correct?
- **Image→diagram is 5 features in disguise**: OCR, shape detection, layout inference, style normalization, format serialization. Treat each as separate.
- **Iteration (Scenario 4) is a second system**: Parsing+modifying existing diagrams ≠ one-shot generation. Scope accordingly.
- **Batch processing is a job queue system**, not a feature gate. Don't ship in v1.
- **Claude API is a single point of failure** — no fallback provider or retry strategy mentioned.

## Next Steps

- [ ] You answer the 10 critical questions above (reply with numbered answers)
- [ ] PRD is updated with answers
- [ ] Design phase begins: define internal representation + MVP architecture
- [ ] Implementation follows phased approach
