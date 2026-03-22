# Sequence Diagram Prompts (Phase 0 Spike)

Each prompt tests a different scenario complexity for sequence diagrams.
Elements expected: participant rectangles, lifelines (vertical dashed lines), arrows, activation boxes.

---

## S1: Simple Login Flow
```
Generate an Excalidraw JSON diagram showing a login sequence:
1. User → Browser: enters credentials
2. Browser → API Gateway: POST /login
3. API Gateway → Auth Service: validate credentials
4. Auth Service → Database: check user
5. Database → Auth Service: user found
6. Auth Service → API Gateway: token
7. API Gateway → Browser: 200 OK + token
Use rectangles for participants (top of lifelines), vertical dashed lines for lifelines.
Use horizontal arrows for messages (labeled), small rectangles for activations.
Output ONLY valid JSON. No markdown fences. No explanation.
```

## S2: JWT Authentication Flow
```
Generate an Excalidraw JSON diagram showing JWT authentication:
1. Client → API Gateway: request + JWT token
2. API Gateway → Auth Service: verify token
3. Auth Service: token valid, extract user_id
4. Auth Service → API Gateway: user_id
5. API Gateway → User Service: GET /users/{user_id}
6. User Service → Database: SELECT user
7. Database → User Service: user data
8. User Service → API Gateway: user JSON
9. API Gateway → Client: response
Use rectangles for actors/services, dashed vertical lines for lifelines.
Label arrows with the action/message.
Output ONLY valid JSON. No markdown fences.
```

## S3: Payment Processing (with retry)
```
Generate an Excalidraw JSON diagram showing payment processing with retry:
1. Client → Order Service: place order
2. Order Service → Payment Service: process payment
3. Payment Service → Payment Gateway: charge card
4. Payment Gateway → Payment Service: success
5. Payment Service → Order Service: payment confirmed
6. [Failure case]: Payment Gateway → Payment Service: declined
7. Payment Service → Order Service: payment failed
8. Order Service → Client: show error
Use rectangles for participants. Mark failure path with red/dashed arrows.
Activation boxes on all active participants.
Output ONLY valid JSON. No markdown fences.
```

## S4: Async Order Processing via Message Queue
```
Generate an Excalidraw JSON diagram showing async order processing:
1. Client → API Gateway: POST /orders
2. API Gateway → Order Service: create order
3. Order Service → Message Queue: publish "order.created"
4. Order Service → API Gateway: order_id (immediate response)
5. API Gateway → Client: 202 Accepted + order_id
6. [Async] Inventory Service: consumes "order.created"
7. Inventory Service: reserve items
8. [Async] Notification Service: consumes "order.created"
9. Notification Service → Client: "order confirmed" email
Use rectangles, dashed vertical lifelines, horizontal arrows for messages.
Mark async arrows with "(async)" label.
Output ONLY valid JSON. No markdown fences.
```

## S5: WebSocket Real-time Update
```
Generate an Excalidraw JSON diagram showing WebSocket real-time updates:
1. Client → Server: connect WebSocket
2. Server → Client: connection established
3. User Action in Browser → Client: click button
4. Client → Server: send message
5. Server → Database: save data
6. Database → Server: save confirmed
7. Server → Client: broadcast update (via WebSocket)
8. Client → UI: render update
9. [Disconnect]: Client → Server: close
10. Server → Client: ack close
Use rectangles, dashed lifelines.
Mark WebSocket messages with double-headed arrows or labeled arrows.
Output ONLY valid JSON. No markdown fences.
```
