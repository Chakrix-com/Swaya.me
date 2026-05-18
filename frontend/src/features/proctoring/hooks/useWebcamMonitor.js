import { useEffect, useRef, useCallback, useState } from 'react';
import api from '../../../services/api';

export function useWebcamMonitor({ stream, config, reportViolation, enabled, sessionToken, examDurationSeconds, captureRef }) {
  // videoNodeRef: stable ref for captureNow (called outside effects)
  // videoEl: state copy so effects re-run when the element mounts
  const videoNodeRef = useRef(null);
  const [videoEl, setVideoEl] = useState(null);
  const timeoutsRef = useRef([]);

  // Callback ref — React calls this when the <video> element mounts/unmounts,
  // updating videoEl state so the stream-setup effect re-runs at the right time.
  const videoRef = useCallback((node) => {
    videoNodeRef.current = node;
    setVideoEl(node);
  }, []);

  const captureNow = useCallback(() => {
    if (!videoNodeRef.current) return;
    try {
      const canvas = document.createElement('canvas');
      canvas.width = 320;
      canvas.height = 240;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoNodeRef.current, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (!blob) return;
        const form = new FormData();
        form.append('file', blob, `snap_${Date.now()}.jpg`);
        api.post('/proctoring/snapshot', form, {
          headers: {
            'Content-Type': 'multipart/form-data',
            ...(sessionToken ? { 'X-Session-Token': sessionToken } : {}),
          },
        }).catch(() => {});
      }, 'image/jpeg', 0.7);
    } catch (_) {}
  }, [sessionToken]);

  // Expose captureNow only when webcam is active
  useEffect(() => {
    if (captureRef) captureRef.current = enabled ? captureNow : null;
  }, [captureNow, captureRef, enabled]);

  // Stream setup — depends on videoEl so it re-runs when the element mounts.
  // This handles the case where stream is available before the video element
  // is in the DOM (e.g. while FullscreenGate or identity capture is showing).
  useEffect(() => {
    if (!enabled || !stream || !videoEl) return;

    videoEl.srcObject = stream;
    videoEl.play().catch(() => {});

    const track = stream.getVideoTracks()[0];
    if (track) {
      track.addEventListener('ended', () => {
        reportViolation('webcam_monitoring', 'WEBCAM_STREAM_ENDED', {});
      });
    }

    const snapshotMin = config?.snapshot_min ?? 10;
    const snapshotMax = config?.snapshot_max ?? 15;
    const count = snapshotMin + Math.floor(Math.random() * (snapshotMax - snapshotMin + 1));
    const middleCount = Math.max(0, count - 2);

    timeoutsRef.current.push(setTimeout(captureNow, 30 * 1000));

    const duration = (examDurationSeconds || 3600);
    const windowStart = 60 * 1000;
    const windowEnd = Math.max(windowStart + 1000, (duration - 60) * 1000);

    const randomDelays = Array.from({ length: middleCount }, () =>
      windowStart + Math.random() * (windowEnd - windowStart)
    ).sort((a, b) => a - b);

    for (const delay of randomDelays) {
      timeoutsRef.current.push(setTimeout(captureNow, delay));
    }

    return () => {
      timeoutsRef.current.forEach(clearTimeout);
      timeoutsRef.current = [];
      stream.getTracks().forEach((t) => t.stop());
    };
  }, [enabled, stream, videoEl, config, reportViolation, examDurationSeconds, captureNow]);

  return videoRef;
}
