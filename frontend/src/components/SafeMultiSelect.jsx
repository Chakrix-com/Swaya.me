import { useEffect, useMemo, useRef, useState } from 'react'
import { theme } from 'antd'
import { CloseOutlined, SearchOutlined } from '@ant-design/icons'

// Deliberately not using antd's Select here — same click-race bug as
// Dropdown (both share @rc-component/trigger's mousedown/pointerdown
// coordination). This does NOT use a raw document.addEventListener
// ('mousedown', ...) listener for outside-click-to-close either — that
// depends on a real mousedown/mouseup/click sequence arriving in the
// expected order, which is fragile over remote-desktop input redirection
// (and untestable via a JS-level .click(), which never fires mousedown at
// all). Instead an invisible full-viewport div renders behind the dropdown
// panel and closes it via a plain React onClick, the same synchronous
// synthetic-click mechanism every other button in this app already uses.
// Not portaled — kept as a normal nested child so it stays in the same
// stacking context as an ancestor Modal, rather than a document.body portal
// potentially painting above the Modal's own mask.
function SafeMultiSelect({ value = [], onChange, options = [], placeholder, notFoundContent, style }) {
  const { token } = theme.useToken()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const inputRef = useRef(null)

  const close = () => { setOpen(false); setQuery('') }

  useEffect(() => {
    if (!open) return
    const onEscape = (e) => { if (e.key === 'Escape') close() }
    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [open])

  const selectedOptions = useMemo(
    () => value.map((v) => options.find((o) => o.value === v)).filter(Boolean),
    [value, options]
  )

  const filteredOptions = useMemo(() => {
    if (!query.trim()) return options
    const q = query.trim().toLowerCase()
    return options.filter((o) => String(o.label).toLowerCase().includes(q))
  }, [query, options])

  const toggleValue = (v) => {
    if (value.includes(v)) {
      onChange(value.filter((x) => x !== v))
    } else {
      onChange([...value, v])
    }
  }

  const removeValue = (e, v) => {
    e.stopPropagation()
    onChange(value.filter((x) => x !== v))
  }

  return (
    <span style={{ position: 'relative', display: 'inline-block', width: '100%', ...style }}>
      <div
        onClick={() => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 0) }}
        style={{
          display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 4,
          minHeight: 32, boxSizing: 'border-box', width: '100%',
          border: `1px solid ${open ? token.colorPrimary : token.colorBorder}`,
          borderRadius: token.borderRadius,
          padding: '3px 8px', cursor: 'text', background: token.colorBgContainer,
        }}
      >
        {selectedOptions.map((o) => (
          <span
            key={o.value}
            className="sw-multiselect-chip"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              background: token.colorFillSecondary, borderRadius: token.borderRadiusSM,
              padding: '1px 6px', fontSize: 12, lineHeight: '18px', color: token.colorText,
            }}
          >
            {o.label}
            <CloseOutlined className="sw-multiselect-chip-remove" style={{ fontSize: 9, cursor: 'pointer' }} onClick={(e) => removeValue(e, o.value)} />
          </span>
        ))}
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          placeholder={selectedOptions.length === 0 ? placeholder : ''}
          style={{
            flex: 1, minWidth: 60, border: 'none', outline: 'none',
            fontSize: 13, background: 'transparent', color: token.colorText,
          }}
        />
      </div>
      {open && (
        <>
          <div onClick={close} style={{ position: 'fixed', inset: 0, zIndex: 1049 }} />
          <div
            className="sw-multiselect-panel"
            style={{
              position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
              maxHeight: 220, overflowY: 'auto', boxSizing: 'border-box',
              background: token.colorBgElevated,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: token.borderRadiusLG,
              boxShadow: token.boxShadowSecondary,
              padding: 4, zIndex: 1050,
            }}
          >
          {filteredOptions.length === 0 ? (
            <div style={{ padding: '8px 12px', fontSize: 13, color: token.colorTextTertiary, display: 'flex', alignItems: 'center', gap: 6 }}>
              <SearchOutlined style={{ fontSize: 12 }} />
              {notFoundContent}
            </div>
          ) : (
            filteredOptions.map((o) => {
              const checked = value.includes(o.value)
              return (
                <div
                  key={o.value}
                  onClick={() => toggleValue(o.value)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    boxSizing: 'border-box', height: 30, padding: '0 10px',
                    borderRadius: token.borderRadiusSM, cursor: 'pointer',
                    fontSize: 13, lineHeight: '30px', color: token.colorText,
                    background: checked ? token.controlItemBgActive : 'transparent',
                  }}
                  onMouseEnter={(e) => { if (!checked) e.currentTarget.style.background = token.controlItemBgHover }}
                  onMouseLeave={(e) => { if (!checked) e.currentTarget.style.background = 'transparent' }}
                >
                  <input type="checkbox" checked={checked} readOnly style={{ pointerEvents: 'none' }} />
                  <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{o.label}</span>
                </div>
              )
            })
          )}
          </div>
        </>
      )}
    </span>
  )
}

export default SafeMultiSelect
