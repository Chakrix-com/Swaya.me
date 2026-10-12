import { useEffect, useRef, useState } from 'react';
import { Button, Steps, Alert } from 'antd';
import { CameraOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { createFaceDetector } from './hooks/useFaceDetector';

// A covered lens gives a near-black or flat frame. Checked on its own because
// it still works where face detection can't run (no WebGL).
const MIN_MEAN_LUMA = 30;
const MIN_LUMA_STDDEV = 8;
const BLOCKED_CHECK_ATTEMPTS = 8;
const BLOCKED_CHECK_GAP_MS = 250;

function frameLooksBlocked(ctx, width, height) {
  const { data } = ctx.getImageData(0, 0, width, height);
  let sum = 0;
  let sumSq = 0;
  const n = data.length / 4;
  for (let i = 0; i < data.length; i += 4) {
    const luma = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    sum += luma;
    sumSq += luma * luma;
  }
  const mean = sum / n;
  const stddev = Math.sqrt(Math.max(0, sumSq / n - mean * mean));
  return mean < MIN_MEAN_LUMA || stddev < MIN_LUMA_STDDEV;
}

export function ExamIdentityCapture({ stream, onComplete, requirePhotoId }) {
  const { t } = useTranslation();
  const videoRef = useRef();
  const [step, setStep] = useState(0);
  const [errorKey, setErrorKey] = useState(null);
  // null = still loading, false = unavailable on this browser
  const [detector, setDetector] = useState(null);
  // Capture stays disabled until the camera has delivered a real frame
  const [videoReady, setVideoReady] = useState(false);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let created = null;
    createFaceDetector('IMAGE')
      .then((d) => {
        if (cancelled) { d.close?.(); return; }
        created = d;
        setDetector(d);
      })
      .catch((err) => {
        console.warn('[proctoring] face detection unavailable for identity check:', err?.message || err);
        if (!cancelled) setDetector(false);
      });
    return () => {
      cancelled = true;
      try { created?.close?.(); } catch (_) {}
    };
  }, []);

  const startVideo = () => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.play();
    }
  };

  const capture = async () => {
    const canvas = document.createElement('canvas');
    canvas.width = 320;
    canvas.height = 240;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const video = videoRef.current;
    if (!video) return;

    setChecking(true);
    try {
      // A camera's first frames are often black (stream start, auto-exposure),
      // so judge "blocked" over a short window rather than on a single frame.
      let blocked = true;
      for (let attempt = 0; attempt < BLOCKED_CHECK_ATTEMPTS && blocked; attempt += 1) {
        if (attempt > 0) await new Promise((resolve) => setTimeout(resolve, BLOCKED_CHECK_GAP_MS));
        if (video.readyState < 2 || !video.videoWidth) continue;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        blocked = frameLooksBlocked(ctx, canvas.width, canvas.height);
      }
      if (blocked) { setErrorKey('cameraBlocked'); return; }

      if (detector) {
        let faces = null;
        try {
          faces = detector.detect(canvas).detections.length;
        } catch (err) {
          // Can't read frames (no WebGL) — fall back to the blocked-lens check alone
          console.warn('[proctoring] face detection failed during identity check:', err?.message || err);
        }
        if (faces === 0) { setErrorKey('noFace'); return; }
        if (faces > 1) { setErrorKey('multipleFaces'); return; }
      }

      setErrorKey(null);
      setStep(1);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 32,
        background: '#fafafa',
      }}
    >
      <div style={{ maxWidth: 520, width: '100%' }}>
        <h2 style={{ textAlign: 'center', marginBottom: 24 }}>{t('proctoring.identityCapture.title')}</h2>
        <Steps
          current={step}
          items={[
            { title: t('proctoring.identityCapture.stepFaceCapture'), icon: <CameraOutlined /> },
            { title: t('proctoring.identityCapture.stepReady'), icon: <CheckCircleOutlined /> },
          ]}
          style={{ marginBottom: 32 }}
        />

        {step === 0 && (
          <div style={{ textAlign: 'center' }}>
            <Alert
              message={t('proctoring.identityCapture.instruction')}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            {errorKey && (
              <Alert
                className="identity-capture-error"
                message={t(`proctoring.identityCapture.${errorKey}`)}
                type="error"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}
            <div
              style={{
                position: 'relative',
                display: 'inline-block',
                border: '2px solid #1677ff',
                borderRadius: 8,
                overflow: 'hidden',
              }}
            >
              <video
                ref={(el) => {
                  videoRef.current = el;
                  if (el) startVideo();
                }}
                width={320}
                height={240}
                muted
                onLoadedData={() => setVideoReady(true)}
                style={{ display: 'block' }}
              />
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  border: '3px dashed rgba(255,255,255,0.5)',
                  borderRadius: 8,
                  pointerEvents: 'none',
                }}
              />
            </div>
            <br />
            <Button
              type="primary"
              icon={<CameraOutlined />}
              size="large"
              onClick={capture}
              loading={detector === null || !videoReady || checking}
              style={{ marginTop: 16 }}
            >
              {t('proctoring.identityCapture.captureButton')}
            </Button>
          </div>
        )}

        {step === 1 && (
          <div style={{ textAlign: 'center' }}>
            <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
            <h3 style={{ marginTop: 12 }}>{t('proctoring.identityCapture.verified')}</h3>
            <Button type="primary" size="large" onClick={onComplete} style={{ marginTop: 16 }}>
              {t('proctoring.identityCapture.startExam')}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
