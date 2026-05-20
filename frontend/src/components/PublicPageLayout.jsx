import React from 'react'
import LanguageSwitcher from './LanguageSwitcher'
import BetaBadge from './BetaBadge'
import OpenSourceBadge from './OpenSourceBadge'
import ThemeToggleButton from './ThemeToggleButton'
import './PublicPageLayout.css'

const PublicPageLayout = ({ children }) => {
  return (
    <div className="public-page-wrapper">
      <div className="public-beta-badge-container">
        <BetaBadge />
      </div>
      <div className="language-switcher-container">
        <OpenSourceBadge />
        <ThemeToggleButton />
        <LanguageSwitcher />
      </div>
      <div className="public-page-content">
        {children}
      </div>
    </div>
  )
}

export default PublicPageLayout
