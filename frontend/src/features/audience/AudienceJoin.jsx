import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Form, Input, Button, Card, message } from 'antd'
import { sessionAPI } from '../../services/api'
import { useDispatch } from 'react-redux'
import { setSession } from '../../store/sessionSlice'

function AudienceJoin() {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { joinCode } = useParams()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    if (joinCode) {
      // Auto-populate join code from URL
      form.setFieldsValue({ join_code: joinCode.toUpperCase() })
    }
  }, [joinCode, form])

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const response = await sessionAPI.join(values)
      dispatch(setSession(response.data))
      message.success('Joined successfully!')
      // Pass session data via navigate state
      navigate(`/session/${response.data.session_id}`, {
        state: {
          sessionToken: response.data.session_token,
          sessionId: response.data.session_id,
          displayName: values.display_name || 'Guest'
        }
      })
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to join session')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="audience-container">
      <Card title="Join Quiz" style={{ width: 400 }}>
        <Form
          form={form}
          name="join"
          onFinish={onFinish}
          layout="vertical"
        >
          <Form.Item
            label="Join Code"
            name="join_code"
            rules={[{ required: true, message: 'Please enter the join code!' }]}
          >
            <Input
              placeholder="Enter 6-digit code"
              maxLength={6}
              style={{ fontSize: 24, textAlign: 'center', textTransform: 'uppercase' }}
            />
          </Form.Item>

          <Form.Item
            label="Display Name (Optional)"
            name="display_name"
          >
            <Input placeholder="Your name" />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block size="large">
              Join Quiz
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default AudienceJoin
