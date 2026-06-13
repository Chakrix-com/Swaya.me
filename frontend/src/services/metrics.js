/**
 * Fire-and-forget analytics beacon.
 * Never throws — failures are silently swallowed so they can't affect UX.
 */
import api from './api'

export function trackEvent(eventType, payload = {}) {
  const { sessionId, quizId, ...properties } = payload
  const body = {
    event_type: eventType,
    ...(sessionId != null && { session_id: sessionId }),
    ...(quizId != null && { quiz_id: quizId }),
    ...(Object.keys(properties).length > 0 && { properties }),
  }
  api.post('/metrics/event', body).catch(() => {})
}
