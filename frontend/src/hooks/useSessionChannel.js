/**
 * useSessionChannel — real-time session state via SSE with polling fallback.
 *
 * Usage (participant):
 *   const { connected } = useSessionChannel(sessionId, sessionToken, onEvent)
 *
 * Usage (host, uses HttpOnly JWT cookie):
 *   const { connected } = useSessionChannel(sessionId, null, onEvent)
 *
 * Uses @microsoft/fetch-event-source so that:
 *   - Participants send X-Session-Token header (keeps session_token out of URLs/logs)
 *   - Hosts send their HttpOnly cookie automatically via credentials: 'include'
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { fetchEventSource } from '@microsoft/fetch-event-source'

const SSE_URL = (sessionId) =>
  `${window.location.origin}/api/v1/quizzes/sessions/${sessionId}/events`

export default function useSessionChannel(sessionId, sessionToken, onEvent) {
  const [connected, setConnected] = useState(false)
  const abortRef = useRef(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const connect = useCallback(() => {
    if (!sessionId) return
    if (abortRef.current) return  // already open

    const controller = new AbortController()
    abortRef.current = controller

    const headers = {}
    if (sessionToken) {
      // Participant: send session_token as a header (not in URL)
      headers['X-Session-Token'] = sessionToken
    }

    fetchEventSource(SSE_URL(sessionId), {
      method: 'GET',
      headers,
      credentials: 'include',  // sends HttpOnly cookie for host auth
      signal: controller.signal,
      onopen: async (response) => {
        if (response.ok) {
          setConnected(true)
          return
        }
        // Non-2xx: emit unavailable so caller falls back to polling
        onEventRef.current?.({ type: 'sse_unavailable' })
        controller.abort()
      },
      onmessage: (msg) => {
        try {
          const event = JSON.parse(msg.data)
          onEventRef.current?.(event)
        } catch {
          // ignore malformed frames
        }
      },
      onclose: () => {
        setConnected(false)
        abortRef.current = null
        onEventRef.current?.({ type: 'sse_unavailable' })
      },
      onerror: (err) => {
        setConnected(false)
        abortRef.current = null
        onEventRef.current?.({ type: 'sse_unavailable' })
        // Returning a positive number would trigger retry; throw to stop
        throw err
      },
    }).catch(() => {
      // fetchEventSource rejects on abort or onerror throw — suppress
    })
  }, [sessionId, sessionToken])

  useEffect(() => {
    connect()
    return () => {
      if (abortRef.current) {
        abortRef.current.abort()
        abortRef.current = null
      }
      setConnected(false)
    }
  }, [connect])

  return { connected }
}
