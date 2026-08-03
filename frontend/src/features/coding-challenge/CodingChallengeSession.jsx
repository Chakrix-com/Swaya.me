/**
 * CodingChallengeSession — candidate-facing coding-challenge UI
 * Route: /c/:token (public, standalone — not embedded in the general exam-taking UI)
 */
import { useState, useEffect, useRef, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Button, Form, Input, Space, Alert, Spin, Result, Radio, Skeleton,
} from 'antd'
import {
  CheckCircleOutlined, ClockCircleOutlined, LinkOutlined, MailOutlined, CodeOutlined,
  TrophyOutlined, GithubOutlined, RobotOutlined, MobileOutlined, SendOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { codingChallengeAPI } from '../../services/api'
import PublicBrandHeader from '../../components/PublicBrandHeader'
import './CodingChallengeSession.css'

const { Title, Text } = Typography

const POLL_INTERVAL_MS = 5000
const MAX_POLL_MS = 5 * 60 * 1000 // 5 minutes, per the design's capped-poll-duration requirement
const GRACE_SECONDS = 60 // buffer before the countdown starts, so opening the tab doesn't eat into it

function formatMinutes(seconds) {
  if (!seconds) return null
  return Math.round(seconds / 60)
}

// Pulls the challenge's own name (e.g. "Palindrome Checker") out of the host's
// markdown so it can be shown as its own line under the "Problem Statement"
// panel heading instead of buried as an H1 inside the body — and strips it out
// of the body so it isn't rendered twice. There's no separate "challenge name"
// field in the data; this is a best-effort read of the markdown's first
// top-level heading, not a guaranteed contract — a host whose markdown doesn't
// start with one just won't get this line, everything else still works.
function splitProblemStatement(markdown) {
  if (!markdown) return { challengeName: null, body: markdown }
  const lines = markdown.split('\n')
  // A line starting with '#' only looks like a heading if it's not inside a
  // fenced code block (```...```) - e.g. a Python comment like "# raises
  // ValueError" in an example's output would otherwise be misread as the
  // challenge's H1 title, and then stripped out of the body, corrupting the
  // fence (confirmed live: exactly this happened with a "# raises
  // InsufficientFundsError..." comment inside an example).
  let inFence = false
  let h1Index = -1
  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim()
    if (/^```/.test(trimmed)) {
      inFence = !inFence
      continue
    }
    if (!inFence && /^#\s+/.test(trimmed)) {
      h1Index = i
      break
    }
  }
  if (h1Index === -1) return { challengeName: null, body: markdown }
  const challengeName = lines[h1Index].replace(/^#\s+/, '').replace(/^coding challenge:?\s*/i, '').trim()
  const bodyLines = [...lines.slice(0, h1Index), ...lines.slice(h1Index + 1)]
  return { challengeName: challengeName || null, body: bodyLines.join('\n').trim() }
}

function formatCountdown(totalSeconds) {
  const clamped = Math.max(0, totalSeconds)
  const h = Math.floor(clamped / 3600)
  const m = Math.floor((clamped % 3600) / 60)
  const s = clamped % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(s).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

// ── Server-anchored countdown — anchored to workspace_created_at, not a client
// click timestamp, so it survives refreshes and can't drift or be gamed ───────

function useCountdown(workspaceCreatedAt, budgetSeconds) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    if (!workspaceCreatedAt) return
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [workspaceCreatedAt])

  if (!workspaceCreatedAt || !budgetSeconds) return null

  const createdMs = new Date(workspaceCreatedAt).getTime()
  const startMs = createdMs + GRACE_SECONDS * 1000
  const endMs = startMs + budgetSeconds * 1000

  if (now < startMs) {
    return { phase: 'grace', graceRemaining: Math.ceil((startMs - now) / 1000) }
  }
  if (now < endMs) {
    return { phase: 'counting', remaining: Math.ceil((endMs - now) / 1000), totalBudget: budgetSeconds }
  }
  return { phase: 'expired' }
}

function TimerDisplay({ countdown, t }) {
  if (!countdown) return null

  if (countdown.phase === 'grace') {
    return (
      <div className="cc-timer cc-timer--grace">
        <ClockCircleOutlined />
        {t('codingChallenge.timerGrace', 'Your timer starts in {{seconds}}s', { seconds: countdown.graceRemaining })}
      </div>
    )
  }

  if (countdown.phase === 'expired') {
    return (
      <div className="cc-timer cc-timer--danger">
        <ClockCircleOutlined />
        <span>00:00 — {t('codingChallenge.timerExpired', "Time's up — submit whenever you're ready")}</span>
      </div>
    )
  }

  const ratio = countdown.remaining / countdown.totalBudget
  const level = countdown.remaining <= 60 ? 'danger' : ratio <= 0.2 ? 'warning' : 'normal'
  return (
    <div className={`cc-timer cc-timer--${level}`}>
      <ClockCircleOutlined />
      {formatCountdown(countdown.remaining)}
    </div>
  )
}

// ── Column 1 — pure visual journey, no actions ──────────────────────────────

function JourneyColumn({ stepIndex, resultVisibility, t }) {
  const resultLabel = resultVisibility === 'hidden'
    ? t('codingChallenge.stepDone', 'Done')
    : t('codingChallenge.stepResult', 'Result')
  const items = [
    { key: 'verify', label: t('codingChallenge.stepVerify', 'Verify'), icon: <MailOutlined /> },
    { key: 'workspace', label: t('codingChallenge.stepOpenWorkspace', 'Open Workspace'), icon: <CodeOutlined /> },
    { key: 'submit', label: t('codingChallenge.stepSubmit', 'Submit'), icon: <SendOutlined /> },
    { key: 'grading', label: t('codingChallenge.stepGrading', 'Grading'), icon: <SyncOutlined spin={stepIndex === 3} /> },
    { key: 'result', label: resultLabel, icon: <TrophyOutlined /> },
  ]
  // Amazon-style order tracker: one continuous line running straight through
  // every icon's center, filled up to how far progress has actually reached.
  const fillPercent = (stepIndex / (items.length - 1)) * 100

  return (
    <Card bordered={false} className="cc-journey-card cc-col-sticky">
      <Title level={5} className="cc-panel-heading">{t('codingChallenge.journeyHeading', 'Progress Tracker')}</Title>
      <div className="cc-journey-icons">
        <div className="cc-journey-track" />
        <div
          className="cc-journey-track-fill"
          style={{ height: `calc((100% - 38px) * ${fillPercent / 100})` }}
        />
        {items.map((item, i) => {
          // The last step (Result) only ever gets reached once the outcome is
          // actually terminal (see journeyStepIndex above) — so unlike every other
          // step, it should render as done, not "current", once it's lit up.
          const isLast = i === items.length - 1
          const status = i < stepIndex ? 'done' : i === stepIndex ? (isLast ? 'done' : 'current') : 'upcoming'
          return (
            <div className="cc-journey-icon-slot" key={item.key}>
              <div className={`cc-journey-icon-wrap${status === 'current' ? ' cc-journey-icon-wrap--current' : ''}`}>
                <div className={`cc-journey-icon cc-journey-icon--${status}`}>{item.icon}</div>
              </div>
              <Text className={`cc-journey-label cc-journey-label--${status}`}>{item.label}</Text>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

// ── Column 2 — problem statement + repo link, nothing else ─────────────────

function ProblemColumn({ info, t }) {
  const { challengeName, body } = useMemo(
    () => splitProblemStatement(info.problem_statement),
    [info.problem_statement],
  )
  return (
    <Card bordered={false} className="cc-problem-card">
      <Title level={5} className="cc-panel-heading">{t('codingChallenge.problemStatementHeading', 'Problem Statement')}</Title>
      <div className="cc-challenge-name-row">
        {challengeName && <div className="cc-challenge-name">{challengeName}</div>}
        {info.git_repo_url && (
          <a
            className="cc-github-badge"
            href={info.git_repo_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <GithubOutlined />
            {t('codingChallenge.viewRepoLink', 'View starter repo on GitHub')} ↗
          </a>
        )}
      </div>
      <div className="cc-problem-subbox">
        <ReactMarkdown>{body}</ReactMarkdown>
      </div>
    </Card>
  )
}

// ── Column 3 content — guidelines / actions / timer / result, phase-driven ──

function FullGuidelines({ info, t }) {
  const minutes = formatMinutes(info.time_budget_seconds)
  return (
    <Space direction="vertical" size="small" style={{ width: '100%', marginBottom: 16 }}>
      {minutes && (
        <div className="cc-guideline-item">
          <ClockCircleOutlined className="cc-guideline-icon cc-guideline-icon--time" />
          <div>
            <Text strong style={{ display: 'block' }}>{t('codingChallenge.timeBudgetLabel', 'Time budget')}</Text>
            <Text type="secondary">{t('codingChallenge.timeBudgetValue', 'You will have {{minutes}} minutes to complete this challenge, starting once your workspace opens.', { minutes })}</Text>
          </div>
        </div>
      )}
      <div className="cc-guideline-item">
        <CodeOutlined className="cc-guideline-icon cc-guideline-icon--grading" />
        <div>
          <Text strong style={{ display: 'block' }}>{t('codingChallenge.howGradingWorksLabel', 'How grading works')}</Text>
          <Text type="secondary">{t('codingChallenge.howGradingWorksValue', "Your submission is evaluated in two parts: automated test results, and a review of your solution's structure and approach.")}</Text>
        </div>
      </div>
      <div className="cc-guideline-item">
        <RobotOutlined className="cc-guideline-icon cc-guideline-icon--ai" />
        <div>
          <Text strong style={{ display: 'block' }}>{t('codingChallenge.aiTransparencyLabel', 'Using AI assistance')}</Text>
          <Text type="secondary">{t('codingChallenge.aiTransparencyValue', 'You may use the built-in AI coding assistant while working. Both your conversation history and your commit history are reviewed as part of the evaluation.')}</Text>
        </div>
      </div>
    </Space>
  )
}

function StartStep({ info, onStarted, onProvisioning, startError, onClearStartError }) {
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
      // /start now returns fast — either "active" (a returning candidate reconnecting
      // to an already-ready workspace, workspace_url present) or "provisioning" (the
      // normal new-candidate path: a background job is doing the real work, poll
      // /status for readiness instead of waiting on this call).
      if (res.data.status === 'active' && res.data.workspace_url) {
        onStarted(res.data)
      } else {
        onProvisioning(res.data)
      }
    } catch (err) {
      setOtpError(err.response?.data?.detail || t('common.error'))
    } finally {
      setStarting(false)
    }
  }

  if (otpStep === 'form') {
    return (
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
        <Button type="primary" size="large" block loading={sendingOtp} onClick={handleSendOtp}>
          {t('codingChallenge.sendCode')}
        </Button>
      </Space>
    )
  }

  return (
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
  )
}

function ProvisioningStep({ t }) {
  return (
    <div style={{ textAlign: 'center', padding: '32px 0' }}>
      <Spin size="large" />
      <Title level={4} style={{ marginTop: 16 }}>
        {t('codingChallenge.provisioningTitle', 'Setting up your workspace')}
      </Title>
      <Text type="secondary">
        {t('codingChallenge.startingHint', 'Setting up your coding workspace — this can take 4-5 minutes. Please stay on this page.')}
      </Text>
    </div>
  )
}

function WorkspaceStep({ workspaceUrl, onSubmit, submitting, countdown, t }) {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Text type="secondary" style={{ fontSize: 12 }}>
        {t('codingChallenge.aiTransparencyReminder', 'Reminder: your AI chat history and commit history are reviewed as part of grading.')}
      </Text>
      <TimerDisplay countdown={countdown} t={t} />
      <div>
        <Button
          type="default"
          size="large"
          block
          icon={<LinkOutlined />}
          onClick={() => window.open(workspaceUrl, '_blank', 'noopener,noreferrer')}
        >
          {t('codingChallenge.openWorkspace')}
        </Button>
        <div style={{ marginTop: 6 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t('codingChallenge.popupBlockedHint', "Didn't see a new tab open? Your browser may have blocked the pop-up — click the button above to open it directly.")}
          </Text>
        </div>
      </div>
      <Button type="primary" size="large" block loading={submitting} onClick={onSubmit}>
        {t('codingChallenge.submitButton')}
      </Button>
    </Space>
  )
}

function ResultStep({ statusData, timedOut, resultVisibility, t }) {
  if (timedOut) {
    return (
      <Result
        icon={<ClockCircleOutlined />}
        title={t('codingChallenge.pollTimeoutTitle')}
        subTitle={t('codingChallenge.pollTimeoutDesc')}
      />
    )
  }

  const status = statusData?.status

  // Hidden mode never reveals an outcome — success and system-failure paths look
  // identical to the candidate, which is the whole point.
  if (resultVisibility === 'hidden') {
    return (
      <Result
        icon={<CheckCircleOutlined style={{ color: 'var(--sw-success, #22c55e)' }} />}
        title={t('codingChallenge.submittedHiddenTitle', 'Submission received')}
        subTitle={t('codingChallenge.submittedHiddenDesc', "Thanks for completing the challenge. The team will review your submission and follow up with you directly.")}
      />
    )
  }

  if (!statusData || status === 'queued' || status === 'grading' || status === 'not_submitted') {
    return (
      <div style={{ textAlign: 'center', padding: '32px 0' }}>
        <Spin size="large" />
        <Title level={4} style={{ marginTop: 16 }}>{t('codingChallenge.gradingInProgress')}</Title>
        <Text type="secondary">{t('codingChallenge.gradingInProgressDesc')}</Text>
      </div>
    )
  }

  // System-side grading failures are never shown as failures to the candidate —
  // it's never their fault, and raw error detail must never reach them (enforced
  // server-side too, in /status). They see the same calm message as hidden mode.
  if (status === 'failed' || status === 'partial_failed') {
    return (
      <Result
        icon={<CheckCircleOutlined style={{ color: 'var(--sw-success, #22c55e)' }} />}
        title={t('codingChallenge.submittedHiddenTitle', 'Submission received')}
        subTitle={t('codingChallenge.submittedHiddenDesc', "Thanks for completing the challenge. The team will review your submission and follow up with you directly.")}
      />
    )
  }

  if (status === 'graded' && resultVisibility === 'status_only') {
    const positive = statusData.result_signal === 'positive'
    return (
      <Result
        icon={<CheckCircleOutlined style={{ color: positive ? 'var(--sw-success, #22c55e)' : 'var(--sw-warning, #d97706)' }} />}
        title={t('codingChallenge.gradedTitle')}
        subTitle={positive
          ? t('codingChallenge.resultSignalPositive', 'Your submission looks solid. The team will follow up with next steps.')
          : t('codingChallenge.resultSignalNeedsImprovement', "Thanks for submitting. The team will review your work and follow up.")}
      />
    )
  }

  if (status === 'graded') {
    return (
      <Result
        icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
        title={t('codingChallenge.gradedTitle')}
        subTitle={t('codingChallenge.gradedScore', { score: statusData.ai_score, verdict: statusData.ai_verdict })}
      />
    )
  }

  return (
    <Result
      icon={<CheckCircleOutlined style={{ color: 'var(--sw-success, #22c55e)' }} />}
      title={t('codingChallenge.submittedHiddenTitle', 'Submission received')}
      subTitle={t('codingChallenge.submittedHiddenDesc', "Thanks for completing the challenge. The team will review your submission and follow up with you directly.")}
    />
  )
}

function ActionColumn({
  phase, info, statusData, pollTimedOut, startError, onClearStartError, onStarted, onProvisioning,
  workspaceUrl, onSubmit, submitting, countdown, t,
}) {
  let heading = t('codingChallenge.actionGettingStarted', 'Getting Started')
  if (phase === 'provisioning') heading = t('codingChallenge.actionSettingUp', 'Setting Up')
  if (phase === 'started') heading = t('codingChallenge.actionYourWorkspace', 'Your Workspace')
  if (phase === 'grading') heading = t('codingChallenge.actionResult', 'Result')

  return (
    <Card bordered={false} className="cc-action-card cc-col-sticky">
      <Title level={5} className="cc-panel-heading">{heading}</Title>
      <div className="cc-action-content">
        {phase === 'start' && (
          <>
            <FullGuidelines info={info} t={t} />
            <StartStep
              info={info}
              onStarted={onStarted}
              onProvisioning={onProvisioning}
              startError={startError}
              onClearStartError={onClearStartError}
            />
          </>
        )}
        {phase === 'provisioning' && <ProvisioningStep t={t} />}
        {phase === 'started' && (
          <WorkspaceStep workspaceUrl={workspaceUrl} onSubmit={onSubmit} submitting={submitting} countdown={countdown} t={t} />
        )}
        {phase === 'grading' && (
          <ResultStep statusData={statusData} timedOut={pollTimedOut} resultVisibility={info.result_visibility} t={t} />
        )}
      </div>
    </Card>
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
  const [workspaceCreatedAt, setWorkspaceCreatedAt] = useState(null)
  const [effectiveTimeBudgetSeconds, setEffectiveTimeBudgetSeconds] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [statusData, setStatusData] = useState(null)
  const [pollTimedOut, setPollTimedOut] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  const pollTimerRef = useRef(null)
  const pollStartRef = useRef(null)

  const countdown = useCountdown(workspaceCreatedAt, effectiveTimeBudgetSeconds)

  // Hidden mode never reveals a distinct "still grading" state — ResultStep shows
  // the same calm "submitted" card the instant we reach the grading phase, so the
  // journey should jump straight to the final step too, not linger on "Grading".
  const isTerminalStatus = statusData && ['graded', 'partial_failed', 'failed'].includes(statusData.status)
  const journeyStepIndex = phase === 'provisioning' ? 1
    : phase === 'started' ? 2
    : phase === 'grading' ? ((info?.result_visibility === 'hidden' || isTerminalStatus || pollTimedOut) ? 4 : 3)
    : 0

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    setIsMobile(mq.matches)
    const handler = (e) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

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

  // Reuses the same timer/start refs as pollStatus — the two never run
  // concurrently, since 'provisioning' and 'grading' are mutually exclusive
  // phases, so sharing the refs is safe and avoids duplicating the timer
  // bookkeeping. On failure or a timeout, both are treated as "please retry" —
  // sends the candidate back to the OTP form rather than a distinct timeout
  // screen, since a fresh OTP is required for /start to succeed again anyway.
  const failProvisioning = () => {
    clearInterval(pollTimerRef.current)
    setStartError(t('codingChallenge.provisionFailedError', 'Workspace setup failed. Please request a new verification code and try again.'))
    setPhase('start')
  }

  const pollProvisioning = async () => {
    try {
      const res = await codingChallengeAPI.getStatus(token)
      if (res.data.status === 'provision_failed') {
        failProvisioning()
        return
      }
      if (res.data.workspace_url) {
        clearInterval(pollTimerRef.current)
        handleStarted(res.data)
        return
      }
    } catch {
      // transient poll failure — keep trying until the max-duration cap
    }
    if (Date.now() - pollStartRef.current > MAX_POLL_MS) {
      failProvisioning()
    }
  }

  useEffect(() => {
    const load = async () => {
      try {
        const res = await codingChallengeAPI.getInfo(token)
        const infoData = { ...res.data, token }
        setInfo(infoData)

        // Resume-safety: a candidate reopening their own invite link (closed tab,
        // browser crash, switched devices) should land wherever they actually are,
        // not always restart at OTP entry — most importantly, if they've already
        // submitted, /start would otherwise 409 trying to re-provision a workspace
        // that's already gone.
        try {
          const statusRes = await codingChallengeAPI.getStatus(token)
          if (statusRes.data.status === 'provision_failed') {
            // A prior /start's background provisioning never succeeded — send them
            // back to the OTP form (a fresh OTP is required for /start to work
            // again) instead of silently landing on a blank 'start' phase.
            setStartError(t('codingChallenge.provisionFailedError', 'Workspace setup failed. Please request a new verification code and try again.'))
            setPhase('start')
            return
          }
          if (statusRes.data.status !== 'not_submitted') {
            setStatusData(statusRes.data)
            setPhase('grading')
            if (!['graded', 'partial_failed', 'failed'].includes(statusRes.data.status)) {
              pollStartRef.current = Date.now()
              pollTimerRef.current = setInterval(pollStatus, POLL_INTERVAL_MS)
            }
            return
          }
          // Mid-challenge resume (workspace open, not yet submitted): skip OTP
          // entirely and drop them straight back into their workspace + timer,
          // now that /status hands back everything needed to reconstruct that view.
          if (statusRes.data.workspace_url) {
            setWorkspaceUrl(statusRes.data.workspace_url)
            setWorkspaceCreatedAt(statusRes.data.workspace_created_at || null)
            setEffectiveTimeBudgetSeconds(statusRes.data.effective_time_budget_seconds || null)
            setPhase('started')
            return
          }
          // status is 'not_submitted' but no workspace_url yet: a provisioning job
          // is already in flight for this candidate (they called /start, then
          // reloaded/reopened the tab) — resume straight into polling instead of
          // showing the OTP form again.
          setWorkspaceCreatedAt(statusRes.data.workspace_created_at || null)
          setEffectiveTimeBudgetSeconds(statusRes.data.effective_time_budget_seconds || null)
          setPhase('provisioning')
          pollStartRef.current = Date.now()
          pollTimerRef.current = setInterval(pollProvisioning, POLL_INTERVAL_MS)
          return
        } catch {
          // 404 = no workspace yet, a genuinely fresh candidate — fall through to 'start'
        }
        setPhase('start')
      } catch (err) {
        setError(err.response?.data?.detail || t('common.error'))
        setPhase('error')
      }
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => () => clearInterval(pollTimerRef.current), [])

  const handleStarted = (data) => {
    setWorkspaceUrl(data.workspace_url)
    setWorkspaceCreatedAt(data.workspace_created_at || null)
    setEffectiveTimeBudgetSeconds(data.effective_time_budget_seconds || null)
    setPhase('started')
    window.open(data.workspace_url, '_blank', 'noopener,noreferrer')
  }

  const handleProvisioning = (data) => {
    setWorkspaceCreatedAt(data.workspace_created_at || null)
    setEffectiveTimeBudgetSeconds(data.effective_time_budget_seconds || null)
    setPhase('provisioning')
    pollStartRef.current = Date.now()
    pollTimerRef.current = setInterval(pollProvisioning, POLL_INTERVAL_MS)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await codingChallengeAPI.submit(token)
      setPhase('grading')
      // Hidden mode never reveals an outcome, so there's nothing worth polling for —
      // skip straight to the calm "submitted" message instead of a live spinner
      // that implies a reveal is coming.
      if (info.result_visibility !== 'hidden') {
        pollStartRef.current = Date.now()
        pollStatus()
        pollTimerRef.current = setInterval(pollStatus, POLL_INTERVAL_MS)
      }
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="coding-challenge-session">
      <PublicBrandHeader />
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 16px' }}>
        {phase === 'loading' && (
          <div style={{ paddingTop: 24 }}>
            <Skeleton active paragraph={{ rows: 2 }} />
            <Skeleton active paragraph={{ rows: 4 }} style={{ marginTop: 24 }} />
          </div>
        )}

        {phase === 'error' && (
          <Result status="error" title={t('common.error')} subTitle={error} />
        )}

        {info && phase !== 'loading' && phase !== 'error' && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div className="cc-page-header">
              <div className="cc-header-capsule cc-header-capsule--left">
                {t('codingChallenge.eyebrowLabel', 'Coding Challenge')}
              </div>
              <Title level={3} className="cc-page-title">{info.quiz_title}</Title>
              {info.tenant_name && (
                <div className="cc-header-capsule cc-header-capsule--right">
                  {t('codingChallenge.invitedBy', 'Invited by {{name}}', { name: info.tenant_name })}
                </div>
              )}
            </div>

            {isMobile && phase !== 'grading' && (
              <Alert
                type="warning"
                showIcon
                icon={<MobileOutlined />}
                message={t('codingChallenge.mobileWarning', "This challenge needs a full code editor — you'll have a much better experience continuing on a desktop or laptop.")}
              />
            )}

            <div className="cc-columns">
              <JourneyColumn stepIndex={journeyStepIndex} resultVisibility={info.result_visibility} t={t} />
              <ProblemColumn info={info} t={t} />
              <ActionColumn
                phase={phase}
                info={info}
                statusData={statusData}
                pollTimedOut={pollTimedOut}
                startError={startError}
                onClearStartError={() => setStartError(null)}
                onStarted={handleStarted}
                onProvisioning={handleProvisioning}
                workspaceUrl={workspaceUrl}
                onSubmit={handleSubmit}
                submitting={submitting}
                countdown={countdown}
                t={t}
              />
            </div>
          </Space>
        )}
      </div>
    </div>
  )
}
