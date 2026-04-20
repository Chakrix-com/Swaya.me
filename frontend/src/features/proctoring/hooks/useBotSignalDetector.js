import { useEffect, useRef } from 'react';

let mouseEventCount = 0;
if (typeof window !== 'undefined') {
  document.addEventListener('mousemove', () => mouseEventCount++, { once: false, passive: true });
}

function checkTimingConsistency() {
  const samples = [];
  const start = performance.now();
  for (let i = 0; i < 5; i++) {
    samples.push(performance.now() - start);
  }
  const variance = samples.reduce((acc, v, i, a) => {
    const mean = a.reduce((s, x) => s + x, 0) / a.length;
    return acc + Math.pow(v - mean, 2);
  }, 0) / samples.length;
  return variance < 0.001;
}

// Antigravity and similar extensions patch Function.prototype.toString to hide
// their wrapping — calling fn.toString() on a wrapped function still returns
// '[native code]'. We defeat this by using a freshly-created iframe's
// Function.prototype.toString, which the extension has NOT patched.
let _iframeToString = null;
function getIframeToString() {
  if (_iframeToString) return _iframeToString;
  try {
    const iframe = document.createElement('iframe');
    iframe.style.cssText = 'display:none;width:0;height:0;position:absolute';
    document.body.appendChild(iframe);
    _iframeToString = iframe.contentWindow.Function.prototype.toString;
    document.body.removeChild(iframe);
  } catch { _iframeToString = null; }
  return _iframeToString;
}

// Returns true if fn is genuinely native, using iframe's unpolluted toString
// so Antigravity's toString-spoofing doesn't fool us.
function isNativeFn(fn) {
  try {
    const iframeStr = getIframeToString();
    const str = iframeStr ? iframeStr.call(fn) : fn.toString();
    return str.includes('[native code]');
  } catch { return false; }
}

/**
 * Detects browser extensions that tamper with DOM APIs to bypass proctoring.
 * Antigravity and similar extensions inject at document_start (before page JS)
 * and patch Function.prototype.toString to hide their wrapping. We use an
 * iframe's unpolluted toString reference to see through that disguise.
 */
function detectExtensionTampering() {
  const signals = {};

  // 1. addEventListener wrapping — Antigravity's core technique: it wraps
  //    addEventListener to intercept visibilitychange/blur before page handlers.
  if (!isNativeFn(EventTarget.prototype.addEventListener))
    signals.addEventListener_wrapped = true;
  if (!isNativeFn(EventTarget.prototype.dispatchEvent))
    signals.dispatchEvent_wrapped = true;
  if (!isNativeFn(EventTarget.prototype.removeEventListener))
    signals.removeEventListener_wrapped = true;

  // 2. document.hidden getter override — always returns false so the page
  //    never sees the tab as backgrounded.
  try {
    const desc = Object.getOwnPropertyDescriptor(Document.prototype, 'hidden')
               || Object.getOwnPropertyDescriptor(document, 'hidden');
    if (!desc || !desc.get || !isNativeFn(desc.get))
      signals.hidden_getter_replaced = true;
  } catch { signals.hidden_getter_error = true; }

  // 3. visibilityState getter override.
  try {
    const desc = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState')
               || Object.getOwnPropertyDescriptor(document, 'visibilityState');
    if (!desc || !desc.get || !isNativeFn(desc.get))
      signals.visibilityState_getter_replaced = true;
  } catch {}

  // 4. hasFocus override — always returns true.
  if (!isNativeFn(Document.prototype.hasFocus))
    signals.hasFocus_wrapped = true;

  // 5. window.blur suppression.
  try {
    if (!isNativeFn(window.blur))
      signals.window_blur_wrapped = true;
  } catch {}

  // 6. Object.defineProperty tampering.
  try {
    if (!isNativeFn(Object.defineProperty))
      signals.defineProperty_wrapped = true;
  } catch {}

  // 7. Function.prototype.toString itself patched — if the extension didn't
  //    bother protecting its iframe context, this catches it directly.
  try {
    if (!isNativeFn(Function.prototype.toString))
      signals.toString_patched = true;
  } catch {}

  // 8. requestFullscreen wrapping — some extensions intercept this to
  //    silently reject or ignore fullscreen requests.
  try {
    if (!isNativeFn(Element.prototype.requestFullscreen))
      signals.requestFullscreen_wrapped = true;
  } catch {}

  // 8. Synthetic visibilitychange suppression: dispatch the event ourselves
  //    and verify our handler fires. Extensions that silently drop handlers
  //    will fail this test (received stays false).
  //    This is a high-confidence standalone signal — threshold is 1 for it.
  try {
    let received = false;
    const handler = () => { received = true; };
    document.addEventListener('visibilitychange', handler, { once: true });
    document.dispatchEvent(new Event('visibilitychange'));
    document.removeEventListener('visibilitychange', handler);
    if (!received)
      signals.visibilitychange_suppressed = true;
  } catch {}

  return signals;
}

// These signals alone are strong enough to trigger a lock without needing
// a second corroborating signal.
const HIGH_CONFIDENCE_SIGNALS = new Set([
  'visibilitychange_suppressed',
  'addEventListener_wrapped',
  'hidden_getter_replaced',
  'visibilityState_getter_replaced',
  'requestFullscreen_wrapped',
]);

export function useBotSignalDetector({ reportViolation, enabled }) {
  const reportedExtensionRef = useRef(false);
  const windowFocusedRef = useRef(true);

  // ── Static check on mount ─────────────────────────────────────────────────
  useEffect(() => {
    if (!enabled) return;

    const timer = setTimeout(() => {
      // Original bot signals
      const botSignals = {
        webdriver: navigator.webdriver === true,
        cdpAttached: !!(window.__cdc_adoQpoasnfa76pfcZLmcfl_Symbol || window.__selenium_unwrapped),
        noPlugins: navigator.plugins && navigator.plugins.length === 0,
        timingTooClean: checkTimingConsistency(),
        noMouseHistory: mouseEventCount === 0,
      };

      const botDetected = Object.values(botSignals).filter(Boolean).length;
      const botConfidence = botDetected / Object.keys(botSignals).length;

      if (botConfidence >= 0.6) {
        reportViolation('bot_signal_detect', 'BOT_SIGNAL_DETECTED', { ...botSignals, source: 'automation' });
        return;
      }

      // Extension tampering check
      const extSignals = detectExtensionTampering();
      const extKeys = Object.keys(extSignals);
      const hasHighConfidence = extKeys.some((k) => HIGH_CONFIDENCE_SIGNALS.has(k));
      // Fire on any single high-confidence signal OR on 2+ lower-confidence ones.
      if (hasHighConfidence || extKeys.length >= 2) {
        reportViolation('bot_signal_detect', 'BOT_SIGNAL_DETECTED', { ...extSignals, source: 'extension' });
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [enabled, reportViolation]);

  // ── Dynamic: blur ↔ document.hidden mismatch check ───────────────────────
  // If the window loses focus but document.hidden stays false, an extension is
  // overriding the hidden property to prevent tab-switch detection.
  useEffect(() => {
    if (!enabled) return;

    const onBlur = () => {
      windowFocusedRef.current = false;
      // Give extension 150ms to intercept, then check if it lied
      setTimeout(() => {
        if (reportedExtensionRef.current) return;
        if (document.hidden === false && document.hasFocus() === true) {
          reportedExtensionRef.current = true;
          reportViolation('bot_signal_detect', 'BOT_SIGNAL_DETECTED', {
            source: 'extension',
            signal: 'focus_lie',
            hidden: document.hidden,
            hasFocus: document.hasFocus(),
          });
        }
      }, 150);
    };

    const onFocus = () => { windowFocusedRef.current = true; };

    window.addEventListener('blur', onBlur);
    window.addEventListener('focus', onFocus);
    return () => {
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
    };
  }, [enabled, reportViolation]);

  // ── Periodic mismatch poll (catches extensions that suppress blur entirely) ─
  useEffect(() => {
    if (!enabled) return;

    const poll = setInterval(() => {
      if (reportedExtensionRef.current) return;
      // If we think the window is not focused but document says it is → lie
      if (!windowFocusedRef.current && document.hidden === false) {
        reportedExtensionRef.current = true;
        reportViolation('bot_signal_detect', 'BOT_SIGNAL_DETECTED', {
          source: 'extension',
          signal: 'hidden_lie_poll',
          hidden: document.hidden,
        });
      }
    }, 2000);

    return () => clearInterval(poll);
  }, [enabled, reportViolation]);
}
