import { startTransition } from 'react'
import { Dropdown, Button } from 'antd'
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

const ThemePicker = () => {
  const dispatch = useDispatch()
  const themeId = useSelector((state) => state.theme.themeId)

  const items = Object.entries(themes).map(([id, theme]) => ({
    key: id,
    label: (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
        <Swatch colors={theme.swatch} />
        <span>{theme.name}</span>
        {id === themeId && <CheckOutlined style={{ fontSize: 11 }} />}
      </span>
    ),
    onClick: () => startTransition(() => dispatch(setTheme(id))),
  }))

  return (
    <Dropdown menu={{ items }} trigger={['click']} placement="bottomRight"
      getPopupContainer={trigger => trigger.parentElement}>
      <Button type="text" icon={<BgColorsOutlined />} className="theme-picker-btn" />
    </Dropdown>
  )
}

export default ThemePicker
