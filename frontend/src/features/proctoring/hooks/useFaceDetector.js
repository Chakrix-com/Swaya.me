import { useEffect, useRef } from 'react';

export function useFaceDetector({ videoRef, config, reportViolation, enabled }) {
  const detectorRef = useRef(null);
  const faceAbsentSince = useRef(null);
  const gazeAwaySince = useRef(null);
  const animFrameRef = useRef(null);

  useEffect(() => {
    if (!enabled || !videoRef?.current) return;

    let cancelled = false;

    async function init() {
      try {
        // Lazy-load mediapipe only when webcam is actually required
        const { FaceDetector, FilesetResolver } = await import('@mediapipe/tasks-vision');
        const vision = await FilesetResolver.forVisionTasks(
          '/mediapipe/wasm'
        );
        detectorRef.current = await FaceDetector.createFromOptions(vision, {
          baseOptions: { 
            modelAssetPath: '/mediapipe/models/blaze_face_short_range.tflite', 
            delegate: 'GPU' 
          },
          runningMode: 'VIDEO',
          minDetectionConfidence: 0.5,
        });
        if (!cancelled) detect();
      } catch (_) {
        // Face detection unavailable — fail silently
      }
    }

    function detect() {
      if (cancelled || !detectorRef.current || !videoRef.current) return;

      try {
        const result = detectorRef.current.detectForVideo(videoRef.current, Date.now());
        const faceAbsentWarn = (config?.face_absent_warn_sec || 10) * 1000;
        const gazeAwayWarn = (config?.gaze_away_warn_sec || 5) * 1000;

        if (result.detections.length === 0) {
          if (!faceAbsentSince.current) faceAbsentSince.current = Date.now();
          else if (Date.now() - faceAbsentSince.current > faceAbsentWarn) {
            reportViolation('webcam_monitoring', 'FACE_NOT_DETECTED', {});
            faceAbsentSince.current = null;
          }
        } else {
          faceAbsentSince.current = null;
        }

        if (result.detections.length > 1) {
          reportViolation('webcam_monitoring', 'MULTIPLE_FACES_DETECTED', {
            count: result.detections.length,
          });
        }
      } catch (_) {}

      animFrameRef.current = requestAnimationFrame(detect);
    }

    init();

    return () => {
      cancelled = true;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [enabled, videoRef, config, reportViolation]);
}
