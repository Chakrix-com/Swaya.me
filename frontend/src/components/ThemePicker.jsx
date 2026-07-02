import { useEffect, useRef, useState } from 'react'
import { Button, theme } from 'antd'
import { BgColorsOutlined, CheckOutlined } from '@ant-design/icons'
import { useSelector, useDispatch } from 'react-redux'
import { themes } from '../themes/themes'
import { setTheme } from '../store/themeSlice'

const Swatch = ({ colors }) => (
  <span style={{ display: 'inline-flex', gap: 3, alignItems: 'center' }}>
    {colors.map((c, i) => (
      <span
        key={i}
        style={{
          width: 10,
          height: 10,
          borderRadius: '50%',
          background: c,
          border: '1px solid rgba(0,0,0,0.15)',
        }}
      />
    ))}
  </span>
)

// Deliberately not using antd's Dropdown here — this popup manages its own
// open/close state and a single outside-click listener, avoiding
// @rc-component/trigger's multi-listener mousedown/pointerdown coordination
// entirely (traced as the source of the click-race dropdown bugs).
const ThemePicker = () => {
  const dispatch = useDispatch()
  const themeId = useSelector((state) => state.theme.themeId)
  const { token } = theme.useToken()
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!open) return

    const onOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
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

  const handleSelect = (id) => {
    dispatch(setTheme(id))
    setOpen(false)
  }

  return (
    <span ref={containerRef} style={{ position: 'relative', display: 'inline-block' }}>
      <Button
        type="text"
        icon={<BgColorsOutlined />}
        className="theme-picker-btn"
        onClick={() => setOpen((v) => !v)}
      />
      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            right: 0,
            width: 200,
            boxSizing: 'border-box',
            fontSize: 13,
            lineHeight: 'normal',
            background: token.colorBgElevated,
            border: `1px solid ${token.colorBorderSecondary}`,
            borderRadius: token.borderRadiusLG,
            boxShadow: token.boxShadowSecondary,
            padding: 4,
            zIndex: 1050,
          }}
        >
          {Object.entries(themes).map(([id, t]) => (
            <div
              key={id}
              onClick={() => handleSelect(id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                boxSizing: 'border-box',
                height: 30,
                padding: '0 10px',
                borderRadius: token.borderRadiusSM,
                cursor: 'pointer',
                color: token.colorText,
                fontSize: 13,
                lineHeight: '30px',
                background: id === themeId ? token.controlItemBgActive : 'transparent',
              }}
              onMouseEnter={(e) => {
                if (id !== themeId) e.currentTarget.style.background = token.controlItemBgHover
              }}
              onMouseLeave={(e) => {
                if (id !== themeId) e.currentTarget.style.background = 'transparent'
              }}
            >
              <Swatch colors={t.swatch} />
              <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{t.name}</span>
              {id === themeId && <CheckOutlined style={{ fontSize: 11, color: token.colorPrimary, flexShrink: 0 }} />}
            </div>
          ))}
        </div>
      )}
    </span>
  )
}

export default ThemePicker
