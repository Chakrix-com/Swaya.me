import { useEffect } from 'react';

export function useTabSwitchDetector({ config, reportViolation, enabled }) {
  useEffect(() => {
    if (!enabled) return;

    const handleVisibility = () => {
      if (document.hidden) {
        reportViolation('tab_switch_detect', 'TAB_SWITCH', {});
      }
    };

    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [enabled, reportViolation]);
}
