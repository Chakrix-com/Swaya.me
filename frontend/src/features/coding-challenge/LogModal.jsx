import SafeModal from '../../components/SafeModal'

// Lightweight, dependency-free line coloring — good enough for pytest output
// and `git log -p` diffs without pulling in a full syntax-highlighter lib for
// two log types.
function testLineStyle(line) {
  if (/\b(FAIL(ED)?|ERROR)\b/i.test(line)) return { color: 'var(--sw-error, #ef4444)' }
  if (/\b(PASS(ED)?|ok)\b/.test(line) || /^\.+$/.test(line.trim())) return { color: 'var(--sw-success, #22c55e)' }
  return undefined
}

function diffLineStyle(line) {
  if (/^\+(?!\+\+)/.test(line)) return { color: 'var(--sw-success, #22c55e)', background: 'color-mix(in srgb, var(--sw-success, #22c55e) 8%, transparent)' }
  if (/^-(?!--)/.test(line)) return { color: 'var(--sw-error, #ef4444)', background: 'color-mix(in srgb, var(--sw-error, #ef4444) 8%, transparent)' }
  if (/^@@/.test(line)) return { color: 'var(--sw-info, #3b82f6)' }
  if (/^(commit |Author:|Date:)/.test(line)) return { fontWeight: 700 }
  return undefined
}

const STYLERS = { test: testLineStyle, diff: diffLineStyle, plain: () => undefined }

export default function LogModal({ open, onClose, title, content, variant = 'plain' }) {
  const styler = STYLERS[variant] || STYLERS.plain
  const lines = (content || '').split('\n')

  return (
    <SafeModal title={title} open={open} onCancel={onClose} width={760} footer={null}>
      <div
        style={{
          fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6,
          whiteSpace: 'pre-wrap', wordBreak: 'break-all',
          maxHeight: '65vh', overflowY: 'auto',
          background: 'var(--sw-surface, #fafafa)', border: '1px solid var(--sw-border, #e5e7eb)',
          borderRadius: 8, padding: 12,
        }}
      >
        {lines.map((line, i) => (
          <div key={i} style={styler(line)}>{line || ' '}</div>
        ))}
      </div>
    </SafeModal>
  )
}
