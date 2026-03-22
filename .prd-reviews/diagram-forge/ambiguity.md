# Ambiguity Analysis

## Summary

The PRD is well-scoped and clearly written overall, but contains several areas where key terms, conditions, or requirements are undefined or stated ambiguously. The most critical gaps center on: (1) what "clean, editable" actually means in practice, (2) the boundary between what's required vs. optional in the pipeline, (3) how ambiguous inputs are handled, and (4) what success looks like for diagram quality. These gaps could lead to significant rework if not resolved before implementation.

---

## Critical Gaps (things MUST be answered before implementation)

### 1. What does "clean, editable" mean in practice? (Goal 1, Scenarios 1 & 4)

The PRD repeatedly promises "clean, editable" output but never defines:
- Are shapes pre-aligned? Snapped to grid? What grid settings?
- Are labels auto-wrapped? What font sizes are used?
- Are groups/_layers meaningful (e.g., "database tier" grouped together) or flat?
- What level of fidelity to the original is expected? 50%? 90%?
- Scenario 4 says "make this more modern" — what is "modern"? This is subjective. Who adjudicates when the result doesn't match the user's intent?

**Risk**: Without a quality benchmark, the team cannot know when a diagram is "done" and stakeholders cannot evaluate success.

### 2. What diagram types are actually supported? (Goal 2 vs. Scope)

Goal 2 mentions "sequence diagram" explicitly. Goal 3 mentions "architecture diagram." Scenario 3 mentions "architecture diagram" with specific component types. But the Non-Goals only say what is *not* supported (infographics, marketing graphics). The PRD never enumerates what diagram types *are* supported.

- Is "architecture diagram" the same as "component diagram" in UML terms?
- Are ER diagrams supported? Class diagrams? State diagrams?
- Are all Mermaid diagram types in scope?
- When a user describes something ambiguous (e.g., "show the flow"), which diagram type does the system pick?

**Risk**: Without a defined taxonomy of supported diagram types, prompts to the AI layer cannot be reliably structured, and iteration will be ad-hoc.

### 3. What ordering guarantees exist? (Implicit Pipeline Ordering)

The rough approach lists the pipeline as: Input → Parser → AI Generation → Exporter. But:
- Does the Parser run before AI Generation, or are they concurrent/pipelined?
- If a user provides both an image and text description, which takes precedence?
- For Scenario 4 ("add a cache layer"), is the system supposed to modify the existing Excalidraw JSON, or regenerate from scratch? The wording suggests modification, but the pipeline architecture suggests regeneration.
- Are intermediate representations cached? Discarded?

**Risk**: The pipeline ordering affects architecture decisions significantly. If modification is required (Scenario 4), the AI layer needs access to the parsed internal representation, not just the raw input.

### 4. What is the "internal representation"? (Rough Approach)

The Exporter is described as converting "internal representation → Excalidraw JSON / Draw.io XML / SVG." But:
- What is this internal representation? A graph of nodes and edges? A semantic tree?
- Is it diagram-type-specific or universal?
- Who designs this representation? No one yet has.
- Does it include layout hints, or is layout entirely the AI's responsibility?

**Risk**: This is arguably the most important design decision in the system, and the PRD treats it as an implementation detail rather than a product decision. It affects every export path.

### 5. What does "seconds, not minutes" mean as a performance target? (Goal 5)

"Fast iteration: Convert and iterate on diagrams in seconds, not minutes" is a goal, but:
- Is this a SLO? A promise to users? An internal target?
- What's the p95 latency? p99?
- Does "seconds" include network round-trip to the AI provider? Image size variations? Audio length?
- What happens when Claude API latency spikes? Is there a timeout? A fallback?

**Risk**: Without explicit latency targets, there's no way to set timeouts, allocate compute budgets, or define degradation behavior.

### 6. What is the CLI vs. API boundary? (Open Question 5 & Open Question 7)

The PRD says "web API is primary; CLI is secondary." But:
- Is the CLI just a wrapper around the API, or does it call Claude directly?
- If the CLI calls Claude directly, how are API keys managed? (Open Question 7)
- If the CLI uses the local API server, why is it "secondary"? Isn't the API server the primary regardless?
- Is there a planned web UI? The PRD doesn't mention one, but "web API is primary" implies something is consuming it.

**Risk**: API key management and CLI authentication are security-critical decisions that affect deployment and user experience significantly.

### 7. What is the exact user experience for output delivery? (Non-Goals + Scenarios)

The Non-Goals state that output files are "opened in the respective tools" or "downloaded." But:
- Does the API return a file download? A URL to download from? A base64 blob?
- For Excalidraw JSON, does the user get a `.excalidraw` file? A `.json` file?
- For Draw.io, is it `.drawio` or `.xml`?
- What does "opened in the respective tools" mean operationally? Is there a link that opens in Excalidraw Live App? Is that even possible for private diagrams?
- "Output files are downloaded, not stored server-side" — but if not stored, how is the "open in tool" path supposed to work? A temporary URL?

**Risk**: Output delivery UX is a core user-facing concern. Without it defined, the exporter and API response format cannot be designed.

### 8. How are "ambiguous layouts" handled in image→diagram? (Open Question 3)

Open Question 3 acknowledges this is a known problem but leaves it as "open":
- Does the system pick one interpretation and return it?
- Does it return multiple options?
- Does it ask the user for clarification? How?
- If the input is "ambiguous," is this a failure mode or a feature?

**Risk**: This is a core conversion quality question. If not defined, the AI prompts will produce inconsistent results.

---

## Important Considerations

### 9. "Reasonable" and "appropriate" language appears in Open Questions

Open Question 1 asks about OCR tradeoffs — the "privacy vs. capability" framing is fine, but "appropriate" in Open Question 3 ("How to handle ambiguous layouts") needs a defined answer before implementation.

### 10. Conflicting signals on storage (Constraints vs. Non-Goals vs. Open Question 8)

- Constraint: "Uploaded images/audio are not stored long-term"
- Non-Goal: "Diagram *hosting* or *sharing* (output files are downloaded, not stored server-side)"
- Open Question 8: "Should diagrams be stored/retrievable, or always generated fresh?"
- Rough Approach: "Temporary only for MVP; consider S3-compatible for future"

These are consistent but Open Question 8 implies a design decision that hasn't been made. "Temporary" for what duration? Minutes? Hours? Until the session ends? What about the internal representation — is *that* ever stored?

### 11. Whisper deployment ambiguity (Constraints vs. Open Question 2)

The Constraints section says "Whisper (local or API)" — this "or" means the decision is already made in the constraint. But Open Question 2 re-asks this. One of these must be wrong or imprecise.

### 12. SVG export type not defined (Open Question 9)

"Should it be fully editable SVG or rendered raster-like SVG?" is a product decision, not just a technical one. Editable SVG means paths and text elements; "raster-like SVG" means it's essentially a PNG in SVG format. These have wildly different use cases.

### 13. Multi-page/multi-panel diagrams (Open Question 10)

How does a single image input produce multiple diagrams? Is this batch processing (Open Question 4)? Are they separate API calls? Or is there a single response with multiple diagram outputs?

### 14. Persona confusion in Actors section

The Actors list mixes individual roles (software engineers, tech leads) with situational contexts ("Teams in meetings") and a profession ("Technical writers"). Are "teams in meetings" a distinct user type who might have different needs (e.g., real-time collaboration) vs. individual engineers? The Non-Goals explicitly exclude collaborative editing, but "teams in meetings" sounds like a collaborative scenario.

### 15. "Industry-standard diagrams" — whose standard?

The Problem Statement says "industry-standard diagrams" but doesn't specify which industry. Software engineering? The PRD clearly targets software/technical teams, but "industry-standard" could mean UML, BPMN, or something else. If the AI can produce any diagram type, that's an enormous scope. If it's constrained to a subset, which subset?

### 16. What is the failure mode when AI generation fails?

The PRD never describes what happens when the AI layer fails to produce a valid diagram. Does it return an error? A partial diagram? Retry automatically? Retry how many times?

---

## Observations

- The Open Questions section is honest and well-structured, but several of those questions are actually product requirements decisions, not open technical questions. They should be elevated out of "open questions" into "requirements decisions" before implementation begins.
- The "Modular pipeline" design is good architecture intent, but the internal representation is the linchpin — it's mentioned but never described.
- The Scenarios are concrete and useful for user empathy, but they all describe successful paths. No failure scenarios are described.
- The Non-Goals section is strong and helps bound scope. However, "no mobile-native experience" conflicts somewhat with Scenario 1 (Alice uploads from her phone) — a phone upload is a mobile experience, even if the API isn't mobile-native.
- The Claude API is treated as a black box. There's no discussion of: prompt versioning, prompt templates per diagram type, how to handle API changes, or fallback behavior.

---

## Confidence Assessment

**Medium**

The PRD is clear in its high-level intent and does a good job of scoping via Non-Goals. However, the critical design decisions — internal representation format, diagram type taxonomy, latency targets, and output delivery UX — are either absent, buried in "Open Questions," or treated as implementation details. An implementation team reading this PRD would have to make numerous architectural decisions that should be product decisions.

The ambiguity analyst's confidence would increase significantly if:
1. The internal representation format is defined (at least abstractly)
2. A specific list of supported diagram types is enumerated
3. Latency targets (p95) are specified for each input modality
4. Output delivery mechanism is defined (file download, URL, etc.)
5. Failure modes are described
6. Open Questions 3, 5, 8, and 9 are resolved (these have the highest implementation impact)
