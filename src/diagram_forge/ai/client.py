"""Claude API client with circuit breaker and retry."""

import os
import asyncio
from typing import Any

import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

import structlog
from diagram_forge.services.circuit_breaker import get_claude_circuit

logger = structlog.get_logger("diagram_forge.ai")


class ClaudeAPIError(Exception):
    """Raised when Claude API call fails."""
    def __init__(self, message: str, code: str = "UPSTREAM_ERROR"):
        super().__init__(message)
        self.code = code


class CircuitOpenError(ClaudeAPIError):
    """Raised when circuit breaker is open."""
    def __init__(self):
        super().__init__("Claude API circuit breaker is open", "CIRCUIT_OPEN")


class ClaudeClient:
    """
    Client for Anthropic Claude API.
    Handles circuit breaker, retries, and structured output.
    """

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._circuit = get_claude_circuit()
        self._model = "claude-sonnet-4-20250514"
        logger.info("claude_client_init", model=self._model)

    async def generate_diagram(
        self,
        prompt: str,
        diagram_type: str,
        timeout_seconds: float = 20.0,
    ) -> str:
        """
        Generate a diagram via Claude.

        Args:
            prompt: The user's text description
            diagram_type: architecture | sequence | flowchart
            timeout_seconds: Maximum time for the call

        Returns:
            Raw text response (should be parseable as JSON)

        Raises:
            CircuitOpenError: If circuit breaker is open
            ClaudeAPIError: If API call fails
        """
        if not self._circuit.is_available():
            raise CircuitOpenError()

        try:
            # Build system prompt based on diagram type
            system_prompt = self._build_system_prompt(diagram_type)

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.messages.create,
                    model=self._model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                ),
                timeout=timeout_seconds,
            )

            self._circuit.record_success()
            text = response.content[0].text
            logger.info(
                "claude_response",
                model=self._model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
            return text

        except asyncio.TimeoutError:
            self._circuit.record_failure()
            logger.error("claude_timeout", timeout=timeout_seconds)
            raise ClaudeAPIError(f"Claude API timed out after {timeout_seconds}s", "TIMEOUT")

        except Exception as e:
            self._circuit.record_failure()
            logger.error("claude_error", error=str(e))
            raise ClaudeAPIError(str(e), "UPSTREAM_ERROR")

    def _build_system_prompt(self, diagram_type: str) -> str:
        """Build the system prompt for a given diagram type."""
        base = """You are a diagram generation assistant. Generate valid Excalidraw JSON diagrams.

OUTPUT FORMAT: You must output ONLY valid JSON. No markdown fences. No explanation. No preamble.

The JSON must conform to the Excalidraw element schema with these fields:
- id: unique string identifier
- type: one of rectangle, ellipse, diamond, text, arrow
- x, y: coordinates (numbers)
- width, height: dimensions (numbers)
- strokeColor: hex color string
- backgroundColor: hex color string
- fillStyle: "solid"
- roughness: 0
- text: label text (for text elements)
- startBinding, endBinding: arrow bindings (for arrows)

Generate ONLY the JSON output."""

        type_specific = {
            "architecture": """

DIAGRAM TYPE: Architecture / Component Diagram

Include these element types:
- rectangle: services, containers, components
- ellipse: external actors, endpoints
- text: labels on shapes and connections

Include arrows with labels to show relationships and data flow.
Use rectangles for compute/services, ellipses for external entities.
Position elements clearly with appropriate spacing.""",

            "sequence": """

DIAGRAM TYPE: Sequence Diagram

Include these element types:
- rectangle: participants (at top)
- text: participant labels, message labels
- arrow: messages between participants

For arrows: use startBinding and endBinding to connect to participant rectangles.
Add text labels to arrows to show the message/action name.
Position participants horizontally with lifelines (vertical arrangement).
Space arrows vertically to show temporal ordering.""",

            "flowchart": """

DIAGRAM TYPE: Flowchart

Include these element types:
- rectangle: process/action steps
- diamond: decision points (with Yes/No labels on branches)
- text: step labels, decision labels
- arrow: flow direction with labels

Use arrows to connect steps. Decision diamonds should branch with labeled arrows.
Start with a labeled entry point, end with a labeled exit.""",
        }

        return base + type_specific.get(diagram_type, type_specific["architecture"])


# Singleton
_claude_client: ClaudeClient | None = None


def get_claude_client() -> ClaudeClient:
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
