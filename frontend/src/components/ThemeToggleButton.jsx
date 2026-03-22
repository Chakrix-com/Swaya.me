import { useContext } from 'react'
import { Button } from 'antd'
import { SunOutlined, MoonOutlined } from '@ant-design/icons'
import { VisitorThemeContext } from '../App'

export default function ThemeToggleButton({ style }) {
  const { theme, toggle } = useContext(VisitorThemeContext)
  return (
    <Button
      type="text"
      icon={theme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
      onClick={toggle}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      style={{ color: 'var(--visitor-text-primary)', ...style }}
    />
  )
}
