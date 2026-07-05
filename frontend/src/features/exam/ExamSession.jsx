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
  Modal, Badge, message
} from 'antd'
import {
  ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined,
  QuestionCircleOutlined, ArrowRightOutlined, ArrowLeftOutlined,
  TrophyOutlined, MinusCircleOutlined, PlusCircleOutlined, InfoCircleOutlined,
  FlagOutlined, SaveOutlined, MailOutlined, UnorderedListOutlined,
  DownloadOutlined, ShareAltOutlined, CopyOutlined, LinkedinFilled,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { examAPI, proctoringAPI } from '../../services/api'
import PublicBrandHeader from '../../components/PublicBrandHeader'
import RichTextRenderer from '../quiz/components/RichTextRenderer'
import CodeEditor from '../quiz/components/CodeEditor'
import PromoCard from '../../components/PromoCard'
import { VisitorThemeContext } from '../../App'
import { ProctoringProvider, ProctoringGate } from '../proctoring'
import useWakeLock from '../../hooks/useWakeLock'
import dayjs from 'dayjs'
import VideoEmbed from '../quiz/components/VideoEmbed'

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

// ── Question Palette ─────────────────────────────────────────────────────────

function QuestionPalette({ questions, answers, flagged, currentIdx, onNavigate, collapsed, onToggle }) {
  const { t } = useTranslation()
  const answered = questions.filter((q) => answers[q.id] != null).length
  const flaggedCount = flagged.size

  return (
    <nav aria-label={t('exam.paletteTitle', 'Questions')} style={{ marginBottom: 12, border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
      <div
        role="button"
        tabIndex={0}
        aria-expanded={!collapsed}
        onClick={onToggle}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle() } }}
        style={{ padding: '8px 14px', background: '#f8fafc', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
      >
        <Space>
          <UnorderedListOutlined />
          <Text strong style={{ fontSize: 13 }}>
            {t('exam.paletteTitle', 'Questions')}
          </Text>
          <Tag color="green" style={{ fontSize: 11 }}>{answered}/{questions.length} {t('exam.answered', 'answered')}</Tag>
          {flaggedCount > 0 && <Tag color="orange" icon={<FlagOutlined />} style={{ fontSize: 11 }}>{flaggedCount} {t('exam.flagged', 'flagged')}</Tag>}
        </Space>
        <Text type="secondary" style={{ fontSize: 12 }}>{collapsed ? '▼' : '▲'}</Text>
      </div>
      {!collapsed && (
        <div style={{ padding: '10px 12px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {questions.map((q, i) => {
            const isAnswered = answers[q.id] != null
            const isFlagged = flagged.has(q.id)
            const isCurrent = i === currentIdx
            let btnStyle = { minWidth: 36, fontWeight: isCurrent ? 700 : 400 }
            let btnType = 'default'
            if (isCurrent) { btnType = 'primary' }
            else if (isFlagged) { btnStyle = { ...btnStyle, background: '#fff7e6', borderColor: '#ffa940', color: '#fa8c16' } }
            else if (isAnswered) { btnStyle = { ...btnStyle, background: '#f6ffed', borderColor: '#95de64', color: '#389e0d' } }
            return (
              <Button
                key={q.id}
                size="small"
                type={btnType}
                style={btnStyle}
                onClick={() => onNavigate(i)}
                aria-label={`${t('quiz.question')} ${i + 1}${isCurrent ? ` (${t('exam.current', 'current')})` : ''}${isAnswered ? ` (${t('exam.answered', 'answered')})` : ''}${isFlagged ? ` (${t('exam.flagged', 'flagged')})` : ''}`}
                aria-current={isCurrent ? 'true' : undefined}
              >
                {i + 1}
              </Button>
            )
          })}
        </div>
      )}
    </nav>
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
  isFlagged,
  onToggleFlag,
  slug,
  sessionToken,
}) {
  const { t } = useTranslation()
  const { theme } = useContext(VisitorThemeContext)
  const [runResult, setRunResult] = useState(null)
  const [running, setRunning] = useState(false)
  const isLast = questionIndex === totalQuestions - 1
  const isCode = question.question_type === 'code'
  const isSingleLine = question.question_type === 'single_line'

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

      <Card
        bordered={true}
        style={{ borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.08)' }}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <VideoEmbed url={question.question_video_url} />
          {question.question_image_url && (
            <img
              src={question.question_image_url}
              alt="question"
              style={{ maxWidth: '100%', borderRadius: 8 }}
            />
          )}

          {/* Question text with CODE badge */}
          <div>
            {isCode && (
              <Tag color="purple" style={{ marginBottom: 8 }}>
                {t('questionTypes.code', 'Code')}
              </Tag>
            )}
            <RichTextRenderer content={question.text} isDark={theme === 'dark'} />
          </div>

          {isCode ? (() => {
            let parsed = { language: question.options?.[0] || 'python', code: '' }
            if (selectedAnswer && typeof selectedAnswer === 'string') {
              try { parsed = JSON.parse(selectedAnswer) } catch (_) {}
            }

            const handleRunCode = async () => {
              if (!parsed.code.trim()) return
              setRunning(true)
              setRunResult(null)
              try {
                const res = await examAPI.runCode(slug, {
                  session_token: sessionToken,
                  question_id: question.id,
                  language: parsed.language,
                  code: parsed.code,
                })
                setRunResult(res.data)
                setTimeout(() => {
                  document.getElementById('run-result-anchor')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
                }, 100)
              } catch (e) {
                const status = e?.response?.status
                const msg = status === 429
                  ? 'Too many requests — wait a moment and try again'
                  : (e?.response?.data?.detail || e?.response?.data?.error || 'Evaluation failed')
                setRunResult({ verdict: 'ERR', output: '', explanation: msg })
              } finally {
                setRunning(false)
              }
            }

            const VERDICT_META = {
              AC:  { label: '✓ Correct',             color: '#3fb950' },
              WA:  { label: '✗ Wrong Answer',         color: '#f85149' },
              CE:  { label: '✗ Compilation Error',    color: '#f85149' },
              RE:  { label: '✗ Runtime Error',        color: '#e3b341' },
              TLE: { label: '✗ Time Limit Exceeded',  color: '#1677ff' },
            }

            return (
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <CodeEditor
                  code={parsed.code}
                  language={parsed.language}
                  allowedLanguages={question.options || ['python']}
                  isDark={theme === 'dark'}
                  onChange={(code) => { setRunResult(null); onAnswerSelect(JSON.stringify({ language: parsed.language, code })) }}
                  onLanguageChange={(lang) => { setRunResult(null); onAnswerSelect(JSON.stringify({ language: lang, code: parsed.code })) }}
                />
                {/* Run code result */}
                {runResult && (
                  <div id="run-result-anchor" style={{
                    border: '1px solid #30363d',
                    borderRadius: 8,
                    background: '#161b22',
                    padding: '10px 14px',
                    fontFamily: 'monospace',
                    fontSize: 13,
                  }}>
                    {runResult.verdict === 'ERR' ? (
                      <Text style={{ color: '#e3b341' }}>⚠ Evaluator busy — try again in a moment</Text>
                    ) : (
                      <Space direction="vertical" size={6} style={{ width: '100%' }}>
                        <Space>
                          <Text style={{ color: '#8b949e' }}>Result:</Text>
                          <Text style={{ color: VERDICT_META[runResult.verdict]?.color || '#e6edf3', fontWeight: 600 }}>
                            {VERDICT_META[runResult.verdict]?.label || runResult.verdict}
                          </Text>
                        </Space>
                        {runResult.output && (
                          <div>
                            <Text style={{ color: '#8b949e' }}>Output:</Text>
                            <pre style={{ margin: '4px 0 0 0', color: '#e6edf3', whiteSpace: 'pre-wrap', fontSize: 13, maxHeight: 140, overflowY: 'auto' }}>
                              {runResult.output}
                            </pre>
                          </div>
                        )}
                      </Space>
                    )}
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Button
                    onClick={handleRunCode}
                    loading={running}
                    disabled={!parsed.code.trim()}
                    icon={<PlayCircleOutlined />}
                    style={{ background: '#52c41a', borderColor: '#52c41a', color: '#fff' }}
                  >
                    {running ? t('quiz.evaluating', 'Evaluating...') : 'Run Code'}
                  </Button>
                </div>
              </Space>
            )
          })() : isSingleLine ? (
            <Input
              value={selectedAnswer || ''}
              onChange={(e) => onAnswerSelect(e.target.value)}
              placeholder="Type your answer here…"
              size="large"
              style={{ fontSize: 15 }}
            />
          ) : (
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
                    {opt?.includes('</')
                      ? <span dangerouslySetInnerHTML={{ __html: opt }} />
                      : opt}
                  </Space>
                </Radio>
              ))}
            </Space>
          </Radio.Group>
          )}

          <Row justify="space-between" align="middle" style={{ marginTop: 8 }}>
            <Col>
              {/* Flag only shown for non-code questions */}
              {!isCode && (
                <Space>
                  {!hasPerQuestionTimers && questionIndex > 0 && (
                    <Button icon={<ArrowLeftOutlined />} onClick={onPrev}>
                      {t('exam.questionOf', { current: questionIndex, total: totalQuestions })}
                    </Button>
                  )}
                  <Button
                    icon={<FlagOutlined />}
                    onClick={() => onToggleFlag(question.id)}
                    style={isFlagged ? { color: '#fa8c16', borderColor: '#ffa940', background: '#fff7e6' } : {}}
                  >
                    {isFlagged ? t('exam.flagged', 'Flagged') : t('exam.flagForReview', 'Flag')}
                  </Button>
                </Space>
              )}
              {isCode && !hasPerQuestionTimers && questionIndex > 0 && (
                <Button icon={<ArrowLeftOutlined />} onClick={onPrev}>
                  {t('exam.questionOf', { current: questionIndex, total: totalQuestions })}
                </Button>
              )}
            </Col>
            <Col>
              <Space align="center">
                {saving && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <SaveOutlined spin style={{ marginRight: 4 }} />{t('exam.saving', 'Saving…')}
                  </Text>
                )}
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
              </Space>
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
  const pct = result.max_score > 0 ? Math.round((result.total_score / result.max_score) * 100) : 0
  const certToken = result.certificate_token || null
  const apiBase = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/api\/v1$/, '')
  const shareUrl = certToken ? `${window.location.origin}/cert/${certToken}` : null

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareUrl).then(() => {
      message.success('Link copied!')
    })
  }

  return (
    <div style={{ maxWidth: 520, margin: '0 auto', paddingTop: 32 }}>
      <Card bordered={false} style={{ textAlign: 'center' }}>
        <TrophyOutlined style={{ fontSize: 64, color: '#faad14', marginBottom: 12 }} />
        <Title level={2} style={{ marginBottom: 4, fontFamily: "'Fraunces', Georgia, serif" }}>
          {t('exam.submitted', 'Submitted!')}
        </Title>
        {quizTitle && <Text type="secondary" style={{ display: 'block', marginBottom: 20 }}>{quizTitle}</Text>}
        <Row gutter={24} justify="center" style={{ marginBottom: 24 }}>
          <Col>
            <Statistic
              title={t('exam.yourScore')}
              value={result.total_score}
              suffix={`/ ${result.max_score}`}
              valueStyle={{ color: '#1677ff', fontFamily: "'Fraunces', Georgia, serif" }}
            />
          </Col>
          <Col>
            <Statistic
              title={t('exam.percentage', 'Score %')}
              value={pct}
              suffix="%"
              valueStyle={{ color: pct >= 70 ? '#52c41a' : pct >= 40 ? '#faad14' : '#ff4d4f', fontFamily: "'Fraunces', Georgia, serif" }}
            />
          </Col>
        </Row>

        {/* Certificate section */}
        {certToken && (
          <Card
            size="small"
            style={{ marginBottom: 20, background: 'linear-gradient(135deg, #f0f5ff 0%, #e6f7ff 100%)', border: '1px solid #adc6ff', borderRadius: 10 }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Text strong style={{ fontSize: 15 }}>🎓 Your certificate is ready</Text>
              <Space wrap justify="center">
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  onClick={() => window.open(`${apiBase}/api/v1/exam/certificate/${certToken}`, '_blank')}
                >
                  Download Certificate
                </Button>
                <Button
                  icon={<LinkedinFilled style={{ color: '#0A66C2' }} />}
                  onClick={() => window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`, '_blank')}
                >
                  Share on LinkedIn
                </Button>
                <Button icon={<CopyOutlined />} onClick={handleCopyLink}>
                  Copy link
                </Button>
              </Space>
            </Space>
          </Card>
        )}

        <Space direction="vertical" style={{ width: '100%', textAlign: 'left', marginBottom: 20 }}>
          <Text strong style={{ display: 'block', marginBottom: 6 }}>{t('exam.whatsNext', 'What happens next?')}</Text>
          <Space>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            <Text>{t('exam.whatsNextSaved', 'Your answers have been saved and locked.')}</Text>
          </Space>
          {participantEmail && (
            <Space>
              <MailOutlined style={{ color: '#1677ff' }} />
              <Text>{t('exam.reportPendingEmail', 'A detailed report will be emailed to you once results are released.')}</Text>
            </Space>
          )}
          <Space>
            <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
            <Text type="secondary">{t('exam.whatsNextHost', 'The host will review and publish results at their discretion.')}</Text>
          </Space>
        </Space>

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

  const [phase, setPhase] = useState('loading') // loading | status | start | taking | submitting | score | timesup | error
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
  const [flagged, setFlagged] = useState(new Set()) // question ids flagged for review
  const [paletteCollapsed, setPaletteCollapsed] = useState(false)
  const [expiredQuestions, setExpiredQuestions] = useState(new Set()) // question ids that timed out

  useWakeLock(phase === 'taking')

  // Timers
  const [globalSecondsLeft, setGlobalSecondsLeft] = useState(null)
  const [questionSecondsLeft, setQuestionSecondsLeft] = useState(null)
  const globalTimerRef = useRef(null)
  const questionTimerRef = useRef(null)
  // Ref so the timer interval always calls the latest handleAutoSubmit (avoids stale closure)
  const handleAutoSubmitRef = useRef(null)

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
            const saved = sessionStorage.getItem(`exam_session_${slug}`)
            if (saved) {
              const { sessionToken: tok } = JSON.parse(saved)
              if (tok) setRecoveryToken(tok)
            }
          } catch {
            sessionStorage.removeItem(`exam_session_${slug}`)
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
          handleAutoSubmitRef.current?.()
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
    setPhase('submitting')  // unmount ProctoringProvider before async call
    stopGlobalTimer()
    stopQuestionTimer()
    try {
      const res = await examAPI.submit(slug, sessionToken)
      try { sessionStorage.removeItem(`exam_session_${slug}`) } catch {}
      setExamResult(res.data)
      setPhase('score')
    } catch (err) {
      // 410 = server already marked completed_at; network errors = same treatment
      setPhase('timesup')
    }
  }, [sessionToken, slug, stopGlobalTimer, stopQuestionTimer])

  // Keep ref pointing at latest handleAutoSubmit so the timer interval is never stale
  useEffect(() => { handleAutoSubmitRef.current = handleAutoSubmit }, [handleAutoSubmit])

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
      try { sessionStorage.setItem(`exam_session_${slug}`, JSON.stringify({ sessionToken: data.session_token })) } catch {}
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
    const isTextAnswer = q.question_type === 'code' || q.question_type === 'single_line'
    examAPI.saveAnswer(slug, {
      session_token: sessionToken,
      question_id: q.id,
      selected_option_index: isTextAnswer ? null : optionIndex,
      text_answer: isTextAnswer ? (typeof optionIndex === 'string' ? optionIndex : null) : null,
    }).catch(() => {})
  }

  // ── Navigation ────────────────────────────────────────────────────────────

  const handleNext = async () => {
    setSaving(true)
    try {
      const q = questions[currentIdx]
      const optIdx = answers[q.id] ?? null
      const isTextAnswer = q.question_type === 'code' || q.question_type === 'single_line'
      await examAPI.saveAnswer(slug, {
        session_token: sessionToken,
        question_id: q.id,
        selected_option_index: isTextAnswer ? null : optIdx,
        text_answer: isTextAnswer ? (typeof optIdx === 'string' ? optIdx : null) : null,
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

  const handleToggleFlag = (questionId) => {
    setFlagged(prev => {
      const next = new Set(prev)
      next.has(questionId) ? next.delete(questionId) : next.add(questionId)
      return next
    })
  }

  const handleNavigatePalette = (idx) => { setCurrentIdx(idx) }

  // ── Submit ────────────────────────────────────────────────────────────────

  const handleSubmit = () => {
    Modal.confirm({
      title: t('exam.submitExam'),
      content: t('exam.submitConfirm'),
      okText: t('common.submit'),
      cancelText: t('common.cancel'),
      onOk: async () => {
        setPhase('submitting')  // unmount ProctoringProvider before async calls
        stopGlobalTimer()
        stopQuestionTimer()
        setSaving(true)
        try {
          // Save current answer first
          const q = questions[currentIdx]
          const optIdx = answers[q.id] ?? null
          const isTextAnswer = q.question_type === 'code' || q.question_type === 'single_line'
          await examAPI.saveAnswer(slug, {
            session_token: sessionToken,
            question_id: q.id,
            selected_option_index: isTextAnswer ? null : optIdx,
            text_answer: isTextAnswer ? (typeof optIdx === 'string' ? optIdx : null) : null,
          })
          // Final webcam snapshot before submit
          captureSnapshotRef.current?.()
          // Submit
          const res = await examAPI.submit(slug, sessionToken)
          try { sessionStorage.removeItem(`exam_session_${slug}`) } catch {}
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
      sessionStorage.removeItem(`exam_session_${slug}`)
      setExamResult(res.data)
      setPhase('score')
    } catch {
      sessionStorage.removeItem(`exam_session_${slug}`)
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
                <Button size="small" onClick={() => { sessionStorage.removeItem(`exam_session_${slug}`); setRecoveryToken(null) }}>
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
          <>
            <QuestionPalette
              questions={questions}
              answers={answers}
              flagged={flagged}
              currentIdx={currentIdx}
              onNavigate={handleNavigatePalette}
              collapsed={paletteCollapsed}
              onToggle={() => setPaletteCollapsed(c => !c)}
            />
            <ProctoringProvider quizId={examInfo?.quiz_id} sessionToken={sessionToken} onAutoSubmit={handleAutoSubmit}>
              <ProctoringGate initialWarned={!!proctoringConfig} examDurationSeconds={examInfo?.exam_time_limit_seconds} captureRef={captureSnapshotRef}>
                <QuestionScreen
                  key={questions[currentIdx]?.id}
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
                  isFlagged={flagged.has(questions[currentIdx]?.id)}
                  onToggleFlag={handleToggleFlag}
                  slug={slug}
                  sessionToken={sessionToken}
                />
              </ProctoringGate>
            </ProctoringProvider>
          </>
        )}

        {phase === 'submitting' && (
          <div style={{ textAlign: 'center', paddingTop: 80 }}>
            <ClockCircleOutlined style={{ fontSize: 56, color: '#faad14', marginBottom: 16 }} />
            <Title level={3}>{t('exam.timesUpTitle')}</Title>
            <Paragraph type="secondary">{t('exam.timesUpSubmitting')}</Paragraph>
            <Spin size="large" />
          </div>
        )}

        {phase === 'timesup' && (
          <Result
            icon={<ClockCircleOutlined style={{ color: '#faad14' }} />}
            title={t('exam.timesUpTitle')}
            subTitle={t('exam.timesUpError')}
            extra={
              <Button type="primary" icon={<CloseCircleOutlined />}
                onClick={() => { window.close(); setTimeout(() => navigate('/'), 300) }}>
                {t('exam.closeWindow')}
              </Button>
            }
          />
        )}

        {phase === 'score' && examResult && (
          <ScoreScreen result={examResult} quizTitle={examInfo?.title} participantEmail={participantEmail} onBack={() => navigate('/')} />
        )}
      </div>
    </div>
  )
}
