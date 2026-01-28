# Realtime Communication (MVP)

This document defines the realtime communication strategy for the Swaya.me MVP.

---

## Decision: Polling vs WebSocket

**MVP Approach**: To be finalized during implementation based on:
- Complexity of WebSocket connection management
- Latency requirements (< 2s acceptable for MVP)
- Development velocity

**Recommendation**: Start with **polling** for simplicity, migrate to WebSocket post-MVP if needed.

---

## Polling Approach (Recommended for MVP)

### Overview
Audience and host UIs poll status endpoints at regular intervals to receive updates.

### Polling Intervals
- **Audience**: Poll every 2 seconds
- **Host**: Poll every 2 seconds (or use WebSocket for faster updates)

### Advantages
- Simpler implementation (no connection state management)
- No WebSocket infrastructure required
- Easier debugging and testing
- Works across all network environments

### Disadvantages
- Higher latency (2s delay)
- More HTTP requests (acceptable for MVP scale)
- Slightly higher server load (mitigated by Redis caching)

---

## Polling Endpoints

### GET /sessions/{session_id}/status

Get current session state (audience and host).

**Response (200 OK)**:
```json
{
  "session_id": "sess_xyz",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_456",
    "text": "What is 2+2?",
    "options": [
      {"option_id": "opt_1", "text": "3"},
      {"option_id": "opt_2", "text": "4"},
      {"option_id": "opt_3", "text": "5"},
      {"option_id": "opt_4", "text": "6"}
    ],
    "state": "OPEN"
  },
  "live_results": null,
  "last_updated": "2026-01-27T11:10:00Z"
}
```

**When Question is Closed**:
```json
{
  "session_id": "sess_xyz",
  "status": "ACTIVE",
  "current_question": {
    "question_id": "q_456",
    "text": "What is 2+2?",
    "state": "CLOSED"
  },
  "live_results": {
    "correct_option_id": "opt_2",
    "results": [
      {"option_id": "opt_1", "count": 5, "percentage": 10.0},
      {"option_id": "opt_2", "count": 40, "percentage": 80.0},
      {"option_id": "opt_3", "count": 3, "percentage": 6.0},
      {"option_id": "opt_4", "count": 2, "percentage": 4.0}
    ],
    "total_responses": 50
  },
  "last_updated": "2026-01-27T11:15:00Z"
}
```

### Caching Strategy
- Session state cached in Redis with 2s TTL
- Avoid database queries on every poll
- Invalidate cache on state changes (question advance, session end)

---

## WebSocket Approach (Post-MVP Alternative)

### Connection

**Endpoint**: `wss://swaya.me/api/v1/sessions/{session_id}/live`

**Authentication**:
- Host: JWT in query param (`?token=<jwt>`)
- Audience: Participant ID in query param (`?participant_id=<id>`)

### Message Format

All messages follow this structure:
```json
{
  "type": "event_type",
  "session_id": "sess_xyz",
  "timestamp": "2026-01-27T11:10:00Z",
  "data": { }
}
```

### Server → Client Events

#### question_opened
Broadcast when host advances to next question.

```json
{
  "type": "question_opened",
  "session_id": "sess_xyz",
  "timestamp": "2026-01-27T11:10:00Z",
  "data": {
    "question_id": "q_456",
    "text": "What is 2+2?",
    "options": [
      {"option_id": "opt_1", "text": "3"},
      {"option_id": "opt_2", "text": "4"},
      {"option_id": "opt_3", "text": "5"},
      {"option_id": "opt_4", "text": "6"}
    ]
  }
}
```

#### answer_submitted
Broadcast to host when new answer submitted (aggregated).

```json
{
  "type": "answer_submitted",
  "session_id": "sess_xyz",
  "timestamp": "2026-01-27T11:11:30Z",
  "data": {
    "question_id": "q_456",
    "total_responses": 15
  }
}
```

#### question_closed
Broadcast when host closes current question.

```json
{
  "type": "question_closed",
  "session_id": "sess_xyz",
  "timestamp": "2026-01-27T11:15:00Z",
  "data": {
    "question_id": "q_456",
    "correct_option_id": "opt_2",
    "results": [
      {"option_id": "opt_1", "count": 5, "percentage": 10.0},
      {"option_id": "opt_2", "count": 40, "percentage": 80.0},
      {"option_id": "opt_3", "count": 3, "percentage": 6.0},
      {"option_id": "opt_4", "count": 2, "percentage": 4.0}
    ],
    "total_responses": 50
  }
}
```

#### session_ended
Broadcast when host ends quiz session.

```json
{
  "type": "session_ended",
  "session_id": "sess_xyz",
  "timestamp": "2026-01-27T11:30:00Z",
  "data": {
    "message": "Quiz has ended. Thank you for participating!"
  }
}
```

### Client → Server Events

#### ping
Keep connection alive.

```json
{
  "type": "ping",
  "timestamp": "2026-01-27T11:10:00Z"
}
```

**Server Response**:
```json
{
  "type": "pong",
  "timestamp": "2026-01-27T11:10:01Z"
}
```

---

## Connection Management (WebSocket)

### Reconnection Strategy
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
- Resume from last known state using `last_updated` timestamp
- Request missed events via REST API if gap > 10s

### Heartbeat
- Server sends `ping` every 30s
- Client responds with `pong` within 10s
- Connection closed if no `pong` received

### Scalability Considerations (Post-MVP)
- Use Redis Pub/Sub for multi-instance broadcasting
- Sticky sessions for WebSocket connections (via load balancer)
- Connection pooling and limits (1000 connections per instance)

---

## Performance Optimization

### Redis Pub/Sub (WebSocket)
```python
# Publish event to session-specific channel
redis_client.publish(f"session:{session_id}", json.dumps(event))

# Subscribe to session channel
pubsub = redis_client.pubsub()
pubsub.subscribe(f"session:{session_id}")
```

### Caching (Polling)
```python
# Cache session state in Redis with 2s TTL
redis_client.setex(f"session:{session_id}:state", 2, json.dumps(state))

# Read from cache
cached_state = redis_client.get(f"session:{session_id}:state")
```

---

## Error Handling

### Connection Errors (WebSocket)
- **Connection Refused**: Retry with backoff
- **Authentication Failed**: Redirect to join page
- **Session Not Found**: Display error and disconnect

### Polling Errors
- **Session Not Found (404)**: Stop polling, display error
- **Server Error (5xx)**: Retry with exponential backoff
- **Rate Limit (429)**: Increase poll interval to 5s

---

## Testing Strategy

### Load Testing
- Simulate 200 audience members polling every 2s
- Measure Redis cache hit rate (target: > 95%)
- Measure API response time (target: < 200ms)

### Realtime Testing
- Verify question broadcast within 2s of host action
- Verify results update within 2s of answer aggregation
- Test reconnection and session resume

---

## Migration Path

### Phase 1 (MVP): Polling
- Simple polling with 2s interval
- Redis caching for performance

### Phase 2 (Post-MVP): Hybrid
- Polling for audience
- WebSocket for host (real-time control)

### Phase 3 (Scale): Full WebSocket
- WebSocket for all clients
- Redis Pub/Sub for multi-instance broadcast
- Horizontal scaling with sticky sessions

---

## Decision Log

| Date | Decision | Rationale |
|------|---------|-----------|
| 2026-01-27 | Start with polling | Simpler implementation, sufficient for MVP |
| TBD | Evaluate WebSocket | Based on user feedback and latency requirements |
