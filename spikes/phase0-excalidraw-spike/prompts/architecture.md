# Architecture Diagram Prompts (Phase 0 Spike)

Each prompt tests a different scenario complexity for architecture/block diagrams.
Elements expected: rectangles, cylinders (databases), directional arrows, labels.

---

## A1: Simple 3-tier Architecture
```
Generate an Excalidraw JSON diagram showing a simple 3-tier web architecture:
- Client (browser) → API Gateway → Backend Service → Database
Use rectangles for services, cylinders for the database.
Add directional arrows showing request/response flow.
Use the Excalidraw JSON format with the following schema structure:
{
  "type": "excalidraw",
  "version": 2,
  "elements": [
    {
      "id": "unique-id",
      "type": "rectangle|ellipse|arrow|text",
      "x": number,
      "y": number,
      "width": number,
      "height": number,
      "strokeColor": "#000000",
      "backgroundColor": "#ffffff",
      "text": "label text (for text elements)",
      "boundElements": [],
      "startBinding": { "elementId": "...", "focus": 0 },
      "endBinding": { "elementId": "...", "focus": 0 }
    }
  ]
}

Output ONLY valid JSON. No markdown fences. No explanation.
```

## A2: Microservices with Message Queue
```
Generate an Excalidraw JSON diagram showing a microservices architecture:
- API Gateway routes to: User Service, Order Service, Payment Service
- Services communicate via Message Queue (Kafka)
- All services connect to a shared PostgreSQL database
Use rectangles for services, cylinders for database and message queue.
Use directional arrows for synchronous calls, bidirectional arrows for async messages.
Output ONLY valid JSON matching the Excalidraw element schema. No markdown fences.
```

## A3: Cloud Architecture (AWS-style)
```
Generate an Excalidraw JSON diagram showing a cloud architecture:
- Internet → CloudFront CDN → Load Balancer → EC2 Auto-Scaling Group
- Auto-Scaling Group contains 3 EC2 instances
- EC2 instances connect to ElastiCache (Redis) and RDS (PostgreSQL)
- S3 bucket for static assets
Use rectangles for compute, cylinders for databases, ellipses for managed services.
Use directional arrows showing data flow.
Output ONLY valid JSON. No markdown fences. No explanation.
```

## A4: Event-Driven Architecture
```
Generate an Excalidraw JSON diagram showing event-driven architecture:
- User Service publishes "user.created" event to Event Bus
- Notification Service and Analytics Service subscribe to the event
- Each service has its own database
Use rectangles for services, cylinders for databases, the Event Bus as a large rounded rectangle.
Use arrows from Event Bus to subscribing services (labeled with event name).
Output ONLY valid JSON. No markdown fences.
```

## A5: Kubernetes Deployment Architecture
```
Generate an Excalidraw JSON diagram showing a Kubernetes deployment:
- Ingress Controller → Cluster → Pods (2 replicas each) for: Frontend, Backend
- Pods connect to ConfigMap and Secret
- Pods connect to PersistentVolumeClaim → PersistentVolume
- Services (ClusterIP) sit in front of each pod group
Use rectangles for pods and services, document icon for ConfigMap/Secret.
Use directional arrows with labels showing network traffic.
Output ONLY valid JSON. No markdown fences.
```
