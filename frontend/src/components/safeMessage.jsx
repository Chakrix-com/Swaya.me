import { useSyncExternalStore } from 'react';
import { createPortal } from 'react-dom';
import { theme } from 'antd';
import {
  CheckCircleFilled,
  CloseCircleFilled,
  ExclamationCircleFilled,
  InfoCircleFilled,
  LoadingOutlined,
} from '@ant-design/icons';

// Drop-in for antd's `message` (static import or App.useApp()).
//
// antd's toasts close via rc-notification: the auto-close timer pauses while
// the pointer is over a toast, and the element is only removed when its leave
// animation fires `animationend`. On the user's VDI those pointer/animation
// events are unreliable, so toasts piled up and never went away. Here each
// toast is removed by a plain timer — no hover pause, no animation callback.

const DEFAULT_DURATION = 3;
const MAX_VISIBLE = 3;

let toasts = [];
let seq = 0;
const listeners = new Set();
const timers = new Map();

function emit() {
  listeners.forEach((l) => l());
}

function remove(key) {
  clearTimeout(timers.get(key));
  timers.delete(key);
  const before = toasts.length;
  toasts = toasts.filter((x) => x.key !== key);
  if (toasts.length !== before) emit();
}

function open(type, args, durationArg, onCloseArg) {
  const cfg = args && typeof args === 'object' && 'content' in args
    ? args
    : { content: args, duration: durationArg, onClose: onCloseArg };
  const toastType = cfg.type || type;
  // The same text already on screen (e.g. Save clicked 3 times) reuses that
  // toast and restarts its timer instead of stacking identical copies.
  const duplicate = cfg.key == null && typeof cfg.content === 'string'
    ? toasts.find((x) => x.type === toastType && x.content === cfg.content)
    : null;
  const key = cfg.key ?? duplicate?.key ?? `sw-msg-${++seq}`;
  const duration = cfg.duration ?? DEFAULT_DURATION;

  clearTimeout(timers.get(key));
  const toast = { key, type: toastType, content: cfg.content };
  const existing = toasts.findIndex((x) => x.key === key);
  toasts = existing >= 0
    ? toasts.map((x, i) => (i === existing ? toast : x))
    : [...toasts, toast].slice(-MAX_VISIBLE);
  emit();

  let resolveClosed;
  const closed = new Promise((r) => { resolveClosed = r; });
  const close = () => {
    remove(key);
    cfg.onClose?.();
    resolveClosed(true);
  };
  // duration 0 = stays until closed explicitly (same as antd)
  if (duration > 0) timers.set(key, setTimeout(close, duration * 1000));

  // antd returns a callable that is also thenable
  close.then = (onFulfilled, onRejected) => closed.then(onFulfilled, onRejected);
  return close;
}

export const message = {
  open: (cfg) => open(cfg?.type || 'info', cfg),
  success: (c, d, onClose) => open('success', c, d, onClose),
  error: (c, d, onClose) => open('error', c, d, onClose),
  info: (c, d, onClose) => open('info', c, d, onClose),
  warning: (c, d, onClose) => open('warning', c, d, onClose),
  warn: (c, d, onClose) => open('warning', c, d, onClose),
  loading: (c, d, onClose) => open('loading', c, d ?? 0, onClose),
  destroy: (key) => {
    if (key !== undefined) { remove(key); return; }
    timers.forEach((t) => clearTimeout(t));
    timers.clear();
    toasts = [];
    emit();
  },
};

function subscribe(l) {
  listeners.add(l);
  return () => listeners.delete(l);
}

const getSnapshot = () => toasts;

export function SafeMessageHost() {
  const items = useSyncExternalStore(subscribe, getSnapshot);
  const { token } = theme.useToken();
  if (items.length === 0) return null;

  const icons = {
    success: <CheckCircleFilled style={{ color: token.colorSuccess }} />,
    error: <CloseCircleFilled style={{ color: token.colorError }} />,
    warning: <ExclamationCircleFilled style={{ color: token.colorWarning }} />,
    info: <InfoCircleFilled style={{ color: token.colorInfo }} />,
    loading: <LoadingOutlined style={{ color: token.colorPrimary }} />,
  };

  return createPortal(
    <div
      className="sw-message-host"
      style={{
        position: 'fixed',
        top: 8,
        left: 0,
        right: 0,
        zIndex: 2010,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 8,
        pointerEvents: 'none',
        padding: '0 16px',
      }}
    >
      {items.map((m) => (
        <div
          key={m.key}
          role={m.type === 'error' ? 'alert' : 'status'}
          className={`sw-message sw-message-${m.type}`}
          // Clicking a toast dismisses it — a manual escape hatch if a timer is ever missed
          onClick={() => remove(m.key)}
          style={{
            pointerEvents: 'auto',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            maxWidth: '100%',
            padding: '9px 12px',
            background: token.colorBgElevated,
            color: token.colorText,
            fontSize: token.fontSize,
            borderRadius: token.borderRadiusLG,
            boxShadow: token.boxShadow,
          }}
        >
          {icons[m.type] || icons.info}
          <span>{m.content}</span>
        </div>
      ))}
    </div>,
    document.body,
  );
}
