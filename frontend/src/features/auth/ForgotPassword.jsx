import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Form, Input, Button, Card, message, Typography, Space } from 'antd'
import { UserOutlined, MailOutlined, HomeOutlined } from '@ant-design/icons'
import { authAPI } from '../../services/api'
import PublicPageLayout from '../../components/PublicPageLayout'
import logo from '../../assets/logo.png'

const { Title, Text } = Typography

function ForgotPassword() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [submitEmail, setSubmitEmail] = useState('')

  const onFinish = async (values) => {
    setLoading(true)
    try {
      await authAPI.forgotPassword({ email: values.email })
      setSubmitEmail(values.email)
      setSubmitted(true)
    } catch (error) {
      // Even if there's an error, typically for forgot password we don't 
      // reveal if the email exists, but we catch network errors here.
      message.error(error.response?.data?.detail || t('auth.forgotPasswordRequestFailed'))
    } finally {
      setLoading(false)
    }
  }

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

          {!submitted ? (
            <>
              <Title level={3} style={{ textAlign: 'center', marginBottom: '16px' }}>
                {t('auth.forgotPasswordTitle')}
              </Title>
              <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: '24px' }}>
                {t('auth.forgotPasswordSubtitle')}
              </Text>

              <Form
                name="forgot_password"
                onFinish={onFinish}
                autoComplete="off"
                layout="vertical"
              >
                <Form.Item
                  label={t('auth.email')}
                  name="email"
                  rules={[
                    { required: true, message: `${t('auth.email')} is required` },
                    { type: 'email', message: `${t('auth.email')} is invalid` },
                  ]}
                >
                  <Input prefix={<UserOutlined />} placeholder={t('auth.email')} size="large" />
                </Form.Item>

                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={loading} 
                    block 
                    icon={<MailOutlined />}
                    size="large"
                  >
                    {t('auth.sendResetLink')}
                  </Button>
                </Form.Item>
              </Form>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <MailOutlined style={{ fontSize: '48px', color: '#52c41a', marginBottom: '16px' }} />
              <Title level={3}>{t('auth.checkYourEmail')}</Title>
              <Text style={{ display: 'block', marginBottom: '24px' }}>
                {t('auth.forgotPasswordEmailSent', { email: submitEmail })}
              </Text>
            </div>
          )}

          <div style={{ textAlign: 'center', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--visitor-panel-border)' }}>
            <Space split={<Text type="secondary">|</Text>}>
              <Link to="/login">
                <Button type="link">{t('auth.backToLogin')}</Button>
              </Link>
              <Link to="/">
                <Button type="link" icon={<HomeOutlined />}>
                  {t('auth.backToHome')}
                </Button>
              </Link>
            </Space>
          </div>
        </Card>
      </div>
    </PublicPageLayout>
  )
}

export default ForgotPassword
