import React from 'react'
import { Select } from 'antd'
import { useTranslation } from 'react-i18next'
import { GlobalOutlined } from '@ant-design/icons'

const LanguageSwitcher = () => {
  const { i18n } = useTranslation()

  const languages = [
    { label: 'English', value: 'en' },
    { label: 'हिन्दी', value: 'hi' },
    { label: 'தமிழ்', value: 'ta' },
    { label: 'తెలుగు', value: 'te' },
    { label: 'ಕನ್ನಡ', value: 'ka' },
    { label: 'বাঙ্গালি', value: 'bn' },
    { label: 'ગુજરાતી', value: 'gu' },
  ]

  const handleLanguageChange = (value) => {
    i18n.changeLanguage(value)
    localStorage.setItem('preferredLanguage', value)
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
