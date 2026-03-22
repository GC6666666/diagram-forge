#!/usr/bin/env python3
"""
Phase 0 Spike - 2-Step Approach (fallback)
If direct prompt → Excalidraw JSON fails, try:
  Step 1: Prompt → structured description (JSON with nodes, edges, labels)
  Step 2: Description → Excalidraw JSON

Run with: python3 run_spike_2step.py
Requires: ANTHROPIC_API_KEY env var
"""

import json
import os
import time
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed.")
    exit(1)


# Step 1 prompt: Generate structured description
STEP1_PROMPT = """Generate a structured description of the following diagram as JSON.
Output ONLY valid JSON with this exact schema — no markdown fences, no explanation:

{{
  "type": "architecture|sequence|flowchart",
  "nodes": [
    {{
      "id": "unique-id",
      "label": "Human readable label",
      "type": "service|actor|process|decision|storage|client",
      "x": 100,  // approximate x position
      "y": 50    // approximate y position
    }}
  ],
  "edges": [
    {{
      "from": "node-id",
      "to": "node-id",
      "label": "action or message",
      "style": "solid|dashed|bidirectional"
    }}
  ]
}}

Diagram to describe: {description}

Output ONLY the JSON. No markdown fences. No explanation."""

# Step 2 prompt: Convert structured description to Excalidraw JSON
STEP2_PROMPT = """Convert this structured diagram description into Excalidraw JSON format.

Description:
{structured_json}

Generate Excalidraw JSON with the following element types:
- Rectangles for services, processes, actors
- Ellipses for external actors
- Cylinders (ellipse top) for databases/storage
- Diamonds for decisions
- Arrows with startBinding/endBinding for connections
- Text elements for labels

Schema:
{{
  "type": "excalidraw",
  "version": 2,
  "elements": [
    {{
      "id": "unique-string-id",
      "type": "rectangle|ellipse|text|arrow",
      "x": number,
      "y": number,
      "width": number,
      "height": number,
      "strokeColor": "#000000",
      "backgroundColor": "#ffffff",
      "fillStyle": "solid|hachure|cross-hatch",
      "roughness": 0,
      "text": "label (for text elements)",
      "startBinding": {{ "elementId": "id", "focus": 0, "gap": 5 }},
      "endBinding": {{ "elementId": "id", "focus": 0, "gap": 5 }}
    }}
  ]
}}

Output ONLY valid JSON. No markdown fences. No explanation."""


@dataclass
class TwoStepResult:
    prompt_id: str
    diagram_type: str
    description: str
    step1_output: Optional[dict]
    step1_error: Optional[str]
    step2_output: Optional[dict]
    step2_error: Optional[str]
    final_parse_error: Optional[str]
    final_validation_errors: list[str]
    structural_score: int
    structural_notes: str
    is_valid: bool


def extract_json(text: str) -> Optional[dict]:
    """Extract JSON from response text."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return None


def validate_excalidraw(data: dict) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        errors.append("Root must be object")
        return errors
    elements = data.get("elements", [])
    if not elements:
        errors.append("Missing elements")
        return errors
    for i, elem in enumerate(elements[:10]):  # Check first 10
        if not isinstance(elem, dict):
            errors.append(f"Element {i} not object")
            continue
        elem_type = elem.get("type")
        if elem_type not in {"rectangle", "ellipse", "diamond", "text", "arrow", "line"}:
            errors.append(f"Element {i}: unknown type '{elem_type}'")
    return errors


def score_structural(data: dict, dtype: str) -> tuple[int, str]:
    elements = data.get("elements", [])
    if not elements:
        return 0, "No elements"
    types = {e.get("type") for e in elements}
    score = 1
    notes = []
    if "rectangle" in types or "ellipse" in types:
        score += 1
        notes.append("shapes ok")
    if "arrow" in types:
        score += 1
        notes.append("arrows ok")
    if "text" in types:
        score += 1
        notes.append("labels ok")
    positioned = [e for e in elements if e.get("x") is not None]
    if len(positioned) >= 3:
        score += 1
    return min(score, 5), "; ".join(notes) if notes else "ok"


def run_2step(client: anthropic.Anthropic, prompt_id: str, dtype: str,
               description: str) -> TwoStepResult:
    print(f"  {prompt_id}...", end=" ", flush=True)

    # Step 1: structured description
    try:
        r1 = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": STEP1_PROMPT.format(description=description)}]
        )
        step1 = extract_json(r1.content[0].text)
        step1_err = None if step1 else "Failed to parse Step 1 output"
    except Exception as e:
        step1 = None
        step1_err = str(e)

    if step1 is None:
        print("✗ (step1 failed)")
        return TwoStepResult(
            prompt_id=prompt_id, diagram_type=dtype, description=description,
            step1_output=None, step1_error=step1_err, step2_output=None,
            step2_error=None, final_parse_error=step1_err,
            validation_errors=[], structural_score=0,
            structural_notes=f"Step 1 failed: {step1_err}", is_valid=False
        )

    # Step 2: Excalidraw JSON
    try:
        desc_json = json.dumps(step1)
        r2 = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": STEP2_PROMPT.format(structured_json=desc_json)}]
        )
        step2 = extract_json(r2.content[0].text)
        step2_err = None if step2 else "Failed to parse Step 2 output"
    except Exception as e:
        step2 = None
        step2_err = str(e)

    if step2 is None:
        print("✗ (step2 failed)")
        return TwoStepResult(
            prompt_id=prompt_id, diagram_type=dtype, description=description,
            step1_output=step1, step1_error=step1_err, step2_output=None,
            step2_error=step2_err, final_parse_error=step2_err,
            validation_errors=[], structural_score=0,
            structural_notes=f"Step 2 failed: {step2_err}", is_valid=False
        )

    val_errs = validate_excalidraw(step2)
    score, notes = score_structural(step2, dtype)
    is_valid = len(val_errs) == 0
    print(f"{'✓' if is_valid else '✗'} (score={score}/5)")
    return TwoStepResult(
        prompt_id=prompt_id, diagram_type=dtype, description=description,
        step1_output=step1, step1_error=step1_err, step2_output=step2,
        step2_error=step2_err, final_parse_error=None,
        validation_errors=val_errs, structural_score=score,
        structural_notes=notes, is_valid=is_valid
    )


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    # Test prompts (shorter for 2-step)
    tests = [
        ("A-1", "architecture", "Simple 3-tier: Client → API Gateway → Backend → Database"),
        ("A-2", "architecture", "Microservices: Gateway routes to User/Order/Payment Services via Message Queue"),
        ("S-1", "sequence", "Login flow: Browser → API Gateway → Auth Service → Database → Token"),
        ("S-2", "sequence", "JWT auth: Client → Gateway → Auth Service verify → User Service → DB"),
        ("F-1", "flowchart", "User registration: form → validate → save DB → send email → verify → activate"),
        ("F-2", "flowchart", "API rate limit: check key → check counter → under limit? → yes: forward, no: 429"),
    ]

    print(f"\nPhase 0 Spike - 2-Step Approach: {len(tests)} tests\n")
    results = []
    for pid, dtype, desc in tests:
        result = run_2step(client, pid, dtype, desc)
        results.append(result)
        time.sleep(1)

    valid = sum(1 for r in results if r.is_valid)
    avg = sum(r.structural_score for r in results) / len(results) if results else 0

    results_file = results_dir / "spike-2step-results.json"
    with open(results_file, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"PHASE 0 SPIKE - 2-STEP RESULTS")
    print(f"{'='*60}")
    print(f"Valid: {valid}/{len(results)} ({100*valid/len(results):.0f}%)")
    print(f"Avg score: {avg:.1f}/5")
    for r in results:
        print(f"  {'✓' if r.is_valid else '✗'} {r.prompt_id} {r.structural_score}/5")
    print(f"\nResults: {results_file}")

    return 0


if __name__ == "__main__":
    exit(main())
