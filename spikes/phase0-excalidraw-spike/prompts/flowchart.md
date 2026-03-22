# Flowchart Diagram Prompts (Phase 0 Spike)

Each prompt tests a different scenario for flowcharts.
Elements expected: rectangles (process), diamonds (decisions), parallelograms (I/O), arrows.

---

## F1: User Registration Flow
```
Generate an Excalidraw JSON diagram showing a user registration flowchart:
1. Start → Show registration form (parallelogram)
2. → User fills form (rectangle)
3. → Validate inputs (diamond: valid?)
4. → If NO: Show error message → back to form
5. → If YES: Save to database (rectangle)
6. → Send verification email (rectangle)
7. → User clicks email link (parallelogram)
8. → Verify email (diamond: valid token?)
9. → If NO: Show error (rectangle)
10. → If YES: Account activated (rectangle)
11. → End
Use rectangles for processes, diamonds for decisions, parallelograms for I/O.
Use arrows with labels for decision branches.
Output ONLY valid JSON. No markdown fences. No explanation.
```

## F2: API Rate Limiting Flow
```
Generate an Excalidraw JSON diagram showing API rate limiting logic:
1. Request arrives
2. Extract API key from header (rectangle)
3. Check rate limit counter (rectangle)
4. Under limit? (diamond)
5. If NO: Return 429 Too Many Requests → End
6. If YES: Increment counter (rectangle)
7. Check circuit breaker (diamond: open?)
8. If OPEN: Return 503 Service Unavailable → End
9. If CLOSED: Forward to downstream service (rectangle)
10. Success? (diamond)
11. If NO: Trip circuit breaker → End
12. If YES: Return response → End
Use rectangles for all actions, diamonds for all decisions.
Output ONLY valid JSON. No markdown fences.
```

## F3: CI/CD Pipeline
```
Generate an Excalidraw JSON diagram showing a CI/CD pipeline:
1. Developer pushes code → GitHub/GitLab webhook
2. CI pipeline triggered → Run tests (rectangle)
3. Tests pass? (diamond)
4. If NO: Notify developer → End
5. If YES: Build Docker image (rectangle)
6. Push to registry (rectangle)
7. Deploy to staging (rectangle)
8. Staging health check (diamond: healthy?)
9. If NO: Rollback → Notify → End
10. If YES: Deploy to production (rectangle)
11. Smoke test (diamond: passed?)
12. If NO: Automatic rollback → End
13. If YES: Notify success → End
Use rectangles for all steps, diamonds for gates.
Output ONLY valid JSON. No markdown fences.
```

## F4: Order State Machine
```
Generate an Excalidraw JSON diagram showing order state transitions:
States: CREATED → PAYMENT_PENDING → PAID → SHIPPED → DELIVERED
          ↓           ↓            ↓        ↓
      CANCELLED  CANCELLED    REFUND  RETURN_REQUESTED
                              ↓           ↓
                          REFUNDED     RETURNED

Also transitions:
- PAYMENT_PENDING → timeout → CANCELLED
- SHIPPED → tracking update creates new DELIVERED state
Use rectangles for each state (stacked if multiple per box).
Use arrows for transitions (labeled with trigger/action).
Circles or rounded rectangles for terminal states (DELIVERED, CANCELLED, REFUNDED, RETURNED).
Output ONLY valid JSON. No markdown fences.
```

## F5: Error Handling with Retry
```
Generate an Excalidraw JSON diagram showing retry logic with exponential backoff:
1. Operation starts
2. Attempt operation (rectangle)
3. Success? (diamond)
4. If YES: Log success → End
5. If NO: Increment attempt counter (rectangle)
6. attempt < max_attempts? (diamond)
7. If NO: Log failure, alert → End
8. If YES: Calculate backoff delay = min(max_delay, base_delay * 2^attempt) (rectangle)
9. Wait for backoff (rectangle with clock icon concept)
10. → Attempt operation (loop back to step 2)
Max 3 attempts, base delay 1s, max delay 30s.
Use rectangles for actions, diamonds for decisions.
Label the loop arrow clearly.
Output ONLY valid JSON. No markdown fences.
```
