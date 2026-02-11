import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined, LoginOutlined } from '@ant-design/icons'
import { loginStart, loginSuccess, loginFailure, logout } from '../../store/authSlice'
import { authAPI } from '../../services/api'
import PublicPageLayout from '../../components/PublicPageLayout'

function Login() {
  const { t } = useTranslation()
  const dispatch = useDispatch()
  const navigate = useNavigate()
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
        <Card className="login-form" title={t('auth.login')}>
          <Form
            name="login"
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
              label={t('auth.password')}
              name="password"
              rules={[{ required: true, message: `${t('auth.password')} is required` }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder={t('auth.password')} />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block icon={<LoginOutlined />}>
                {t('auth.loginButton')}
              </Button>
            </Form.Item>

            <div style={{ textAlign: 'center' }}>
              {t('auth.noAccount')} <Link to="/register">{t('auth.registerButton')}</Link>
            </div>
          </Form>
        </Card>
      </div>
    </PublicPageLayout>
  )
}

export default Login
