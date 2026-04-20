import { useEffect } from 'react';

export function useCopyPasteBlocker({ reportViolation, enabled }) {
  useEffect(() => {
    if (!enabled) return;

    const block = (e) => {
      e.preventDefault();
      const type = e.type === 'paste' ? 'PASTE_ATTEMPT' : 'COPY_ATTEMPT';
      reportViolation('copy_paste_block', type, {});
    };

    document.addEventListener('copy', block);
    document.addEventListener('cut', block);
    document.addEventListener('paste', block);

    return () => {
      document.removeEventListener('copy', block);
      document.removeEventListener('cut', block);
      document.removeEventListener('paste', block);
    };
  }, [enabled, reportViolation]);
}
