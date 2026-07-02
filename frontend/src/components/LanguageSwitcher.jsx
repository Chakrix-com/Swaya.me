import React, { useState } from 'react'
import { theme } from 'antd'
import { useTranslation } from 'react-i18next'
import { GlobalOutlined } from '@ant-design/icons'
import { languageTrackingAPI } from '../services/api'
import { getOrCreateSessionId } from '../utils/session'

const LanguageSwitcher = () => {
  const { i18n } = useTranslation()
  const { token } = theme.useToken()
  const [previousLanguage, setPreviousLanguage] = useState(i18n.language)

  const languages = [
    { label: 'English', value: 'en' },
    { label: 'हिन्दी', value: 'hi' },
    { label: 'தமிழ்', value: 'ta' },
    { label: 'తెలుగు', value: 'te' },
    { label: 'ಕನ್ನಡ', value: 'ka' },
    { label: 'বাঙ্গালি', value: 'bn' },
    { label: 'ગુજરાતી', value: 'gu' },
    { label: 'Español', value: 'es' },
    { label: 'Deutsch', value: 'de' },
    { label: 'Français', value: 'fr' },
    { label: 'Русский', value: 'ru' },
  ]

  const handleLanguageChange = async (value) => {
    const previous = i18n.language
    
    // Change language in UI
    i18n.changeLanguage(value)
    localStorage.setItem('preferredLanguage', value)
    
    // Track language change (async, don't block UI)
    trackLanguageChange(value, previous)
    
    // Update previous language for next change
    setPreviousLanguage(value)
  }

  const trackLanguageChange = async (newLanguage, oldLanguage) => {
    try {
      // Check if user is authenticated (cookie session; user info in localStorage)
      const isAuthenticated = !!localStorage.getItem('user')

      if (isAuthenticated) {
        // Authenticated user - update preference
        await languageTrackingAPI.updatePreference({
          language: newLanguage,
          previous_language: oldLanguage,
        })
      } else {
        // Anonymous user - log event with session ID
        const sessionId = getOrCreateSessionId()
        const userAgent = navigator.userAgent
        
        await languageTrackingAPI.logEvent({
          session_id: sessionId,
          language: newLanguage,
          previous_language: oldLanguage,
          user_agent: userAgent,
        })
      }
    } catch (error) {
      // Silent failure - don't disrupt user experience
      console.debug('Language tracking failed (non-critical):', error.message)
    }
  }

  // Custom chevron so the dropdown affordance is deliberate and theme-tinted,
  // instead of each browser's inconsistent native arrow rendering.
  const arrowSvg = `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="${token.colorPrimary}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>`
  )}`

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <GlobalOutlined style={{ fontSize: 14, color: token.colorPrimary }} />
      <select
        value={i18n.language}
        onChange={(e) => handleLanguageChange(e.target.value)}
        style={{
          boxSizing: 'border-box',
          width: 88,
          height: 32,
          lineHeight: '30px',
          borderRadius: token.borderRadius,
          border: `1px solid ${token.colorPrimaryBorder}`,
          background: `${token.colorBgContainer} url("${arrowSvg}") no-repeat right 6px center / 10px`,
          color: token.colorText,
          padding: '0 22px 0 8px',
          fontFamily: 'inherit',
          fontSize: 13,
          cursor: 'pointer',
          appearance: 'none',
          WebkitAppearance: 'none',
          MozAppearance: 'none',
        }}
      >
        {languages.map((l) => (
          <option key={l.value} value={l.value}>{l.label}</option>
        ))}
      </select>
    </span>
  )
}

export default LanguageSwitcher
