import { useRef, useCallback } from 'react';
import api from '../../../services/api';

export function useAnswerTimingGuard(sessionToken, enabled) {
  const questionShownAt = useRef(null);

  const markQuestionShown = useCallback(() => {
    questionShownAt.current = Date.now();
  }, []);

  const validateTiming = useCallback(
    async (questionId, questionType, questionWordCount) => {
      if (!enabled || !sessionToken || !questionShownAt.current) {
        return { accepted: true };
      }

      const elapsed_ms = Date.now() - questionShownAt.current;

      try {
        const res = await api.post('/proctoring/answer-timing', {
          session_token: sessionToken,
          question_id: questionId,
          question_type: questionType,
          question_word_count: questionWordCount,
          elapsed_ms,
        });
        return res.data;
      } catch (_) {
        return { accepted: true };
      }
    },
    [sessionToken, enabled]
  );

  return { markQuestionShown, validateTiming };
}
