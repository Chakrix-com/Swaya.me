/**
 * useSessionChannel — real-time session state via SSE with polling fallback.
 *
 * Usage (participant):
 *   const { connected } = useSessionChannel(sessionId, sessionToken, onEvent)
 *
 * Usage (host, uses JWT from localStorage):
 *   const { connected } = useSessionChannel(sessionId, null, onEvent)
 *
 * onEvent(event) — called with every parsed SSE event object:
 *   { type: 'state', data: { ...audienceState } }
 *   { type: 'leaderboard_toggle', visible: bool }
 *
 * If SSE fails or is unsupported, the hook emits a 'sse_unavailable' event
 * so the caller can keep its existing polling logic running unchanged.
 */
import { useEffect, useRef, useState, useCallback } from 'react'

const SSE_PATH = (sessionId, sessionToken) => {
  const base = `/api/v1/quizzes/sessions/${sessionId}/events`
  if (sessionToken) return `${base}?session_token=${encodeURIComponent(sessionToken)}`
  return base
}

export default function useSessionChannel(sessionId, sessionToken, onEvent) {
  const [connected, setConnected] = useState(false)
  const esRef = useRef(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const connect = useCallback(() => {
    if (!sessionId) return
    if (esRef.current) return  // already open

    // Participant: no auth header needed (session_token in URL).
    // Host: EventSource can't set headers — we pass JWT via a short-lived cookie
    // workaround isn't needed because the backend also accepts Bearer in the header;
    // for the host we skip SSE and let the existing polling handle it.
    // Only use SSE for participants (session_token path).
    if (!sessionToken) {
      onEventRef.current?.({ type: 'sse_unavailable' })
      return
    }

    if (typeof EventSource === 'undefined') {
      onEventRef.current?.({ type: 'sse_unavailable' })
      return
    }

    const url = SSE_PATH(sessionId, sessionToken)
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => setConnected(true)

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        onEventRef.current?.(event)
      } catch {
        // ignore malformed frames
      }
    }

    es.onerror = () => {
      setConnected(false)
      es.close()
      esRef.current = null
      // Emit unavailable so caller can fall back to polling
      onEventRef.current?.({ type: 'sse_unavailable' })
    }
  }, [sessionId, sessionToken])

  useEffect(() => {
    connect()
    return () => {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
      setConnected(false)
    }
  }, [connect])

  return { connected }
}
