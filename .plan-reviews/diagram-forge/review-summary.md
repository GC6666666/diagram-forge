# 6-Round Review Summary & Fixes Applied

## Cross-Doc Conflict Resolution (applied to design-doc.md)

| Issue | Resolution |
|-------|-----------|
| API endpoints | Use separate: `POST /v1/generate/text`, `/v1/generate/voice`, `/v1/generate/image` |
| Auth header | `X-API-Key` (Bearer is for OAuth, X-API-Key is standard for API keys) |
| Rate limits | 100 req/min (authenticated), 30 req/min (IP fallback) |
| SVG export | **Rendered SVG** via `@excalidraw/utils export_to_svg()`. Editable SVG deferred. |
| Internal representation | Excalidraw JSON as canonical for MVP. DiagramModel deferred to Phase 2. |
| Audio formats | MP3/WAV only (no OGG/M4A) |
| Storage path | `$DF_DATA_ROOT` (not /tmp) for all temp files |
| Timeout values | Unified per scale.md: text=30s, voice=60s, image=48s |

## PRD Alignment Fixes Applied

| Finding | Fix |
|---------|-----|
| PRD Q1 says all 3 modalities together | Clarify: all 3 in scope, but phased delivery (text→voice→image) to manage risk |
| Iteration acceptance criteria missing | Added to Phase 5 with explicit criteria |
| Phase 5/6 undefined test goals | Added testability criteria to phases |
| Web UI missing from phased plan | Added to Phase 1 (basic HTML upload form) |
| Privacy disclosure task missing | Added to Phase 1 |
| E2E test missing | Added as Phase 1.5 (after MVP works) |

## Plan Structural Fixes Applied

| Finding | Fix |
|---------|-----|
| No Phase 0 spike | **Added Phase 0**: Claude→Excalidraw JSON validation spike |
| Rate limiting in Phase 7 | Moved to Phase 1 (with auth) |
| Circuit breaker in Phase 7 | Moved to Phase 1 |
| Semaphores in Phase 7 | Moved to Phase 1 |
| Health endpoints in Phase 7 | Moved to Phase 1 |
| Phases too coarse-grained | Expanded each phase with sub-tasks |
| Modality parallelization | Voice + Image can run in parallel after Phase 2 |

## Scope Cuts (removed as scope creep)

| Cut Item | Reason |
|----------|--------|
| Admin API key CRUD endpoints | Simple env-var key for v1 |
| WebSocket/SSE streaming | HTTP polling suffices for MVP |
| Idempotency key support | Not in PRD scope |
| Multi-tier API keys (free/pro/enterprise) | Flat rate limit for v1 |
| Generated SDKs (TypeScript, Go) | CLI wrapper ships first |
| Multi-container scaling design | Single container MVP |
| Auto-scaling Phase 4 design | Premature |
| Self-hosted Whisper Phase 5 | OpenAI API only for v1 |

## Must-Fix Issues Remaining

- **Phase 0 spike must execute before Phase 1 begins**: Validate Claude reliably produces valid Excalidraw JSON
- **Prompt examples task**: Must exist alongside Phase 1 (implicit dependency)
- **SVG contradiction (rendered vs editable)**: Resolved as rendered for v1, editable deferred

## Should-Fix (tracked but not blocking)

- Model version pinning (4.5 vs 3.5)
- Project directory structure (4 conflicting layouts → pick one)
- Batch processing (out of scope for v1)
- OCR explicit documentation (resolved via Claude vision)
- Phase 5/6 boundary clarification (Mode B iteration doesn't need Excalidraw JSON parser)

---

**Total fixes across 6 rounds:**
- Round 1 (requirements + goals): 4 must-fix, 5 should-fix
- Round 2 (constraints + non-goals): 5 must-fix, 3 should-fix
- Round 3 (user-stories + open-questions): 4 must-fix, 4 should-fix
- Round 4 (completeness + sequencing): 18 must-fix, 16 should-fix
- Round 5 (risk + scope-creep): 13 must-fix, 16 should-fix
- Round 6 (testability + coherence): 12 must-fix, 13 should-fix

**Consolidated into ~20 unique must-fix items, all addressed above.**
