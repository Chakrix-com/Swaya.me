import { useEffect, useRef } from 'react';

const DETECT_INTERVAL_MS = 500;
const MULTI_FACE_WARN_SEC = 3;
// Minimum gap between two reports of the same condition, so a condition that
// persists escalates steadily instead of burning through every warning at once.
const REPEAT_COOLDOWN_MS = 15 * 1000;

// runningMode 'VIDEO' for the continuous in-exam monitor, 'IMAGE' for one-off
// still checks (identity capture).
export async function createFaceDetector(runningMode = 'VIDEO') {
  // Lazy-load mediapipe only when webcam is actually required
  const { FaceDetector, FilesetResolver } = await import('@mediapipe/tasks-vision');
  const vision = await FilesetResolver.forVisionTasks('/mediapipe/wasm');
  const options = (delegate) => ({
    baseOptions: { modelAssetPath: '/mediapipe/models/blaze_face_short_range.tflite', delegate },
    runningMode,
    minDetectionConfidence: 0.5,
  });
  try {
    return await FaceDetector.createFromOptions(vision, options('GPU'));
  } catch (_) {
    // No usable WebGL (VDI / remote desktop / software rendering) — run on CPU
    return await FaceDetector.createFromOptions(vision, options('CPU'));
  }
}

// videoEl is the mounted <video> element itself (useWebcamMonitor exposes it as
// state) — NOT a ref object. Its ref is a callback ref with no `.current`, which
// is what silently kept this detector from ever starting before.
export function useFaceDetector({ videoEl, config, reportViolation, enabled }) {
  // Latest config/reporter without re-creating the detector when they change identity
  const configRef = useRef(config);
  const reportRef = useRef(reportViolation);
  useEffect(() => { configRef.current = config; }, [config]);
  useEffect(() => { reportRef.current = reportViolation; }, [reportViolation]);

  useEffect(() => {
    if (!enabled || !videoEl) return;

    let cancelled = false;
    let detector = null;
    let intervalId = null;
    let lastTimestamp = 0;
    let detectFailed = false;
    const since = { absent: null, multi: null };
    const lastReported = { absent: 0, multi: 0 };

    // Reports once the condition has held for thresholdMs, then at most once
    // per cooldown for as long as it keeps holding.
    function track(key, active, thresholdMs, eventType, metadata) {
      const now = Date.now();
      if (!active) { since[key] = null; return; }
      if (since[key] == null) since[key] = now;
      if (now - since[key] < thresholdMs) return;
      if (now - lastReported[key] < Math.max(thresholdMs, REPEAT_COOLDOWN_MS)) return;
      lastReported[key] = now;
      reportRef.current?.('webcam_monitoring', eventType, metadata);
    }

    function detect() {
      if (cancelled || !detector) return;
      // No decoded frame yet (stream still starting) — nothing to judge
      if (videoEl.readyState < 2 || !videoEl.videoWidth) return;

      let faces;
      try {
        // detectForVideo requires strictly increasing timestamps
        const ts = Math.max(performance.now(), lastTimestamp + 1);
        lastTimestamp = ts;
        faces = detector.detectForVideo(videoEl, ts).detections.length;
      } catch (err) {
        // Typically: no WebGL at all (mediapipe needs it to read video frames
        // even on the CPU delegate). Log once — not a candidate violation.
        if (!detectFailed) {
          detectFailed = true;
          console.warn('[proctoring] face detection cannot read camera frames:', err?.message || err);
        }
        return;
      }

      const cfg = configRef.current || {};
      // A covered/blocked camera yields no face, so it is reported here too
      track('absent', faces === 0, (cfg.face_absent_warn_sec || 10) * 1000, 'FACE_NOT_DETECTED', {});
      track('multi', faces > 1, (cfg.multi_face_warn_sec || MULTI_FACE_WARN_SEC) * 1000, 'MULTIPLE_FACES_DETECTED', { count: faces });
    }

    createFaceDetector()
      .then((d) => {
        if (cancelled) { d.close?.(); return; }
        detector = d;
        intervalId = setInterval(detect, DETECT_INTERVAL_MS);
      })
      .catch((err) => {
        // Face detection unavailable — exam must still be takeable
        console.warn('[proctoring] face detection unavailable:', err?.message || err);
      });

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
      try { detector?.close?.(); } catch (_) {}
    };
  }, [enabled, videoEl]);
}
