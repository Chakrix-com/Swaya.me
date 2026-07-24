/**
 * CodingChallengeSession — candidate-facing coding-challenge UI
 * Route: /c/:token (public, standalone — not embedded in the general exam-taking UI)
 */
import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Button, Form, Input, Space, Alert, Spin, Result, Radio,
} from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined, LinkOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { codingChallengeAPI } from '../../services/api'
import PublicBrandHeader from '../../components/PublicBrandHeader'

const { Title, Text } = Typography

const POLL_INTERVAL_MS = 5000
const MAX_POLL_MS = 5 * 60 * 1000 // 5 minutes, per the design's capped-poll-duration requirement

// ── OTP + IDE choice + Start step (mirrors ExamSession's StartScreen pattern) ──

function StartStep({ info, onStarted, startError, onClearStartError }) {
  const { t } = useTranslation()
  const [otpStep, setOtpStep] = useState('form') // 'form' | 'otp'
  const [ideType, setIdeType] = useState('code_server')
  const [resendCooldown, setResendCooldown] = useState(0)
  const [sendingOtp, setSendingOtp] = useState(false)
  const [starting, setStarting] = useState(false)
  const [otpError, setOtpError] = useState('')
  const cooldownRef = useRef(null)
  const [form] = Form.useForm()

  const startCooldown = () => {
    setResendCooldown(60)
    cooldownRef.current = setInterval(() => {
      setResendCooldown((c) => {
        if (c <= 1) { clearInterval(cooldownRef.current); return 0 }
        return c - 1
      })
    }, 1000)
  }

  useEffect(() => () => clearInterval(cooldownRef.current), [])

  const handleSendOtp = async () => {
    setSendingOtp(true)
    setOtpError('')
    try {
      await codingChallengeAPI.requestOtp(info.token)
      setOtpStep('otp')
      startCooldown()
    } catch (err) {
      const status = err.response?.status
      setOtpError(status === 429 ? t('codingChallenge.otpRateLimited') : (err.response?.data?.detail || t('common.error')))
    } finally {
      setSendingOtp(false)
    }
  }

  const handleResend = async () => {
    if (resendCooldown > 0) return
    setSendingOtp(true)
    setOtpError('')
    try {
      await codingChallengeAPI.requestOtp(info.token)
      startCooldown()
    } catch (err) {
      setOtpError(err.response?.status === 429 ? t('codingChallenge.otpRateLimited') : (err.response?.data?.detail || t('common.error')))
    } finally {
      setSendingOtp(false)
    }
  }

  const handleStart = async (values) => {
    setStarting(true)
    onClearStartError?.()
    try {
      const res = await codingChallengeAPI.start(info.token, ideType, values.otp.trim())
      onStarted(res.data.workspace_url)
    } catch (err) {
      setOtpError(err.response?.data?.detail || t('common.error'))
    } finally {
      setStarting(false)
    }
  }

  if (otpStep === 'form') {
    return (
      <Card bordered={false}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Text>{t('codingChallenge.otpIntro', { email: info.candidate_email })}</Text>
          {(info.ide_choices || []).length > 1 && (
            <div>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>{t('codingChallenge.chooseIde')}</Text>
              <Radio.Group value={ideType} onChange={(e) => setIdeType(e.target.value)}>
                {(info.ide_choices || []).map((choice) => (
                  <Radio.Button key={choice} value={choice}>
                    {choice === 'code_server' ? t('codingChallenge.ideCodeServer') : choice}
                  </Radio.Button>
                ))}
              </Radio.Group>
            </div>
          )}
          {otpError && <Alert type="error" showIcon message={otpError} />}
          <Button type="primary" size="large" loading={sendingOtp} onClick={handleSendOtp}>
            {t('codingChallenge.sendCode')}
          </Button>
        </Space>
      </Card>
    )
  }

  return (
    <Card bordered={false}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Alert type="success" showIcon message={t('codingChallenge.otpSent', { email: info.candidate_email })} />
        {(startError || otpError) && <Alert type="error" showIcon message={startError || otpError} />}
        <Form form={form} layout="vertical" onFinish={handleStart}>
          <Form.Item
            name="otp"
            label={t('codingChallenge.otpLabel')}
            rules={[
              { required: true, message: t('codingChallenge.otpRequired') },
              { len: 6, message: t('codingChallenge.otpLength') },
            ]}
          >
            <Input
              placeholder={t('codingChallenge.otpPlaceholder')}
              size="large"
              maxLength={6}
              autoFocus
              style={{ letterSpacing: 8, fontSize: 20, textAlign: 'center' }}
              onChange={() => { setOtpError(''); onClearStartError?.() }}
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" size="large" block loading={starting}>
              {t('codingChallenge.startButton')}
            </Button>
          </Form.Item>
        </Form>
        <Button type="link" disabled={resendCooldown > 0} loading={sendingOtp} onClick={handleResend} style={{ padding: 0 }}>
          {resendCooldown > 0 ? t('codingChallenge.resendIn', { seconds: resendCooldown }) : t('codingChallenge.resendCode')}
        </Button>
      </Space>
    </Card>
  )
}

// ── Workspace-open + Submit step ────────────────────────────────────────────

function WorkspaceStep({ workspaceUrl, onSubmit, submitting }) {
  const { t } = useTranslation()
  return (
    <Card bordered={false}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message={t('codingChallenge.workspaceReadyTitle')}
          description={t('codingChallenge.workspaceReadyDesc')}
        />
        <Button
          type="default"
          size="large"
          icon={<LinkOutlined />}
          onClick={() => window.open(workspaceUrl, '_blank', 'noopener,noreferrer')}
        >
          {t('codingChallenge.openWorkspace')}
        </Button>
        <Button type="primary" size="large" loading={submitting} onClick={onSubmit}>
          {t('codingChallenge.submitButton')}
        </Button>
      </Space>
    </Card>
  )
}

// ── Grading-in-progress + result step ───────────────────────────────────────

function ResultStep({ statusData, timedOut }) {
  const { t } = useTranslation()

  if (timedOut) {
    return (
      <Result
        icon={<ClockCircleOutlined />}
        title={t('codingChallenge.pollTimeoutTitle')}
        subTitle={t('codingChallenge.pollTimeoutDesc')}
      />
    )
  }

  if (!statusData || statusData.status === 'queued' || statusData.status === 'grading' || statusData.status === 'not_submitted') {
    return (
      <Card bordered={false}>
        <div style={{ textAlign: 'center', padding: '32px 0' }}>
          <Spin size="large" />
          <Title level={4} style={{ marginTop: 16 }}>{t('codingChallenge.gradingInProgress')}</Title>
          <Text type="secondary">{t('codingChallenge.gradingInProgressDesc')}</Text>
        </div>
      </Card>
    )
  }

  if (statusData.status === 'graded') {
    return (
      <Result
        icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
        title={t('codingChallenge.gradedTitle')}
        subTitle={t('codingChallenge.gradedScore', { score: statusData.ai_score, verdict: statusData.ai_verdict })}
      />
    )
  }

  if (statusData.status === 'partial_failed') {
    return (
      <Result
        status="warning"
        title={t('codingChallenge.partialFailedTitle')}
        subTitle={statusData.error_message || t('codingChallenge.partialFailedDesc')}
      />
    )
  }

  return (
    <Result
      status="error"
      title={t('codingChallenge.failedTitle')}
      subTitle={statusData.error_message || t('codingChallenge.failedDesc')}
    />
  )
}

// ── Main component ───────────────────────────────────────────────────────────

export default function CodingChallengeSession() {
  const { token } = useParams()
  const { t } = useTranslation()

  const [phase, setPhase] = useState('loading') // loading | error | start | started | grading | done
  const [info, setInfo] = useState(null)
  const [error, setError] = useState(null)
  const [startError, setStartError] = useState(null)
  const [workspaceUrl, setWorkspaceUrl] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [statusData, setStatusData] = useState(null)
  const [pollTimedOut, setPollTimedOut] = useState(false)

  const pollTimerRef = useRef(null)
  const pollStartRef = useRef(null)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await codingChallengeAPI.getInfo(token)
        setInfo({ ...res.data, token })
        setPhase('start')
      } catch (err) {
        setError(err.response?.data?.detail || t('common.error'))
        setPhase('error')
      }
    }
    load()
  }, [token, t])

  useEffect(() => () => clearInterval(pollTimerRef.current), [])

  const handleStarted = (url) => {
    setWorkspaceUrl(url)
    setPhase('started')
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  const pollStatus = async () => {
    try {
      const res = await codingChallengeAPI.getStatus(token)
      setStatusData(res.data)
      if (['graded', 'partial_failed', 'failed'].includes(res.data.status)) {
        clearInterval(pollTimerRef.current)
        return
      }
    } catch {
      // transient poll failure — keep trying until the max-duration cap
    }
    if (Date.now() - pollStartRef.current > MAX_POLL_MS) {
      clearInterval(pollTimerRef.current)
      setPollTimedOut(true)
    }
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await codingChallengeAPI.submit(token)
      setPhase('grading')
      pollStartRef.current = Date.now()
      pollStatus()
      pollTimerRef.current = setInterval(pollStatus, POLL_INTERVAL_MS)
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="coding-challenge-session">
      <PublicBrandHeader />
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '24px 16px' }}>
        {phase === 'loading' && (
          <div style={{ textAlign: 'center', paddingTop: 80 }}>
            <Spin size="large" />
          </div>
        )}

        {phase === 'error' && (
          <Result status="error" title={t('common.error')} subTitle={error} />
        )}

        {info && phase !== 'loading' && phase !== 'error' && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Title level={3} style={{ marginBottom: 0 }}>{info.quiz_title}</Title>
            <Card bordered={false} bodyStyle={{ maxHeight: 400, overflowY: 'auto' }}>
              <ReactMarkdown>{info.problem_statement}</ReactMarkdown>
            </Card>

            {phase === 'start' && (
              <StartStep
                info={info}
                onStarted={handleStarted}
                startError={startError}
                onClearStartError={() => setStartError(null)}
              />
            )}

            {phase === 'started' && (
              <WorkspaceStep workspaceUrl={workspaceUrl} onSubmit={handleSubmit} submitting={submitting} />
            )}

            {phase === 'grading' && (
              <ResultStep statusData={statusData} timedOut={pollTimedOut} />
            )}
          </Space>
        )}
      </div>
    </div>
  )
}
