import { useEffect, useMemo, useRef, useState } from 'react'
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
// Not portaled — kept as a normal nested child so it stays in the same
// stacking context as an ancestor Modal, rather than a document.body portal
// potentially painting above the Modal's own mask.
function flatten(nodes, depth = 0, out = []) {
  for (const n of nodes) {
    out.push({ value: n.value, title: n.title, depth })
    if (n.children?.length) flatten(n.children, depth + 1, out)
  }
  return out
}

function SafeTreeSelect({ value, onChange, treeData = [], placeholder, allowClear = true, style }) {
  const { token } = theme.useToken()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const onEscape = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [open])

  const flatOptions = useMemo(() => flatten(treeData), [treeData])
  const selected = flatOptions.find((o) => o.value === value)

  const handleSelect = (v) => {
    onChange(v)
    setOpen(false)
  }

  const handleClear = (e) => {
    e.stopPropagation()
    onChange(undefined)
  }

  return (
    <span style={{ position: 'relative', display: 'inline-block', width: '100%', ...style }}>
      <div
        onClick={() => setOpen((v) => !v)}
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
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 1049 }} />
          <div
            style={{
              position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
              maxHeight: 260, overflowY: 'auto', boxSizing: 'border-box',
              background: token.colorBgElevated,
              border: `1px solid ${token.colorBorderSecondary}`,
              borderRadius: token.borderRadiusLG,
              boxShadow: token.boxShadowSecondary,
              padding: 4, zIndex: 1050,
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
        </>
      )}
    </span>
  )
}

export default SafeTreeSelect
