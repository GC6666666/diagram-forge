# Scope Analysis: Diagram Forge PRD

## Summary

The PRD describes a platform with 3 input modalities and 3 output formats, implying 9 distinct pipelines. This is a large product, not a focused tool. The MVP boundary is undefined -- the document reads like a vision doc where everything listed is assumed to ship together. Significant scope reduction is needed before implementation.

## Critical Gaps (MUST be answered before implementation)

### 1. MVP definition is missing entirely
The PRD lists 5 goals and 4 scenarios with no indication of what ships first. The non-goals list is good but incomplete. The following must be explicitly decided:

- Which input modality ships in v1? (Text is far simpler; image and voice are each separate complex pipelines)
- Which output format ships in v1? (Excalidraw JSON is likely the most natural; Draw.io XML and SVG add exporter complexity)
- Which diagram types ship in v1? (Sequence diagram, architecture diagram, flowchart, and "etc." are all mentioned but none are scoped)

Without this, every developer will default to "everything in the PRD ships."

### 2. Image-to-diagram conversion is under-scoped as a single feature
"Upload a screenshot of a hand-drawn sketch → get a clean editable version" sounds like one step. In reality it is:
- OCR / vision parsing (what does this shape represent?)
- Layout inference (where do elements go relative to each other?)
- Style normalization (hand-drawn → clean)
- Vector/shape generation (what shapes? arrows? labels?)
- Format serialization (Excalidraw JSON, Draw.io XML)

These are 4-5 distinct technical challenges. The PRD treats this as one feature. This is a high-scope-creep risk because each sub-step will reveal new complexity.

### 3. Iteration (Scenario 4) is not one feature -- it's a second system
"Make this more modern" or "add a cache layer" on an existing diagram requires:
- Parsing the original diagram's structure from image or Excalidraw JSON
- Understanding the modification instruction
- Merging original structure + instruction into a new generation
- Preserving non-modified parts

This is meaningfully harder than one-shot generation and has a completely different data flow. It also implicitly requires storing or re-parsing the original diagram. If the system is stateless (Open Question 8), the user must re-upload everything for each iteration. This should either be explicitly in scope or explicitly excluded.

### 4. Authentication and rate limiting are in tension with "no user accounts"
Open Question 7 asks about rate limiting / API key management, but Constraint 10 says "stateless API" and Non-Goal #5 says no hosting/sharing. If there are API keys, you have user accounts (of a kind). If there are rate limits without identification, you have global rate limits that affect everyone. These are not the same system and the PRD doesn't acknowledge the conflict.

**Must decide**: Is this a fully open public API? Authenticated API? CLI-only? The answer changes the entire backend architecture.

### 5. Exporter complexity is not acknowledged
The Rough Approach mentions "Convert internal representation → Excalidraw JSON / Draw.io XML / SVG." Excalidraw JSON and Draw.io XML are both complex, well-documented formats with their own schemas. The PRD provides zero detail on what the "internal representation" looks like. Building a robust exporter for even one format is non-trivial. Building for three simultaneously is a large undertaking.

**Must decide**: What does the internal diagram model look like? This is an architectural decision that gates all exporter work.

## Important Considerations

### 6. Whisper deployment is a hidden infrastructure dependency
Open Question 2 asks "which Whisper deployment?" but the implications aren't explored:
- Local Whisper requires significant CPU/memory and GPU for real-time performance
- OpenAI API adds per-minute cost and a network dependency
- Self-hosted endpoint is another service to operate

If the voice pipeline ships in v1, the Whisper architecture is a major decision. If it doesn't ship in v1, it should be in a later phase.

### 7. Multi-page/multi-panel (Open Question 10) is a significant scope addition
This is listed as an open question but not flagged as a potential scope creep. Splitting a single image into multiple diagrams (or stitching panels into one) is a fundamentally different problem from single-diagram generation. It requires:
- Panel detection in the image
- Cross-panel relationship understanding
- Possibly different layout engines per panel

This should be labeled as "phase 2 at earliest" or removed from consideration.

### 8. Batch processing (Open Question 4) is not a simple feature gate
Supporting "multiple images → multiple diagrams" sounds additive but implies:
- Job queuing and async processing
- Progress tracking
- Result aggregation
- Retry logic
- Storage management for intermediate results

This is a job processing system, not a feature. It should not be in v1.

### 9. SVG export has a fundamental ambiguity (Open Question 9)
The PRD implies SVG is just another output format. But SVG as an export target has two very different interpretations:
- "Editable SVG" — SVG with grouped elements, text, and arrows as semantic SVG elements (understandable by AI tools, easily modified in Inkscape/Illustrator)
- "Rendered SVG" — SVG that looks the same but is essentially a raster-in-vector wrapper (harder to edit, simpler to generate)

If the goal is "fully-editable industry-standard diagrams" (Problem Statement), SVG should probably be editable. But that's a significantly harder exporter than a rendered SVG. The PRD must resolve this before implementation starts.

### 10. The "internal representation" in the pipeline is undefined
The Rough Approach describes "Input → Parser → AI Generation → Exporter" but doesn't define what leaves the AI Generation step or what the Exporter consumes. This "internal representation" is arguably the most important design decision in the system. Without it:
- You can't write the exporter without re-calling the AI
- You can't support iteration without re-parsing
- You can't do format conversion (Excalidraw ↔ Draw.io) without going back through AI

This should be specified in a technical design doc before implementation.

### 11. Diagram type scoping is absent
The PRD mentions sequence diagrams, architecture diagrams, flowcharts, and "etc." but provides no list of supported types. Different diagram types have different semantic structures (UML vs. block diagrams vs. flowcharts) and likely need different prompt templates, different AI instructions, and possibly different layout algorithms.

**Must decide**: Is v1 limited to block/architecture diagrams only? Or does it include UML (sequence, class, state), flowchart (BPMN-style), and network diagrams? Each additional type is incremental complexity.

### 12. Prompt engineering for diagram generation is treated as trivial
The Rough Approach says "Claude API calls with structured prompts per diagram type." In practice, getting reliable, high-quality diagram output from an LLM is an iterative research problem. The same prompt will produce different quality outputs on different models, and small changes in system prompt can dramatically affect arrow styles, label placement, and layout. This work is not scoped and has no acceptance criteria.

## Observations

- The PRD is well-structured for a vision/product document but reads as a "feature complete" spec when it should read as "initial release" spec. The goal should be to identify the smallest useful subset, not to validate that all described features are desirable.

- The "Fast iteration: Convert and iterate on diagrams in seconds, not minutes" goal sets a performance expectation that has no corresponding constraint. What is the latency target? This matters for architecture decisions (e.g., if Whisper runs locally vs. API, if Claude API is called once vs. multiple times per diagram).

- Open Questions 1-10 are all substantive architectural decisions, not minor clarifications. The PRD has 10 open questions that each materially affect the implementation. This suggests the PRD is pre-implementation rather than ready-for-build.

- The PRD makes no mention of error handling, partial failures, or degraded modes. What happens when the AI produces malformed Excalidraw JSON? What happens when Whisper mis-transcribes a technical term? These are not edge cases -- they are the expected path for real-world usage.

- There is no discussion of diagram quality evaluation. Who judges if the output is "correct"? There are no acceptance criteria, no example outputs, no human-in-the-loop for review.

- The privacy claim ("Uploaded images/audio are not stored long-term") is vague. What does long-term mean? 24 hours? 1 hour? Are they stored at all during processing? What logs exist? For a tool targeting engineers who may upload architecture diagrams containing sensitive infrastructure details, this matters.

- The PRD references no existing similar tools for reference. Mermaid, Structurizr, PlantUML, and even Excalidraw's own AI features are competitive context that should inform scope decisions.

## Confidence Assessment

**Low confidence** that the current PRD represents a buildable scope.

**Rationale**: The PRD describes a platform with 3 modalities, 3 output formats, 4+ diagram types, iteration support, and a job processing system, all in a document with 10 unresolved architectural questions and no MVP definition. This reads as a product vision, not an implementation plan. Before any code is written, the team needs to agree on what ships first -- likely text-to-Excalidraw-only with one diagram type (architecture/block diagrams) as the absolute minimum. Everything else is phase 2+.

## Recommended Scope for v1

If the goal is a usable v1 that delivers value:

| Component | v1 | Later |
|---|---|---|
| Input: Text | Yes | |
| Input: Voice | No | Phase 2 |
| Input: Image | No | Phase 3 |
| Output: Excalidraw JSON | Yes | |
| Output: Draw.io XML | No | Phase 2 |
| Output: SVG | No | Phase 3 |
| Diagram types: Architecture/Block | Yes | |
| Diagram types: Sequence | No | Phase 2 |
| Diagram types: Flowchart | No | Phase 2 |
| Iteration on existing diagrams | No | Phase 3 |
| Batch processing | No | Phase 4 |
| Multi-panel diagrams | No | Phase 4 |
| Authentication / API keys | No | Phase 2 |
| Stateless (no storage) | Yes | |
| Docker deployment | Yes | |
