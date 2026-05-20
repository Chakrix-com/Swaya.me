import { useContext } from 'react'
import logo from '../assets/logo.png'
import { Typography, Button } from 'antd'
import { SunOutlined, MoonOutlined } from '@ant-design/icons'
import BetaBadge from './BetaBadge'
import OpenSourceBadge from './OpenSourceBadge'
import LanguageSwitcher from './LanguageSwitcher'
import { VisitorThemeContext } from '../App'
import './PublicBrandHeader.css'

const { Text } = Typography

export default function PublicBrandHeader() {
  const { theme, toggle } = useContext(VisitorThemeContext)

  return (
    <header className="public-brand-header">
      <div className="public-brand-header__logo">
        <img src={logo} alt="Swaya.me" className="public-brand-header__img" />
        <Text className="public-brand-header__name">Swaya.me</Text>
        <BetaBadge />
      </div>
      <div className="public-brand-header__actions">
        <OpenSourceBadge />
        <Button
          type="text"
          icon={theme === 'dark' ? <SunOutlined /> : <MoonOutlined />}
          onClick={toggle}
          className="public-brand-header__theme-btn"
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        />
        <LanguageSwitcher />
      </div>
    </header>
  )
}
