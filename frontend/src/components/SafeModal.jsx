import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { Button, theme } from 'antd'
import { CloseOutlined } from '@ant-design/icons'

// Deliberately not using antd's Modal here. rc-dialog (antd Modal's
// underlying implementation) wires its own mask mousedown handling and a
// focus-trap that re-asserts focus into the dialog on every blur. Every
// other rc-component/trigger-based element in this app's confirmed-broken
// set (Dropdown/Select/click-triggered Popover) was already replaced with a
// hand-rolled pattern (see SafeMultiSelect.jsx, SafeTreeSelect.jsx,
// MoreActionsMenu.jsx) for the same VDI/remote-desktop click-race reason.
// Modal was the one container left untouched, and a focus-trap fighting a
// delayed/duplicated blur event (as RDP input redirection can produce) is a
// plausible way to get an actual hang, not just a missed click.
//
// No focus-trap of any kind here — initial focus (autoFocus on an input
// inside children) is a one-time focus() call and is fine; this component
// never re-asserts focus on blur.
//
// The mask does NOT use a raw document.addEventListener('mousedown', ...)
// listener either — that depends on a real mousedown/mouseup/click sequence
// arriving in the expected order, which is fragile over remote-desktop
// input redirection (and untestable via a JS-level .click(), which never
// fires mousedown at all). Instead an invisible full-viewport div closes
// the modal via a plain React onClick, the same synchronous synthetic-click
// mechanism every other button in this app already uses.
//
// Portaled to document.body — unlike SafeMultiSelect/SafeTreeSelect (which
// stay nested so they don't paint above an ancestor Modal's mask), SafeModal
// IS the top-level dialog, so it has no ancestor to stay nested inside.
function SafeModal({
  title,
  open,
  onCancel,
  onOk,
  confirmLoading = false,
  okText = 'OK',
  cancelText = 'Cancel',
  okButtonProps,
  footer,
  children,
  width = 420,
  maskClosable = true,
  borderRadius,
  closable = true,
}) {
  const { token } = theme.useToken()

  useEffect(() => {
    if (!open || !closable) return
    const onEscape = (e) => { if (e.key === 'Escape') onCancel?.() }
    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [open, closable, onCancel])

  if (!open) return null

  const resolvedFooter = footer === undefined ? (
    <>
      <Button onClick={onCancel}>{cancelText}</Button>
      <Button type="primary" loading={confirmLoading} onClick={onOk} {...okButtonProps}>
        {okText}
      </Button>
    </>
  ) : footer

  return createPortal(
    <>
      <div
        className="sw-safemodal-mask"
        onClick={() => { if (closable && maskClosable !== false) onCancel?.() }}
        style={{
          position: 'fixed', inset: 0, zIndex: 2000,
          background: 'rgba(0, 0, 0, 0.45)',
        }}
      />
      <div
        style={{
          position: 'fixed', inset: 0, zIndex: 2001,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 16, pointerEvents: 'none',
        }}
      >
        <div
          className="sw-safemodal-panel"
          style={{
            position: 'relative', pointerEvents: 'auto',
            width, maxWidth: '100%', boxSizing: 'border-box',
            maxHeight: 'calc(100vh - 32px)',
            display: 'flex', flexDirection: 'column',
            background: token.colorBgElevated,
            borderRadius: borderRadius ?? token.borderRadiusLG,
            boxShadow: token.boxShadowSecondary,
          }}
        >
          {(title || closable) && (
            <div
              className="sw-safemodal-header"
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '16px 20px', borderBottom: `1px solid ${token.colorBorderSecondary}`,
                fontSize: 16, fontWeight: 600, color: token.colorText,
                flexShrink: 0,
              }}
            >
              <div>{title}</div>
              {closable && (
                <CloseOutlined
                  className="sw-safemodal-close"
                  style={{ fontSize: 14, color: token.colorTextTertiary, cursor: 'pointer' }}
                  onClick={() => onCancel?.()}
                />
              )}
            </div>
          )}
          <div className="sw-safemodal-body" style={{ padding: 20, color: token.colorText, overflowY: 'auto', minHeight: 0 }}>
            {children}
          </div>
          {resolvedFooter !== null && (
            <div
              className="sw-safemodal-footer"
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8,
                padding: '12px 20px', borderTop: `1px solid ${token.colorBorderSecondary}`,
                flexShrink: 0,
              }}
            >
              {resolvedFooter}
            </div>
          )}
        </div>
      </div>
    </>,
    document.body
  )
}

export default SafeModal
