# Session Events — SSE Design, Fallback, and Scaling

**Date:** 2026-06-13  
**Status:** Implemented  

---

## Transport: Server-Sent Events (SSE)

All participant real-time updates use HTTP SSE — no WebSocket dependency.

**Endpoint:** `GET /api/v1/quizzes/sessions/{session_id}/events`

| Auth | Participant | Host |
|---|---|---|
| Method | `?session_token=<token>` in URL | Not supported — host uses polling |
| Why | `EventSource` cannot set headers; token in URL lets browser connect directly | JWT in `Authorization` header would need a proxy workaround |

**Event stream format:**
```
event: state
data: {"status":"active","current_question":{...},"participant_count":23,...}

: ping

event: leaderboard_toggle
data: {"visible":true}
```

- `: ping` keepalive every ~400 ms prevents proxy/CDN timeout drops.
- `X-Accel-Buffering: no` header disables nginx buffering for Swaya's nginx reverse-proxy.
- `Cache-Control: no-cache`, `Connection: keep-alive` are set on the response.

---

## Polling fallback

`useSessionChannel` (frontend hook at `frontend/src/hooks/useSessionChannel.js`) wraps SSE with a polling fallback:

1. Opens an `EventSource` if `sessionToken` is provided and `EventSource` is available.
2. On first successful `onmessage`: emits `{ type: 'sse_connected' }` — AudienceSession slows polling from 2 s → 5 s.
3. On `onerror` (network drop, proxy teardown): closes the stream, emits `{ type: 'sse_unavailable' }` — AudienceSession returns to 2 s polling.
4. On `visibilitychange` to `visible`: the browser reconnects `EventSource` automatically (browser-native reconnect).

**Polling floor:** 2 s (SSE down), 5 s (SSE up). REST call is `GET /sessions/{id}/audience-results?session_token=...`.

---

## Data flow

```
Host action (advance/end)
  → session_service_async.advance_session()
  → DB write (QuizSession.current_question_index, status)
  → Redis broadcast (future: Pub/Sub; current: poll reads DB)

Participant EventSource
  ← DB poll every 400 ms in the SSE generator loop
  ← yields diff only when payload changes
  ← also yields ping keepalive regardless
```

**Current limitation:** each SSE connection polls MySQL. At 1000 concurrent participants across 10 sessions, this is ~2500 DB reads/s. Acceptable for current scale (PRO tier cap: 2000 participants). For ENTERPRISE scale, replace inner DB poll with Redis Pub/Sub broadcast.

---

## Reconnect resilience (P4-2)

Participants who refresh or lose connection recover automatically:
1. `sessionToken` + `sessionId` + `displayName` are written to `sessionStorage` on join.
2. `sessionId` is also in the URL (`/session/:sessionId`) — used as primary fallback.
3. On mount, AudienceSession reads: `locationState → Redux → sessionStorage → URL params`.
4. `sessionStorage` is cleared on session end, invalidation, or explicit leave.

---

## Scaling path

| Scale | Approach |
|---|---|
| ≤ 2000 participants / 5 sessions | Current: DB poll in SSE loop (400 ms), fallback REST poll |
| 2000–10000 (ENTERPRISE) | Redis Pub/Sub: `session:{id}:events` channel; SSE generator subscribes via `SUBSCRIBE`, yields on message |
| Multi-server | Sticky sessions (nginx `ip_hash`) OR Redis Pub/Sub (server-agnostic) |

---

## Security

- Participant `session_token` is a server-generated UUID stored in the `participants` table. It cannot be guessed.
- The backend validates token on every SSE connection open and on every REST call via `_require_participant_for_session()`.
- SSE response does **not** include other participants' answers during the question window — only aggregate counts.
- If the session is restarted (new join code), old tokens get `HTTP 403` with `"Session has been restarted"` — client shows a rejoin prompt.
