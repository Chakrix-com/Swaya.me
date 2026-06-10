import logo from '../assets/logo.png'
import { Typography } from 'antd'
import BetaBadge from './BetaBadge'
import OpenSourceBadge from './OpenSourceBadge'
import LanguageSwitcher from './LanguageSwitcher'
import './PublicBrandHeader.css'

const { Text } = Typography

export default function PublicBrandHeader() {
  return (
    <header className="public-brand-header">
      <div className="public-brand-header__logo">
        <img src={logo} alt="Swaya.me" className="public-brand-header__img" />
        <Text className="public-brand-header__name">Swaya.me</Text>
        <BetaBadge />
      </div>
      <div className="public-brand-header__actions">
        <OpenSourceBadge />
        <LanguageSwitcher />
      </div>
    </header>
  )
}
