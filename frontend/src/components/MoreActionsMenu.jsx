import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Button, Popconfirm } from 'antd'
import { MoreOutlined } from '@ant-design/icons'

// Deliberately not using antd's Dropdown here — this popup manages its own
// open/close state and a single outside-click listener, avoiding
// @rc-component/trigger's multi-listener mousedown/pointerdown coordination
// entirely (traced as the source of click-race dropdown bugs on some
// environments). Rendered through a portal into document.body with
// position:fixed so it can't be clipped by a scrollable/clipped ancestor
// (e.g. a table row), with simple viewport-edge collision handling.
const ITEM_HEIGHT = 34
const DIVIDER_HEIGHT = 9
const CONTAINER_PADDING = 12

function MoreActionsMenu({ items, trigger, disabled = false, width = 190 }) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const triggerRef = useRef(null)
  const popupRef = useRef(null)

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

    const onOutsideClick = (e) => {
      if (
        triggerRef.current && !triggerRef.current.contains(e.target) &&
        popupRef.current && !popupRef.current.contains(e.target)
      ) {
        setOpen(false)
      }
    }
    const onEscape = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', onOutsideClick)
    document.addEventListener('keydown', onEscape)
    return () => {
      document.removeEventListener('mousedown', onOutsideClick)
      document.removeEventListener('keydown', onEscape)
    }
  }, [open])

  return (
    <span
      ref={triggerRef}
      style={{ position: 'relative', display: 'inline-block' }}
      onClick={() => { if (!disabled) (open ? setOpen(false) : openMenu()) }}
    >
      {trigger || <Button size="small" icon={<MoreOutlined />} disabled={disabled} />}
      {open && createPortal(
        <div
          ref={popupRef}
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
        </div>,
        document.body
      )}
    </span>
  )
}

export default MoreActionsMenu
