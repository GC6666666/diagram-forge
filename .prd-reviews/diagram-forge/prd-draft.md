# PRD: Diagram Forge

## Problem Statement

Engineers and technical teams frequently need to create professional diagrams (architecture diagrams, sequence diagrams, flowcharts, etc.) but tools like Mermaid produce generic-looking output, while hand-drawing or using tools like Lucidchart/Figma is time-consuming. There is no tool that takes the natural description of a system (image, voice, or text) and produces beautiful, fully-editable industry-standard diagrams quickly.

Diagram Forge solves this by accepting multiple input modalities and producing output in Excalidraw, Draw.io, and SVG formats — combining AI-powered understanding with best-in-class diagram editors.

## Goals

1. **Image → Diagram**: Upload a screenshot or photo of a hand-drawn/sketched diagram → get a clean, editable version in Excalidraw/Draw.io
2. **Voice → Diagram**: Dictate "user logs in, then calls API, API hits database" → generates a sequence diagram
3. **Text → Diagram**: Describe in plain English → generates the diagram
4. **Multi-format export**: Output to Excalidraw (JSON), Draw.io (XML), and SVG
5. **Fast iteration**: Convert and iterate on diagrams in seconds, not minutes

## Non-Goals

- Real-time collaborative editing (handled by Excalidraw/Draw.io themselves)
- Direct browser-based editing (output files are opened in the respective tools)
- Support for non-computer-industry diagram types (e.g., infographics, marketing graphics)
- Mobile-native experience (web API is primary; CLI is secondary)
- Diagram *hosting* or *sharing* (output files are downloaded, not stored server-side)

## User Stories / Scenarios

**Scenario 1: Hand-drawn sketch to clean diagram**
Alice sketches an architecture on a whiteboard, takes a photo with her phone, uploads it. Within seconds she downloads an Excalidraw JSON file with clean boxes, arrows, and labels.

**Scenario 2: Voice to sequence diagram**
Bob is in a meeting, describes an API flow verbally: "The client sends a request to the gateway, which authenticates with OAuth, then calls the user service..." — within seconds, a sequence diagram is ready.

**Scenario 3: Text description to architecture diagram**
Charlie writes: "Microservices with API Gateway, Auth Service, User Service, Order Service, Payment Service, Database. Gateway routes to services, services communicate via async messaging." → Clean architecture diagram generated.

**Scenario 4: Iterating on existing diagrams**
Diana pastes an existing diagram screenshot and says "make this more modern" or "add a cache layer" → Updated diagram returned.

**Actors:**
- Software engineers documenting systems
- Tech leads planning architecture
- Teams in meetings needing quick visual documentation
- Technical writers creating documentation

## Constraints

- **Language**: Python 3.11+
- **AI Provider**: Claude API (Anthropic) for diagram generation
- **Speech-to-Text**: Whisper (local or API)
- **No persistent user accounts required** for MVP (stateless API)
- **Output formats**: Excalidraw JSON, Draw.io XML, SVG
- **Privacy**: Uploaded images/audio are not stored long-term

## Clarifications from Human Review

**Q1 (v1 scope)**: Architecture diagrams, sequence diagrams, and flowcharts in v1. All three input modalities (text, voice, image) ship together, but only these three diagram types.
**Q2 (diagram types)**: Architecture/Block diagrams, Sequence diagrams, Flowcharts. These three ship in v1.
**Q3 (iteration)**: Yes, iteration on existing diagrams is needed. Users re-upload full context (stateless model).
**Q4 (internal representation)**: TBD — defer design, validate approach via prompt engineering first.
**Q5 (AI generation approach)**: Prompt engineering + post-processing. No structured intermediate format in v1.
**Q6 (Whisper)**: OpenAI Whisper API. Simplest path for v1.
**Q7 (CLI vs API)**: FastAPI + Web UI + CLI wrapper. CLI wraps the API.
**Q8 (authentication)**: Pre-shared API keys for v1. Simple key-based access control.
**Q9 (input limits)**: TBD by crew: PNG/JPEG/WebP ≤10MB, 4096×4096px max; MP3/WAV ≤60s; text ≤4000 chars.
**Q10 (data retention)**: 24-hour TTL on temporary files. Claude API data flow disclosed in privacy policy.

1. Should OCR be done client-side or server-side? (client = faster server, privacy; server = more capable)
2. Which Whisper deployment? (local for privacy, OpenAI API for quality, or a self-hosted endpoint?)
3. How to handle ambiguous layouts in image→diagram conversion? (multiple valid interpretations)
4. Should we support batch processing (multiple images → multiple diagrams)?
5. CLI vs API-first? What's the primary interface?
6. Self-hosted deployment target? (Docker? Single script? Cloud-native?)
7. Rate limiting / API key management for the MVP?
8. Should diagrams be stored/retrievable, or always generated fresh?
9. SVG export — should it be fully editable SVG or rendered raster-like SVG?
10. How to handle multi-page/multi-panel diagrams from a single image?

## Rough Approach

- **FastAPI** as the API layer (async, clean REST interface)
- **Modular pipeline**: Input → Parser → AI Generation → Exporter
- **Input handlers**: Image (PIL), Audio (Whisper), Text (direct prompt)
- **AI Layer**: Claude API calls with structured prompts per diagram type
- **Exporter**: Convert internal representation → Excalidraw JSON / Draw.io XML / SVG
- **Storage**: Temporary only for MVP; consider S3-compatible for future
- **Deployment**: Docker container, single `docker run` deployment
