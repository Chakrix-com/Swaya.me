import { useEffect } from 'react';

export function useRightClickBlocker({ reportViolation, enabled }) {
  useEffect(() => {
    if (!enabled) return;

    const block = (e) => {
      e.preventDefault();
      reportViolation('right_click_block', 'RIGHT_CLICK_ATTEMPT', {});
    };

    document.addEventListener('contextmenu', block);
    return () => document.removeEventListener('contextmenu', block);
  }, [enabled, reportViolation]);
}
