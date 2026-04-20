import { useEffect, useRef } from 'react';

const TAB_ID = Math.random().toString(36).slice(2);

export function useMultiTabDetector({ reportViolation, enabled }) {
  const channelRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;

    try {
      const channel = new BroadcastChannel('proctor_tabs');
      channelRef.current = channel;

      channel.onmessage = (e) => {
        if (e.data?.type === 'TAB_OPEN' && e.data?.tabId !== TAB_ID) {
          reportViolation('multi_tab_detect', 'MULTI_TAB_DETECTED', { otherTab: e.data.tabId });
        }
      };

      channel.postMessage({ type: 'TAB_OPEN', tabId: TAB_ID });

      return () => {
        channel.postMessage({ type: 'TAB_CLOSE', tabId: TAB_ID });
        channel.close();
      };
    } catch (_) {
      // BroadcastChannel not supported
    }
  }, [enabled, reportViolation]);
}
