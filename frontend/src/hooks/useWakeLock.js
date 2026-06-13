/**
 * useWakeLock — acquires a Screen Wake Lock while `active` is true.
 * Silently no-ops on browsers that don't support the Wake Lock API.
 * Re-acquires on page visibility change (lock is released on tab hide).
 */
import { useEffect, useRef } from 'react'

export default function useWakeLock(active) {
  const lockRef = useRef(null)

  useEffect(() => {
    if (!active || !('wakeLock' in navigator)) return

    let cancelled = false

    const acquire = async () => {
      try {
        lockRef.current = await navigator.wakeLock.request('screen')
      } catch {
        // Permission denied or feature unavailable — silent no-op
      }
    }

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !cancelled) {
        acquire()
      }
    }

    acquire()
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', onVisibilityChange)
      lockRef.current?.release().catch(() => {})
      lockRef.current = null
    }
  }, [active])
}
