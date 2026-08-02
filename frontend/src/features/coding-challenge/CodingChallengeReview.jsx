/**
 * CodingChallengeReview — unified candidate pipeline (host-facing)
 * Route: /quiz/coding-challenge-review/:questionId (authenticated host)
 * One row per unique candidate email, spanning the whole journey — invited
 * (pending/expired), started (in progress/abandoned), submitted (queued/
 * grading), through graded/partial/failed — rather than three disconnected
 * views (invite list, workspace list, submission list) the host would
 * otherwise have to piece together themselves.
 * All candidate-originated content (transcript, timeline, test output) is
 * rendered as plain text — never dangerouslySetInnerHTML, matching the
 * project's stance elsewhere.
 */
import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Typography, Table, Tag, Alert, Spin, Result, Button, Space, Empty, Progress, Tooltip, App,
} from 'antd'
import {
  ArrowLeftOutlined, ClockCircleOutlined, SyncOutlined, StopOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined,
  FileTextOutlined, HistoryOutlined, MessageOutlined, ReloadOutlined, SendOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { codingChallengeAPI } from '../../services/api'
import LogModal from './LogModal'
import TranscriptModal from './TranscriptModal'
import MoreActionsMenu from '../../components/MoreActionsMenu'
import SafeConfirm from '../../components/SafeConfirm'

const { Title, Text, Paragraph } = Typography

// Live states — worth auto-refreshing for, since they can change without the
// host doing anything. "pending" is deliberately excluded: nothing changes
// there without a resend, which is a host action that already reloads data.
const LIVE_STATUSES = ['in_progress', 'queued', 'grading']

const STATUS_CONFIG = {
  pending: { color: 'processing', icon: <ClockCircleOutlined /> },
  expired: { color: 'default', icon: <ClockCircleOutlined /> },
  in_progress: { color: 'gold', icon: <SyncOutlined spin /> },
  abandoned: { color: 'default', icon: <StopOutlined /> },
  queued: { color: 'default', icon: <ClockCircleOutlined /> },
  grading: { color: 'processing', icon: <SyncOutlined spin /> },
  graded: { color: 'success', icon: <CheckCircleOutlined /> },
  partial_failed: { color: 'warning', icon: <ExclamationCircleOutlined /> },
  failed: { color: 'error', icon: <CloseCircleOutlined /> },
}

// One accent color per pipeline status, reused for both the Tag (via
// STATUS_CONFIG's antd color name) and the filter chip's active state (via
// this app's own --sw-* tokens) — so a chip and the badges it filters for
// always read as the same color, not an unrelated indigo for every chip.
const STATUS_ACCENT = {
  pending: 'var(--sw-info, #3b82f6)',
  expired: 'var(--sw-text3, #999)',
  in_progress: 'var(--sw-warning, #d97706)',
  abandoned: 'var(--sw-text3, #999)',
  queued: 'var(--sw-text3, #999)',
  grading: 'var(--sw-info, #3b82f6)',
  graded: 'var(--sw-success, #22c55e)',
  partial_failed: 'var(--sw-warning, #d97706)',
  failed: 'var(--sw-error, #ef4444)',
}

const STATUS_LABEL_KEYS = {
  pending: 'codingChallenge.inviteStatusPending',
  expired: 'codingChallenge.inviteStatusExpired',
  in_progress: 'codingChallenge.pipelineInProgress',
  abandoned: 'codingChallenge.pipelineAbandoned',
  queued: 'codingChallenge.pipelineQueued',
  grading: 'codingChallenge.pipelineGrading',
  graded: 'codingChallenge.pipelineGraded',
  partial_failed: 'codingChallenge.pipelinePartial',
  failed: 'codingChallenge.pipelineFailed',
}

const CRITERION_LABELS = {
  functional_correctness: 'codingChallenge.critFunctionalCorrectness',
  ai_usage_efficiency: 'codingChallenge.critAiUsageEfficiency',
  prompt_quality: 'codingChallenge.critPromptQuality',
  validation_discipline: 'codingChallenge.critValidationDiscipline',
  code_quality: 'codingChallenge.critCodeQuality',
  architecture: 'codingChallenge.critArchitecture',
  time_taken: 'codingChallenge.critTimeTaken',
  proctoring: 'codingChallenge.critProctoring',
}

function scoreBand(score) {
  if (score >= 70) return 'var(--sw-success, #22c55e)'
  if (score >= 40) return 'var(--sw-warning, #f59e0b)'
  return 'var(--sw-error, #ef4444)'
}

function StatusTag({ status, t }) {
  const cfg = STATUS_CONFIG[status] || { color: 'default', icon: null }
  return <Tag color={cfg.color} icon={cfg.icon}>{t(STATUS_LABEL_KEYS[status] || status, status)}</Tag>
}

function ScoreCell({ score }) {
  if (score == null) return <Text type="secondary">—</Text>
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 110 }}>
      <Progress percent={score} size="small" showInfo={false} strokeColor={scoreBand(score)} style={{ width: 60 }} />
      <Text strong>{score}</Text>
    </div>
  )
}

function TestsCell({ passed, total }) {
  if (total == null) return <Text type="secondary">—</Text>
  const color = passed === total ? 'success' : passed === 0 ? 'error' : 'warning'
  return <Tag color={color}>{passed}/{total}</Tag>
}

// Functional Correctness/Time Taken/Proctoring are computed straight from
// test results — no AI narrative exists for them. The other 5 are what
// assess_coding_challenge actually judges and writes a rationale about. The
// old UI listed all 8 in one table with one rationale paragraph trailing
// underneath — which, sitting directly below "Functional Correctness" (the
// table's first row), read as if it were explaining that row instead of the
// AI-assessed ones it's actually about.
const DETERMINISTIC_CRITERIA = ['functional_correctness', 'time_taken', 'proctoring']

function breakdownColumns(t) {
  return [
    { title: t('codingChallenge.criterion', 'Criterion'), dataIndex: 'criterion' },
    { title: t('codingChallenge.weight', 'Weight'), dataIndex: 'weight', render: (w) => `${w}%` },
    {
      title: t('codingChallenge.score', 'Score'), dataIndex: 'score',
      render: (s) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Progress percent={s} size="small" showInfo={false} strokeColor={scoreBand(s)} style={{ width: 60 }} />
          <span>{s}</span>
        </div>
      ),
    },
    { title: t('codingChallenge.contribution', 'Contribution'), dataIndex: 'contribution' },
  ]
}

function toRows(breakdown, keys, t) {
  return keys
    .filter((k) => breakdown[k])
    .map((criterion) => ({
      key: criterion,
      criterion: t(CRITERION_LABELS[criterion] || criterion, criterion),
      weight: breakdown[criterion].weight,
      score: breakdown[criterion].score,
      contribution: breakdown[criterion].contribution,
    }))
}

function RationaleText({ rationale }) {
  const points = rationale.split('\n').map((line) => line.trim()).filter(Boolean)
  if (points.length <= 1) {
    return <Paragraph style={{ margin: '4px 0 0', fontSize: 13 }}>{rationale}</Paragraph>
  }
  return (
    <ul style={{ margin: '4px 0 0', paddingLeft: 18, fontSize: 13 }}>
      {points.map((point, i) => (
        <li key={i} style={{ marginBottom: 2 }}>{point}</li>
      ))}
    </ul>
  )
}

function ScoreBreakdownTable({ breakdown, rationale, t }) {
  const deterministicRows = toRows(breakdown, DETERMINISTIC_CRITERIA, t)
  const aiKeys = Object.keys(breakdown).filter((k) => !DETERMINISTIC_CRITERIA.includes(k))
  const aiRows = toRows(breakdown, aiKeys, t)
  const columns = breakdownColumns(t)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {deterministicRows.length > 0 && (
        <div>
          <Text type="secondary" style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4 }}>
            {t('codingChallenge.deterministicSection', 'From test results')}
          </Text>
          <Table dataSource={deterministicRows} pagination={false} size="small" columns={columns} style={{ marginTop: 4 }} />
        </div>
      )}
      {aiRows.length > 0 && (
        <div>
          <Text type="secondary" style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4 }}>
            {t('codingChallenge.aiAssessedSection', 'AI-assessed')}
          </Text>
          <Table dataSource={aiRows} pagination={false} size="small" columns={columns} style={{ marginTop: 4 }} />
          {rationale && (
            <div
              style={{
                marginTop: 8, padding: '10px 12px', borderRadius: 8,
                borderLeft: '3px solid var(--sw-info, #3b82f6)',
                background: 'color-mix(in srgb, var(--sw-info, #3b82f6) 6%, transparent)',
              }}
            >
              <Text strong style={{ fontSize: 11, color: 'var(--sw-info, #3b82f6)' }}>
                {t('codingChallenge.aiAssessmentNotes', 'AI Assessment Notes')}
              </Text>
              <RationaleText rationale={rationale} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function formatTime(iso) {
  return iso ? dayjs(iso).format('MMM D, h:mm A') : null
}

function AttemptPicker({ attempts, selectedIdx, onSelect, t }) {
  return (
    <div>
      <Text type="secondary" style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.4 }}>
        {t('codingChallenge.attemptHistoryHeading', 'Attempt history')}
      </Text>
      <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
        {attempts.map((a, i) => {
          const active = i === selectedIdx
          const cfg = STATUS_CONFIG[a.status] || { color: 'default' }
          return (
            <button
              type="button"
              key={a.attempt_number}
              onClick={() => onSelect(i)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600,
                padding: '4px 10px', borderRadius: 8, cursor: 'pointer',
                border: `1px solid ${active ? 'var(--sw-primary, #6366f1)' : 'var(--sw-border, #d9d9d9)'}`,
                background: active ? 'color-mix(in srgb, var(--sw-primary, #6366f1) 12%, transparent)' : 'transparent',
              }}
            >
              {t('codingChallenge.attemptBadge', 'Attempt {{number}}', { number: a.attempt_number })}
              <Tag color={cfg.color} style={{ margin: 0 }}>{t(STATUS_LABEL_KEYS[a.status] || a.status, a.status)}</Tag>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function CandidateDetail({ entry, hasCustomWeights, t, questionId, onRegraded, onReinvite }) {
  const attempts = entry.attempts && entry.attempts.length > 0
    ? entry.attempts
    : [{ attempt_number: 1, status: entry.status, started_at: entry.started_at, submission: entry.submission }]
  const [selectedIdx, setSelectedIdx] = useState(attempts.length - 1)
  const selected = attempts[Math.min(selectedIdx, attempts.length - 1)]
  const submission = selected.submission
  const [regrading, setRegrading] = useState(false)
  const [confirmReinvite, setConfirmReinvite] = useState(false)
  const { message } = App.useApp()

  const handleRegrade = async () => {
    setRegrading(true)
    try {
      await codingChallengeAPI.regrade(questionId, submission.id)
      message.success(t('codingChallenge.regradeSuccess', 'Regrading complete'))
      onRegraded?.()
    } catch (err) {
      const detail = err.response?.data?.detail
      message.error(typeof detail === 'string' ? detail : t('common.error'))
    } finally {
      setRegrading(false)
    }
  }

  const reinviteAction = onReinvite && (
    <Button
      size="small" icon={<SendOutlined />} disabled={!entry.can_reinvite}
      onClick={() => setConfirmReinvite(true)}
    >
      {t('codingChallenge.reinviteAction', 'Re-invite')}
    </Button>
  )
  const reinviteRow = reinviteAction && (
    <div>
      {entry.can_reinvite ? reinviteAction : (
        <Tooltip title={t('codingChallenge.reinviteDisabledReason', 'Available once the current attempt is submitted or expires.')}>
          <span>{reinviteAction}</span>
        </Tooltip>
      )}
      <SafeConfirm
        open={confirmReinvite}
        danger={false}
        title={t('codingChallenge.reinviteConfirmTitle', 'Re-invite {{email}}?', { email: entry.candidate_email })}
        description={t('codingChallenge.reinviteConfirmDesc', 'This starts Attempt {{number}} for this candidate.', { number: (entry.attempt_count || 0) + 1 })}
        okText={t('codingChallenge.reinviteAction', 'Re-invite')}
        cancelText={t('common.cancel', 'Cancel')}
        onConfirm={() => { onReinvite(entry); setConfirmReinvite(false) }}
        onCancel={() => setConfirmReinvite(false)}
      />
    </div>
  )

  if (!submission) {
    const messages = {
      pending: t('codingChallenge.pipelinePendingDesc', 'Invited on {{time}} — hasn\'t opened the link yet.', { time: formatTime(entry.invited_at) }),
      expired: t('codingChallenge.pipelineExpiredDesc', 'Invited on {{time}} — the link has expired without being used. Resend from the Invite Candidates panel.', { time: formatTime(entry.invited_at) }),
      in_progress: t('codingChallenge.pipelineInProgressDesc', 'Started on {{time}} — still working, hasn\'t submitted yet.', { time: formatTime(selected.started_at) }),
      abandoned: t('codingChallenge.pipelineAbandonedDesc', 'Started on {{time}} but the workspace was abandoned before submitting.', { time: formatTime(selected.started_at) }),
    }
    return (
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {attempts.length > 1 && <AttemptPicker attempts={attempts} selectedIdx={selectedIdx} onSelect={setSelectedIdx} t={t} />}
        <Alert type="info" showIcon message={messages[selected.status] || t('codingChallenge.notSubmittedYet', 'Not submitted yet')} />
        {reinviteRow}
      </Space>
    )
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {attempts.length > 1 && <AttemptPicker attempts={attempts} selectedIdx={selectedIdx} onSelect={setSelectedIdx} t={t} />}
      {submission.status === 'partial_failed' && submission.error_message && (
        <Alert
          type="warning"
          showIcon
          message={t('codingChallenge.partialFailedTitle', 'Graded with a partial result')}
          description={
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text>{submission.error_message}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('codingChallenge.partialFailedRecoverable', 'The candidate\'s code, tests, and AI transcript were all captured successfully — only the AI scoring step failed. This can be safely retried.')}
              </Text>
              <Button size="small" icon={<ReloadOutlined />} loading={regrading} onClick={handleRegrade}>
                {t('codingChallenge.regradeButton', 'Regrade')}
              </Button>
            </Space>
          }
        />
      )}
      {submission.status === 'failed' && submission.error_message && (
        <Alert
          type="error"
          showIcon
          message={t('codingChallenge.failedTitle', 'Grading could not be completed')}
          description={
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text>{submission.error_message}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t('codingChallenge.failedUnrecoverable', 'The candidate\'s work could not be captured before this failure — there\'s nothing to regrade. Re-invite the candidate to try again.')}
              </Text>
            </Space>
          }
        />
      )}

      {submission.score_breakdown && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Title level={5} style={{ margin: 0 }}>{t('codingChallenge.scoreBreakdown', 'Score Breakdown')}</Title>
            <Tooltip title={hasCustomWeights
              ? t('codingChallenge.customWeightsHint', 'This challenge uses host-overridden scoring weights.')
              : t('codingChallenge.defaultWeightsHint', 'This challenge uses the platform default scoring weights.')}
            >
              <Tag color={hasCustomWeights ? 'purple' : 'default'} style={{ cursor: 'help' }}>
                {hasCustomWeights ? t('codingChallenge.customWeights', 'Custom weights') : t('codingChallenge.platformDefault', 'Platform default')}
              </Tag>
            </Tooltip>
          </div>
          <ScoreBreakdownTable breakdown={submission.score_breakdown} rationale={submission.ai_rationale} t={t} />
        </div>
      )}
      {reinviteRow}
    </Space>
  )
}

export default function CodingChallengeReview() {
  const { questionId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [statusFilter, setStatusFilter] = useState('all')
  const [logModal, setLogModal] = useState(null) // { title, content, variant } | null
  const [transcriptModal, setTranscriptModal] = useState(null) // { rawTranscript, tokenUsage } | null
  const pollRef = useRef(null)
  const { message } = App.useApp()

  const handleReinvite = async (email) => {
    try {
      const res = await codingChallengeAPI.invite(data.quiz_id, [email])
      const result = res.data[0]
      if (result?.error) {
        message.warning(result.error)
      } else {
        message.success(t('codingChallenge.reinviteSuccess', 'Re-invited {{email}}', { email }))
      }
      load(true)
    } catch (err) {
      message.error(err.response?.data?.detail || t('common.error'))
    }
  }

  const load = async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const res = await codingChallengeAPI.getReview(questionId)
      setData(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || t('common.error'))
    } finally {
      if (!silent) setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionId])

  // Auto-refresh only while something could plausibly change on its own —
  // stops the moment every candidate is in a terminal state, so this isn't
  // polling forever on an otherwise-static page.
  useEffect(() => {
    const hasLiveRows = data?.candidates?.some((c) => LIVE_STATUSES.includes(c.status))
    clearInterval(pollRef.current)
    if (hasLiveRows) {
      pollRef.current = setInterval(() => load(true), 10000)
    }
    return () => clearInterval(pollRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  if (loading) {
    return <div style={{ textAlign: 'center', paddingTop: 80 }}><Spin size="large" /></div>
  }
  if (error) {
    return <Result status="error" title={t('common.error')} subTitle={error} />
  }

  const candidates = data.candidates || []
  const filtered = statusFilter === 'all' ? candidates : candidates.filter((c) => c.status === statusFilter)
  const presentStatuses = [...new Set(candidates.map((c) => c.status))]

  const columns = [
    {
      title: t('codingChallenge.candidate', 'Candidate'), dataIndex: 'candidate_email',
      render: (email, record) => (
        <Space size={6}>
          <Text>{email}</Text>
          {record.attempt_count > 1 && (
            <Tag color="purple">{t('codingChallenge.attemptBadge', 'Attempt {{number}}', { number: record.attempt_count })}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('common.status', 'Status'), dataIndex: 'status',
      render: (status) => <StatusTag status={status} t={t} />,
    },
    {
      title: t('codingChallenge.tests', 'Tests'),
      render: (_, record) => <TestsCell passed={record.submission?.passed_count} total={record.submission?.total_count} />,
    },
    {
      title: t('codingChallenge.score', 'Score'), dataIndex: ['submission', 'ai_score'],
      sorter: (a, b) => (a.submission?.ai_score ?? -1) - (b.submission?.ai_score ?? -1),
      defaultSortOrder: 'descend',
      render: (_, record) => <ScoreCell score={record.submission?.ai_score} />,
    },
    {
      title: t('codingChallenge.logs', 'Logs'),
      render: (_, record) => {
        const s = record.submission
        return (
          <Space size={4}>
            <Tooltip title={t('codingChallenge.testOutput', 'Test Output')}>
              <Button
                type="text" size="small" icon={<FileTextOutlined />} disabled={s?.test_output == null}
                onClick={() => setLogModal({ title: t('codingChallenge.testOutput', 'Test Output'), content: s.test_output, variant: 'test' })}
              />
            </Tooltip>
            <Tooltip title={t('codingChallenge.codeHistory', 'Code History')}>
              <Button
                type="text" size="small" icon={<HistoryOutlined />} disabled={s?.code_timeline == null}
                onClick={() => setLogModal({ title: t('codingChallenge.codeHistory', 'Code History'), content: s.code_timeline, variant: 'diff' })}
              />
            </Tooltip>
            <Tooltip title={t('codingChallenge.aiTranscript', 'AI Chat Transcript')}>
              <Button
                type="text" size="small" icon={<MessageOutlined />} disabled={s?.ai_transcript_raw == null}
                onClick={() => setTranscriptModal({ rawTranscript: s.ai_transcript_raw, tokenUsage: s.ai_token_usage })}
              />
            </Tooltip>
          </Space>
        )
      },
    },
    {
      title: t('codingChallenge.lastActivity', 'Last Activity'),
      render: (_, record) => {
        const time = record.submission?.graded_at || record.submission?.submitted_at || record.started_at || record.invited_at
        return <Text type="secondary" style={{ fontSize: 12 }}>{formatTime(time)}</Text>
      },
    },
    {
      title: '', key: 'actions', width: 50,
      render: (_, record) => (
        <MoreActionsMenu
          items={[
            {
              key: 'reinvite',
              label: record.can_reinvite
                ? t('codingChallenge.reinviteAction', 'Re-invite')
                : (
                  <Tooltip title={t('codingChallenge.reinviteDisabledReason', 'Available once the current attempt is submitted or expires.')}>
                    <span>{t('codingChallenge.reinviteAction', 'Re-invite')}</span>
                  </Tooltip>
                ),
              icon: <SendOutlined />,
              disabled: !record.can_reinvite,
              confirm: {
                title: t('codingChallenge.reinviteConfirmTitle', 'Re-invite {{email}}?', { email: record.candidate_email }),
                description: t('codingChallenge.reinviteConfirmDesc', 'This starts Attempt {{number}} for this candidate.', { number: (record.attempt_count || 0) + 1 }),
                okText: t('codingChallenge.reinviteAction', 'Re-invite'),
                cancelText: t('common.cancel', 'Cancel'),
                onConfirm: () => handleReinvite(record.candidate_email),
              },
            },
          ]}
        />
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Tooltip title={t('common.back', 'Back')}>
            <Button shape="circle" icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} />
          </Tooltip>
          <div
            style={{
              width: 38, height: 38, borderRadius: 10, flexShrink: 0,
              background: 'color-mix(in srgb, var(--sw-primary, #6366f1) 14%, transparent)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
            }}
          >
            👥
          </div>
          <Title level={3} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            {t('codingChallenge.reviewTitle', 'Candidates')}
            {candidates.length > 0 && (
              <span
                style={{
                  fontSize: 13, fontWeight: 700, padding: '1px 9px', borderRadius: 10,
                  background: 'color-mix(in srgb, var(--sw-primary, #6366f1) 14%, transparent)',
                  color: 'var(--sw-primary, #6366f1)',
                }}
              >
                {candidates.length}
              </span>
            )}
          </Title>
        </div>

        {candidates.length > 0 && (
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {['all', ...presentStatuses].map((s) => {
              const active = statusFilter === s
              const accent = s === 'all' ? 'var(--sw-primary, #6366f1)' : STATUS_ACCENT[s] || 'var(--sw-primary, #6366f1)'
              return (
                <button
                  type="button"
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 600,
                    padding: '3px 10px', borderRadius: 12, cursor: 'pointer', whiteSpace: 'nowrap',
                    border: `1px solid ${active ? accent : 'var(--sw-border, #d9d9d9)'}`,
                    background: active ? `color-mix(in srgb, ${accent} 14%, transparent)` : 'transparent',
                    color: active ? accent : 'inherit',
                  }}
                >
                  {s === 'all' ? t('common.all', 'All') : t(STATUS_LABEL_KEYS[s] || s, s)}
                  {' '}({s === 'all' ? candidates.length : candidates.filter((c) => c.status === s).length})
                </button>
              )
            })}
          </div>
        )}
      </div>

      {candidates.length === 0 ? (
        <Empty description={t('codingChallenge.noCandidatesYet', 'No candidates yet — invite someone to get started.')} />
      ) : (
        <Table
          dataSource={filtered}
          rowKey="candidate_email"
          columns={columns}
          pagination={false}
          expandable={{
            expandedRowRender: (record) => (
              <CandidateDetail
                entry={record} hasCustomWeights={data.has_custom_weights} t={t} questionId={questionId}
                onRegraded={() => load(true)}
                onReinvite={(entry) => handleReinvite(entry.candidate_email)}
              />
            ),
          }}
        />
      )}

      <LogModal
        open={!!logModal}
        onClose={() => setLogModal(null)}
        title={logModal?.title}
        content={logModal?.content}
        variant={logModal?.variant}
      />
      <TranscriptModal
        open={!!transcriptModal}
        onClose={() => setTranscriptModal(null)}
        rawTranscript={transcriptModal?.rawTranscript}
        tokenUsage={transcriptModal?.tokenUsage}
        t={t}
      />
    </div>
  )
}
