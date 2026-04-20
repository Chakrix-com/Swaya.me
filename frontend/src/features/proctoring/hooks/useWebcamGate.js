import { useState, useEffect } from 'react';

export function useWebcamGate({ onGranted, onDenied, enabled }) {
  const [status, setStatus] = useState('not_required');

  useEffect(() => {
    if (!enabled) return;
    setStatus('pending');

    navigator.mediaDevices
      .getUserMedia({ video: true, audio: false })
      .then((stream) => {
        setStatus('granted');
        onGranted(stream);
      })
      .catch(() => {
        setStatus('denied');
        onDenied();
      });
  }, [enabled]);

  return status;
}
