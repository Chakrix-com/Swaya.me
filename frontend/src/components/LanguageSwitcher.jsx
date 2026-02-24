import React, { useState } from 'react'
import { Select } from 'antd'
import { useTranslation } from 'react-i18next'
import { GlobalOutlined } from '@ant-design/icons'
import { languageTrackingAPI } from '../services/api'
import { getOrCreateSessionId } from '../utils/session'

const LanguageSwitcher = () => {
  const { i18n } = useTranslation()
  const [previousLanguage, setPreviousLanguage] = useState(i18n.language)

  const languages = [
    { label: 'English', value: 'en' },
    { label: 'हिन्दी', value: 'hi' },
    { label: 'தமிழ்', value: 'ta' },
    { label: 'తెలుగు', value: 'te' },
    { label: 'ಕನ್ನಡ', value: 'ka' },
    { label: 'বাঙ্গালি', value: 'bn' },
    { label: 'ગુજરાતી', value: 'gu' },
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
      // Check if user is authenticated
      const token = localStorage.getItem('token')
      
      if (token) {
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

  return (
    <Select
      value={i18n.language}
      onChange={handleLanguageChange}
      options={languages}
      style={{ width: 150 }}
      prefix={<GlobalOutlined />}
      suffixIcon={<GlobalOutlined />}
    />
  )
}

export default LanguageSwitcher
