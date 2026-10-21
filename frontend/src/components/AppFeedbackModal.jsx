import { useState, useEffect, useContext, useRef } from 'react'
import { Rate, Button, Space, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import { PaperClipOutlined, CloseOutlined } from '@ant-design/icons'
import RichTextEditor from '../features/quiz/components/RichTextEditor'
import { appFeedbackAPI } from '../services/api'
import { VisitorThemeContext } from '../App'
import SafeModal from './SafeModal'
import { message } from './safeMessage'

const { Text } = Typography

const isEmpty = (html) => !html || html.replace(/<[^>]*>/g, '').trim() === ''

// Mirrors backend/features/app_feedback/attachments.py
const MAX_ATTACHMENTS = 3
const MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024

export default function AppFeedbackModal({ open, onClose }) {
  const { t } = useTranslation()
  const { theme } = useContext(VisitorThemeContext)
  const isDark = theme === 'dark'

  const [feedbackText, setFeedbackText] = useState('')
  const [rating, setRating] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [capturedUrl, setCapturedUrl] = useState('')
  // [{ file, url }] — url is an object URL for the thumbnail
  const [attachments, setAttachments] = useState([])
  const fileInputRef = useRef(null)

  // Capture URL when modal opens
  useEffect(() => {
    if (open) {
      setCapturedUrl(window.location.href)
      setFeedbackText('')
      setRating(0)
      attachmentsRef.current.forEach((a) => URL.revokeObjectURL(a.url))
      setAttachments([])
    }
  }, [open])

  // Release thumbnail object URLs on unmount (removals/resets revoke their own)
  const attachmentsRef = useRef(attachments)
  attachmentsRef.current = attachments
  useEffect(() => () => attachmentsRef.current.forEach((a) => URL.revokeObjectURL(a.url)), [])

  const addFiles = (fileList) => {
    const images = Array.from(fileList || []).filter((f) => f.type.startsWith('image/'))
    if (images.length === 0) return
    const tooBig = images.filter((f) => f.size > MAX_ATTACHMENT_BYTES)
    if (tooBig.length) message.error(t('appFeedback.attachTooLarge'))
    const ok = images.filter((f) => f.size <= MAX_ATTACHMENT_BYTES)
    setAttachments((prev) => {
      const room = MAX_ATTACHMENTS - prev.length
      if (ok.length > room) message.warning(t('appFeedback.attachLimit', { count: MAX_ATTACHMENTS }))
      return [...prev, ...ok.slice(0, Math.max(0, room)).map((file) => ({ file, url: URL.createObjectURL(file) }))]
    })
  }

  // Ctrl+V of a copied screenshot anywhere in the dialog attaches it
  const handlePaste = (e) => {
    const files = Array.from(e.clipboardData?.files || []).filter((f) => f.type.startsWith('image/'))
    if (files.length) {
      e.preventDefault()
      addFiles(files)
    }
  }

  const removeAttachment = (index) => {
    setAttachments((prev) => {
      if (prev[index]) URL.revokeObjectURL(prev[index].url)
      return prev.filter((_, i) => i !== index)
    })
  }

  const handleSubmit = async () => {
    if (isEmpty(feedbackText)) return
    setSubmitting(true)
    try {
      const data = {
        feedback_text: feedbackText,
        rating: rating > 0 ? rating : undefined,
        page_url: capturedUrl,
      }
      if (attachments.length) {
        await appFeedbackAPI.submitWithAttachments(data, attachments.map((a) => a.file))
      } else {
        await appFeedbackAPI.submit(data)
      }
      message.success(t('appFeedback.successMessage'))
      onClose()
    } catch {
      message.error(t('appFeedback.errorMessage'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <SafeModal
      open={open}
      onCancel={onClose}
      title={t('appFeedback.modalTitle')}
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
      <Space direction="vertical" style={{ width: '100%' }} size="middle" onPaste={handlePaste}>
        <Text type="secondary">{t('appFeedback.modalSubtitle')}</Text>
        <RichTextEditor
          value={feedbackText}
          onChange={setFeedbackText}
          placeholder={t('appFeedback.placeholder')}
          isDark={isDark}
          showCode={false}
        />
        <div className="app-feedback-attachments">
          <Space wrap size={8} align="center">
            <Button
              icon={<PaperClipOutlined />}
              onClick={() => fileInputRef.current?.click()}
              disabled={attachments.length >= MAX_ATTACHMENTS}
            >
              {t('appFeedback.attachButton')}
            </Button>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('appFeedback.attachHint', { count: MAX_ATTACHMENTS })}
            </Text>
          </Space>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            hidden
            onChange={(e) => { addFiles(e.target.files); e.target.value = '' }}
          />
          {attachments.length > 0 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              {attachments.map((a, i) => (
                <div key={a.url} className="app-feedback-thumb" style={{ position: 'relative', width: 96, height: 72 }}>
                  <img
                    src={a.url}
                    alt={a.file.name || t('appFeedback.screenshot')}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 6, border: '1px solid rgba(128,128,128,0.35)' }}
                  />
                  <button
                    type="button"
                    aria-label={t('appFeedback.removeAttachment')}
                    title={t('appFeedback.removeAttachment')}
                    onClick={() => removeAttachment(i)}
                    style={{
                      position: 'absolute', top: -6, right: -6, width: 20, height: 20, borderRadius: '50%',
                      border: 'none', background: 'rgba(0,0,0,0.7)', color: '#fff', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, padding: 0,
                    }}
                  >
                    <CloseOutlined />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
        <Space>
          <Text>{t('appFeedback.ratingLabel')}</Text>
          <Rate value={rating} onChange={setRating} />
        </Space>
      </Space>
    </SafeModal>
  )
}
