import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Form, Input, Button, Card, message, Typography, Space } from 'antd'
import { LockOutlined, CheckCircleOutlined, HomeOutlined } from '@ant-design/icons'
import { authAPI } from '../../services/api'
import PublicPageLayout from '../../components/PublicPageLayout'
import logo from '../../assets/logo.png'

const { Title, Text } = Typography

function ResetPassword() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const onFinish = async (values) => {
    if (!token) {
      message.error(t('auth.resetTokenMissingToast'))
      return
    }

    setLoading(true)
    try {
      await authAPI.resetPassword({ 
        token: token,
        new_password: values.password 
      })
      setSuccess(true)
      message.success(t('auth.resetPasswordSuccessToast'))
    } catch (error) {
      message.error(error.response?.data?.detail || t('auth.resetPasswordFailedDefault'))
    } finally {
      setLoading(false)
    }
  }

  // If no token is present in URL, show an error state early
  if (!token) {
    return (
      <PublicPageLayout>
        <div className="login-container">
          <Card className="login-form">
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Title level={3} type="danger">{t('auth.invalidResetLinkTitle')}</Title>
              <Text>{t('auth.invalidResetLinkSubtitle')}</Text>
              <div style={{ marginTop: '24px' }}>
                <Link to="/forgot-password">
                  <Button type="primary">{t('auth.requestNewLink')}</Button>
                </Link>
              </div>
            </div>
          </Card>
        </div>
      </PublicPageLayout>
    )
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

          {!success ? (
            <>
              <Title level={3} style={{ textAlign: 'center', marginBottom: '16px' }}>
                {t('auth.resetYourPasswordTitle')}
              </Title>
              <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: '24px' }}>
                {t('auth.resetYourPasswordSubtitle')}
              </Text>

              <Form
                key={i18n.language}
                name="reset_password"
                onFinish={onFinish}
                autoComplete="off"
                layout="vertical"
              >
                <Form.Item
                  label={t('auth.newPasswordLabel')}
                  name="password"
                  rules={[
                    { required: true, message: t('auth.newPasswordRequired') },
                    { min: 8, message: t('auth.passwordMinLength') },
                    { pattern: /^(?=.*[A-Z])(?=.*\d)/, message: t('auth.passwordUpperNumber') },
                  ]}
                  extra={t('auth.passwordComplexityHint')}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder={t('auth.newPasswordPlaceholder')} size="large" />
                </Form.Item>

                <Form.Item
                  label={t('auth.confirmNewPasswordLabel')}
                  name="confirmPassword"
                  dependencies={['password']}
                  rules={[
                    { required: true, message: t('auth.confirmNewPasswordRequired') },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('password') === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error(t('auth.passwordMismatch')));
                      },
                    }),
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder={t('auth.confirmNewPasswordPlaceholder')} size="large" />
                </Form.Item>

                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    loading={loading} 
                    block 
                    icon={<CheckCircleOutlined />}
                    size="large"
                  >
                    {t('auth.saveNewPassword')}
                  </Button>
                </Form.Item>
              </Form>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <CheckCircleOutlined style={{ fontSize: '48px', color: '#52c41a', marginBottom: '16px' }} />
              <Title level={3}>{t('auth.passwordResetTitle')}</Title>
              <Text style={{ display: 'block', marginBottom: '24px' }}>
                {t('auth.passwordResetSubtitle')}
              </Text>
              <Button type="primary" size="large" block onClick={() => navigate('/login')}>
                {t('auth.goToLogin')}
              </Button>
            </div>
          )}

          <div style={{ textAlign: 'center', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--visitor-panel-border)' }}>
             <Link to="/">
                <Button type="link" icon={<HomeOutlined />}>
                  {t('auth.backToHome')}
                </Button>
              </Link>
          </div>
        </Card>
      </div>
    </PublicPageLayout>
  )
}

export default ResetPassword
