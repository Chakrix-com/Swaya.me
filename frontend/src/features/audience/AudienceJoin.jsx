import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Form, Input, Button, Card, message, Tag, Space, Typography } from 'antd'
import { LoginOutlined, ReloadOutlined, UserOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { sessionAPI } from '../../services/api'
import { useDispatch } from 'react-redux'
import { setSession } from '../../store/sessionSlice'
import PublicBrandHeader from '../../components/PublicBrandHeader'

const { Title, Text } = Typography

const ADJECTIVES = ['Swift', 'Clever', 'Brave', 'Calm', 'Bold', 'Keen', 'Quick', 'Wise', 'Bright', 'Sharp', 'Cool', 'Epic', 'Jazzy', 'Nifty', 'Plucky', 'Snappy', 'Zesty']
const NOUNS = ['Falcon', 'Panda', 'Comet', 'Quasar', 'Ember', 'Titan', 'Rocket', 'Nebula', 'Pixel', 'Nova', 'Lynx', 'Phoenix', 'Vortex', 'Prism', 'Cipher', 'Axiom']

function randomName() {
  const adj = ADJECTIVES[Math.floor(Math.random() * ADJECTIVES.length)]
  const noun = NOUNS[Math.floor(Math.random() * NOUNS.length)]
  return `${adj} ${noun}`
}

const MODE_LABEL = {
  quiz: 'Live Quiz',
  poll: 'Live Poll',
  offline_poll: 'Survey',
  exam: 'Test',
}
const MODE_COLOR = {
  quiz: 'blue',
  poll: 'purple',
  offline_poll: 'green',
  exam: 'orange',
}

function AudienceJoin() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { joinCode: paramCode } = useParams()
  const [codeForm] = Form.useForm()
  const [nameForm] = Form.useForm()

  const [step, setStep] = useState('code')        // 'code' | 'name'
  const [activityInfo, setActivityInfo] = useState(null)  // { quiz_title, quiz_type, participant_count }
  const [resolvedCode, setResolvedCode] = useState('')
  const [looking, setLooking] = useState(false)
  const [joining, setJoining] = useState(false)

  const prevCodeRef = useRef('')

  useEffect(() => {
    if (paramCode) {
      const clean = paramCode.replace(/\D/g, '').slice(0, 6)
      codeForm.setFieldsValue({ join_code: clean })
      if (clean.length === 6) {
        handleLookup(clean)
      }
    }
  }, [paramCode])

  const handleLookup = async (code) => {
    const clean = (code || codeForm.getFieldValue('join_code') || '').replace(/\D/g, '').slice(0, 6)
    if (clean.length < 6) { return }
    if (clean === prevCodeRef.current && step === 'name') return
    prevCodeRef.current = clean
    setLooking(true)
    try {
      const res = await sessionAPI.lookup(clean)
      setActivityInfo(res.data)
      setResolvedCode(clean)
      nameForm.setFieldsValue({ display_name: randomName() })
      setStep('name')
    } catch {
      message.error(t('audience.invalidCode', { defaultValue: 'No active session found for that code.' }))
    } finally {
      setLooking(false)
    }
  }

  const handleJoin = async (values) => {
    setJoining(true)
    try {
      const response = await sessionAPI.join({
        join_code: resolvedCode,
        display_name: values.display_name?.trim() || undefined,
      })
      dispatch(setSession(response.data))
      navigate(`/session/${response.data.session_id}`, {
        state: {
          sessionToken: response.data.session_token,
          sessionId: response.data.session_id,
          displayName: values.display_name || t('audience.anonymous', { defaultValue: 'Anonymous' }),
        }
      })
    } catch (error) {
      message.error(error.response?.data?.detail || t('common.error'))
    } finally {
      setJoining(false)
    }
  }

  return (
    <div
      className="audience-join min-vh-100 d-flex flex-column"
      style={{ position: 'relative' }}
    >
      <PublicBrandHeader />

      <div className="container overflow-hidden py-4" style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
        <div className="row justify-content-center mx-0" style={{ width: '100%' }}>
          <div className="col-12 col-sm-10 col-md-7 col-lg-5 px-0 px-sm-3">

            {step === 'code' ? (
              <Card title={t('audience.joinQuiz')}>
                <Form form={codeForm} name="code" onFinish={() => handleLookup()} layout="vertical">
                  <Form.Item
                    label={t('audience.sessionCode')}
                    name="join_code"
                    rules={[{ required: true, len: 6, message: t('audience.sessionCodeRequired', { defaultValue: 'Enter a 6-digit code' }) }]}
                    getValueFromEvent={(e) => e.target.value.replace(/\D/g, '').slice(0, 6)}
                  >
                    <Input
                      placeholder={t('audience.enterSixDigitCode', { defaultValue: 'Enter 6-digit code' })}
                      maxLength={6}
                      inputMode="numeric"
                      pattern="[0-9]*"
                      style={{ fontSize: 28, textAlign: 'center', letterSpacing: 8, fontWeight: 700 }}
                      autoFocus
                    />
                  </Form.Item>
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={looking}
                      block
                      size="large"
                      icon={<LoginOutlined />}
                    >
                      {t('audience.continue', { defaultValue: 'Continue' })}
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            ) : (
              <Card>
                {/* Activity preview */}
                <div style={{ textAlign: 'center', padding: '12px 0 24px', borderBottom: '1px solid var(--sw-border, #f0f0f0)', marginBottom: 24 }}>
                  <Tag color={MODE_COLOR[activityInfo?.quiz_type] || 'blue'} style={{ marginBottom: 12, fontSize: 13 }}>
                    {t(`audience.mode.${activityInfo?.quiz_type}`, { defaultValue: MODE_LABEL[activityInfo?.quiz_type] || activityInfo?.quiz_type })}
                  </Tag>
                  <Title level={3} style={{ margin: '0 0 4px' }}>{activityInfo?.quiz_title}</Title>
                  {activityInfo?.participant_count > 0 && (
                    <Text type="secondary">
                      {t('audience.othersHere', { count: activityInfo.participant_count, defaultValue: `${activityInfo.participant_count} others here` })}
                    </Text>
                  )}
                </div>

                {/* Name entry + reroll */}
                <Form form={nameForm} name="name" onFinish={handleJoin} layout="vertical">
                  <Form.Item
                    label={t('audience.displayName')}
                    name="display_name"
                  >
                    <Space.Compact style={{ width: '100%' }}>
                      <Input
                        prefix={<UserOutlined />}
                        placeholder={t('audience.displayNameOptional', { defaultValue: 'Your Name (Optional)' })}
                        maxLength={40}
                      />
                      <Button
                        icon={<ReloadOutlined />}
                        title={t('audience.rerollName', { defaultValue: 'Suggest a random name' })}
                        onClick={() => nameForm.setFieldsValue({ display_name: randomName() })}
                      />
                    </Space.Compact>
                  </Form.Item>

                  <Space style={{ width: '100%' }} direction="vertical">
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={joining}
                      block
                      size="large"
                      icon={<PlayCircleOutlined />}
                    >
                      {t('audience.join')}
                    </Button>
                    <Button
                      type="link"
                      block
                      size="small"
                      onClick={() => { setStep('code'); setActivityInfo(null); prevCodeRef.current = '' }}
                    >
                      {t('audience.changeCode', { defaultValue: '← Change code' })}
                    </Button>
                  </Space>
                </Form>
              </Card>
            )}

          </div>
        </div>
      </div>
    </div>
  )
}

export default AudienceJoin
