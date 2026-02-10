import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined, LoginOutlined } from '@ant-design/icons'
import { loginStart, loginSuccess, loginFailure, logout } from '../../store/authSlice'
import { authAPI } from '../../services/api'

function Login() {
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
      message.success('Login successful!')
      navigate('/dashboard')
    } catch (error) {
      dispatch(loginFailure(error.response?.data?.detail || 'Login failed'))
      message.error(error.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <div className="login-container">
      <Card className="login-form" title="Login to Swaya.me">
        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
        >
          <Form.Item
            label="Email"
            name="email"
            rules={[
              { required: true, message: 'Please input your email!' },
              { type: 'email', message: 'Please enter a valid email!' },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="Email" />
          </Form.Item>

          <Form.Item
            label="Password"
            name="password"
            rules={[{ required: true, message: 'Please input your password!' }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Password" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block icon={<LoginOutlined />}>
              Log in
            </Button>
          </Form.Item>

          <div style={{ textAlign: 'center' }}>
            Don't have an account? <Link to="/register">Register now</Link>
          </div>
        </Form>
      </Card>
    </div>
  )
}

export default Login
