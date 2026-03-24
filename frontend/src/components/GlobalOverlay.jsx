import { useState } from 'react'
import { FloatButton } from 'antd'
import { MessageOutlined } from '@ant-design/icons'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import AppFeedbackModal from './AppFeedbackModal'

export default function GlobalOverlay() {
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const { t } = useTranslation()

  // Hide on presentation/present routes
  if (location.pathname.startsWith('/present/')) return null

  return (
    <>
      <FloatButton
        icon={<MessageOutlined />}
        type="primary"
        tooltip={t('appFeedback.floatButtonTooltip')}
        onClick={() => setOpen(true)}
        style={{ bottom: 32, right: 32 }}
      />
      <AppFeedbackModal open={open} onClose={() => setOpen(false)} />
    </>
  )
}
