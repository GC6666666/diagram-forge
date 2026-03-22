"""Prompt library per diagram type — examples that guide Claude."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class PromptExample:
    """An example prompt demonstrating correct output for a diagram type."""
    description: str      # Human-readable description
    prompt: str           # The actual prompt text
    diagram_type: str     # architecture | sequence | flowchart


ARCHITECTURE_EXAMPLES: list[PromptExample] = [
    PromptExample(
        description="Three-tier web architecture",
        prompt="Generate an Excalidraw JSON diagram showing a simple 3-tier web architecture: Client (browser) → API Gateway → Backend Service → Database. Use rectangles for services, cylinders for the database. Add directional arrows showing request/response flow. Output ONLY valid JSON. No markdown fences.",
        diagram_type="architecture",
    ),
    PromptExample(
        description="Microservices with message queue",
        prompt="Generate an Excalidraw JSON diagram showing a microservices architecture: API Gateway routes to User Service, Order Service, Payment Service. Services communicate via Message Queue (Kafka). All services connect to a shared PostgreSQL database. Use rectangles for services, cylinders for databases. Output ONLY valid JSON. No markdown fences.",
        diagram_type="architecture",
    ),
    PromptExample(
        description="Cloud architecture (AWS-style)",
        prompt="Generate an Excalidraw JSON diagram showing a cloud architecture: Internet → CloudFront CDN → Load Balancer → EC2 Auto-Scaling Group (3 instances). EC2 connects to ElastiCache (Redis) and RDS (PostgreSQL). S3 bucket for static assets. Use rectangles for compute, cylinders for databases. Output ONLY valid JSON.",
        diagram_type="architecture",
    ),
    PromptExample(
        description="Event-driven architecture",
        prompt="Generate an Excalidraw JSON diagram showing event-driven architecture: User Service publishes events to Event Bus. Notification Service and Analytics Service subscribe to events. Each service has its own database. Use rectangles for services, cylinders for databases. Output ONLY valid JSON.",
        diagram_type="architecture",
    ),
    PromptExample(
        description="Kubernetes deployment",
        prompt="Generate an Excalidraw JSON diagram showing a Kubernetes deployment: Ingress → Cluster → Pods (2 replicas) for Frontend and Backend. Pods connect to ConfigMap and Secret. Services (ClusterIP) sit in front of pod groups. Use rectangles for pods/services, document icon for ConfigMap/Secret. Output ONLY valid JSON.",
        diagram_type="architecture",
    ),
]


SEQUENCE_EXAMPLES: list[PromptExample] = [
    PromptExample(
        description="Simple login flow",
        prompt="Generate an Excalidraw JSON diagram showing a login sequence: Browser → API Gateway (POST /login) → Auth Service → Database. Return token back through the chain. Use rectangles for participants, dashed lines for lifelines, horizontal arrows for messages. Output ONLY valid JSON.",
        diagram_type="sequence",
    ),
    PromptExample(
        description="JWT authentication",
        prompt="Generate an Excalidraw JSON diagram showing JWT authentication flow: Client → API Gateway (request + JWT) → Auth Service (verify) → User Service (fetch user) → Database → back to Client. Use rectangles, arrows with labels. Output ONLY valid JSON.",
        diagram_type="sequence",
    ),
    PromptExample(
        description="Payment processing with retry",
        prompt="Generate an Excalidraw JSON diagram showing payment processing: Client → Order Service → Payment Service → Payment Gateway. Show success and failure paths. Use rectangles for participants, arrows for messages, mark failure path. Output ONLY valid JSON.",
        diagram_type="sequence",
    ),
    PromptExample(
        description="Async order via message queue",
        prompt="Generate an Excalidraw JSON diagram showing async order processing: Client → API Gateway → Order Service → Message Queue. Inventory Service and Notification Service consume events asynchronously. Return 202 Accepted immediately. Use rectangles, async arrows. Output ONLY valid JSON.",
        diagram_type="sequence",
    ),
    PromptExample(
        description="WebSocket real-time update",
        prompt="Generate an Excalidraw JSON diagram showing WebSocket real-time updates: Client connects to Server via WebSocket. User action → Client → Server → Database → broadcast back via WebSocket → Client updates UI. Show connect/disconnect. Output ONLY valid JSON.",
        diagram_type="sequence",
    ),
]


FLOWCHART_EXAMPLES: list[PromptExample] = [
    PromptExample(
        description="User registration",
        prompt="Generate an Excalidraw JSON diagram showing user registration flowchart: Start → Form → Validate → Error? (diamond) → NO: show error → YES: Save to Database → Send Email → Click Link → Verify → Activate → End. Use rectangles for steps, diamonds for decisions, arrows for flow. Output ONLY valid JSON.",
        diagram_type="flowchart",
    ),
    PromptExample(
        description="API rate limiting",
        prompt="Generate an Excalidraw JSON diagram showing API rate limiting: Request → Extract Key → Check Counter → Under Limit? (diamond) → NO: Return 429 → YES: Increment → Circuit Breaker? → Forward → Return Response. Use rectangles for actions, diamonds for decisions. Output ONLY valid JSON.",
        diagram_type="flowchart",
    ),
    PromptExample(
        description="CI/CD pipeline",
        prompt="Generate an Excalidraw JSON diagram showing CI/CD pipeline: Push → Tests (rectangle) → Pass? (diamond) → NO: Notify → YES: Build Docker → Push Registry → Deploy Staging → Health Check → Pass? (diamond) → NO: Rollback → YES: Deploy Prod → Smoke Test → Done. Output ONLY valid JSON.",
        diagram_type="flowchart",
    ),
    PromptExample(
        description="Order state machine",
        prompt="Generate an Excalidraw JSON diagram showing order state transitions: CREATED → PAYMENT_PENDING → PAID → SHIPPED → DELIVERED. Also: CANCELLED (from CREATED/PAYMENT_PENDING), REFUNDED (from PAID). Use rectangles for states, arrows with labels for transitions. Output ONLY valid JSON.",
        diagram_type="flowchart",
    ),
    PromptExample(
        description="Retry with exponential backoff",
        prompt="Generate an Excalidraw JSON diagram showing retry logic: Operation → Attempt → Success? (diamond) → YES: End. NO: attempt < max? (diamond) → NO: Alert, End. YES: Calculate backoff → Wait → Retry (loop back). Max 3 attempts, base delay 1s, max 30s. Output ONLY valid JSON.",
        diagram_type="flowchart",
    ),
]


def get_prompts(diagram_type: str) -> list[PromptExample]:
    """Get prompt examples for a diagram type."""
    return {
        "architecture": ARCHITECTURE_EXAMPLES,
        "sequence": SEQUENCE_EXAMPLES,
        "flowchart": FLOWCHART_EXAMPLES,
    }.get(diagram_type, [])


def build_user_prompt(text: str, diagram_type: str) -> str:
    """
    Build the user prompt for diagram generation.
    Includes a random example for better few-shot guidance.
    """
    import random

    examples = get_prompts(diagram_type)
    example = random.choice(examples) if examples else None

    prompt = text
    if example:
        prompt = f"Example of a good output:\n{example.prompt}\n\nNow generate a diagram for:\n{text}"

    return prompt
