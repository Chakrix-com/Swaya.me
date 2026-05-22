/**
 * ExamSession — participant-facing exam UI
 * Route: /e/:slug (public)
 */
import { useState, useEffect, useCallback, useRef, useContext } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Button, Form, Input, Progress, Space,
  Alert, Spin, Row, Col, Tag, Statistic, Divider, Radio, Result,
  Modal, Badge
} from 'antd'
import {
  ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined,
  QuestionCircleOutlined, ArrowRightOutlined, ArrowLeftOutlined,
  TrophyOutlined, MinusCircleOutlined, PlusCircleOutlined, InfoCircleOutlined,
} from '@ant-design/icons'
import { examAPI, proctoringAPI } from '../../services/api'
import PublicBrandHeader from '../../components/PublicBrandHeader'
import RichTextRenderer from '../quiz/components/RichTextRenderer'
import PromoCard from '../../components/PromoCard'
import { VisitorThemeContext } from '../../App'
import { ProctoringProvider, ProctoringGate } from '../proctoring'
import dayjs from 'dayjs'

const { Title, Text, Paragraph } = Typography

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatSeconds(secs) {
  if (secs == null) return '--'
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

// ── Status Screen ─────────────────────────────────────────────────────────────

function StatusScreen({ info }) {
  const { t } = useTranslation()

  if (info.status === 'upcoming') {
    return (
      <Result
        icon={<ClockCircleOutlined style={{ color: '#1890ff' }} />}
        title={t('exam.examUpcoming')}
        subTitle={info.starts_at
          ? t('exam.opensOn', { date: dayjs(info.starts_at).format('DD MMM YYYY, HH:mm') })
          : ''}
      />
    )
  }

  if (info.status === 'closed') {
    return (
      <Result
        status="warning"
        title={t('exam.examClosed')}
        subTitle={info.ends_at
          ? t('exam.closesOn', { date: dayjs(info.ends_at).format('DD MMM YYYY, HH:mm') })
          : ''}
      />
    )
  }

  return null
}

// Proctoring rule IDs that map to i18n keys
const PROCTORING_RULE_IDS = [
  'tab_switch_detect', 'copy_paste_block', 'right_click_block',
  'fullscreen_enforce', 'multi_tab_detect', 'devtools_detect',
  'bot_signal_detect', 'webcam_monitoring',
]

// ── Start Screen ─────────────────────────────────────────────────────────────

function StartScreen({ info, proctoringConfig, onStart, loading, startError = null, onClearStartError }) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const requireEmail = !!info.require_email
  const [otpStep, setOtpStep] = useState('form') // 'form' | 'otp'
  const [sentEmail, setSentEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [resendCooldown, setResendCooldown] = useState(0)
  const [sendingOtp, setSendingOtp] = useState(false)
  const [otpError, setOtpError] = useState('')
  const [acknowledged, setAcknowledged] = useState(false)
  const cooldownRef = useRef(null)
  const nameValue = Form.useWatch('display_name', form)
  const emailValue = Form.useWatch('email', form)

  const timeLimitMins = info.time_limit_seconds ? Math.floor(info.time_limit_seconds / 60) : null

  const activeRuleIds = proctoringConfig
    ? (proctoringConfig.rules || []).map((r) => r.rule_id).filter((id) => PROCTORING_RULE_IDS.includes(id))
    : []
  const webcamOn = proctoringConfig?.webcam_required
  const hasProctoringRules = activeRuleIds.length > 0 || webcamOn

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

  const handleSendOtp = async (values) => {
    setSendingOtp(true)
    setOtpError('')
    try {
      await examAPI.requestOtp(info.exam_slug || window.location.pathname.split('/').pop(), {
        display_name: values.display_name.trim(),
        email: values.email.trim().toLowerCase(),
      })
      setDisplayName(values.display_name.trim())
      setSentEmail(values.email.trim().toLowerCase())
      setOtpStep('otp')
      startCooldown()
    } catch (err) {
      const detail = err.response?.data?.detail || ''
      if (err.response?.status === 429) {
        setOtpError(t('exam.otpRateLimited'))
      } else {
        setOtpError(detail || t('common.error'))
      }
    } finally {
      setSendingOtp(false)
    }
  }

  const handleVerifyOtp = async (values) => {
    setOtpError('')
    onStart(displayName, sentEmail, values.otp.trim())
  }

  const handleResend = async () => {
    if (resendCooldown > 0) return
    setSendingOtp(true)
    setOtpError('')
    try {
      await examAPI.requestOtp(info.exam_slug || window.location.pathname.split('/').pop(), {
        display_name: displayName,
        email: sentEmail,
      })
      startCooldown()
    } catch (err) {
      const detail = err.response?.data?.detail || ''
      setOtpError(err.response?.status === 429 ? t('exam.otpRateLimited') : detail || t('common.error'))
    } finally {
      setSendingOtp(false)
    }
  }

  const examStatsBlock = (
    <Row gutter={[16, 16]}>
      <Col span={8}>
        <Statistic title={t('quiz.questions')} value={info.question_count} prefix={<QuestionCircleOutlined />} />
      </Col>
      {timeLimitMins && (
        <Col span={8}>
          <Statistic title={t('exam.timeLimitMinutes')} value={timeLimitMins} suffix="min" prefix={<ClockCircleOutlined />} />
        </Col>
      )}
      {info.ends_at && (
        <Col span={8}>
          <Statistic
            title={t('exam.closesOn', { date: '' })}
            value={dayjs(info.ends_at).format('HH:mm, DD MMM')}
            prefix={<ClockCircleOutlined />}
          />
        </Col>
      )}
    </Row>
  )

  const scoringBlock = (
    <div>
      <Text strong style={{ display: 'block', marginBottom: 8 }}>
        <InfoCircleOutlined style={{ marginRight: 6 }} />
        {t('exam.scoringRules')}
      </Text>
      <Space wrap>
        <Tag icon={<PlusCircleOutlined />} color="success" style={{ fontSize: 13, padding: '3px 10px' }}>
          {t('exam.pointsForCorrect', { points: info.points_per_correct })}
        </Tag>
        {info.negative_points_per_wrong > 0 ? (
          <Tag icon={<MinusCircleOutlined />} color="error" style={{ fontSize: 13, padding: '3px 10px' }}>
            {t('exam.penaltyForWrong', { points: info.negative_points_per_wrong })}
          </Tag>
        ) : (
          <Tag icon={<CheckCircleOutlined />} color="default" style={{ fontSize: 13, padding: '3px 10px' }}>
            {t('exam.noPenalty')}
          </Tag>
        )}
        <Tag color="default" style={{ fontSize: 13, padding: '3px 10px' }}>
          {t('exam.zeroForUnanswered')}
        </Tag>
      </Space>
      {info.scoring_varies && (
        <Text type="secondary" style={{ display: 'block', marginTop: 6, fontSize: 12 }}>
          {t('exam.pointsVary')}
        </Text>
      )}
    </div>
  )

  if (otpStep === 'otp') {
    return (
      <Card style={{ maxWidth: 600, margin: '0 auto' }} bordered={false}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={3} style={{ marginBottom: 4 }}>{info.title}</Title>
          </div>
          <Alert
            type="success"
            showIcon
            message={t('exam.otpSent', { email: sentEmail })}
          />
          {(startError || otpError) && (
            <Alert type="error" showIcon message={startError || otpError} />
          )}
          <Form layout="vertical" onFinish={handleVerifyOtp}>
            <Form.Item
              name="otp"
              label={t('exam.otpLabel')}
              rules={[
                { required: true, message: t('exam.otpRequired') },
                { len: 6, message: t('exam.otpLength') },
              ]}
            >
              <Input
                placeholder={t('exam.otpPlaceholder')}
                size="large"
                maxLength={6}
                autoFocus
                style={{ letterSpacing: 8, fontSize: 20, textAlign: 'center' }}
                onChange={() => { if (startError) onClearStartError?.() }}
              />
            </Form.Item>
            <Form.Item style={{ marginBottom: 8 }}>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                block
                loading={loading}
                icon={<ArrowRightOutlined />}
              >
                {t('exam.verifyAndStart')}
              </Button>
            </Form.Item>
          </Form>
          <div style={{ textAlign: 'center' }}>
            <Button
              type="link"
              disabled={resendCooldown > 0 || sendingOtp}
              onClick={handleResend}
              loading={sendingOtp}
            >
              {resendCooldown > 0
                ? t('exam.resendCooldown', { seconds: resendCooldown })
                : t('exam.resendOtp')}
            </Button>
          </div>
        </Space>
      </Card>
    )
  }

  return (
    <Card style={{ maxWidth: 600, margin: '0 auto' }} bordered={false}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>{info.title}</Title>
          {info.description && <Paragraph type="secondary">{info.description}</Paragraph>}
        </div>

        {examStatsBlock}

        <Divider style={{ margin: '4px 0' }} />

        {scoringBlock}

        {/* Time warnings */}
        {(info.has_per_question_timers || timeLimitMins) && (
          <Alert
            type="warning"
            showIcon
            message={
              <Space direction="vertical" size={2}>
                {timeLimitMins && (
                  <span dangerouslySetInnerHTML={{ __html: t('exam.timeLimitWarning', { minutes: timeLimitMins }) }} />
                )}
                {info.has_per_question_timers && (
                  <Text>{t('exam.perQuestionTimerWarning')}</Text>
                )}
              </Space>
            }
          />
        )}

        {/* Proctoring rules preview */}
        {hasProctoringRules && (
          <div style={{
            background: '#fff7f7',
            border: '1px solid #fca5a5',
            borderRadius: 8,
            padding: '16px 20px',
          }}>
            {/* Title + subtitle */}
            <Text strong style={{ display: 'block', fontSize: 14, color: '#dc2626' }}>
              <span role="img" aria-label="warning" style={{ marginRight: 6 }}>⚠️</span>
              {t('proctoring.warning.title')}
            </Text>
            <Text style={{ display: 'block', fontSize: 13, color: '#6b7280', marginTop: 2, marginBottom: 10 }}>
              {t('proctoring.warning.subtitle')}
            </Text>

            {/* Webcam notice */}
            {webcamOn && (
              <div style={{ marginBottom: 10, fontSize: 13, color: '#92400e', background: '#fef3c7', borderRadius: 6, padding: '8px 12px' }}>
                {t('proctoring.warning.webcamNotice')}
              </div>
            )}

            {/* Violations list */}
            <Text style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
              {t('proctoring.warning.violationsTitle')}
            </Text>
            <ul style={{ margin: '0 0 10px', paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {activeRuleIds.map((ruleId) => (
                <li key={ruleId} style={{ fontSize: 13, color: '#374151' }}>
                  {t(`proctoring.warning.rules.${ruleId}`)}
                </li>
              ))}
            </ul>

            {/* Lock + auto-submit warning */}
            {proctoringConfig?.escalation?.lock_on_violation_count > 0 && (
              <div style={{ fontSize: 13, color: '#7f1d1d', background: '#fee2e2', borderRadius: 6, padding: '8px 12px', marginBottom: 10 }}>
                {t('proctoring.warning.lockMessage', { count: proctoringConfig.escalation.lock_on_violation_count })}
                {proctoringConfig.escalation.auto_submit_on_lock
                  ? t('proctoring.warning.autoSubmit')
                  : t('proctoring.warning.noAutoSubmit')}
              </div>
            )}

            {/* All violations logged */}
            <Text style={{ display: 'block', fontSize: 12, color: '#6b7280', marginBottom: 4 }}>
              {t('proctoring.warning.allLogged')}
            </Text>
          </div>
        )}

        {otpError && <Alert type="error" showIcon message={otpError} />}

        <Form
          form={form}
          layout="vertical"
          onFinish={requireEmail ? handleSendOtp : (values) => onStart(values.display_name.trim(), null, null)}
        >
          <Form.Item
            name="display_name"
            label={t('exam.enterName')}
            rules={[{ required: true, message: t('exam.enterNameRequired') }]}
          >
            <Input
              placeholder={t('exam.enterNamePlaceholder')}
              size="large"
              maxLength={100}
              autoFocus
            />
          </Form.Item>
          {requireEmail && (
            <Form.Item
              name="email"
              label={t('exam.emailLabel')}
              rules={[
                { required: true, message: t('exam.emailRequired') },
                { type: 'email', message: t('exam.emailInvalid') },
              ]}
            >
              <Input
                placeholder={t('exam.emailPlaceholder')}
                size="large"
                maxLength={255}
                type="email"
              />
            </Form.Item>
          )}
          {hasProctoringRules && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 16 }}>
              <input
                type="checkbox"
                id="proctor-ack"
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.target.checked)}
                style={{ marginTop: 3, flexShrink: 0 }}
              />
              <label htmlFor="proctor-ack" style={{ fontSize: 13, color: '#374151', cursor: 'pointer' }}>
                {t('proctoring.warning.checkboxLabel')}
              </label>
            </div>
          )}
          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={requireEmail ? sendingOtp : loading}
              disabled={
                !nameValue?.trim() ||
                (requireEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailValue?.trim() ?? '')) ||
                (hasProctoringRules && !acknowledged)
              }
              icon={<ArrowRightOutlined />}
            >
              {requireEmail ? t('exam.sendOtp') : t('exam.startExam')}
            </Button>
          </Form.Item>
        </Form>
      </Space>
    </Card>
  )
}

// ── Question Screen ──────────────────────────────────────────────────────────

function QuestionScreen({
  question,
  questionIndex,
  totalQuestions,
  selectedAnswer,
  onAnswerSelect,
  onNext,
  onPrev,
  onSubmit,
  globalSecondsLeft,
  questionSecondsLeft,
  hasPerQuestionTimers,
  saving,
}) {
  const { t } = useTranslation()
  const { theme } = useContext(VisitorThemeContext)
  const isLast = questionIndex === totalQuestions - 1

  const globalUrgent = globalSecondsLeft != null && globalSecondsLeft < 60
  const qUrgent = questionSecondsLeft != null && questionSecondsLeft < 10

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      {/* Progress bar */}
      <Progress
        percent={Math.round(((questionIndex + 1) / totalQuestions) * 100)}
        format={() => t('exam.questionOf', { current: questionIndex + 1, total: totalQuestions })}
        style={{ marginBottom: 16 }}
      />

      {/* Global exam countdown — prominent bar */}
      {globalSecondsLeft != null && (
        <div style={{
          background: globalUrgent ? 'rgba(255,77,79,0.1)' : 'rgba(22,119,255,0.08)',
          border: `1px solid ${globalUrgent ? 'rgba(255,77,79,0.4)' : 'rgba(22,119,255,0.25)'}`,
          borderRadius: 8,
          padding: '10px 16px',
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <Space>
            <ClockCircleOutlined style={{ color: globalUrgent ? '#ff4d4f' : '#1677ff', fontSize: 16 }} />
            <Text style={{ color: globalUrgent ? '#ff4d4f' : undefined }}>
              {t('exam.timeRemaining')}
            </Text>
          </Space>
          <Text strong style={{ fontSize: 20, fontVariantNumeric: 'tabular-nums', color: globalUrgent ? '#ff4d4f' : '#1677ff' }}>
            {formatSeconds(globalSecondsLeft)}
          </Text>
        </div>
      )}

      {/* Per-question timer tag */}
      {questionSecondsLeft != null && (
        <div style={{ marginBottom: 8 }}>
          <Tag
            icon={<ClockCircleOutlined />}
            color={qUrgent ? 'red' : 'orange'}
            style={{ fontSize: 13, padding: '3px 10px' }}
          >
            {t('exam.questionTimeRemaining')}: {formatSeconds(questionSecondsLeft)}
          </Tag>
        </div>
      )}

      <Card bordered={false}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {question.question_image_url && (
            <img
              src={question.question_image_url}
              alt="question"
              style={{ maxWidth: '100%', borderRadius: 8 }}
            />
          )}
          <RichTextRenderer content={question.text} isDark={theme === 'dark'} />

          <Radio.Group
            value={selectedAnswer}
            onChange={(e) => onAnswerSelect(e.target.value)}
            style={{ width: '100%' }}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {(question.options || []).map((opt, idx) => (
                <Radio
                  key={idx}
                  value={idx}
                  className={`exam-radio-option${selectedAnswer === idx ? ' selected' : ''}`}
                >
                  <Space>
                    {question.option_images?.[String.fromCharCode(65 + idx)] && (
                      <img
                        src={question.option_images[String.fromCharCode(65 + idx)]}
                        alt={`option ${idx}`}
                        style={{ height: 40, width: 40, objectFit: 'cover', borderRadius: 4 }}
                      />
                    )}
                    {opt?.startsWith('<')
                      ? <span dangerouslySetInnerHTML={{ __html: opt }} />
                      : opt}
                  </Space>
                </Radio>
              ))}
            </Space>
          </Radio.Group>

          <Row justify="space-between" style={{ marginTop: 8 }}>
            <Col>
              {!hasPerQuestionTimers && questionIndex > 0 && (
                <Button icon={<ArrowLeftOutlined />} onClick={onPrev}>
                  {t('exam.questionOf', { current: questionIndex, total: totalQuestions })}
                </Button>
              )}
            </Col>
            <Col>
              {isLast ? (
                <Button
                  type="primary"
                  onClick={onSubmit}
                  loading={saving}
                  icon={<CheckCircleOutlined />}
                >
                  {t('exam.submitExam')}
                </Button>
              ) : (
                <Button
                  type="primary"
                  onClick={onNext}
                  loading={saving}
                  icon={<ArrowRightOutlined />}
                >
                  {t('common.next', 'Next')}
                </Button>
              )}
            </Col>
          </Row>
        </Space>
      </Card>
    </div>
  )
}

// ── Score Screen ─────────────────────────────────────────────────────────────

function ScoreScreen({ result, quizTitle, participantEmail, onBack }) {
  const { t } = useTranslation()
  return (
    <div style={{ maxWidth: 480, margin: '0 auto', textAlign: 'center', paddingTop: 40 }}>
      <Card bordered={false}>
        <TrophyOutlined style={{ fontSize: 56, color: '#faad14', marginBottom: 16 }} />
        <Title level={2} style={{ marginBottom: 4 }}>{t('exam.yourScore')}</Title>
        <Title level={1} style={{ color: '#1890ff', marginTop: 0, marginBottom: 24 }}>
          {result.total_score} / {result.max_score}
        </Title>
        {participantEmail && (
          <Alert
            type="info"
            showIcon
            message={t('exam.reportPendingEmail')}
            style={{ marginBottom: 24, textAlign: 'left' }}
          />
        )}
        <Button icon={<CloseCircleOutlined />} onClick={() => { window.close(); setTimeout(() => onBack(), 300) }}>
          {t('exam.closeWindow', 'Close')}
        </Button>
      </Card>
      <PromoCard />
    </div>
  )
}

// ── Main ExamSession ─────────────────────────────────────────────────────────

export default function ExamSession() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [phase, setPhase] = useState('loading') // loading | status | start | taking | score | error
  const [examInfo, setExamInfo] = useState(null)
  const [examResult, setExamResult] = useState(null)
  const [participantEmail, setParticipantEmail] = useState(null)
  const [error, setError] = useState(null)
  const [startError, setStartError] = useState(null) // inline error on the start screen (e.g. wrong OTP)
  const [proctoringConfig, setProctoringConfig] = useState(null)

  // Ref populated by ProctoringGate/useWebcamMonitor — called just before submit to capture final snapshot
  const captureSnapshotRef = useRef(null)

  // Exam state
  const [sessionToken, setSessionToken] = useState(null)
  const [startedAt, setStartedAt] = useState(null)
  const [questions, setQuestions] = useState([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState({}) // questionId -> selectedOptionIndex
  const [expiredQuestions, setExpiredQuestions] = useState(new Set()) // question ids that timed out

  // Timers
  const [globalSecondsLeft, setGlobalSecondsLeft] = useState(null)
  const [questionSecondsLeft, setQuestionSecondsLeft] = useState(null)
  const globalTimerRef = useRef(null)
  const questionTimerRef = useRef(null)

  const [starting, setStarting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [recoveryToken, setRecoveryToken] = useState(null)
  const [recovering, setRecovering] = useState(false)

  // ── Load exam info ────────────────────────────────────────────────────────

  useEffect(() => {
    const load = async () => {
      try {
        const res = await examAPI.getInfo(slug)
        setExamInfo(res.data)
        if (res.data.status === 'open') {
          // Fetch proctoring config so StartScreen can show the rules preview
          if (res.data.quiz_id) {
            try {
              const pcRes = await proctoringAPI.getConfig(res.data.quiz_id)
              setProctoringConfig(pcRes.data)
            } catch {
              // Non-fatal; proctoring config may not exist for all exams
            }
          }
          setPhase('start')
          // Check for an interrupted session from a previous tab crash
          try {
            const saved = localStorage.getItem(`exam_session_${slug}`)
            if (saved) {
              const { sessionToken: tok } = JSON.parse(saved)
              if (tok) setRecoveryToken(tok)
            }
          } catch {
            localStorage.removeItem(`exam_session_${slug}`)
          }
        } else {
          setPhase('status')
        }
      } catch (err) {
        if (err.response?.status === 404) {
          setError(t('exam.examNotFound'))
        } else {
          setError(err.response?.data?.detail || t('common.error'))
        }
        setPhase('error')
      }
    }
    load()
  }, [slug, t])

  // ── Global timer ──────────────────────────────────────────────────────────

  const stopGlobalTimer = useCallback(() => {
    if (globalTimerRef.current) {
      clearInterval(globalTimerRef.current)
      globalTimerRef.current = null
    }
  }, [])

  const startGlobalTimer = useCallback((timeLimitSeconds, startedAtDate) => {
    stopGlobalTimer()
    // Backend returns naive UTC datetimes (no 'Z'/'+ offset'); force UTC parsing
    const utcStr = String(startedAtDate).replace(' ', 'T').replace(/Z?$/, 'Z').replace('ZZ', 'Z')
    const elapsed = (Date.now() - new Date(utcStr).getTime()) / 1000
    const remaining = Math.max(0, Math.floor(timeLimitSeconds - elapsed))
    setGlobalSecondsLeft(remaining)

    globalTimerRef.current = setInterval(() => {
      setGlobalSecondsLeft(prev => {
        if (prev <= 1) {
          stopGlobalTimer()
          // Auto-submit
          handleAutoSubmit()
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }, [stopGlobalTimer])

  // ── Per-question timer ────────────────────────────────────────────────────

  const stopQuestionTimer = useCallback(() => {
    if (questionTimerRef.current) {
      clearInterval(questionTimerRef.current)
      questionTimerRef.current = null
    }
    setQuestionSecondsLeft(null)
  }, [])

  const startQuestionTimer = useCallback((maxSeconds, questionId) => {
    stopQuestionTimer()
    setQuestionSecondsLeft(maxSeconds)

    questionTimerRef.current = setInterval(() => {
      setQuestionSecondsLeft(prev => {
        if (prev <= 1) {
          stopQuestionTimer()
          // Mark question as expired and auto-advance
          setExpiredQuestions(old => new Set([...old, questionId]))
          setCurrentIdx(ci => ci + 1 < questions.length ? ci + 1 : ci)
          return 0
        }
        return prev - 1
      })
    }, 1000)
  }, [stopQuestionTimer, questions.length])

  // Restart question timer when question changes
  useEffect(() => {
    if (phase !== 'taking') return
    const q = questions[currentIdx]
    if (!q) return
    if (q.max_time_seconds && !expiredQuestions.has(q.id)) {
      startQuestionTimer(q.max_time_seconds, q.id)
    } else {
      stopQuestionTimer()
    }
    return () => stopQuestionTimer()
  }, [currentIdx, phase, questions, expiredQuestions, startQuestionTimer, stopQuestionTimer])

  useEffect(() => {
    return () => {
      stopGlobalTimer()
      stopQuestionTimer()
    }
  }, [stopGlobalTimer, stopQuestionTimer])

  // ── Auto-submit (global timer expiry) ────────────────────────────────────

  const handleAutoSubmit = useCallback(async () => {
    if (!sessionToken) return
    try {
      const res = await examAPI.submit(slug, sessionToken)
      try { localStorage.removeItem(`exam_session_${slug}`) } catch {}
      setExamResult(res.data)
      setPhase('score')
    } catch (err) {
      setPhase('error')
      setError(t('exam.sessionExpired'))
    }
  }, [sessionToken, slug, t])

  // ── Start exam ────────────────────────────────────────────────────────────

  const handleStart = async (displayName, email, otp) => {
    setStarting(true)
    const body = { display_name: displayName }
    if (email) body.email = email
    if (otp) body.otp = otp
    try {
      const res = await examAPI.start(slug, body)
      const data = res.data
      setSessionToken(data.session_token)
      try { localStorage.setItem(`exam_session_${slug}`, JSON.stringify({ sessionToken: data.session_token })) } catch {}
      setParticipantEmail(email || null)
      setStartedAt(data.started_at)
      setQuestions(data.questions)
      setCurrentIdx(0)

      if (data.time_limit_seconds) {
        startGlobalTimer(data.time_limit_seconds, data.started_at)
      }

      setPhase('taking')
    } catch (err) {
      const detail = err.response?.data?.detail || ''
      const status  = err.response?.status
      if (status === 403 || detail.includes('abandoned') || detail.includes('already')) {
        setError(t('exam.alreadyAttempted'))
        setPhase('error')
      } else if (status === 400 && (detail.toLowerCase().includes('otp') || detail.toLowerCase().includes('email'))) {
        // OTP or email error — show inline, keep the user on the start/OTP screen
        setStartError(detail)
      } else {
        setError(detail || t('common.error'))
        setPhase('error')
      }
    } finally {
      setStarting(false)
    }
  }

  // ── Save answer ───────────────────────────────────────────────────────────

  const handleAnswerSelect = (optionIndex) => {
    const q = questions[currentIdx]
    setAnswers(prev => ({ ...prev, [q.id]: optionIndex }))
    // Fire-and-forget save
    examAPI.saveAnswer(slug, {
      session_token: sessionToken,
      question_id: q.id,
      selected_option_index: optionIndex,
    }).catch(() => {})
  }

  // ── Navigation ────────────────────────────────────────────────────────────

  const handleNext = async () => {
    setSaving(true)
    try {
      const q = questions[currentIdx]
      const optIdx = answers[q.id] ?? null
      await examAPI.saveAnswer(slug, {
        session_token: sessionToken,
        question_id: q.id,
        selected_option_index: optIdx,
      })
      setCurrentIdx(ci => Math.min(ci + 1, questions.length - 1))
    } catch {
      // ignore
    } finally {
      setSaving(false)
    }
  }

  const handlePrev = () => {
    const hasPerQ = questions.some(q => q.max_time_seconds)
    if (!hasPerQ) {
      setCurrentIdx(ci => Math.max(ci - 1, 0))
    }
  }

  // ── Submit ────────────────────────────────────────────────────────────────

  const handleSubmit = () => {
    Modal.confirm({
      title: t('exam.submitExam'),
      content: t('exam.submitConfirm'),
      okText: t('common.submit'),
      cancelText: t('common.cancel'),
      onOk: async () => {
        setSaving(true)
        try {
          // Save current answer first
          const q = questions[currentIdx]
          const optIdx = answers[q.id] ?? null
          await examAPI.saveAnswer(slug, {
            session_token: sessionToken,
            question_id: q.id,
            selected_option_index: optIdx,
          })
          // Final webcam snapshot before submit
          captureSnapshotRef.current?.()
          // Submit
          const res = await examAPI.submit(slug, sessionToken)
          try { localStorage.removeItem(`exam_session_${slug}`) } catch {}
          stopGlobalTimer()
          stopQuestionTimer()
          setExamResult(res.data)
          setPhase('score')
        } catch (err) {
          setError(err.response?.data?.detail || t('common.error'))
          setPhase('error')
        } finally {
          setSaving(false)
        }
      }
    })
  }

  // ── Crash recovery submit ────────────────────────────────────────────────

  const handleRecoverySubmit = async () => {
    setRecovering(true)
    try {
      const res = await examAPI.submit(slug, recoveryToken)
      localStorage.removeItem(`exam_session_${slug}`)
      setExamResult(res.data)
      setPhase('score')
    } catch {
      localStorage.removeItem(`exam_session_${slug}`)
      setRecoveryToken(null)
    } finally {
      setRecovering(false)
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  const hasPerQuestionTimers = questions.some(q => q.max_time_seconds)

  return (
    <div className="exam-session">
      <PublicBrandHeader />
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '24px 16px' }}>
        {phase === 'loading' && (
          <div style={{ textAlign: 'center', paddingTop: 80 }}>
            <Spin size="large" />
          </div>
        )}

        {phase === 'error' && (
          <Result
            status="error"
            title={t('common.error')}
            subTitle={error}
            extra={
              <Button onClick={() => navigate('/')}>{t('exam.backToDashboard')}</Button>
            }
          />
        )}

        {phase === 'status' && examInfo && (
          <StatusScreen info={examInfo} />
        )}

        {phase === 'start' && recoveryToken && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message={t('exam.recoveryTitle')}
            description={t('exam.recoveryDesc')}
            action={
              <Space>
                <Button size="small" type="primary" loading={recovering} onClick={handleRecoverySubmit}>
                  {t('exam.recoverySubmit')}
                </Button>
                <Button size="small" onClick={() => { localStorage.removeItem(`exam_session_${slug}`); setRecoveryToken(null) }}>
                  {t('common.dismiss')}
                </Button>
              </Space>
            }
          />
        )}

        {phase === 'start' && examInfo && (
          <StartScreen
            info={examInfo}
            proctoringConfig={proctoringConfig}
            onStart={handleStart}
            loading={starting}
            startError={startError}
            onClearStartError={() => setStartError(null)}
          />
        )}

        {phase === 'taking' && questions.length > 0 && (
          <ProctoringProvider quizId={examInfo?.quiz_id} sessionToken={sessionToken} onAutoSubmit={handleAutoSubmit}>
            <ProctoringGate initialWarned={!!proctoringConfig} examDurationSeconds={examInfo?.exam_time_limit_seconds} captureRef={captureSnapshotRef}>
              <QuestionScreen
                question={questions[currentIdx]}
                questionIndex={currentIdx}
                totalQuestions={questions.length}
                selectedAnswer={answers[questions[currentIdx]?.id] ?? null}
                onAnswerSelect={handleAnswerSelect}
                onNext={handleNext}
                onPrev={handlePrev}
                onSubmit={handleSubmit}
                globalSecondsLeft={globalSecondsLeft}
                questionSecondsLeft={questionSecondsLeft}
                hasPerQuestionTimers={hasPerQuestionTimers}
                saving={saving}
              />
            </ProctoringGate>
          </ProctoringProvider>
        )}

        {phase === 'score' && examResult && (
          <ScoreScreen result={examResult} quizTitle={examInfo?.title} participantEmail={participantEmail} onBack={() => navigate('/')} />
        )}
      </div>
    </div>
  )
}
