# Phase 0: Claude → Excalidraw JSON Spike

## Objective
Validate that Claude Sonnet 4.5 can reliably produce valid, structurally correct Excalidraw JSON.

## Methodology
1. Run each prompt through Claude Sonnet 4.5 via Messages API
2. Parse response as JSON
3. Validate against Excalidraw element schema
4. Open in Excalidraw app (https://app.excalidraw.com) or Excalidraw React app
5. Score structural correctness (1-5 scale per criterion)

## Pass Criteria
- ≥70% of outputs parse as valid JSON AND score ≥3/5 on structural correctness
- If <70%: pivot to 2-step approach (description → Excalidraw JSON)

## Run Commands
```bash
cd spikes/phase0-excalidraw-spike
# Set API key
export ANTHROPIC_API_KEY=sk-...

# Run all prompts
python3 run_spike.py

# Open results
cat results/spike-results.json | jq .
```

## Results
See `results/` directory for per-prompt outputs and scores.
