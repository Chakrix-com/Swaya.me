import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Form, Input, Button, Card, message, Typography, Space } from 'antd'
import { UserOutlined, LockOutlined, UserAddOutlined, RocketOutlined, HomeOutlined } from '@ant-design/icons'
import { loginStart, loginSuccess, loginFailure } from '../../store/authSlice'
import { authAPI } from '../../services/api'
import PublicPageLayout from '../../components/PublicPageLayout'

const { Title, Text } = Typography

function Register() {
  const { t } = useTranslation()
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { loading } = useSelector((state) => state.auth)

  const onFinish = async (values) => {
    dispatch(loginStart())
    try {
      const response = await authAPI.register(values)
      dispatch(loginSuccess(response.data))
      message.success('Registration successful! An admin will assign you to an organization.')
      navigate('/dashboard')
    } catch (error) {
      dispatch(loginFailure(error.response?.data?.detail || 'Registration failed'))
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
              <Space direction="vertical" size={4}>
                <RocketOutlined style={{ fontSize: '48px', color: '#667eea' }} />
                <Title level={2} style={{ margin: 0, color: '#667eea' }}>
                  Swaya.me
                </Title>
                <Text type="secondary">{t('auth.platformSubtitle')}</Text>
              </Space>
            </Link>
          </div>

          <Title level={3} style={{ textAlign: 'center', marginBottom: '24px' }}>
            {t('auth.register')}
          </Title>

          <Form
            name="register"
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

            <Form.Item
              label={t('auth.fullName')}
              name="full_name"
            >
              <Input prefix={<UserOutlined />} placeholder={`${t('auth.fullName')} (Optional)`} size="large" />
            </Form.Item>

            <Form.Item
              label={t('auth.password')}
              name="password"
              rules={[
                { required: true, message: `${t('auth.password')} is required` },
                { min: 8, message: 'Password must be at least 8 characters!' },
                {
                  pattern: /^(?=.*[A-Z])(?=.*\d)/,
                  message: 'Password must contain uppercase and number!',
                },
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder={t('auth.password')} size="large" />
            </Form.Item>

            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading} 
                block 
                icon={<UserAddOutlined />}
                size="large"
              >
                {t('auth.registerButton')}
              </Button>
            </Form.Item>

            <div style={{ textAlign: 'center', marginTop: '16px' }}>
              {t('auth.haveAccount')} <Link to="/login">{t('auth.login')}</Link>
            </div>

            <div style={{ textAlign: 'center', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #f0f0f0' }}>
              <Link to="/">
                <Button type="link" icon={<HomeOutlined />}>
                  {t('auth.backToHome')}
                </Button>
              </Link>
            </div>
          </Form>
        </Card>
      </div>
    </PublicPageLayout>
  )
}

export default Register
