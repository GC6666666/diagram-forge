# Integration Design: Diagram Forge

## System Architecture Overview

```
                        ┌─────────────────────────────────────────────┐
                        │              FastAPI Service                │
                        │  (Stateless, Docker container, single /v1/) │
                        └──────────┬──────────────┬──────────────────┘
                                   │              │
               ┌───────────────────┘              └───────────────────┐
               │ REST API Layer                                          │
               │ POST /v1/diagram                                         │
               │ GET  /v1/health, /v1/ready                              │
               └──────┬──────────────┬──────────────────┬────────────────┘
                      │              │                  │
         ┌────────────┴───┐    ┌──────┴────────┐  ┌──────┴──────┐
         │  Input Handlers │    │  AI Layer    │  │  Exporters │
         │  ┌───────────┐  │    │  ┌─────────┐│  │  ┌────────┐ │
         │  │ Text      │  │    │  │ Claude   ││  │  │Excalidraw││
         │  │ Voice     │  │───▶│  │ Client   ││  │  │.json    │ │
         │  │ Image     │  │    │  └────┬────┘│  │  ├────────┤ │
         │  └─────┬─────┘  │    │       │     │  │  │Draw.io │ │
         │        │        │    │       ▼     │  │  │.xml    │ │
         │        │        │    │  DiagramModel│  │  ├────────┤ │
         │        │        │    │  (pydantic) │  │  │  SVG   │ │
         │        │        │    └─────┬──────┘  │  └────────┘ │
         │        │        │          │                ▲       │
         └────────┴────────┴──────────┴────────────────┴───────┘
               │              │                  ▲
               ▼              ▼                  │
         ┌──────────┐  ┌──────────┐       ┌──────────────┐
         │Whisper   │  │  Claude  │       │  DiagramModel│
         │OpenAI API│  │  API     │       │  dataclass   │
         └──────────┘  └──────────┘       └──────────────┘
```

**Key architectural decisions:**
- All three input modalities converge on a shared **DiagramModel** intermediate representation
- The AI layer is the only AI call; image analysis uses Claude with vision, text and voice also go through Claude
- Exporters are pure functions from `DiagramModel → bytes` — no shared state
- The service is fully stateless; no diagram storage in v1
- Claude 3.5 Sonnet is the single model for all generation; vision enabled for image inputs
- Whisper is OpenAI API only for v1 (local/deployment deferred)

---

## Pipeline: Text → Diagram

Full step-by-step flow from text description to exported diagram files.

```
Text Input
    │
    ▼
[Step 1] Input Validation
    - type check: str (not None, not empty)
    - length check: ≤4000 characters
    - content check: not just whitespace
    - rate limit check (API key)
    │
    ▼
[Step 2] Preprocessing
    - strip leading/trailing whitespace
    - normalize internal whitespace (collapse multiple spaces/newlines)
    - preserve intentional line breaks (paragraphs)
    - optionally extract explicit diagram type hint from text (e.g., "// type: sequence")
    │
    ▼
[Step 3] Diagram Type Inference (if not explicitly specified)
    - Keyword matching against known patterns:
      - Sequence: "calls", "then", "after", "request", "response", "waits for",
                  participant names, HTTP verbs, API calls, "lifeline"
      - Flowchart: "if", "else", "decision", "loop", "retry", "input", "output",
                   "process", "start", "end", "yes/no"
      - Architecture (default): component names, service names, "gateway", "database",
                                "→", arrows, network topology, "communicates via"
    - Confidence scoring: if confidence < 0.7, return explicit type to user or ask
    - If multiple types match, prefer: Flowchart > Sequence > Architecture
    │
    ▼
[Step 4] Prompt Construction
    - system_prompt = PROMPTS[diagram_type].system  (type-specific system instructions)
    - user_prompt = PROMPTS[diagram_type].user_template.format(
          description=preprocessed_text,
          style_guide=STYLE_GUIDE,
          examples=EXAMPLES[diagram_type]
      )
    - Combine into single messages array for Claude API
    │
    ▼
[Step 5] Claude API Call
    - model: claude-3-5-sonnet-20241022
    - max_tokens: 4096
    - temperature: 0.3  (low for deterministic diagram structure)
    - response_format: { type: "json_object" }
    - Request timeout: 30s
    - Retry: up to 2 times on transient errors (429, 500, 503)
    - Circuit breaker: trip after 5 consecutive failures, 60s recovery
    │
    ▼
[Step 6] Response Parsing
    - Extract text from Claude response (content field)
    - Parse as JSON
    - Handle Claude JSON repair: trailing commas, comments, code fences
      (strip ```json blocks, attempt repair with regex before failing)
    - Validate against DiagramModel schema (pydantic)
    │
    ▼
[Step 7] Post-Generation Validation
    - Required fields present: diagram_type, elements
    - elements is non-empty list
    - Each element has required fields per type
    - Element count: 1 ≤ len(elements) ≤ 200 (reject absurdly large/small)
    - All connection targets reference valid element IDs
    - Positions are non-negative
    - Labels match referenced elements
    - If validation fails: attempt JSON repair (1 retry), else return error
    │
    ▼
[Step 8] Export
    - For each requested format in output_formats (default: ["excalidraw"]):
        - Call appropriate exporter: DiagramModel → bytes
        - Return as file download or base64 in JSON response
    │
    ▼
    Response: { diagram: DiagramModel, files: { format: base64 } }
```

**Error taxonomy for text pipeline:**
| Code | Condition | HTTP Status | Message |
|------|-----------|-------------|---------|
| TEXT_001 | Empty/whitespace input | 400 | "Input text is empty" |
| TEXT_002 | Input too long | 400 | f"Input exceeds {MAX_CHARS} characters" |
| TEXT_003 | Ambiguous type, low confidence | 400 | "Could not determine diagram type. Please specify type explicitly." |
| TEXT_004 | AI returned invalid JSON (after retry) | 502 | "Diagram generation failed. Please try again." |
| TEXT_005 | AI timeout | 504 | "Generation timed out. Try a shorter description." |
| TEXT_006 | AI circuit breaker open | 503 | "Service temporarily unavailable. Retry later." |
| TEXT_007 | Output validation failed | 502 | "Generated diagram was malformed. Please try again." |

---

## Pipeline: Voice → Diagram

```
Audio Input (MP3/WAV, ≤60s)
    │
    ▼
[Step 1] Audio Validation
    - Content-Type check: audio/mpeg, audio/wav, audio/webm, audio/ogg
    - File size ≤ 10MB
    - Duration ≤ 60s (probe with mutagen)
    - File not corrupted (can be read by audio library)
    │
    ▼
[Step 2] Whisper API Transcription
    - endpoint: https://api.openai.com/v1/audio/transcriptions
    - model: whisper-1
    - language: auto-detect (or specified)
    - response_format: verbose_json (includes word-level timestamps optional)
    - timeout: 60s
    - Retry: 1 time on transient errors
    - Request-level: pass audio bytes as file multipart upload
    │
    ▼
[Step 3] Transcript Validation
    - text is not empty
    - text length ≤ 4000 characters equivalent (reject if Whisper returns >5min audio)
    - Optionally: check for technical vocabulary presence (warn if empty/incoherent)
    │
    ▼
[Step 4] Merge with Text Pipeline (Step 3 onward)
    - The transcript string is treated identically to a text input
    - Diagram type inference, prompt construction, Claude call, parsing, export
    - Add transcription to metadata: `diagram.metadata.source_transcript = transcript`
    │
    ▼
    Response: { transcript: str, diagram: DiagramModel, files: { format: base64 } }
```

**Error taxonomy for voice pipeline:**
| Code | Condition | HTTP Status | Message |
|------|-----------|-------------|---------|
| VOICE_001 | Unsupported format | 400 | f"Unsupported audio format. Supported: mp3, wav, webm, ogg" |
| VOICE_002 | File too large | 400 | f"Audio exceeds {MAX_SIZE}MB" |
| VOICE_003 | Duration too long | 400 | f"Audio exceeds {MAX_DURATION}s" |
| VOICE_004 | Corrupt audio | 400 | "Audio file is unreadable or corrupt" |
| VOICE_005 | Whisper returned empty | 400 | "No speech detected in audio" |
| VOICE_006 | Whisper API error | 502 | "Transcription service error. Please try again." |
| VOICE_007 | Whisper timeout | 504 | "Transcription timed out" |

**Whisper API call example:**
```python
async with aiohttp.ClientSession() as session:
    form = aiohttp.FormData()
    form.add_field("file", audio_bytes, filename="audio.mp3", content_type="audio/mpeg")
    form.add_field("model", "whisper-1")
    form.add_field("response_format", "verbose_json")
    async with session.post(url, data=form, headers={"Authorization": f"Bearer {api_key}"}) as resp:
        result = await resp.json()
        return result["text"]
```

---

## Pipeline: Image → Diagram

Two sub-modes: **sketch-to-diagram** (one-shot) and **iteration** (modify existing).

### Mode A: Sketch-to-Diagram

```
Image Input (PNG/JPEG/WebP, ≤10MB, ≤4096×4096px)
    │
    ▼
[Step 1] Image Validation
    - Content-Type: image/png, image/jpeg, image/webp
    - File size ≤ 10MB
    - Image dimensions ≤ 4096×4096px (PIL.Image.open().size)
    - Image readable (PIL can open, not corrupt)
    - Optional: detect if image is too dark/blurry (average luminance, edge density)
      — if so, warn user but proceed
    │
    ▼
[Step 2] Claude Vision Analysis (replaces OCR + layout inference)
    - Encode image as base64 JPEG (quality=85, max dimension=2048px for cost)
    - Single Claude API call with vision capability:
      model: claude-3-5-sonnet-20241022 (vision enabled by default)
      max_tokens: 4096
      temperature: 0.2
    - System prompt: "You are a diagram parsing expert..."
    - User prompt contains the image + analysis instruction
    - Claude outputs JSON matching DiagramModel schema directly
    │
    ▼
[Step 3] Output Parsing & Validation
    - Parse Claude JSON → DiagramModel
    - Same post-generation validation as text pipeline (Step 7)
    - If parse fails: retry once with repair attempt
    │
    ▼
[Step 4] Export
    - Standard export to requested formats
    │
    ▼
    Response: { diagram: DiagramModel, files: { format: base64 } }
```

**Vision prompt template (sketch-to-diagram):**
```
Analyze this diagram image and produce a clean, structured version.

Instructions:
1. Identify ALL diagram elements: boxes, rectangles, cylinders (databases), people icons,
   cloud shapes, arrows, lines, labels, text annotations
2. Determine the diagram type: architecture, sequence, or flowchart
3. Infer the semantic meaning of each element and its label
4. Determine arrow directions and connection semantics (thick arrow = high bandwidth,
   dashed = async, solid = sync, arrowhead = direction)
5. Infer the layout: which elements are grouped, which are peers, which are upstream/downstream
6. Output ONLY a valid JSON object matching this schema:
{
  "diagram_type": "architecture" | "sequence" | "flowchart",
  "metadata": { "title": "..." },
  "elements": [
    { "id": "...", "type": "rectangle", "x": 100, "y": 200, "width": 150, "height": 80,
      "label": "API Gateway", "style": { "fill_color": "#...", "stroke_color": "#..." } },
    ...
  ],
  "connections": [
    { "id": "...", "from_id": "...", "to_id": "...", "label": "HTTPS", "style": "solid" },
    ...
  ]
}

Rules:
- Every element referenced in connections must exist in elements
- Include all text visible in the image, even on arrows
- For handwritten/sketchy input: normalize to clean professional shapes
- Preserve the relative spatial layout (elements that appear vertically aligned
  should be vertically aligned in the output)
- Output valid JSON only, no markdown, no explanation
```

### Mode B: Image + Iteration Instruction

```
Image + Text Instruction
    │
    ▼
[Step 1] Validate both inputs (image + text, same checks as above)
    │
    ▼
[Step 2] Vision + Modification Analysis
    - Encode image as base64 JPEG
    - Single Claude vision call with both image + modification text
    - Claude parses current diagram AND applies modification in one pass
    - Outputs complete new DiagramModel (not a diff — full replacement)
    │
    ▼
[Step 3] Post-Generation Validation + Export (same as above)
```

**Vision + iteration prompt:**
```
This image shows an existing diagram. Apply the following modification request
and output the complete updated diagram as JSON.

Modification request: "{user_instruction}"

Instructions:
1. Analyze the existing diagram (same as sketch-to-diagram analysis)
2. Interpret the modification request
3. Apply ONLY the requested change while preserving everything else
4. If the modification is ambiguous, make a sensible default choice and note it
5. Output the COMPLETE updated diagram as JSON (not a diff)

Rules:
- Output valid JSON only, no markdown, no explanation
- All existing elements not explicitly modified must remain unchanged
- Positions may shift slightly to accommodate new elements
```

**Error taxonomy for image pipeline:**
| Code | Condition | HTTP Status | Message |
|------|-----------|-------------|---------|
| IMAGE_001 | Unsupported format | 400 | f"Unsupported image format. Supported: png, jpeg, webp" |
| IMAGE_002 | File too large | 400 | f"Image exceeds {MAX_SIZE}MB" |
| IMAGE_003 | Dimensions too large | 400 | f"Image exceeds {MAX_W}x{MAX_H}px" |
| IMAGE_004 | Corrupt/unreadable image | 400 | "Image file is unreadable or corrupt" |
| IMAGE_005 | Vision returned invalid JSON (after retry) | 502 | "Diagram analysis failed. Please try with a clearer image." |
| IMAGE_006 | Vision timeout | 504 | "Image analysis timed out. Try a smaller/different image." |
| IMAGE_007 | Empty diagram (no elements detected) | 422 | "No diagram elements detected. Ensure the image shows a clear diagram." |

---

## Per-Diagram-Type Strategy

### Type 1: Architecture / Block Diagrams

**Semantic structure:** Nodes (components, services, databases, external entities) connected by directed edges with optional labels.

**Element types used:**
- `rectangle` — components, services, applications, microservices
- `ellipse` — external entities (actors, users, third-party systems)
- `cylinder` — databases, storage
- `cloud` — cloud regions, internet
- `rectangle` (grouped) — logical clusters, VPCs, environments

**Connection types:**
- `solid_arrow` — synchronous call / request
- `dashed_arrow` — async message / event
- `bidirectional_arrow` — bidirectional communication
- `line` — no-arrow connections

**Layout strategy:** Topological sort → layered layout (left-to-right or top-to-bottom). Components with no incoming edges are "upstream" (sources); components with no outgoing edges are "downstream" (sinks). Groups are detected by proximity and drawn as rounded rectangles containing their members.

**Layout dimensions:** Default canvas 1200×800px. Elements sized: min 120×60px, max 200×100px. Minimum gap between elements: 40px horizontal, 30px vertical.

**Example system prompt excerpt:**
```
System: You generate architecture/block diagrams. Your output represents:
- Rectangles: Services, microservices, applications, containers
- Cylinders: Databases, storage, message queues
- Ellipses: External actors, users, third-party services
- Clouds: Cloud boundaries, internet
- Arrows: synchronous (solid), async (dashed), bidirectional
- Groups: Logical boundaries (VPC, environment, team)

Style: Clean, professional, minimal. Use a consistent 2px stroke.
Colors: blue (#3b82f6) for services, gray (#6b7280) for external,
orange (#f97316) for databases, green (#22c55e) for success paths.
```

### Type 2: Sequence Diagrams

**Semantic structure:** Horizontal participants (lifelines) with vertical timelines, messages sent between participants as arrows, activations indicating when an actor is processing.

**Element types used:**
- `rectangle` (thin, top-aligned) — participant boxes with actor name
- `line` (vertical) — lifelines (implicit, derived from participant positions)
- `arrow` (horizontal) — messages with labels
- `rectangle` (small, on lifeline) — activation boxes

**Connection/message types:**
- `solid_arrow` — synchronous request
- `dashed_arrow` — response
- `arrow` (self-call) — message from participant to itself (loop back on own lifeline)
- `stereotype_arrow` — async event (e.g., "<<create>>", "<<destroy>>")

**Layout strategy:** Participants arranged left-to-right in the order mentioned (or inferred). Lifelines extend downward from participant boxes. Messages are placed at appropriate vertical positions along lifelines. Self-calls loop back. Activation boxes are small rectangles on the lifeline during processing time.

**Layout dimensions:** Default canvas 1400×600px. Participant boxes: 120×40px, spaced 60px apart. Lifelines extend 500px down. Messages spaced 30px apart vertically.

**Example system prompt excerpt:**
```
System: You generate UML sequence diagrams. Your output represents:
- Top rectangles: Participants (actors, objects, systems)
- Vertical lines: Lifelines extending from each participant
- Horizontal arrows: Messages between participants
- Small rectangles on lifelines: Activation/specification bars
- Dashed arrows: Return messages
- Arrows from participant to itself: Self-calls

Style: Standard UML 2.0 notation.
Colors: participant fill #f3f4f6, activation fill #dbeafe.
Arrow labels placed above the arrow.
```

### Type 3: Flowcharts

**Semantic structure:** Directed graph with typed nodes (process, decision, input/output, terminal) and flow edges.

**Element types used:**
- `rectangle` — process / action step
- `diamond` — decision (yes/no branches)
- `parallelogram` — input/output
- `rounded_rectangle` — terminal (start/end)
- `rectangle` (double-sided) — preparation / manual operation

**Connection types:**
- `solid_arrow` — normal flow
- `labeled_arrow` — decision branches ("Yes"/"No", condition text)
- `arrow` (dashed) — flow that is harder to follow

**Layout strategy:** Depth-first traversal of the graph from start terminal. Decision nodes branch vertically (yes) and horizontally (no), or per convention. Maximum column width enforced. If a decision creates >8 branches, collapse into "Other" or warn.

**Layout dimensions:** Default canvas 1000×1200px. Rectangles: 160×60px. Diamonds: 80×80px. Parallelograms: 160×60px with skew. Spacing: 40px between elements vertically.

**Example system prompt excerpt:**
```
System: You generate flowcharts. Your output represents:
- Rounded rectangles: Start and End terminals
- Rectangles: Process steps, actions, operations
- Diamonds: Decision points (always has Yes/No or condition output)
- Parallelograms: Input/Output operations
- Arrows: Control flow direction

Style: Clean flowchart convention. Yes/No labels on decision branches.
Colors: terminal #22c55e (start) / #ef4444 (end), process #3b82f6, decision #f59e0b, I/O #8b5cf6.
All arrows point in the primary flow direction (top-to-bottom preferred).
```

### Type Detection Decision Tree

```
Input text/image
    │
    ├─ Contains "if", "else", "switch", "while", "for", "decision"?  ──▶ Flowchart
    │
    ├─ Contains participant/object names + message verbs (calls, sends,
    │   requests, receives, responses, awaits)?                     ──▶ Sequence
    │
    └─ Default: Architecture / Block Diagram
```

If user specifies `diagram_type` explicitly in the request, skip inference entirely.

---

## AI Prompt Strategy

### Prompt Library Structure

All prompts are stored in `/src/ai/prompts/` as structured prompt objects, not hardcoded strings.

```
src/ai/prompts/
├── __init__.py          # PromptRegistry class, PROMPTS dict
├── base.py              # BasePrompt dataclass with system, user_template, examples
├── diagram_types/
│   ├── __init__.py
│   ├── architecture.py  # System prompt + user template + 2 examples
│   ├── sequence.py      # System prompt + user template + 2 examples
│   └── flowchart.py     # System prompt + user template + 2 examples
└── examples/
    ├── architecture/
    │   ├── microservices.json   # Example input + expected DiagramModel output
    │   └── three_tier.json
    ├── sequence/
    │   ├── api_auth.json
    │   └── order_process.json
    └── flowchart/
        ├── user_login.json
        └── data_pipeline.json
```

### Prompt Registry

```python
# src/ai/prompts/__init__.py
class PromptRegistry:
    def __init__(self):
        self._prompts: dict[str, BasePrompt] = {
            "architecture": load_architecture_prompt(),
            "sequence": load_sequence_prompt(),
            "flowchart": load_flowchart_prompt(),
        }

    def get(self, diagram_type: str) -> BasePrompt:
        return self._prompts[diagram_type]

    def build_messages(self, diagram_type: str, description: str) -> list[dict]:
        prompt = self.get(diagram_type)
        user_content = prompt.user_template.format(description=description)
        return [
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": user_content},
        ]
```

### Prompt Versioning

Each prompt object has a `version: str` field (e.g., "1.0.0") and `model: str` (e.g., "claude-3-5-sonnet-20241022"). When the model is updated or prompts are changed, increment the version. Store a prompt changelog in `/src/ai/prompts/CHANGELOG.md`.

### System Prompt Architecture

Each diagram type system prompt has three sections:
1. **Role definition** — What the AI is and what it produces
2. **Schema contract** — The exact JSON schema it must output (included verbatim)
3. **Style guide** — Colors, shapes, layout conventions, visual rules

### Few-Shot Examples

Each diagram type includes 1-2 examples in the prompt as structured JSON matching the expected output. Examples are embedded in the prompt user template (not as separate messages) to keep token usage predictable. Example inputs are kept under 200 words each.

### Temperature Strategy

- Architecture: `temperature=0.3` — structure is important, minor creative freedom OK
- Sequence: `temperature=0.2` — exact message ordering matters, precision over creativity
- Flowchart: `temperature=0.2` — logical flow must be precise

### Response Format

Claude `response_format={ type: "json_object" }` is used for all diagram generation calls. This constrains Claude to output valid JSON without requiring the ````json` fence wrapper in prompts, simplifying parsing.

---

## Exporter Implementations

### Exporter Interface

```python
# src/exporters/base.py
from abc import ABC, abstractmethod

class DiagramExporter(ABC):
    """Base class for all diagram exporters."""

    @property
    @abstractmethod
    def output_format(self) -> str:
        """File extension, e.g. 'excalidraw', 'drawio', 'svg'."""
        pass

    @property
    @abstractmethod
    def content_type(self) -> str:
        """MIME type, e.g. 'application/json', 'image/svg+xml'."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension with dot, e.g. '.json', '.svg'."""
        pass

    @abstractmethod
    def export(self, diagram: DiagramModel) -> bytes:
        """Export DiagramModel to format-specific bytes."""
        pass
```

### Exporter Registry

```python
# src/exporters/registry.py
EXPORTERS: dict[str, type[DiagramExporter]] = {
    "excalidraw": ExcalidrawExporter,
    "drawio": DrawioExporter,
    "svg": SVGExporter,
}

def export(diagram: DiagramModel, formats: list[str]) -> dict[str, bytes]:
    return { fmt: EXPORTERS[fmt]().export(diagram) for fmt in formats }
```

### Exporter 1: Excalidraw JSON

**File:** `src/exporters/excalidraw.py`

**Schema reference:** Excalidraw scene format (internal JSON, documented at excalidraw-docs)

**Output structure:**
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "Diagram Forge",
  "elements": [ ... ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  }
}
```

**Element mapping:**

| DiagramModel Element | Excalidraw Element Type |
|---------------------|------------------------|
| `rectangle` | `{ id, type: "rectangle", x, y, width, height, fillColor, strokeColor, strokeWidth: 2, borderRadius: 8 }` |
| `ellipse` | `{ id, type: "ellipse", x, y, width, height, fillColor, strokeColor, strokeWidth: 2 }` |
| `diamond` | `{ id, type: "diamond", x, y, width, height, fillColor, strokeColor, strokeWidth: 2 }` |
| `parallelogram` | `{ id, type: "freedraw", ... }` (custom polygon approximation) |
| `text` (label) | `{ id, type: "text", x, y, text, fontSize: 14, fontFamily: "Inter", textAlign: "center" }` |
| `arrow` (connection) | `{ id, type: "arrow", x1, y1, x2, y2, points: [[0,0],[dx,dy]], startBinding, endBinding, strokeColor, strokeWidth: 2, arrowHeadStart/End: "arrow" }` |
| `line` (lifeline) | `{ id, type: "line", x1, y1, x2, y2, strokeColor: "#374151", strokeWidth: 1 }` |
| `group` | `{ id, type: "frame", x, y, width, height, fillColor: "#f9fafb", strokeColor: "#e5e7eb" }` |

**Arrow binding (critical for Excalidraw editability):**
```python
arrow["startBinding"] = {
    "elementId": source_element.id,
    "focus": 0.0,
    "gap": 4,
}
arrow["endBinding"] = {
    "elementId": target_element.id,
    "focus": 0.0,
    "gap": 4,
}
```

**YAML notes for Excalidraw compatibility:**
- Version: always `2`
- Every element needs a globally unique `id` (UUID4)
- Labels on arrows: create a separate `text` element positioned at the midpoint of the arrow
- All colors: hex format `#RRGGBB`
- Group membership: Excalidraw uses `groupIds: [uuid]` on elements

### Exporter 2: Draw.io XML

**File:** `src/exporters/drawio.py`

**Output structure:**
```xml
<mxfile host="app.diagrams.net">
  <diagram name="Diagram">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1200" pageHeight="800">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- elements as mxCell children -->
      </mxGraphModel>
  </diagram>
</mxfile>
```

**Element mapping:**

| DiagramModel Element | Draw.io mxCell |
|---------------------|---------------|
| `rectangle` | `<mxCell value="label" style="rounded=1;whiteSpace=wrap;fillColor=#3b82f6;fontColor=#ffffff;strokeColor=#1d4ed8;" vertex="1" parent="1"><mxGeometry x="100" y="100" width="150" height="60" as="geometry"/></mxCell>` |
| `ellipse` | `<mxCell ... style="ellipse;whiteSpace=wrap;..." vertex="1" ...>` |
| `diamond` | `<mxCell ... style="rhombus;whiteSpace=wrap;..." vertex="1" ...>` |
| `parallelogram` | `<mxCell ... style="rhombus;whiteSpace=wrap;shape=parallelogram;..." vertex="1" ...>` |
| `text` (label) | `<mxCell value="text" style="text;html=1;strokeColor=none;fillColor=none;align=center;" vertex="1" parent="1"><mxGeometry ... as="geometry"/></mxCell>` |
| `arrow` (connection) | `<mxCell id="..." style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#374151;endArrow=classic;" edge="1" parent="1" source="src_id" target="tgt_id"><mxGeometry relative="1" as="geometry"/><Array as="geometry"><mxPoint x="0" y="25" as="offset"/><mxPoint x="80" y="25" as="offset"/></Array><mxCell value="label" vertex="1" connectable="0" parent="..."><mxGeometry relative="1" as="geometry"/></mxCell></mxCell>` |
| `group` | `<mxCell ... style="group" vertex="1" ...>` with child cells |

**Arrow labels in Draw.io:** Draw.io supports labels on edges via the `value` attribute of the mxCell, but positioning requires a child `mxCell` with `relative="1"` geometry. For simplicity, we use the `value` attribute on the edge cell and let Draw.io render it at the midpoint.

**Style constants per diagram type:**

```python
DRAWIO_STYLES = {
    "architecture": {
        "rectangle": "rounded=1;whiteSpace=wrap;fillColor={fill};fontColor=#ffffff;strokeColor={stroke};strokeWidth=2;",
        "ellipse": "ellipse;whiteSpace=wrap;fillColor={fill};fontColor=#ffffff;strokeColor={stroke};strokeWidth=2;",
        "cylinder": "shape=cylinder3;whiteSpace=wrap;fillColor={fill};fontColor=#ffffff;strokeColor={stroke};boundedLbl=1;",
        "cloud": "shape=cloud;whiteSpace=wrap;fillColor=#dbeafe;fontColor=#1e40af;strokeColor=#3b82f6;",
    },
    "sequence": {
        "participant": "rounded=1;whiteSpace=wrap;fillColor=#f3f4f6;fontColor=#111827;strokeColor=#374151;strokeWidth=2;",
        "activation": "fillColor=#dbeafe;strokeColor=#1d4ed8;strokeWidth=1;",
    },
    "flowchart": {
        "rectangle": "rounded=0;whiteSpace=wrap;fillColor=#3b82f6;fontColor=#ffffff;strokeColor=#1d4ed8;strokeWidth=2;",
        "diamond": "rhombus;whiteSpace=wrap;fillColor=#f59e0b;fontColor=#ffffff;strokeColor=#d97706;strokeWidth=2;",
        "parallelogram": "shape=parallelogram;whiteSpace=wrap;fillColor=#8b5cf6;fontColor=#ffffff;strokeColor=#6d28d9;strokeWidth=2;",
        "terminal": "rounded=1;whiteSpace=wrap;fillColor=#22c55e;fontColor=#ffffff;strokeColor=#16a34a;strokeWidth=2;",
    }
}
```

### Exporter 3: SVG

**File:** `src/exporters/svg.py`

**Design decision:** Generate **editable SVG** (semantic SVG with grouped elements, text, and arrows as proper SVG elements) rather than rendered/raster-like SVG. This aligns with the PRD's "fully-editable industry-standard diagrams" goal.

**Output structure:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 1200 800" width="1200" height="800">
  <title>Architecture Diagram</title>
  <desc>Generated by Diagram Forge</desc>

  <!-- Styles -->
  <style>
    .element-rect { fill: #3b82f6; stroke: #1d4ed8; stroke-width: 2; }
    .element-text { font-family: Inter, system-ui, sans-serif; font-size: 14px; fill: #ffffff; text-anchor: middle; }
    .arrow { stroke: #374151; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
    .arrow-label { font-family: Inter, system-ui, sans-serif; font-size: 12px; fill: #374151; }
    .group-bg { fill: #f9fafb; stroke: #e5e7eb; stroke-width: 1; stroke-dasharray: 4,4; }
  </style>

  <!-- Arrow marker definition -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#374151"/>
    </marker>
    <marker id="dashed-arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#9ca3af"/>
    </marker>
  </defs>

  <!-- Groups (render first, so they appear behind elements) -->
  <rect id="group-..." class="group-bg" x="..." y="..." width="..." height="..." rx="8"/>
  <!-- Groups get explicit IDs for referencing in edits -->

  <!-- Elements -->
  <g id="el-uuid" transform="translate(x, y)">
    <rect class="element-rect" width="150" height="60" rx="8"/>
    <text class="element-text" x="75" y="35">API Gateway</text>
  </g>

  <!-- Connections -->
  <!-- Arrow lines with labels rendered as SVG text -->
  <line class="arrow" x1="..." y1="..." x2="..." y2="..."/>
  <text class="arrow-label" x="..." y="...">HTTPS</text>
</svg>
```

**Editable SVG requirements:**
- Every element is a `<g>` group with a descriptive `id` (element UUID)
- Text is actual `<text>` SVG elements (not paths), searchable and editable
- Arrows use proper SVG `<marker>` definitions for arrowheads
- Groups use explicit `<rect>` backgrounds with dashed stroke
- All positions use absolute coordinates in a `viewBox`
- Colors reference CSS classes, making re-theming trivial

**SVG-specific element mapping:**

| DiagramModel Element | SVG Element |
|---------------------|------------|
| `rectangle` | `<rect>` with class for styling |
| `ellipse` | `<ellipse>` |
| `diamond` | `<polygon>` (4-point diamond shape) |
| `parallelogram` | `<polygon>` (4-point parallelogram) |
| `text` (label) | `<text>` |
| `arrow` | `<line>` + `<text>` for label |
| `group` | `<rect>` + `<g>` wrapping children |

---

## Iteration Flow

**Principle:** Stateless model. The user re-submits the full context (original input + modification instruction) each time. No diagram storage.

### Iteration Option A: Image + Modification Text (recommended for visual iteration)

```
User uploads: existing_diagram_image.png + "add a cache layer between API and DB"
    │
    ▼
Image Pipeline Mode B (vision + iteration)
    │
    ▼
Claude vision: parses current diagram + applies modification in one call
    │
    ▼
Returns: complete new DiagramModel (full replacement, not diff)
    │
    ▼
Export to requested formats
```

**Prompt injection for iteration:**
```
[System: ...]
[User: Diagram image + "Apply this modification: {instruction}"]
```

Claude is instructed: "Output the complete updated diagram, not a diff. Preserve all unmodified elements. Apply only the requested change."

### Iteration Option B: Text + Modification Text (for quick text-based iteration)

```
User submits: "The original description..." + "Change the architecture to use microservices instead of a monolith"
    │
    ▼
Text Pipeline (treats combined text as a new description)
    │
    ▼
Claude regenerates from the combined instruction
```

This mode requires the user to re-describe what they want, but is simpler for text inputs.

### Iteration Option C: Excalidraw JSON + Modification Text (most precise, future phase)

```
User pastes: existing_diagram.excalidraw.json (or portion) + "add a monitoring service"
    │
    ▼
Parse Excalidraw JSON → DiagramModel (parse elements into our schema)
    │
    ▼
Claude: receives DiagramModel as structured input (text serialization) + modification
    │
    ▼
Claude outputs updated DiagramModel
    │
    ▼
Export
```

This is the most precise iteration mode but requires implementing the Excalidraw JSON → DiagramModel parser. **Deferred to Phase 3.**

### Iteration Error Handling

If Claude's output loses or misplaces elements during iteration:
- Run a "completeness check" post-generation: verify all expected elements from the original are present or explicitly removed in the modification
- If elements are missing: retry once with a stricter prompt ("Ensure all original elements are preserved: {list of original element names}")
- If still failing: return error with `INCOMPLETE_ITERATION` code, suggest user re-upload original with explicit instructions

---

## Internal Representation (Deferred)

As specified in PRD Open Question Q4: **internal representation is deferred to Phase 2**. The approach is validated via prompt engineering first.

The `DiagramModel` pydantic class serves as the in-memory representation for v1. When the internal representation design is revisited in Phase 2, considerations include:

- Should it be a richer typed AST (Element nodes with typed children)?
- Should layout be computed (dagre, elkjs) or left to the AI?
- Should there be a versioned schema with migration support?
- Should there be a text-based serialization format (YAML, TOML) for debugging?

These questions are out of scope for this integration design and will be addressed when the internal representation is formally designed.

---

## Project Structure / Directory Layout

```
diagram-forge/
├── .env.example              # API keys, config template
├── .gitignore
├── Dockerfile                # Single-stage build, python:3.11-slim
├── docker-compose.yml        # Dev setup (service + mock services)
├── pyproject.toml            # Poetry config
├── README.md
├── CHANGELOG.md

├── src/
│   └── diagram_forge/
│       ├── __init__.py
│       ├── __main__.py           # python -m diagram_forge entrypoint
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes.py         # FastAPI route definitions (/v1/diagram, /health)
│       │   ├── schemas.py        # Pydantic request/response models
│       │   ├── middleware.py     # Request ID, logging, error wrapping
│       │   └── deps.py           # FastAPI dependencies (auth, rate limit, client instances)
│       │
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── text.py           # TextPipeline: steps 1-8 (text → diagram)
│       │   ├── voice.py          # VoicePipeline: steps 1-7 (audio → text → diagram)
│       │   └── image.py          # ImagePipeline: Mode A (sketch) + Mode B (iteration)
│       │
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── client.py         # ClaudeAPIClient (singleton, async)
│       │   ├── retry.py          # Retry strategy + circuit breaker
│       │   ├── parser.py         # Claude response → DiagramModel (JSON repair, validation)
│       │   ├── prompts/
│       │   │   ├── __init__.py   # PromptRegistry
│       │   │   ├── base.py       # BasePrompt dataclass
│       │   │   ├── diagram_types/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── architecture.py  # System prompt + template + examples
│       │   │   │   ├── sequence.py      # System prompt + template + examples
│       │   │   │   └── flowchart.py     # System prompt + template + examples
│       │   │   └── examples/
│       │   │       ├── architecture/
│       │   │       │   ├── microservices.json   # I/O pair
│       │   │       │   └── three_tier.json
│       │   │       ├── sequence/
│       │   │       │   ├── api_auth.json
│       │   │       │   └── order_process.json
│       │   │       └── flowchart/
│       │   │           ├── user_login.json
│       │   │           └── data_pipeline.json
│       │   └── type_inference.py  # Diagram type detection from text keywords
│       │
│       ├── exporters/
│       │   ├── __init__.py       # export() registry function
│       │   ├── base.py           # DiagramExporter ABC
│       │   ├── excalidraw.py     # ExcalidrawExporter → .excalidraw.json
│       │   ├── drawio.py         # DrawioExporter → .drawio.xml
│       │   └── svg.py            # SVGExporter → .svg
│       │
│       ├── models/
│       │   ├── __init__.py       # DiagramModel, element dataclasses
│       │   ├── diagram.py        # DiagramModel, Metadata
│       │   ├── elements.py       # Rectangle, Ellipse, Diamond, Arrow, Text, Group, Connection
│       │   └── validators.py     # DiagramModel validators (completeness, bounds)
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── whisper.py        # WhisperAPIClient
│       │   └── storage.py        # Temp file storage (24h TTL cleanup)
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logging.py        # Structured JSON logging
│           ├── image_utils.py    # PIL helpers (resize, encode, validate)
│           └── audio_utils.py    # mutagen helpers (duration, format probe)
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_models.py        # DiagramModel validation tests
│   │   ├── test_exporters.py     # Each exporter: roundtrip tests
│   │   ├── test_type_inference.py
│   │   ├── test_prompt_registry.py
│   │   └── test_json_repair.py   # Claude JSON repair tests
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_text_pipeline.py
│   │   ├── test_voice_pipeline.py
│   │   └── test_image_pipeline.py
│   └── fixtures/
│       ├── prompts/              # Test prompt fixtures
│       ├── examples/             # Example diagram JSONs for fixture testing
│       └── images/                # Test images (generated, not real)
│
├── configs/
│   ├── default.yaml              # Default config (overridden by env)
│   └── logging.yaml               # Logging configuration
│
└── scripts/
    ├── lint.sh
    ├── test.sh
    └── generate_examples.py       # Tool to generate new prompt examples from Claude
```

**Key structural decisions:**
- `/src/diagram_forge/models/` — pure data classes, no business logic
- `/src/diagram_forge/pipeline/` — orchestrates steps, no format logic
- `/src/diagram_forge/exporters/` — pure format conversion, no orchestration
- `/src/diagram_forge/ai/` — prompt management and Claude interaction only
- `/src/diagram_forge/api/` — HTTP contract, serialization, and middleware only

This enforces the constraint that the shared AI layer and model are the integration point across all three modalities.

---

## Implementation Notes

### 1. Claude JSON Response Handling

Claude with `response_format={ type: "json_object" }` guarantees JSON output but the JSON can still be malformed (trailing commas in older model versions, inconsistent key names). Implement robust repair:

```python
def repair_json(text: str) -> str:
    """Attempt to fix common Claude JSON malformation issues."""
    text = text.strip()
    text = re.sub(r',(\s*[}\]])', r'\1', text)  # trailing commas
    text = re.sub(r'//.*', '', text)             # JS comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)  # block comments
    return text
```

If repair fails after stripping markdown fences, retry the generation once with an adjusted prompt ("Output only raw JSON, no markdown or code blocks").

### 2. Excalidraw as Canonical Intermediate

Excalidraw JSON is the most natural output (our primary format, aligns with MCP tool). For SVG, we can either generate directly from DiagramModel or convert Excalidraw JSON to SVG (excalidraw-to-svg npm package or equivalent). The direct generation path is preferred for v1.

### 3. Image Encoding for Claude Vision

Always resize images before base64 encoding to minimize API costs and latency:
```python
def encode_image_for_vision(image_bytes: bytes, max_dim: int = 2048) -> tuple[bytes, str]:
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue(), "image/jpeg"
```

### 4. Request Cancellation

Use FastAPI's `AsyncGenerator` / streaming response for large requests. If the client disconnects mid-request, check for cancellation:
```python
try:
    await asyncio.wait_for(generate_diagram(), timeout=60)
except asyncio.CancelledError:
    # Clean up any in-progress work
    raise
```

### 5. Temporary File Cleanup

All uploaded files (images, audio) and generated output files are stored in `/tmp/diagram-forge/` with a 24h TTL. Use a background task or cron to clean expired files:
```python
# src/services/storage.py
TEMP_DIR = Path("/tmp/diagram-forge")
TTL_SECONDS = 86400  # 24 hours

def cleanup_expired():
    now = time.time()
    for f in TEMP_DIR.glob("*"):
        if now - f.stat().st_mtime > TTL_SECONDS:
            f.unlink()
```

### 6. API Response Format

```python
class DiagramResponse(BaseModel):
    request_id: str  # For tracing
    diagram_type: str
    metadata: Metadata
    elements: list[Element]
    connections: list[Connection]
    files: dict[str, str]  # format → base64-encoded file content
    timing_ms: dict[str, float]  # Optional: pipeline stage timings for debugging
```

### 7. Rate Limiting (MVP)

Simple token bucket per API key (in-memory):
```python
# src/api/deps.py
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

class RateLimiter:
    def __init__(self, rate: int = 10, per: int = 60):  # 10/min default
        self.buckets: dict[str, TokenBucket] = {}

rate_limiter = RateLimiter()

async def check_rate_limit(key: str = Security(api_key_header)):
    bucket = rate_limiter.buckets.setdefault(key, TokenBucket(rate=10, per=60))
    if not bucket.consume():
        raise HTTPException(429, detail="Rate limit exceeded", headers={"Retry-After": "60"})
```

### 8. Multi-Modal Routing

The FastAPI route dispatches to the correct pipeline:

```python
# src/api/routes.py
@router.post("/v1/diagram")
async def create_diagram(request: DiagramRequest) -> DiagramResponse:
    request_id = generate_request_id()
    logger = get_logger(request_id)

    try:
        if request.image:
            pipeline = ImagePipeline(client=claude_client, request_id=request_id)
            result = await pipeline.run(request.image, request.instruction,
                                        request.iteration_mode)
        elif request.audio:
            pipeline = VoicePipeline(client=claude_client, whisper=whisper_client,
                                    request_id=request_id)
            result = await pipeline.run(request.audio)
        else:
            pipeline = TextPipeline(client=claude_client, request_id=request_id)
            result = await pipeline.run(request.text, request.diagram_type,
                                        request.output_formats)

        return DiagramResponse(request_id=request_id, **result)

    except DiagramForgeError as e:
        logger.error(f"Pipeline error: {e.code} — {e.message}")
        raise HTTPException(e.http_status, detail={"code": e.code, "message": e.message})
```

---

## Phased Implementation Plan

### Phase 1: Core Text Pipeline (MVP baseline)

**Goal:** Ship text → Excalidraw JSON as fast as possible to validate prompt engineering.

**Deliverables:**
- Project scaffold (FastAPI, models, exporters)
- `TextPipeline` with hardcoded prompts (no prompt library yet)
- `ExcalidrawExporter` only
- Basic unit tests
- Dockerfile

**Entry criteria:** Text → Excalidraw JSON roundtrip works for all 3 diagram types with >70% structural accuracy.

### Phase 2: Multi-Format Export + Prompt Library

**Goal:** Complete the output side and harden the prompt system.

**Deliverables:**
- `DrawioExporter` and `SVGExporter`
- `PromptRegistry` with versioned prompts per diagram type
- Example fixtures (input/output pairs) per diagram type
- JSON repair and validation improvements
- Full unit + integration test suite (≥80% coverage)
- Input validation layer (size, format, type checks)
- Basic error taxonomy with user-facing messages

**Entry criteria:** All three exporters produce valid, openable files for all diagram types.

### Phase 3: Voice Pipeline

**Goal:** Add Whisper-based voice input.

**Deliverables:**
- `VoicePipeline` (Whisper API → text pipeline)
- Full voice error taxonomy
- Voice-specific integration tests

**Entry criteria:** Voice dictation of a 3-step sequence produces a correct sequence diagram.

### Phase 4: Image Pipeline (Sketch-to-Diagram)

**Goal:** Add vision-based image analysis.

**Deliverables:**
- `ImagePipeline` Mode A (sketch-to-diagram, vision-only)
- Vision prompt engineering and examples
- Image validation (size, format, dimension checks)
- Image pipeline integration tests

**Entry criteria:** Photo of hand-drawn architecture sketch → clean Excalidraw JSON.

### Phase 5: Iteration + Image Pipeline Mode B

**Goal:** Enable modifying existing diagrams.

**Deliverables:**
- `ImagePipeline` Mode B (vision + modification)
- Completeness check for iteration
- Iteration-specific prompts

**Entry criteria:** Upload existing diagram + "add a cache layer" → diagram with cache layer added.

### Phase 6: Excalidraw JSON Parser + Precise Iteration

**Goal:** Parse existing Excalidraw files for precise iteration.

**Deliverables:**
- `ExcalidrawParser` (Excalidraw JSON → DiagramModel)
- Iteration Option C (Excalidraw JSON + modification text)
- Excalidraw roundtrip validation

**Entry criteria:** Existing .excalidraw.json file + "add monitoring" → updated .excalidraw.json.

### Phase 7: Operational Hardening

**Goal:** Production readiness.

**Deliverables:**
- Rate limiting with API key management
- Circuit breaker with AI provider
- Health/ready endpoints
- Structured logging + request tracing
- Cost monitoring
- Staging environment

---

## Summary: How the Three Modalities Share the AI Generation Layer

All three pipelines converge at the `ClaudeAPIClient.generate_diagram()` call:

```
TextPipeline ──────────────────────┐
                                  │
VoicePipeline ──▶ Whisper ─────────┼──▶ ClaudeAPIClient ──▶ DiagramModel ──▶ [Excalidraw, Draw.io, SVG]
                                  │
ImagePipeline ─────────────────────┘
```

The `ClaudeAPIClient` is a single, shared, stateless service:
- Same model (Claude 3.5 Sonnet)
- Same `generate_diagram()` method signature
- Same retry/circuit-breaker logic
- Different `messages` per call type (text prompt, vision prompt with image, vision+iteration prompt)

The modality differentiation happens entirely in **prompt construction** before the call and in **response parsing** after. The AI layer itself is modality-agnostic.

**Prompt construction per modality:**
| Modality | Claude API call type | Input to system prompt | Input to user prompt |
|----------|---------------------|----------------------|---------------------|
| Text | Text-only | Type-specific system instructions | Preprocessed text description |
| Voice | Text-only | Type-specific system instructions | Whisper transcript |
| Image (sketch) | Vision (image + text) | Vision analysis instructions | "Analyze this diagram and output JSON" |
| Image (iteration) | Vision (image + text) | Vision + modification instructions | Image + modification text |

This unified model means adding a new input modality (e.g., PDF document) requires only a new pipeline class that constructs the appropriate prompt for the shared `ClaudeAPIClient` — no changes to the AI layer, models, or exporters.
