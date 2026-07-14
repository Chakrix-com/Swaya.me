import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Button, Popconfirm } from 'antd'
import { MoreOutlined } from '@ant-design/icons'

// Deliberately not using antd's Dropdown here — that's built on
// @rc-component/trigger's mousedown/pointerdown coordination, which is
// broken on the user's office VDI/remote-desktop environment.
//
// This popup does NOT use a raw `document.addEventListener('mousedown', ...)`
// listener for outside-click-to-close either — that pattern depends on a
// real mousedown/mouseup/click sequence arriving in the expected order,
// which is exactly the kind of thing a JS-level click() (used in automated
// testing) never exercises, and exactly the kind of thing that's fragile
// over remote-desktop input redirection. Instead: an invisible full-viewport
// overlay renders behind the popup and closes it via a normal React
// onClick — the same synchronous, synthetic-click mechanism every button in
// this app already uses. No raw document listeners, no event-ordering
// assumptions, nothing that can race.
const ITEM_HEIGHT = 34
const DIVIDER_HEIGHT = 9
const CONTAINER_PADDING = 12

function MoreActionsMenu({ items, trigger, disabled = false, width = 190 }) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const triggerRef = useRef(null)

  const openMenu = () => {
    const rect = triggerRef.current.getBoundingClientRect()
    const margin = 8
    const estimatedHeight = CONTAINER_PADDING +
      items.reduce((h, item) => h + (item.type === 'divider' ? DIVIDER_HEIGHT : ITEM_HEIGHT), 0)

    let top = rect.bottom + 4
    if (top + estimatedHeight > window.innerHeight - margin) {
      top = rect.top - estimatedHeight - 4
    }
    let left = rect.right - width
    if (left < margin) left = margin
    if (left + width > window.innerWidth - margin) left = window.innerWidth - margin - width

    setPos({ top, left })
    setOpen(true)
  }

  useEffect(() => {
    if (!open) return
    const onEscape = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [open])

  return (
    <span
      ref={triggerRef}
      style={{ position: 'relative', display: 'inline-block' }}
      onClick={() => { if (!disabled) (open ? setOpen(false) : openMenu()) }}
    >
      {trigger || <Button size="small" icon={<MoreOutlined />} disabled={disabled} />}
      {open && createPortal(
        <>
          <div
            onClick={() => setOpen(false)}
            style={{ position: 'fixed', inset: 0, zIndex: 1049 }}
          />
          <div
            className="dashboard-more-menu"
            style={{ position: 'fixed', top: pos.top, left: pos.left, width, zIndex: 1050, boxSizing: 'border-box' }}
          >
            {items.map((item, i) => {
              if (item.type === 'divider') {
                return <div key={`div-${i}`} style={{ borderTop: '1px solid var(--sw-border)', margin: '4px 0' }} />
              }
              const itemClass = `dashboard-more-menu-item${item.danger ? ' dashboard-more-menu-item--danger' : ''}${item.disabled ? ' dashboard-more-menu-item--disabled' : ''}`
              const label = <>{item.icon}<span>{item.label}</span></>

              if (item.confirm && !item.disabled) {
                return (
                  <Popconfirm
                    key={item.key}
                    title={item.confirm.title}
                    description={item.confirm.description}
                    onConfirm={() => { item.confirm.onConfirm(); setOpen(false) }}
                    okText={item.confirm.okText}
                    okButtonProps={{ danger: true }}
                    cancelText={item.confirm.cancelText}
                  >
                    <div className={itemClass}>{label}</div>
                  </Popconfirm>
                )
              }
              return (
                <div
                  key={item.key}
                  className={itemClass}
                  onClick={() => { if (item.disabled) return; item.onClick?.(); setOpen(false) }}
                >
                  {label}
                </div>
              )
            })}
          </div>
        </>,
        document.body
      )}
    </span>
  )
}

export default MoreActionsMenu
