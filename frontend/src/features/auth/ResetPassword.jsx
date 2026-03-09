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
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const onFinish = async (values) => {
    if (!token) {
      message.error("Passsword reset token is missing from the URL.")
      return
    }

    setLoading(true)
    try {
      await authAPI.resetPassword({ 
        token: token,
        new_password: values.password 
      })
      setSuccess(true)
      message.success("Password has been successfully reset! You can now log in.")
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to reset password. The link may have expired.')
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
              <Title level={3} type="danger">Invalid Link</Title>
              <Text>No reset token was found in the URL. Please request a new password reset link.</Text>
              <div style={{ marginTop: '24px' }}>
                <Link to="/forgot-password">
                  <Button type="primary">Request New Link</Button>
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
                Reset Your Password
              </Title>
              <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: '24px' }}>
                Please enter your new password below.
              </Text>

              <Form
                name="reset_password"
                onFinish={onFinish}
                autoComplete="off"
                layout="vertical"
              >
                <Form.Item
                  label="New Password"
                  name="password"
                  rules={[
                    { required: true, message: 'New password is required' },
                    { min: 8, message: 'Password must be at least 8 characters' }
                  ]}
                  extra="Must be at least 8 characters, and contain at least one uppercase letter and one number."
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="Enter new password" size="large" />
                </Form.Item>

                <Form.Item
                  label="Confirm New Password"
                  name="confirmPassword"
                  dependencies={['password']}
                  rules={[
                    { required: true, message: 'Please confirm your new password' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('password') === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('The two passwords do not match.'));
                      },
                    }),
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} placeholder="Confirm new password" size="large" />
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
                    Save New Password
                  </Button>
                </Form.Item>
              </Form>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <CheckCircleOutlined style={{ fontSize: '48px', color: '#52c41a', marginBottom: '16px' }} />
              <Title level={3}>Password Reset</Title>
              <Text style={{ display: 'block', marginBottom: '24px' }}>
                Your password has been successfully updated.
              </Text>
              <Button type="primary" size="large" block onClick={() => navigate('/login')}>
                Go to Login
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
