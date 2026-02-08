import { useDispatch, useSelector } from 'react-redux'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined, TeamOutlined } from '@ant-design/icons'
import { loginStart, loginSuccess, loginFailure } from '../../store/authSlice'
import { authAPI } from '../../services/api'

function Register() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { loading } = useSelector((state) => state.auth)

  const onFinish = async (values) => {
    dispatch(loginStart())
    try {
      const response = await authAPI.register(values)
      dispatch(loginSuccess(response.data))
      message.success('Registration successful!')
      navigate('/dashboard')
    } catch (error) {
      dispatch(loginFailure(error.response?.data?.detail || 'Registration failed'))
      message.error(error.response?.data?.detail || 'Registration failed')
    }
  }

  return (
    <div className="login-container">
      <Card className="login-form" title="Create Account">
        <Form
          name="register"
          onFinish={onFinish}
          autoComplete="off"
          layout="vertical"
        >
          <Form.Item
            label="Organization Name"
            name="tenant_name"
            rules={[{ required: true, message: 'Please input your organization name!' }]}
          >
            <Input prefix={<TeamOutlined />} placeholder="Organization Name" />
          </Form.Item>

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
            label="Full Name"
            name="full_name"
          >
            <Input prefix={<UserOutlined />} placeholder="Full Name (Optional)" />
          </Form.Item>

          <Form.Item
            label="Password"
            name="password"
            rules={[
              { required: true, message: 'Please input your password!' },
              { min: 8, message: 'Password must be at least 8 characters!' },
              {
                pattern: /^(?=.*[A-Z])(?=.*\d)/,
                message: 'Password must contain uppercase and number!',
              },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Password" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              Register
            </Button>
          </Form.Item>

          <div style={{ textAlign: 'center' }}>
            Already have an account? <Link to="/login">Login here</Link>
          </div>
        </Form>
      </Card>
    </div>
  )
}

export default Register
