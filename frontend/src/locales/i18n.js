import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import enTranslation from './en/translation.json'
import hiTranslation from './hi/translation.json'
import taTranslation from './ta/translation.json'
import teTranslation from './te/translation.json'
import kaTranslation from './ka/translation.json'
import bnTranslation from './bn/translation.json'
import guTranslation from './gu/translation.json'

const resources = {
  en: {
    translation: enTranslation,
  },
  hi: {
    translation: hiTranslation,
  },
  ta: {
    translation: taTranslation,
  },
  te: {
    translation: teTranslation,
  },
  ka: {
    translation: kaTranslation,
  },
  bn: {
    translation: bnTranslation,
  },
  gu: {
    translation: guTranslation,
  },
}

i18n
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    defaultNS: 'translation',
    ns: ['translation'],
    interpolation: {
      escapeValue: false, // React already escapes content
    },
  })

// Get saved language from localStorage or default to English
const savedLanguage = localStorage.getItem('preferredLanguage')
if (savedLanguage) {
  i18n.changeLanguage(savedLanguage)
} else {
  i18n.changeLanguage('en')
}

export default i18n

