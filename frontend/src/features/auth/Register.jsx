import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined, UserAddOutlined } from '@ant-design/icons'
import { loginStart, loginSuccess, loginFailure } from '../../store/authSlice'
import { authAPI } from '../../services/api'
import PublicPageLayout from '../../components/PublicPageLayout'

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
        <Card className="login-form" title={t('auth.register')}>
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
              <Input prefix={<UserOutlined />} placeholder={t('auth.email')} />
            </Form.Item>

            <Form.Item
              label={t('auth.fullName')}
              name="full_name"
            >
              <Input prefix={<UserOutlined />} placeholder={`${t('auth.fullName')} (Optional)`} />
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
              <Input.Password prefix={<LockOutlined />} placeholder={t('auth.password')} />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block icon={<UserAddOutlined />}>
                {t('auth.registerButton')}
              </Button>
            </Form.Item>

            <div style={{ textAlign: 'center' }}>
              {t('auth.haveAccount')} <Link to="/login">{t('auth.login')}</Link>
            </div>
          </Form>
        </Card>
      </div>
    </PublicPageLayout>
  )
}

export default Register
