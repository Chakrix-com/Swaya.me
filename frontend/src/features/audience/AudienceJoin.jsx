import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Form, Input, Button, Card, message } from 'antd'
import { LoginOutlined } from '@ant-design/icons'
import { sessionAPI } from '../../services/api'
import { useDispatch } from 'react-redux'
import { setSession } from '../../store/sessionSlice'
import LanguageSwitcher from '../../components/LanguageSwitcher'

function AudienceJoin() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { joinCode } = useParams()
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    if (joinCode) {
      form.setFieldsValue({ join_code: joinCode.toUpperCase() })
    }
  }, [joinCode, form])

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const response = await sessionAPI.join(values)
      dispatch(setSession(response.data))
      message.success(t('audience.joinSuccess') || 'Joined successfully!')
      navigate(`/session/${response.data.session_id}`, {
        state: {
          sessionToken: response.data.session_token,
          sessionId: response.data.session_id,
          displayName: values.display_name || 'Guest'
        }
      })
    } catch (error) {
      message.error(error.response?.data?.detail || t('common.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-vh-100 d-flex align-items-center justify-content-center"
      style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', position: 'relative' }}
    >
      <div style={{ position: 'absolute', top: 20, right: 20, zIndex: 100 }}>
        <LanguageSwitcher />
      </div>

      <div className="container py-4">
        <div className="row justify-content-center">
          <div className="col-12 col-sm-8 col-md-6 col-lg-4">
            <Card title={t('audience.joinQuiz')}>
              <Form form={form} name="join" onFinish={onFinish} layout="vertical">
                <Form.Item
                  label={t('audience.sessionCode')}
                  name="join_code"
                  rules={[{ required: true, message: `${t('audience.sessionCode')} is required` }]}
                >
                  <Input
                    placeholder="Enter 6-digit code"
                    maxLength={6}
                    style={{ fontSize: 24, textAlign: 'center', textTransform: 'uppercase' }}
                  />
                </Form.Item>

                <Form.Item label={t('audience.displayName')} name="display_name">
                  <Input placeholder={`${t('audience.displayName')} (Optional)`} />
                </Form.Item>

                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={loading}
                    block
                    size="large"
                    icon={<LoginOutlined />}
                  >
                    {t('audience.join')}
                  </Button>
                </Form.Item>
              </Form>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AudienceJoin
