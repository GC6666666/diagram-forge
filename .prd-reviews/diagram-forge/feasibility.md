# Technical Feasibility

## Summary

The project is at the earliest possible stage: a README and a PRD draft. Zero source code exists. Every module -- the API layer, AI pipeline, exporters, OCR, and voice processing -- must be built from scratch. The vision is broad (3 input modalities, 3 output formats, 6+ diagram types) but the engineering challenges are significant and several are underestimated in the PRD.

Overall assessment: **feasible, but with substantial hard problems that need concrete solutions before implementation can begin.** The "fast iteration" performance goal is likely over-optimistic for image-based inputs. The LLM-to-diagram-generation problem is not well understood in the PRD and is the central technical risk.

## Critical Gaps (things MUST be answered before implementation)

### 1. Internal representation is undefined
The PRD mentions a "modular pipeline: Input -> Parser -> AI Generation -> Exporter" with an internal representation that gets converted to Excalidraw JSON, Draw.io XML, and SVG. This canonical format is never specified. Every exporter depends on it, and it determines the entire shape of the system. Without it, you cannot write a single line of exporter code. **This must be designed first.**

### 2. LLM-to-structured-diagram approach is unspecified
The PRD assumes Claude can generate Excalidraw JSON or Draw.io XML, but Claude cannot natively output these formats. The approach to get structured diagram data from an unstructured LLM is the central technical problem and is left as an exercise to the implementer. Options include:
- Claude with extremely detailed prompts to generate text-descriptions that get post-processed
- Multi-step generation: describe diagram -> structured JSON -> convert to format
- Using Claude's function_calling / structured output feature (if available and capable)
- Two-model approach: vision model describes the diagram, another model generates coordinates

Each approach has tradeoffs in reliability, consistency, and token cost. **The chosen approach must be validated experimentally before committing to the architecture.**

### 3. Image understanding pipeline has no specified approach
"Image -> Diagram" is presented as a single feature but involves multiple sub-problems:
- Text extraction (OCR) -- to identify labels and annotations
- Visual element detection -- to identify boxes, arrows, lines, containers
- Layout inference -- to understand spatial relationships and hierarchy
- Coordinate mapping -- to place elements in the output diagram
- Arrow/connection interpretation -- to understand which elements connect to which

The PRD mentions "GPT-4V or PaddleOCR" for OCR but this only covers text extraction, not shape/arrow/connection extraction. There is no stated approach for the harder problems of layout and connection inference. **This is the hardest problem in the project and is the most underestimated in the PRD.** A hand-drawn sketch on a whiteboard with arrows can have ambiguous spatial relationships that no current model reliably interprets.

### 4. Export format implementations are non-trivial and unresearched
- **Excalidraw JSON**: The schema is documented but complex. An Excalidraw diagram involves scene coordinates, element types (rectangle, ellipse, arrow, text, etc.), stroke styles, binding (arrows to elements), viewBox, and library references. The schema has evolved and there are subtle compatibility concerns.
- **Draw.io XML**: The format is less well-documented publicly. Draw.io has its own XML schema for shapes, connections, styles, and page layouts. Building a correct exporter requires either reverse-engineering the format or finding a library.
- **SVG**: The PRD flags this as ambiguous ("fully editable SVG vs rendered raster-like SVG"). These are fundamentally different things. "Fully editable" SVG would use native SVG shapes with text, arrows, and groups. "Rendered" SVG would be a single `<path>` with embedded text. The distinction affects the entire exporter design.

**None of the three export formats have been evaluated for implementation complexity.** The PRD lists them as outputs but does not account for the engineering effort to build correct, complete exporters for each.

## Important Considerations

### 5. Performance target ("seconds, not minutes") is likely over-optimistic for image inputs
A realistic pipeline for "Image -> Diagram" involves:
- Image upload and preprocessing
- Vision model analysis (GPT-4V or similar) -- typically 2-10 seconds per image
- LLM diagram generation -- typically 1-5 seconds
- Format conversion and export -- typically <1 second

The total is likely **5-15 seconds for image inputs**, which is "tens of seconds" not "seconds." Voice and text inputs are faster (Whisper + LLM generation), potentially 3-8 seconds total. The PRD's "seconds, not minutes" framing is achievable for text/voice but may disappoint users for image inputs.

### 6. Excalidraw MCP server is already running in this environment
During this review session, an Excalidraw MCP server is active (visible in `excalidraw.log`). This MCP tool can create, query, update, and delete Excalidraw elements programmatically. This could potentially be leveraged as a lower-complexity path for Excalidraw export: instead of generating Excalidraw JSON from scratch, the pipeline could use the MCP tool to construct diagrams programmatically. This is worth exploring as it would eliminate the need to reverse-engineer the Excalidraw JSON schema. **However, this would couple the system to an MCP tool that must be running alongside the API, which may conflict with the "single docker run" deployment goal.**

### 7. Whisper GPU requirements
Whisper (especially larger models like `large-v3`) requires significant GPU memory. The deployment target ("single docker run") makes GPU support uncertain. Options include:
- OpenAI Whisper API (outsourced, but adds cost and latency)
- Self-hosted Whisper (requires GPU, adds deployment complexity)
- Distil-Whisper or smaller models (tradeoff between quality and speed)
- This is an unresolved deployment constraint.

### 8. API key management / authentication is unaddressed
Open Question 7 ("Rate limiting / API key management for the MVP") is flagged but unresolved. For a stateless API serving multiple users, this is a non-trivial problem:
- How to authenticate requests without persistent user accounts?
- How to manage rate limits per client?
- How to protect the Claude API key on the backend?
- A simple API key scheme is feasible for MVP but needs explicit design.

### 9. Scope is wide for an MVP with zero code
The PRD targets: 3 input modalities, 3 output formats, 6+ diagram types (architecture, sequence, flowchart, ER, class, component), 2 deployment targets (API + CLI), voice dictation, image upload, and text description. With zero code written and several hard unsolved problems, this scope is aggressive. **A phased approach is strongly recommended: ship text->Excalidraw first (simplest path), add others incrementally.**

### 10. Prompt engineering is underestimated
Getting consistent, correct diagram output from Claude requires extensive prompt engineering per diagram type. Each of the 6+ diagram types needs its own prompt optimized for:
- Correct component representation (sequence diagram lifelines vs architecture diagram boxes)
- Correct notation (UML arrows vs simple arrows)
- Consistent styling (colors, fonts, stroke widths)
- Correct layout hints (top-to-bottom for flowcharts, left-to-right for sequences)
- Handling edge cases (too many elements, ambiguous descriptions)

This is a significant ongoing maintenance cost, not a one-time effort. Diagram conventions vary and Claude's output will vary across runs without careful prompt design.

### 11. Ambiguous layouts (Open Question 3) may not be solvable
The PRD explicitly flags "How to handle ambiguous layouts in image->diagram conversion?" as an open question. This is correctly identified as hard, but it is positioned as an "open question" rather than a risk. It should be positioned as: **"This is a fundamental limitation of current vision models and we should either scope it out of MVP or define a graceful degradation strategy (e.g., return top-1 interpretation + confidence score + user correction endpoint)."**

### 12. No existing codebase to build on
The entire project is a README. There is no scaffolding, no FastAPI app, no pipeline, no tests, no Docker setup, no dependencies declared. Everything must be built from scratch. This means the "engineering effort" estimate in the PRD is likely understated -- there is no reuse of existing codebases.

## Observations

- **The Excalidraw MCP integration in this session suggests an alternative architecture**: Instead of generating Excalidraw JSON, the pipeline could use the MCP tool to construct diagrams element-by-element. This reduces the Excalidraw schema engineering cost but introduces a dependency on the MCP server being available.

- **Claude's structured output capabilities have improved** with the Messages API and potential function calling. This may be more viable than the PRD assumes, but still needs experimental validation for complex nested diagram structures.

- **The privacy goal ("uploaded images/audio are not stored long-term") is straightforward** given the stateless API design. No data persistence layer means no data to protect. This is a strength of the current design.

- **ER Diagram and Class Diagram from text** are listed in the README but the user stories focus only on architecture, sequence, and flowchart. The README scope exceeds the PRD scope. This is a consistency issue that should be resolved.

- **SVG as an output format overlaps with Excalidraw**: Excalidraw JSON can be exported to SVG by the Excalidraw client. If the goal is "fully editable SVG", Excalidraw JSON is a superset. The value of a separate SVG exporter needs clarification.

## Confidence Assessment

**Low confidence** that the PRD as written can be implemented to meet all stated goals.

**Rationale:**
1. Zero source code exists; every module is greenfield
2. The central technical problem -- LLM-to-structured-diagram output -- is unspecified and non-trivial
3. The image understanding pipeline is the hardest problem in the project and has no stated approach
4. Export format implementations have not been researched
5. The performance target is likely over-optimistic for the image modality
6. Scope is wide relative to the amount of solved problems
7. Several open questions (internal representation, SVG editability, Whisper deployment, layout ambiguity) are blocking decisions that must be resolved before architecture can be designed

**Recommended path forward:**
- Design the internal representation first (blocking all downstream work)
- Build a proof-of-concept for text->Excalidraw only (simplest path through the hardest problem)
- Evaluate Excalidraw MCP as an alternative export mechanism
- Define the image understanding pipeline approach before committing to architecture
- Reduce MVP scope to text->Excalidraw + Excalidraw MCP, ship that first
