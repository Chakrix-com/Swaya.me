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

export function ProctoringProvider({ quizId, sessionToken, onAutoSubmit, children }) {
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

        // Init the proctoring session in Redis+DB as soon as config confirms proctoring is on.
        // The response includes is_locked — if the session was already locked (e.g. after a
        // page reload), enforce the lock immediately so the candidate cannot continue.
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
          ).then((initRes) => {
            if (initRes.data?.is_locked) {
              lockReasonRef.current = 'SESSION_ALREADY_LOCKED';
              setIsLocked(true);
              if (data.escalation?.auto_submit_on_lock && onAutoSubmit) {
                autoSubmitRef.current = true;
                onAutoSubmit();
              }
            }
          }).catch(() => {});
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
          if (ruleSet?.escalation?.auto_submit_on_lock && onAutoSubmit) {
            autoSubmitRef.current = true;
            onAutoSubmit();
          }
        } else if (!data.silent) {
          setViolationsLeft(data.violations_remaining);
          setWarningActive(true);
        }
      } catch (_) {
        // Non-fatal
      }
    },
    [isLocked, sessionToken, ruleSet, onAutoSubmit]
  );

  // While loading: block children behind a spinner so the exam never renders
  // before proctoring config is confirmed. This prevents a race where a fast user
  // (or one who blocks the config request) bypasses the gate entirely.
  if (!ruleSet) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16 }}>
        <div style={{ width: 40, height: 40, border: '4px solid #f0f0f0', borderTop: '4px solid #1677ff', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  // Config loaded but proctoring disabled for this quiz — pass through with no-op context
  if (!ruleSet.enabled) {
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
      {!isLocked && children}
    </ProctoringCtx.Provider>
  );
}
