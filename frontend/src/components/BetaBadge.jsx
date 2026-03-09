import React from 'react'
import { useTranslation } from 'react-i18next'
import './BetaBadge.css'

function BetaBadge({ className = '' }) {
  const { t } = useTranslation()
  return (
    <span
      className={`beta-badge ${className}`.trim()}
      aria-label={t('common.betaAriaLabel', { defaultValue: 'Beta version' })}
    >
      {t('common.beta', { defaultValue: 'Beta' })}
    </span>
  )
}

export default BetaBadge
