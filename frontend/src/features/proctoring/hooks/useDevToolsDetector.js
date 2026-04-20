import { useEffect } from 'react';

export function useDevToolsDetector({ config, reportViolation, enabled }) {
  useEffect(() => {
    if (!enabled) return;

    const threshold = config?.size_threshold_px || 160;

    const check = () => {
      if (
        window.outerWidth - window.innerWidth > threshold ||
        window.outerHeight - window.innerHeight > threshold
      ) {
        reportViolation('devtools_detect', 'DEVTOOLS_OPEN', {
          outerWidth: window.outerWidth,
          innerWidth: window.innerWidth,
          outerHeight: window.outerHeight,
          innerHeight: window.innerHeight,
        });
      }
    };

    const interval = setInterval(check, 1000);
    return () => clearInterval(interval);
  }, [enabled, config, reportViolation]);
}
