import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { theme } from 'antd'
import { CloseCircleFilled, DownOutlined } from '@ant-design/icons'

// Deliberately not using antd's TreeSelect here — same click-race bug as
// Dropdown/Select (all share @rc-component/trigger's mousedown/pointerdown
// coordination). This does NOT use a raw document.addEventListener
// ('mousedown', ...) listener for outside-click-to-close either — that
// depends on a real mousedown/mouseup/click sequence arriving in the
// expected order, which is fragile over remote-desktop input redirection
// (and untestable via a JS-level .click(), which never fires mousedown at
// all). Instead an invisible full-viewport div renders behind the dropdown
// panel and closes it via a plain React onClick, the same synchronous
// synthetic-click mechanism every other button in this app already uses.
//
// Portaled to document.body with fixed positioning (getBoundingClientRect
// off the trigger, same pattern as MoreActionsMenu) rather than a nested
// absolute child — this is used inside SafeModal, and a nested child gets
// clipped by the modal body's `overflow-y: auto` once the option list is
// taller than the space left in the modal (bug: list appeared to "hide" once
// there were more than a couple of folders). Portal z-index must clear
// SafeModal's mask/panel (2000/2001).
function flatten(nodes, depth = 0, out = []) {
  for (const n of nodes) {
    out.push({ value: n.value, title: n.title, depth })
    if (n.children?.length) flatten(n.children, depth + 1, out)
  }
  return out
}

const PANEL_MAX_HEIGHT = 260

function SafeTreeSelect({ value, onChange, treeData = [], placeholder, allowClear = true, style }) {
  const { token } = theme.useToken()
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0 })
  const triggerRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const onEscape = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [open])

  const flatOptions = useMemo(() => flatten(treeData), [treeData])
  const selected = flatOptions.find((o) => o.value === value)

  const handleToggle = () => {
    if (open) { setOpen(false); return }
    const rect = triggerRef.current.getBoundingClientRect()
    const margin = 8
    let top = rect.bottom + 4
    if (top + PANEL_MAX_HEIGHT > window.innerHeight - margin) {
      top = Math.max(margin, rect.top - PANEL_MAX_HEIGHT - 4)
    }
    setPos({ top, left: rect.left, width: rect.width })
    setOpen(true)
  }

  const handleSelect = (v) => {
    onChange(v)
    setOpen(false)
  }

  const handleClear = (e) => {
    e.stopPropagation()
    onChange(undefined)
  }

  return (
    <span ref={triggerRef} style={{ position: 'relative', display: 'inline-block', width: '100%', ...style }}>
      <div
        onClick={handleToggle}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          minHeight: 32, boxSizing: 'border-box', width: '100%',
          border: `1px solid ${open ? token.colorPrimary : token.colorBorder}`,
          borderRadius: token.borderRadius,
          padding: '0 11px', cursor: 'pointer', background: token.colorBgContainer,
        }}
      >
        <span style={{ flex: 1, fontSize: 13, color: selected ? token.colorText : token.colorTextPlaceholder, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {selected ? selected.title : placeholder}
        </span>
        {allowClear && value !== undefined && value !== null && (
          <CloseCircleFilled style={{ fontSize: 12, color: token.colorTextQuaternary, cursor: 'pointer' }} onClick={handleClear} />
        )}
        <DownOutlined style={{ fontSize: 10, color: token.colorTextQuaternary }} />
      </div>
      {open && createPortal(
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 2009 }} />
          <div
            style={{
              position: 'fixed', top: pos.top, left: pos.left, width: pos.width,
              maxHeight: PANEL_MAX_HEIGHT, overflowY: 'auto', boxSizing: 'border-box',
              background: token.colorBgElevated,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: token.borderRadiusLG,
              boxShadow: token.boxShadowSecondary,
              padding: 4, zIndex: 2010,
            }}
          >
            {flatOptions.length === 0 ? (
              <div style={{ padding: '8px 12px', fontSize: 13, color: token.colorTextTertiary }}>—</div>
            ) : (
              flatOptions.map((o) => {
                const checked = o.value === value
                return (
                  <div
                    key={o.value}
                    onClick={() => handleSelect(o.value)}
                    style={{
                      display: 'flex', alignItems: 'center',
                      boxSizing: 'border-box', height: 30, padding: `0 10px 0 ${10 + o.depth * 16}px`,
                      borderRadius: token.borderRadiusSM, cursor: 'pointer',
                      fontSize: 13, lineHeight: '30px', color: token.colorText,
                      background: checked ? token.controlItemBgActive : 'transparent',
                    }}
                    onMouseEnter={(e) => { if (!checked) e.currentTarget.style.background = token.controlItemBgHover }}
                    onMouseLeave={(e) => { if (!checked) e.currentTarget.style.background = 'transparent' }}
                  >
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{o.title}</span>
                  </div>
                )
              })
            )}
          </div>
        </>,
        document.body
      )}
    </span>
  )
}

export default SafeTreeSelect
