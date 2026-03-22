#!/usr/bin/env python3
"""
Phase 0 Spike: Validate Claude → Excalidraw JSON
Run with: python3 run_spike.py
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
    print("ERROR: anthropic package not installed. Run: pip install anthropic")
    exit(1)


@dataclass
class PromptResult:
    prompt_id: str
    diagram_type: str  # architecture | sequence | flowchart
    prompt_text: str
    raw_response: str
    parsed_json: Optional[dict]
    parse_error: Optional[str]
    validation_errors: list[str]
    structural_score: int  # 0-5
    structural_notes: str
    is_valid: bool
    timestamp: str


def extract_json(text: str) -> Optional[dict]:
    """Extract JSON from Claude response, handling markdown fences."""
    # Try to find JSON in code blocks first
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)

    # Try raw text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def validate_excalidraw(data: dict) -> list[str]:
    """Validate Excalidraw JSON structure. Returns list of errors."""
    errors = []

    if not isinstance(data, dict):
        errors.append("Root must be a JSON object")
        return errors

    # Check for elements array
    elements = data.get("elements")
    if not elements:
        errors.append("Missing 'elements' array")
        return errors

    if not isinstance(elements, list):
        errors.append("'elements' must be an array")
        return errors

    if len(elements) == 0:
        errors.append("'elements' is empty")
        return errors

    valid_types = {
        "rectangle", "ellipse", "diamond", "text", "arrow",
        "line", "freedraw", "image", "frame"
    }

    for i, elem in enumerate(elements):
        if not isinstance(elem, dict):
            errors.append(f"Element {i} is not an object")
            continue

        elem_type = elem.get("type")
        if elem_type not in valid_types:
            errors.append(f"Element {i}: unknown type '{elem_type}'")

        # Arrows should have start/end points or bindings
        if elem_type == "arrow":
            if "x" not in elem or "y" not in elem:
                errors.append(f"Arrow {i}: missing x/y position")

    return errors


def score_structural_correctness(data: dict, diagram_type: str) -> tuple[int, str]:
    """Score the structural correctness of the diagram (1-5)."""
    elements = data.get("elements", [])
    if not elements:
        return 0, "No elements found"

    elem_types = {e.get("type") for e in elements}

    if diagram_type == "architecture":
        # Expect rectangles, ellipses, arrows, text
        score = 1
        notes = []

        if "rectangle" in elem_types or "ellipse" in elem_types:
            score += 1
            notes.append("has shapes")
        else:
            notes.append("MISSING: no rectangles/ellipses")

        if "arrow" in elem_types:
            score += 1
            notes.append("has arrows")
        else:
            notes.append("MISSING: no arrows")

        if "text" in elem_types:
            score += 1
            notes.append("has labels")
        else:
            notes.append("MISSING: no text labels")

        # Check for meaningful content (elements with position and size)
        meaningful = [e for e in elements if e.get("x") is not None and e.get("y") is not None]
        if len(meaningful) >= 3:
            score += 1
            notes.append(f"{len(meaningful)} positioned elements")

        return min(score, 5), "; ".join(notes)

    elif diagram_type == "sequence":
        # Expect rectangles (participants), arrows (messages), text (labels)
        score = 1
        notes = []

        if "rectangle" in elem_types or "ellipse" in elem_types:
            score += 1
            notes.append("has participant shapes")
        else:
            notes.append("MISSING: no participant shapes")

        arrows = [e for e in elements if e.get("type") == "arrow"]
        if arrows:
            score += 1
            notes.append(f"has {len(arrows)} arrows (messages)")
        else:
            notes.append("MISSING: no message arrows")

        if "text" in elem_types:
            score += 1
            notes.append("has message labels")
        else:
            notes.append("MISSING: no labels on arrows")

        if len(arrows) >= 3:
            score += 1
            notes.append("multiple message exchanges")

        return min(score, 5), "; ".join(notes)

    elif diagram_type == "flowchart":
        # Expect rectangles, diamonds, arrows, text
        score = 1
        notes = []

        if "rectangle" in elem_types:
            score += 1
            notes.append("has process rectangles")
        else:
            notes.append("MISSING: no rectangles")

        if "diamond" in elem_types:
            score += 1
            notes.append("has decision diamonds")
        else:
            notes.append("NOTE: no decision diamonds")

        if "arrow" in elem_types:
            score += 1
            notes.append("has flow arrows")
        else:
            notes.append("MISSING: no arrows")

        if "text" in elem_types:
            score += 1
            notes.append("has labels")
        else:
            notes.append("MISSING: no text labels")

        return min(score, 5), "; ".join(notes)

    return 1, "Unknown diagram type"


def load_prompts(prompts_dir: Path) -> list[tuple[str, str, str]]:
    """Load all prompts from markdown files. Returns [(id, type, prompt_text)]."""
    prompts = []
    for md_file in sorted(prompts_dir.glob("*.md")):
        diagram_type = md_file.stem  # architecture, sequence, flowchart
        content = md_file.read_text()

        # Split by "## " headers to get individual prompts
        sections = re.split(r"\n## ", content)
        first_title = sections[0].strip()
        # First section starts with "# Prompt Name\n\n```\n..."
        # Extract the code block content
        blocks = re.findall(r"```\s*(.*?)```", first_title, re.DOTALL)
        if blocks:
            # Skip the first block (the template) and process the rest
            pass

        # Better approach: split by numbered headers
        parts = re.split(r"\n## [A-Z]\d+: ", content)
        for i, part in enumerate(parts[1:], 1):  # Skip header line
            lines = part.strip().split("\n")
            prompt_name = lines[0].strip()
            # Find the code block
            code_match = re.search(r"```\s*(.*?)```", part, re.DOTALL)
            if code_match:
                prompt_text = code_match.group(1).strip()
                prompt_id = f"{diagram_type[0].upper()}-{i}"  # A-1, S-1, F-1
                prompts.append((prompt_id, diagram_type, prompt_text))

    return prompts


def run_prompt(client: anthropic.Anthropic, prompt_id: str, diagram_type: str,
               prompt_text: str) -> PromptResult:
    """Run a single prompt against Claude Sonnet 4.5."""
    print(f"  Running {prompt_id}...", end=" ", flush=True)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt_text
                }
            ]
        )

        raw = response.content[0].text
        parsed = extract_json(raw)
        parse_error = None
        validation_errors = []
        is_valid = False
        structural_score = 0
        structural_notes = ""

        if parsed is None:
            parse_error = "Failed to extract JSON from response"
        else:
            validation_errors = validate_excalidraw(parsed)
            if not validation_errors:
                is_valid = True
                structural_score, structural_notes = score_structural_correctness(
                    parsed, diagram_type
                )

        print(f"{'✓' if is_valid else '✗'} (score={structural_score}/5)")

        return PromptResult(
            prompt_id=prompt_id,
            diagram_type=diagram_type,
            prompt_text=prompt_text,
            raw_response=raw[:500] + "..." if len(raw) > 500 else raw,
            parsed_json=parsed,
            parse_error=parse_error,
            validation_errors=validation_errors,
            structural_score=structural_score,
            structural_notes=structural_notes,
            is_valid=is_valid,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

    except Exception as e:
        print(f"ERROR: {e}")
        return PromptResult(
            prompt_id=prompt_id,
            diagram_type=diagram_type,
            prompt_text=prompt_text,
            raw_response="",
            parsed_json=None,
            parse_error=str(e),
            validation_errors=[],
            structural_score=0,
            structural_notes=f"Exception: {e}",
            is_valid=False,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    prompts_dir = Path(__file__).parent / "prompts"
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    prompts = load_prompts(prompts_dir)
    print(f"\nPhase 0 Spike: {len(prompts)} prompts to test\n")

    results: list[PromptResult] = []
    for prompt_id, diagram_type, prompt_text in prompts:
        result = run_prompt(client, prompt_id, diagram_type, prompt_text)
        results.append(result)
        time.sleep(1)  # Rate limiting

    # Save results
    results_file = results_dir / "spike-results.json"
    with open(results_file, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)

    # Summary
    total = len(results)
    valid = sum(1 for r in results if r.is_valid)
    avg_score = sum(r.structural_score for r in results) / total if total else 0
    by_type = {}
    for r in results:
        by_type.setdefault(r.diagram_type, []).append(r)

    print(f"\n{'='*60}")
    print(f"PHASE 0 SPIKE RESULTS")
    print(f"{'='*60}")
    print(f"Total prompts: {total}")
    print(f"Valid JSON: {valid}/{total} ({100*valid/total:.0f}%)")
    print(f"Average structural score: {avg_score:.1f}/5")
    print()

    print("By diagram type:")
    for dtype, res in by_type.items():
        v = sum(1 for r in res if r.is_valid)
        avg = sum(r.structural_score for r in res) / len(res)
        print(f"  {dtype:15s}: {v}/{len(res)} valid, avg score {avg:.1f}/5")

    print()
    print("Per-prompt scores:")
    for r in results:
        status = "✓" if r.is_valid else "✗"
        print(f"  {status} {r.prompt_id:5s} {r.structural_score}/5 — {r.structural_notes[:60]}")

    print()
    print(f"Results saved to: {results_file}")

    # Pass/fail
    pass_rate = valid / total if total else 0
    print()
    if pass_rate >= 0.7:
        print("✓ PASS: ≥70% valid outputs. Phase 1 can proceed.")
        print("  Recommendation: use direct prompt+parse approach")
    else:
        print("✗ FAIL: <70% valid outputs. Pivot to 2-step approach recommended.")
        print("  Recommendation: generate description → generate Excalidraw JSON")

    return 0 if pass_rate >= 0.7 else 1


if __name__ == "__main__":
    exit(main())
