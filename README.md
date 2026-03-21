# Diagram Forge

Convert images and voice dictation into professional computer industry diagrams — architecture diagrams, sequence diagrams, flowcharts, and more — in fully editable formats.

## Core Features

- **Image → Diagram** — Upload a screenshot or photo of a hand-drawn/sketched diagram, get a clean editable version
- **Voice → Diagram** — Dictate "user logs in, then calls API, API hits database" → generates sequence diagram
- **Text → Diagram** — Describe in plain English → generates the diagram
- **Editable Output** — Export to Excalidraw (JSON), Draw.io (XML), or SVG

## Why Not Mermaid?

Mermaid has limited styling and looks generic. Diagram Forge targets:
- **Excalidraw** — Beautiful hand-drawn aesthetic, fully interactive
- **Draw.io / diagrams.net** — Industry standard, enterprise-ready
- **SVG** — Portable, searchable, styleable

## Architecture

```
data/
├── input/          # Raw images, audio, text
├── output/        # Generated diagrams
└── templates/     # Reusable diagram templates

src/
├── ocr/           # Image text extraction (GPT-4V, PaddleOCR)
├── voice/         # Speech-to-text (Whisper)
├── diagram/       # AI diagram generation (Claude API)
└── exporter/      # Format converters (→ Excalidraw, Draw.io, SVG)
```

## Supported Diagram Types

| Type | Input | Output |
|------|-------|--------|
| Architecture Diagram | Image / Text | Excalidraw, Draw.io |
| Sequence Diagram | Voice / Text | Excalidraw, Draw.io |
| Flowchart | Image / Text | Excalidraw, Draw.io |
| ER Diagram | Text | Draw.io |
| Class Diagram | Text | Excalidraw, Draw.io |
| Component Diagram | Text | Excalidraw, Draw.io |

## Tech Stack

- **Python 3.11+** — Core language
- **Claude API** — AI diagram generation
- **Whisper** — Speech-to-text
- **Excalidraw** — Output format (JSON)
- **draw.io** — Output format (XML)
- **FastAPI** — API layer
