import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Form, Input, Button, Card, message, Typography, Space, Alert } from 'antd'
import { UserOutlined, LockOutlined, LoginOutlined, HomeOutlined } from '@ant-design/icons'
import { loginStart, loginSuccess, loginFailure, logout } from '../../store/authSlice'
import { authAPI } from '../../services/api'
import PublicPageLayout from '../../components/PublicPageLayout'
import logo from '../../assets/logo.png'

const { Title, Text } = Typography

function Login() {
  const { t, i18n } = useTranslation()
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const { loading, isAuthenticated, token } = useSelector((state) => state.auth)

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true })
      return
    }

    if (token) {
      const hydrateUser = async () => {
        try {
          const response = await authAPI.getMe()
          dispatch(loginSuccess({ access_token: token, user: response.data }))
          navigate('/dashboard', { replace: true })
        } catch (error) {
          dispatch(logout())
        }
      }

      hydrateUser()
    }
  }, [dispatch, isAuthenticated, navigate, token])

  const onFinish = async (values) => {
    dispatch(loginStart())
    try {
      const response = await authAPI.login(values)
      dispatch(loginSuccess(response.data))
      message.success(t('auth.loginSuccess'))
      navigate('/dashboard')
    } catch (error) {
      dispatch(loginFailure(error.response?.data?.detail || 'Login failed'))
      message.error(error.response?.data?.detail || t('auth.invalidCredentials'))
    }
  }

  return (
    <PublicPageLayout>
      <div className="login-container">
        <Card className="login-form">
          {/* Logo/Branding Header */}
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
              <Space direction="vertical" size={16} align="center" style={{ width: '100%' }}>
                <img src={logo} alt="Swaya Logo" style={{ display: 'block', margin: '0 auto', height: 'auto', maxHeight: '64px', maxWidth: '100%', objectFit: 'contain', borderRadius: '12px' }} />
                <Title level={2} style={{ margin: 0, color: 'var(--visitor-accent)', textAlign: 'center' }}>
                  Swaya.me
                </Title>
                <Text type="secondary">{t('auth.platformSubtitle')}</Text>
              </Space>
            </Link>
          </div>

          <Title level={3} style={{ textAlign: 'center', marginBottom: '24px' }}>
            {t('auth.login')}
          </Title>

          {location.state?.needsEmailVerification && (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message={t('auth.verifyEmailNoticeTitle', { defaultValue: 'Verify your email before logging in' })}
              description={t('auth.verifyEmailNoticeBody', {
                defaultValue: 'We sent a verification link to {{email}}. Please verify your email and then log in.',
                email: location.state?.registrationEmail || t('auth.email'),
              })}
            />
          )}

          <Form
            key={i18n.language}
            name="login"
            onFinish={onFinish}
            autoComplete="off"
            layout="vertical"
          >
            <Form.Item
              label={t('auth.email')}
              name="email"
              rules={[
                { required: true, message: t('auth.emailRequired') },
                { type: 'email', message: t('auth.emailInvalid') },
              ]}
            >
              <Input prefix={<UserOutlined />} placeholder={t('auth.email')} size="large" />
            </Form.Item>

            <Form.Item
              label={t('auth.password')}
              name="password"
              rules={[{ required: true, message: t('auth.passwordRequired') }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder={t('auth.password')} size="large" />
            </Form.Item>

            <div style={{ textAlign: 'right', marginBottom: '24px', marginTop: '-12px' }}>
              <Link to="/forgot-password" style={{ color: 'var(--visitor-accent)' }}>
                Forgot Password?
              </Link>
            </div>

            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading} 
                block 
                icon={<LoginOutlined />}
                size="large"
              >
                {t('auth.loginButton')}
              </Button>
            </Form.Item>

            <div style={{ textAlign: 'center', marginTop: '16px', color: 'var(--visitor-text-secondary)' }}>
              {t('auth.noAccount')} <Link to="/register">{t('auth.registerButton')}</Link>
            </div>

            <div style={{ textAlign: 'center', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--visitor-panel-border)' }}>
              <Link to="/">
                <Button type="link" icon={<HomeOutlined />}>
                  {t('auth.backToHome')}
                </Button>
              </Link>
            </div>
          </Form>

          <div style={{ textAlign: 'center', marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--visitor-panel-border)', fontSize: 12, color: 'var(--visitor-text-secondary)' }}>
            <Space split={<Text type="secondary">·</Text>} wrap size={4} style={{ justifyContent: 'center', width: '100%' }}>
              <Link to="/about" style={{ fontSize: 12, color: 'var(--visitor-text-secondary)' }}>{t('pages.legal.aboutLink')}</Link>
              <Link to="/privacy-policy" style={{ fontSize: 12, color: 'var(--visitor-text-secondary)' }}>{t('pages.legal.privacyLink')}</Link>
              <Link to="/terms-of-service" style={{ fontSize: 12, color: 'var(--visitor-text-secondary)' }}>{t('pages.legal.termsLink')}</Link>
              <Link to="/help" style={{ fontSize: 12, color: 'var(--visitor-text-secondary)' }}>{t('pages.legal.helpLink')}</Link>
              <a href="mailto:info@chakrix.net" style={{ fontSize: 12, color: 'var(--visitor-text-secondary)' }}>{t('pages.legal.contactLink')}</a>
            </Space>
          </div>
        </Card>
      </div>
    </PublicPageLayout>
  )
}

export default Login
