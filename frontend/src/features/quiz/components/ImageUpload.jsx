import { Upload, Button, message, Tag } from 'antd'
import { UploadOutlined, DeleteOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { questionAPI } from '../../../services/api'

/**
 * ImageUpload component for uploading question/option images
 * 
 * @param {number} quizId - Quiz ID
 * @param {number} questionId - Question ID (optional - if missing, uses temp upload)
 * @param {string} imageType - Type: "question" | "option_a" | "option_b" | "option_c" | "option_d"
 * @param {string} currentImageUrl - Current image URL (if exists)
 * @param {function} onImageChange - Callback when image changes (url, tempKey) => void
 * @param {object} tempData - Temp image data {url, tempKey} (if exists)
 */
export default function ImageUpload({ 
  quizId, 
  questionId, 
  imageType, 
  currentImageUrl, 
  onImageChange,
  tempData = null
}) {
  const { t } = useTranslation()
  const [uploading, setUploading] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Determine if we're in temp mode (no question ID) or permanent mode
  const isTempMode = !questionId
  const displayUrl = tempData?.url || currentImageUrl
  const isTemp = !!tempData

  const handleUpload = async (file) => {
    // Validate file type
    const isImage = file.type.startsWith('image/')
    if (!isImage) {
      message.error(t('quiz.imageUploadOnlyImages'))
      return false
    }

    // Validate file size (2MB)
    const isLt2M = file.size / 1024 / 1024 < 2
    if (!isLt2M) {
      message.error(t('quiz.imageUploadMaxSize'))
      return false
    }

    try {
      setUploading(true)
      const response = await questionAPI.uploadImage(quizId, questionId, file, imageType)
      
      const { image_url, is_temp, temp_key } = response.data
      
      if (is_temp) {
        message.success(t('quiz.imageUploadedTemp'))
      } else {
        message.success(t('quiz.imageUploadedSuccess'))
      }
      
      // Call parent callback with new image URL and temp metadata
      if (onImageChange) {
        if (is_temp) {
          onImageChange(image_url, temp_key)
        } else {
          onImageChange(image_url, null)
        }
      }
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.imageUploadFailed'))
    } finally {
      setUploading(false)
    }

    // Prevent default upload behavior
    return false
  }

  const handleDelete = async () => {
    if (!displayUrl) return

    try {
      setDeleting(true)
      
      // Delete temp or permanent image
      if (isTemp) {
        await questionAPI.deleteImage(quizId, null, imageType, tempData.tempKey)
      } else {
        await questionAPI.deleteImage(quizId, questionId, imageType, null)
      }
      
      message.success(t('quiz.imageDeletedSuccess'))
      
      // Call parent callback with null
      if (onImageChange) {
        onImageChange(null, null)
      }
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.imageDeleteFailed'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div style={{ marginTop: 8 }}>
      {displayUrl ? (
        <div>
          <img 
            src={displayUrl} 
            alt={imageType} 
            style={{ 
              maxWidth: 200, 
              maxHeight: 150, 
              borderRadius: 4, 
              marginBottom: 8,
              display: 'block'
            }} 
          />
          {isTemp && (
            <Tag color="orange" style={{ marginBottom: 8 }}>
              {t('quiz.imageTempTag')}
            </Tag>
          )}
          <Button 
            icon={<DeleteOutlined />} 
            onClick={handleDelete} 
            loading={deleting}
            danger
            size="small"
          >
            {t('quiz.removeImage')}
          </Button>
        </div>
      ) : (
        <Upload
          accept="image/*"
          showUploadList={false}
          beforeUpload={handleUpload}
        >
          <Button icon={<UploadOutlined />} loading={uploading} size="small">
            {t('quiz.uploadImage')} {isTempMode && `(${t('quiz.tempShort')})`}
          </Button>
        </Upload>
      )}
    </div>
  )
}
