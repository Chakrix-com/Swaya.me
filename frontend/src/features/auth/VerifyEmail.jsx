import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Card, Result, Button, Spin, Typography, Space } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { authAPI } from '../../services/api'
import PublicPageLayout from '../../components/PublicPageLayout'
import logo from '../../assets/logo.png'

const { Title, Text } = Typography

function VerifyEmail() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  
  const [status, setStatus] = useState('verifying') // 'verifying', 'success', 'error'
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    const verifyToken = async () => {
      if (!token) {
        setStatus('error')
        setErrorMessage('No verification token provided.')
        return
      }

      try {
        await authAPI.verifyEmail({ token })
        setStatus('success')
      } catch (error) {
        setStatus('error')
        setErrorMessage(error.response?.data?.detail || 'Verification failed. The link may be expired or invalid.')
      }
    }

    verifyToken()
  }, [token])

  return (
    <PublicPageLayout>
      <div className="login-container">
        <Card className="login-form">
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
              <Space direction="vertical" size={16}>
                <img src={logo} alt="Swaya Logo" style={{ height: 'auto', maxHeight: '64px', maxWidth: '100%', objectFit: 'contain', borderRadius: '12px' }} />
                <Title level={2} style={{ margin: 0, color: 'var(--visitor-accent)' }}>
                  Swaya.me
                </Title>
              </Space>
            </Link>
          </div>

          {status === 'verifying' && (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Spin size="large" />
              <Title level={4} style={{ marginTop: '24px' }}>
                Verifying your email...
              </Title>
              <Text type="secondary">Please wait while we confirm your account.</Text>
            </div>
          )}

          {status === 'success' && (
            <Result
              status="success"
              title="Email Verified Successfully!"
              subTitle="Your account is now active. You can log in to start creating quizzes."
              extra={[
                <Button type="primary" key="login" onClick={() => navigate('/login')} size="large">
                  Go to Login
                </Button>
              ]}
            />
          )}

          {status === 'error' && (
            <Result
              status="error"
              title="Verification Failed"
              subTitle={errorMessage}
              extra={[
                <Button key="register" onClick={() => navigate('/register')} size="large">
                  Back to Registration
                </Button>,
                <Button type="primary" key="login" onClick={() => navigate('/login')} size="large">
                  Go to Login
                </Button>
              ]}
            >
              <div className="desc">
                <Text type="secondary">
                  If you continue to experience issues, please contact support or try registering again.
                </Text>
              </div>
            </Result>
          )}
        </Card>
      </div>
    </PublicPageLayout>
  )
}

export default VerifyEmail
