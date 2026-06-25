import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, Typography, Button, Space, Spin, Result, Divider } from 'antd'
import { DownloadOutlined, CopyOutlined, LinkedinFilled } from '@ant-design/icons'
import { examAPI } from '../../services/api'
import PublicBrandHeader from '../../components/PublicBrandHeader'

const { Title, Text } = Typography

export default function CertificatePage() {
  const { token } = useParams()
  const [meta, setMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  const apiBase = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/api\/v1$/, '')
  const certImageUrl = `${apiBase}/api/v1/exam/certificate/${token}`
  const shareUrl = `${window.location.origin}/cert/${token}`

  useEffect(() => {
    examAPI.getCertMeta(token)
      .then(res => {
        setMeta(res.data)
        document.title = `Certificate — ${res.data.name} · ${res.data.quiz_title}`
      })
      .catch(() => setError('Certificate not found or has expired.'))
      .finally(() => setLoading(false))
  }, [token])

  const handleCopy = () => {
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Result status="404" title="Certificate not found" subTitle={error} />
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <PublicBrandHeader />
      <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 16px' }}>
        <Card bordered={false} style={{ borderRadius: 12 }}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Title level={3} style={{ marginBottom: 4 }}>Certificate of Completion</Title>
            <Text type="secondary">{meta.org_name}</Text>
          </div>

          {/* Certificate image */}
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <img
              src={certImageUrl}
              alt={`Certificate for ${meta.name}`}
              style={{
                maxWidth: '100%',
                borderRadius: 8,
                boxShadow: '0 4px 24px rgba(0,0,0,0.12)',
                border: '1px solid #e8e8e8',
              }}
            />
          </div>

          {/* Details */}
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Text strong style={{ fontSize: 16 }}>{meta.name}</Text>
            <br />
            <Text type="secondary">"{meta.quiz_title}"</Text>
            <br />
            <Text>Score: <Text strong style={{ color: meta.score_pct >= 60 ? '#52c41a' : '#faad14' }}>{meta.score_pct}%</Text></Text>
            <Text type="secondary" style={{ marginLeft: 12 }}>
              · {new Date(meta.issued_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
            </Text>
          </div>

          <Divider />

          {/* Share actions */}
          <Space wrap style={{ justifyContent: 'center', width: '100%' }}>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => window.open(certImageUrl, '_blank')}
            >
              Download Certificate
            </Button>
            <Button
              icon={<LinkedinFilled style={{ color: '#0A66C2' }} />}
              onClick={() => window.open(
                `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
                '_blank'
              )}
            >
              Share on LinkedIn
            </Button>
            <Button icon={<CopyOutlined />} onClick={handleCopy}>
              {copied ? 'Copied!' : 'Copy link'}
            </Button>
          </Space>
        </Card>
      </div>
    </div>
  )
}
