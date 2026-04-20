import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import api from '../../services/api';
import { useViolationReporter } from './hooks/useViolationReporter';
import { ProctoringOverlay } from './ProctoringOverlay';
import { ProctoringLockScreen } from './ProctoringLockScreen';

const ProctoringCtx = createContext({
  resolvedRules: [],
  isLocked: false,
  violationsLeft: null,
  warningActive: false,
  sessionToken: null,
  honeypotConfig: null,
  reportViolation: () => {},
  webcamRequired: false,
  ruleSet: null,
});

export function useProctoringContext() {
  return useContext(ProctoringCtx);
}

export function ProctoringProvider({ quizId, sessionToken, children }) {
  const [ruleSet, setRuleSet] = useState(null);
  const [isLocked, setIsLocked] = useState(false);
  const [violationsLeft, setViolationsLeft] = useState(null);
  const [warningActive, setWarningActive] = useState(false);
  const [honeypotConfig, setHoneypotConfig] = useState(null);
  const { reportViolation: rawReport } = useViolationReporter(sessionToken);
  const lockReasonRef = useRef(null);
  const autoSubmitRef = useRef(false);

  useEffect(() => {
    if (!quizId) return;
    api
      .get(`/proctoring/config/${quizId}`, {
        headers: sessionToken ? { 'X-Session-Token': sessionToken } : {},
      })
      .then((res) => {
        const data = res.data;
        setRuleSet(data);
        if (data.honeypot_config) setHoneypotConfig(data.honeypot_config);

        // Init the proctoring session in Redis+DB as soon as config confirms proctoring is on
        if (data.enabled && sessionToken) {
          api.post(
            '/proctoring/session/init',
            {
              quiz_id: quizId,
              browser_fingerprint: navigator.userAgent,
              user_agent: navigator.userAgent,
              webcam_granted: false,
            },
            { headers: { 'X-Session-Token': sessionToken } }
          ).catch(() => {});
        }
      })
      .catch(() => {
        setRuleSet({ enabled: false, rules: [], escalation: {}, webcam_required: false });
      });
  }, [quizId, sessionToken]);

  const reportViolation = useCallback(
    async (rule_id, event_type, metadata = {}) => {
      if (isLocked) return;
      try {
        const res = await api.post(
          '/proctoring/event',
          { session_token: sessionToken, rule_id, event_type, metadata },
          { headers: sessionToken ? { 'X-Session-Token': sessionToken } : {} }
        );
        const data = res.data;
        if (data.is_locked) {
          lockReasonRef.current = event_type;
          setIsLocked(true);
          if (ruleSet?.escalation?.auto_submit_on_lock) {
            autoSubmitRef.current = true;
          }
        } else if (!data.silent) {
          setViolationsLeft(data.violations_remaining);
          setWarningActive(true);
        }
      } catch (_) {
        // Non-fatal
      }
    },
    [isLocked, sessionToken, ruleSet]
  );

  // While loading OR when disabled: render children immediately with a no-op context
  if (!ruleSet || !ruleSet.enabled) {
    return (
      <ProctoringCtx.Provider value={{
        resolvedRules: [],
        isLocked: false,
        violationsLeft: null,
        warningActive: false,
        sessionToken,
        honeypotConfig: null,
        reportViolation: () => {},
        webcamRequired: false,
        ruleSet: null,
      }}>
        {children}
      </ProctoringCtx.Provider>
    );
  }

  return (
    <ProctoringCtx.Provider
      value={{
        resolvedRules: ruleSet.rules || [],
        isLocked,
        violationsLeft,
        warningActive,
        sessionToken,
        honeypotConfig,
        reportViolation,
        webcamRequired: ruleSet.webcam_required,
        ruleSet,
      }}
    >
      {isLocked && (
        <ProctoringLockScreen
          lockReason={lockReasonRef.current}
          autoSubmitted={autoSubmitRef.current}
        />
      )}
      {warningActive && !isLocked && (
        <ProctoringOverlay
          violationsLeft={violationsLeft}
          onDismiss={() => setWarningActive(false)}
        />
      )}
      {children}
    </ProctoringCtx.Provider>
  );
}
