import { useState, useEffect, useContext } from 'react'
import { Modal, Rate, Button, Space, Typography, App as AntApp } from 'antd'
import { useTranslation } from 'react-i18next'
import RichTextEditor from '../features/quiz/components/RichTextEditor'
import { appFeedbackAPI } from '../services/api'
import { VisitorThemeContext } from '../App'

const { Text } = Typography

const isEmpty = (html) => !html || html.replace(/<[^>]*>/g, '').trim() === ''

export default function AppFeedbackModal({ open, onClose }) {
  const { t } = useTranslation()
  const { message } = AntApp.useApp()
  const { theme } = useContext(VisitorThemeContext)
  const isDark = theme === 'dark'

  const [feedbackText, setFeedbackText] = useState('')
  const [rating, setRating] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [capturedUrl, setCapturedUrl] = useState('')

  // Capture URL when modal opens
  useEffect(() => {
    if (open) {
      setCapturedUrl(window.location.href)
      setFeedbackText('')
      setRating(0)
    }
  }, [open])

  const handleSubmit = async () => {
    if (isEmpty(feedbackText)) return
    setSubmitting(true)
    try {
      await appFeedbackAPI.submit({
        feedback_text: feedbackText,
        rating: rating > 0 ? rating : undefined,
        page_url: capturedUrl,
      })
      message.success(t('appFeedback.successMessage'))
      onClose()
    } catch {
      message.error(t('appFeedback.errorMessage'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={t('appFeedback.modalTitle')}
      destroyOnClose
      footer={
        <Space>
          <Button onClick={onClose}>{t('common.cancel', { defaultValue: 'Cancel' })}</Button>
          <Button
            type="primary"
            loading={submitting}
            disabled={isEmpty(feedbackText)}
            onClick={handleSubmit}
          >
            {t('appFeedback.submitButton')}
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Text type="secondary">{t('appFeedback.modalSubtitle')}</Text>
        <RichTextEditor
          value={feedbackText}
          onChange={setFeedbackText}
          placeholder={t('appFeedback.placeholder')}
          isDark={isDark}
          showCode={false}
        />
        <Space>
          <Text>{t('appFeedback.ratingLabel')}</Text>
          <Rate value={rating} onChange={setRating} />
        </Space>
      </Space>
    </Modal>
  )
}
