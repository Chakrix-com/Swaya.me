import { useEffect, useRef } from 'react';
import api from '../../../services/api';

export function useWebcamMonitor({ stream, config, reportViolation, enabled, sessionToken }) {
  const videoRef = useRef(null);
  const snapshotIntervalRef = useRef(null);

  useEffect(() => {
    if (!enabled || !stream || !videoRef.current) return;

    videoRef.current.srcObject = stream;
    videoRef.current.play().catch(() => {});

    const track = stream.getVideoTracks()[0];
    if (track) {
      track.addEventListener('ended', () => {
        reportViolation('webcam_monitoring', 'WEBCAM_STREAM_ENDED', {});
      });
    }

    const interval = (config?.snapshot_interval_sec || 30) * 1000;

    snapshotIntervalRef.current = setInterval(() => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = 320;
        canvas.height = 240;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
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
    }, interval);

    return () => {
      clearInterval(snapshotIntervalRef.current);
      stream.getTracks().forEach((t) => t.stop());
    };
  }, [enabled, stream, config, reportViolation]);

  return videoRef;
}
