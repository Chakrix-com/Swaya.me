import { useEffect, useRef } from 'react';
import api from '../../../services/api';

export function useBehavioralCollector({ sessionToken, config, enabled }) {
  const buffer = useRef({
    mouse: [],
    keys: [],
    scrolls: [],
    backspaces: 0,
    firstInteraction: null,
  });

  useEffect(() => {
    if (!enabled || !sessionToken) return;

    const batchInterval = (config?.batch_interval_sec || 10) * 1000;

    const onMouseMove = (e) => {
      buffer.current.mouse.push({ x: e.clientX, y: e.clientY, t: Date.now() });
      if (buffer.current.mouse.length > 200) buffer.current.mouse.splice(0, 100);
    };

    const onKeyDown = (e) => {
      if (!buffer.current.firstInteraction) buffer.current.firstInteraction = Date.now();
      if (e.key === 'Backspace') buffer.current.backspaces++;
      buffer.current.keys.push(Date.now());
    };

    const onScroll = () => buffer.current.scrolls.push(Date.now());

    document.addEventListener('mousemove', onMouseMove, { passive: true });
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('scroll', onScroll, { passive: true });

    const flush = setInterval(async () => {
      const b = buffer.current;
      if (b.keys.length === 0 && b.mouse.length === 0) return;

      const intervals = b.keys.slice(1).map((t, i) => t - b.keys[i]);
      const sample = {
        session_token: sessionToken,
        mouse_path: b.mouse.slice(-50),
        keystroke_intervals: intervals,
        backspace_count: b.backspaces,
        scroll_events: b.scrolls.slice(-20).map((t) => ({ t })),
        time_to_first_interaction_ms: b.firstInteraction
          ? b.firstInteraction - (b.keys[0] || Date.now())
          : 0,
      };

      buffer.current = { mouse: [], keys: [], scrolls: [], backspaces: 0, firstInteraction: null };

      try {
        await api.post('/proctoring/biometrics', sample);
      } catch (_) {}
    }, batchInterval);

    return () => {
      clearInterval(flush);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('scroll', onScroll);
    };
  }, [enabled, sessionToken, config]);
}
