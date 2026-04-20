import { useEffect, useRef } from 'react';

export function useFullscreenEnforcer({ config, reportViolation, enabled }) {
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;

    // Called when fullscreen exits: report violation and try to re-enter.
    // Initial fullscreen entry is handled by the FullscreenGate button click
    // (browsers block requestFullscreen outside a direct user gesture).
    const onExit = () => {
      if (!document.fullscreenElement) {
        reportViolation('fullscreen_enforce', 'FULLSCREEN_EXIT', {});
        document.documentElement.requestFullscreen().catch(() => {});
      }
    };

    document.addEventListener('fullscreenchange', onExit);

    const intervalMs = (config?.re_prompt_interval_sec || 30) * 1000;
    intervalRef.current = setInterval(() => {
      if (!document.fullscreenElement) onExit();
    }, intervalMs);

    return () => {
      document.removeEventListener('fullscreenchange', onExit);
      clearInterval(intervalRef.current);
    };
  }, [enabled, config, reportViolation]);
}
