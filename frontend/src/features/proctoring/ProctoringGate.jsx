import { useState, useCallback, useEffect, useRef } from 'react';
import { Button, Spin, Checkbox } from 'antd';
import { FullscreenOutlined, WarningFilled, VideoCameraOutlined, EyeOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useProctoringContext } from './ProctoringProvider';
import { useProctoringModule } from './hooks/useProctoringModule';
import { useWebcamGate } from './hooks/useWebcamGate';
import { useWebcamMonitor } from './hooks/useWebcamMonitor';
import { useFaceDetector } from './hooks/useFaceDetector';
import { WebcamDeniedScreen } from './WebcamDeniedScreen';
import { ExamIdentityCapture } from './ExamIdentityCapture';
import api from '../../services/api';

function ProctoringModuleActivator() {
  useProctoringModule();
  return null;
}

// Waits for fullscreen to be confirmed before showing the exam.
// If fullscreen is blocked (e.g. by an extension), reports a violation
// and lets the participant in anyway so they aren't deadlocked — but the
// FULLSCREEN_BLOCKED event is logged and can trigger escalation.
// Confirms fullscreen is active before showing exam content.
// Initialises as 'active' if fullscreen was already requested by the caller
// (e.g. the warning screen's acknowledge button) so no second click is needed.
// Falls back to a manual button if fullscreen wasn't yet granted.
// FullscreenGate — enforces fullscreen as a hard requirement.
// The exam content is NEVER shown unless document.fullscreenElement is set.
function FullscreenGate({ children, reportViolation }) {
  const { t } = useTranslation();
  const [state, setState] = useState(() =>
    document.fullscreenElement ? 'active' : 'entering'
  );
  const timerRef = useRef(null);

  // Attempt to enter fullscreen and transition state on the result.
  // Must be called synchronously inside a user-gesture handler OR at mount
  // time when the gesture that triggered mount is still in the call stack.
  const attemptFullscreen = useCallback(() => {
    clearTimeout(timerRef.current);

    // If already in fullscreen (e.g. fast browser), go straight to active.
    if (document.fullscreenElement) {
      setState('active');
      return;
    }

    const onFSChange = () => {
      if (document.fullscreenElement) {
        clearTimeout(timerRef.current);
        document.removeEventListener('fullscreenchange', onFSChange);
        setState('active');
      }
    };
    document.addEventListener('fullscreenchange', onFSChange);

    document.documentElement.requestFullscreen().catch(() => {
      clearTimeout(timerRef.current);
      document.removeEventListener('fullscreenchange', onFSChange);
      reportViolation('fullscreen_enforce', 'FULLSCREEN_BLOCKED', { reason: 'api_rejected' });
      setState('blocked');
    });

    // 4-second safety net in case fullscreenchange never fires
    timerRef.current = setTimeout(() => {
      document.removeEventListener('fullscreenchange', onFSChange);
      if (!document.fullscreenElement) {
        reportViolation('fullscreen_enforce', 'FULLSCREEN_BLOCKED', { reason: 'timeout' });
        setState('blocked');
      }
    }, 4000);
  }, [reportViolation]);

  // Run attemptFullscreen once on mount (the initial gate entry).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { attemptFullscreen(); return () => clearTimeout(timerRef.current); }, []);

  // Watch for the user exiting fullscreen while the exam is active.
  useEffect(() => {
    if (state !== 'active') return;
    const onExit = () => {
      if (!document.fullscreenElement) setState('exited');
    };
    document.addEventListener('fullscreenchange', onExit);
    return () => document.removeEventListener('fullscreenchange', onExit);
  }, [state]);

  // Retry button — this IS a direct user gesture so requestFullscreen() works.
  const retryFullscreen = useCallback(() => {
    setState('entering');
    attemptFullscreen();
  }, [attemptFullscreen]);

  if (state === 'active') return children;

  if (state === 'entering') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 20, background: '#000' }}>
        <Spin size="large" style={{ color: '#fff' }} />
        <p style={{ margin: 0, color: '#ccc', fontSize: 15 }}>{t('proctoring.fullscreen.entering')}</p>
      </div>
    );
  }

  // blocked or exited — hard block, exam never shown
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 20, background: '#1a1a1a', padding: 24 }}>
      <FullscreenOutlined style={{ fontSize: 56, color: '#faad14' }} />
      <p style={{ fontSize: 18, fontWeight: 600, color: '#fff', margin: 0, textAlign: 'center' }}>
        {t('proctoring.fullscreen.blockedTitle')}
      </p>
      <p style={{ fontSize: 14, color: '#aaa', maxWidth: 380, textAlign: 'center', margin: 0 }}>
        {t('proctoring.fullscreen.blockedDesc')}
      </p>
      <Button type="primary" size="large" onClick={retryFullscreen} icon={<FullscreenOutlined />}
        style={{ marginTop: 8 }}>
        {t('proctoring.fullscreen.retryButton')}
      </Button>
    </div>
  );
}

const RULE_KEYS = [
  'tab_switch_detect', 'copy_paste_block', 'right_click_block',
  'fullscreen_enforce', 'multi_tab_detect', 'devtools_detect',
  'bot_signal_detect', 'webcam_monitoring',
];

function ProctoringWarningScreen({ ruleSet, fullscreenRequired, onAcknowledge }) {
  const { t } = useTranslation();
  const [checked, setChecked] = useState(false);
  const lockAt = ruleSet?.escalation?.lock_on_violation_count;
  const autoSubmit = ruleSet?.escalation?.auto_submit_on_lock;
  const webcamOn = ruleSet?.webcam_required;

  // This is the ONLY click that enters fullscreen.
  // Called synchronously inside the button's onClick so the browser honours
  // requestFullscreen() as a direct user gesture — no async batching.
  const handleAcknowledge = useCallback(() => {
    if (fullscreenRequired) {
      // requestFullscreen must be called synchronously in a user-gesture handler.
      // We call onAcknowledge() immediately after so FullscreenGate mounts while
      // the fullscreen transition is still in progress and catches the event.
      document.documentElement.requestFullscreen().catch(() => {});
    }
    onAcknowledge();
  }, [fullscreenRequired, onAcknowledge]);

  const activeRuleKeys = (ruleSet?.rules || [])
    .map((r) => r.rule_id)
    .filter((id) => RULE_KEYS.includes(id));

  return (
    <div style={{ minHeight: '100vh', background: '#fff7f7', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '32px 16px' }}>
      <div style={{ maxWidth: 640, width: '100%', background: '#fff', borderRadius: 12, boxShadow: '0 4px 32px rgba(220,38,38,0.12)', border: '1.5px solid #fca5a5', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ background: '#dc2626', padding: '20px 28px', display: 'flex', alignItems: 'center', gap: 12 }}>
          <WarningFilled style={{ fontSize: 28, color: '#fff' }} />
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: 18, lineHeight: 1.2 }}>
              {t('proctoring.warning.title')}
            </div>
            <div style={{ color: '#fecaca', fontSize: 13, marginTop: 2 }}>
              {t('proctoring.warning.subtitle')}
            </div>
          </div>
        </div>

        <div style={{ padding: '24px 28px' }}>
          {/* Webcam notice */}
          {webcamOn && (
            <div style={{ background: '#fef3c7', border: '1px solid #f59e0b', borderRadius: 8, padding: '12px 16px', marginBottom: 20, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <VideoCameraOutlined style={{ color: '#d97706', fontSize: 18, marginTop: 2, flexShrink: 0 }} />
              <span style={{ fontSize: 14, color: '#92400e', lineHeight: 1.5 }}>
                {t('proctoring.warning.webcamNotice')}
              </span>
            </div>
          )}

          {/* Violations list */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontWeight: 600, fontSize: 14, color: '#1f2937', marginBottom: 10 }}>
              <EyeOutlined style={{ marginRight: 6, color: '#dc2626' }} />
              {t('proctoring.warning.violationsTitle')}
            </div>
            <ul style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 7 }}>
              {activeRuleKeys.map((ruleId) => (
                <li key={ruleId} style={{ fontSize: 14, color: '#374151', lineHeight: 1.5 }}>
                  {t(`proctoring.warning.rules.${ruleId}`)}
                </li>
              ))}
            </ul>
          </div>

          {/* Lock threshold */}
          {lockAt && (
            <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: 8, padding: '12px 16px', marginBottom: 20, fontSize: 14, color: '#7f1d1d', lineHeight: 1.6 }}>
              <strong>{t('proctoring.warning.lockMessage', { count: lockAt })}</strong>
              {autoSubmit ? t('proctoring.warning.autoSubmit') : t('proctoring.warning.noAutoSubmit')}
              {' '}{t('proctoring.warning.allLogged')}
            </div>
          )}

          {/* Acknowledgement checkbox */}
          <div style={{
            borderTop: '1px solid #f3f4f6',
            paddingTop: 18,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}>
            <Checkbox
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              style={{ fontSize: 14, color: '#374151', alignItems: 'flex-start' }}
            >
              {t('proctoring.warning.checkboxLabel')}
            </Checkbox>

            <Button
              type="primary"
              danger
              size="large"
              disabled={!checked}
              onClick={handleAcknowledge}
              block
              icon={fullscreenRequired ? <FullscreenOutlined /> : undefined}
              style={{ fontWeight: 600, fontSize: 15 }}
            >
              {fullscreenRequired
                ? t('proctoring.warning.acknowledgeButtonFullscreen')
                : t('proctoring.warning.acknowledgeButton')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function WebcamPip({ stream }) {
  const { t } = useTranslation();
  const pipRef = useRef(null);

  useEffect(() => {
    if (pipRef.current && stream) {
      pipRef.current.srcObject = stream;
      pipRef.current.play().catch(() => {});
    }
  }, [stream]);

  if (!stream) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: 20,
      right: 20,
      zIndex: 9999,
      borderRadius: 10,
      overflow: 'hidden',
      boxShadow: '0 4px 16px rgba(0,0,0,0.35)',
      border: '2px solid rgba(255,255,255,0.6)',
      width: 160,
      background: '#000',
    }}>
      <video
        ref={pipRef}
        muted
        playsInline
        style={{ width: '100%', display: 'block', transform: 'scaleX(-1)' }}
      />
      <div style={{
        position: 'absolute',
        top: 6,
        left: 8,
        display: 'flex',
        alignItems: 'center',
        gap: 5,
        background: 'rgba(0,0,0,0.45)',
        borderRadius: 4,
        padding: '2px 6px',
      }}>
        <span style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: '#52c41a',
          display: 'inline-block',
          boxShadow: '0 0 4px #52c41a',
        }} />
        <span style={{ color: '#fff', fontSize: 10, fontWeight: 600, letterSpacing: 0.5 }}>{t('common.live')}</span>
      </div>
    </div>
  );
}

export function ProctoringGate({ children, initialWarned = false, examDurationSeconds, captureRef }) {
  const { t } = useTranslation();
  const { resolvedRules, webcamRequired, reportViolation, sessionToken, ruleSet } = useProctoringContext();
  const [warned, setWarned] = useState(initialWarned);
  const [stream, setStream] = useState(null);
  const [identityDone, setIdentityDone] = useState(!webcamRequired);

  const fullscreenRequired = resolvedRules.some((r) => r.rule_id === 'fullscreen_enforce');
  const webcamRule = resolvedRules.find((r) => r.rule_id === 'webcam_monitoring');
  const requirePhotoId = webcamRule?.config?.require_photo_id || false;

  // All hooks must run unconditionally before any early return
  const webcamStatus = useWebcamGate({
    enabled: warned && webcamRequired,
    onGranted: (s) => {
      setStream(s);
      if (sessionToken) {
        api.post('/proctoring/session/webcam-granted', {}, {
          headers: { 'X-Session-Token': sessionToken },
        }).catch(() => {});
      }
    },
    onDenied: () => {
      reportViolation('webcam_monitoring', 'WEBCAM_PERMISSION_DENIED', {});
    },
  });

  const videoRef = useWebcamMonitor({
    stream,
    config: webcamRule?.config,
    reportViolation,
    enabled: !!stream && webcamRequired,
    sessionToken,
    examDurationSeconds,
    captureRef,
  });

  useFaceDetector({
    videoRef,
    config: webcamRule?.config,
    reportViolation,
    enabled: !!stream && webcamRequired,
  });

  // 1. Warning gate — must acknowledge before anything else starts
  if (!warned && resolvedRules.length > 0) {
    return (
      <ProctoringWarningScreen
        ruleSet={ruleSet}
        fullscreenRequired={fullscreenRequired}
        onAcknowledge={() => setWarned(true)}
      />
    );
  }

  // 2. Webcam permission
  if (webcamRequired && webcamStatus === 'denied') return <WebcamDeniedScreen />;

  if (webcamRequired && (webcamStatus === 'pending' || webcamStatus === 'not_required')) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 16 }}>
        <p>{t('proctoring.webcam.requesting')}</p>
      </div>
    );
  }

  // 3. Identity capture
  if (webcamRequired && !identityDone && stream) {
    return (
      <ExamIdentityCapture
        stream={stream}
        requirePhotoId={requirePhotoId}
        onComplete={() => setIdentityDone(true)}
      />
    );
  }

  // 4. Fullscreen gate + exam
  // The hidden capture video must live OUTSIDE FullscreenGate — FullscreenGate
  // delays rendering its children until fullscreen is confirmed, so if the video
  // were inside it, videoRef.current would be null when useWebcamMonitor's effect
  // first runs (stream already set), and srcObject would never be assigned.
  const examContent = (
    <>
      <ProctoringModuleActivator />
      {webcamRequired && <WebcamPip stream={stream} />}
      {children}
    </>
  );

  return (
    <>
      {webcamRequired && (
        <video ref={videoRef} muted playsInline style={{ position: 'fixed', top: -9999, left: -9999, width: 320, height: 240, visibility: 'hidden', pointerEvents: 'none' }} />
      )}
      {fullscreenRequired
        ? <FullscreenGate reportViolation={reportViolation}>{examContent}</FullscreenGate>
        : examContent}
    </>
  );
}
