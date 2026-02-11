import React from 'react'
import LanguageSwitcher from './LanguageSwitcher'
import './PublicPageLayout.css'

const PublicPageLayout = ({ children }) => {
  return (
    <div className="public-page-wrapper">
      <div className="language-switcher-container">
        <LanguageSwitcher />
      </div>
      <div className="public-page-content">
        {children}
      </div>
    </div>
  )
}

export default PublicPageLayout
