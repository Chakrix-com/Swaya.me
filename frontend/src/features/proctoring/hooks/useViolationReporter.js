import { useCallback, useRef } from 'react';
import api from '../../../services/api';

export function useViolationReporter(sessionToken) {
  const queue = useRef([]);
  const flushing = useRef(false);

  const flush = useCallback(async () => {
    if (flushing.current || queue.current.length === 0) return;
    flushing.current = true;
    const batch = queue.current.splice(0, queue.current.length);
    for (const item of batch) {
      try {
        await api.post('/proctoring/event', {
          session_token: sessionToken,
          rule_id: item.rule_id,
          event_type: item.event_type,
          metadata: item.metadata || {},
        });
      } catch (_) {
        // Non-fatal — proctoring errors must not block exam
      }
    }
    flushing.current = false;
  }, [sessionToken]);

  const reportViolation = useCallback(
    (rule_id, event_type, metadata = {}) => {
      if (!sessionToken) return { logged: false, is_locked: false, violations_remaining: null, silent: false };
      queue.current.push({ rule_id, event_type, metadata });
      // Fire-and-forget flush
      api
        .post('/proctoring/event', {
          session_token: sessionToken,
          rule_id,
          event_type,
          metadata,
        })
        .then((res) => res.data)
        .catch(() => null);
      return { logged: true, is_locked: false, violations_remaining: null, silent: false };
    },
    [sessionToken]
  );

  return { reportViolation };
}
