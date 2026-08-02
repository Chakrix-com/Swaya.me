import { useRef, useState } from 'react'
import { theme } from 'antd'
import { CloseOutlined } from '@ant-design/icons'
import './EmailChipInput.css'

// Gmail "To" field pattern: type an email, commit it as a chip on Enter/Tab/
// comma/semicolon, or paste a comma/semicolon/newline-separated block and it
// splits into multiple chips at once. Each chip validates independently and
// stays editable-by-removal even if invalid, rather than being silently
// dropped, so the host can see exactly what needs fixing.
//
// Built from scratch rather than antd's Select mode="tags" — same
// @rc-component/trigger click-race issue flagged for Dropdown/Select
// elsewhere in this app (see CLAUDE.md), and mirrors the plain-controlled-
// input + manual chip rendering approach already established in
// SafeMultiSelect.jsx (no portal, no document mousedown listener).

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function isValidEmail(email) {
  return EMAIL_RE.test(email.trim())
}

function EmailChipInput({ value = [], onChange, placeholder, disabled, autoFocus, maxItems }) {
  const { token } = theme.useToken()
  const [draft, setDraft] = useState('')
  const [flashIndex, setFlashIndex] = useState(null)
  const inputRef = useRef(null)

  const flash = (idx) => {
    setFlashIndex(idx)
    setTimeout(() => setFlashIndex((cur) => (cur === idx ? null : cur)), 450)
  }

  const addEmails = (rawTokens) => {
    let next = value
    for (const raw of rawTokens) {
      const email = raw.trim()
      if (!email) continue
      const dupIdx = next.findIndex((e) => e.toLowerCase() === email.toLowerCase())
      if (dupIdx !== -1) {
        flash(dupIdx)
        continue
      }
      if (maxItems && next.length >= maxItems) break
      next = [...next, email]
    }
    if (next !== value) onChange(next)
  }

  const commitDraft = () => {
    if (!draft.trim()) return
    addEmails([draft])
    setDraft('')
  }

  const handleKeyDown = (e) => {
    if (['Enter', 'Tab', ',', ';'].includes(e.key)) {
      if (draft.trim()) {
        e.preventDefault()
        commitDraft()
      }
    } else if (e.key === 'Backspace' && !draft && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  const handlePaste = (e) => {
    const text = e.clipboardData.getData('text')
    if (!/[,;\n]/.test(text)) return // single token — let it land in the input normally
    e.preventDefault()
    addEmails(text.split(/[,;\n]+/))
  }

  const removeAt = (idx) => onChange(value.filter((_, i) => i !== idx))

  return (
    <div
      onClick={() => inputRef.current?.focus()}
      style={{
        display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 6,
        minHeight: 40, boxSizing: 'border-box', width: '100%',
        border: `1px solid ${token.colorBorder}`,
        borderRadius: token.borderRadius,
        padding: '6px 8px', cursor: disabled ? 'not-allowed' : 'text',
        background: disabled ? token.colorBgContainerDisabled : token.colorBgContainer,
      }}
    >
      {value.map((email, idx) => {
        const valid = isValidEmail(email)
        return (
          <span
            key={`${email}-${idx}`}
            className={`sw-email-chip${valid ? '' : ' sw-email-chip--invalid'}${flashIndex === idx ? ' sw-email-chip--flash' : ''}`}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              background: valid ? token.colorFillSecondary : 'color-mix(in srgb, var(--sw-error, #d32f2f) 12%, transparent)',
              border: valid ? 'none' : '1px solid color-mix(in srgb, var(--sw-error, #d32f2f) 45%, transparent)',
              borderRadius: token.borderRadiusSM,
              padding: '2px 6px 2px 8px', fontSize: 12, lineHeight: '20px',
              color: valid ? token.colorText : 'var(--sw-error, #d32f2f)',
            }}
            title={valid ? undefined : 'Not a valid email address'}
          >
            {email}
            <CloseOutlined
              style={{ fontSize: 9, cursor: 'pointer' }}
              onClick={(e) => { e.stopPropagation(); removeAt(idx) }}
            />
          </span>
        )
      })}
      <input
        ref={inputRef}
        value={draft}
        disabled={disabled}
        autoFocus={autoFocus}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onBlur={commitDraft}
        placeholder={value.length === 0 ? placeholder : ''}
        style={{
          flex: 1, minWidth: 140, border: 'none', outline: 'none',
          fontSize: 13, background: 'transparent', color: token.colorText,
        }}
      />
    </div>
  )
}

export default EmailChipInput
