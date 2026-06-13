/**
 * IntegrityReport — per-candidate dedicated integrity view
 * Route: /quiz/:id/exam-results/integrity/:participantId
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Button, Space, Tag, Progress, Alert, Spin, Timeline,
  Image, Row, Col, Statistic, Divider, Tooltip, Badge,
} from 'antd'
import {
  ArrowLeftOutlined, CameraOutlined, WarningOutlined, CheckCircleOutlined,
  LockOutlined, UnlockOutlined, SafetyOutlined, ClockCircleOutlined,
  UserOutlined, TrophyOutlined,
} from '@ant-design/icons'
import { examAPI, proctoringAPI } from '../../services/api'
import dayjs from 'dayjs'

const { Title, Text } = Typography

function integrityColor(score) {
  if (score == null) return '#8c8c8c'
  if (score >= 70) return '#52c41a'
  if (score >= 40) return '#faad14'
  return '#ff4d4f'
}

function integrityLabel(score) {
  if (score == null) return 'N/A'
  if (score >= 70) return 'Clean'
  if (score >= 40) return 'Suspicious'
  return 'High Risk'
}

function ViolationTimeline({ events }) {
  if (!events || events.length === 0) {
    return <Alert message="No violation events recorded" type="success" showIcon />
  }
  return (
    <Timeline
      items={events.map((e) => ({
        color: e.event_type?.includes('LOCK') || e.event_type?.includes('HONEYPOT') ? 'red' : 'orange',
        dot: <WarningOutlined />,
        children: (
          <div>
            <Text strong style={{ fontSize: 13 }}>{e.event_type}</Text>
            {e.rule_id && <Tag style={{ marginLeft: 8 }}>{e.rule_id}</Tag>}
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {e.occurred_at ? dayjs(e.occurred_at).format('HH:mm:ss') : ''}
              </Text>
            </div>
            {e.metadata && Object.keys(e.metadata).length > 0 && (
              <pre style={{ fontSize: 11, marginTop: 4, color: '#666', background: '#f5f5f5', padding: 6, borderRadius: 4 }}>
                {JSON.stringify(e.metadata, null, 2)}
              </pre>
            )}
          </div>
        ),
      }))}
    />
  )
}

function SnapshotGrid({ snapshots, events, loading }) {
  if (loading) return <Spin size="small" />
  if (snapshots.length === 0) {
    return <Alert message="No webcam snapshots recorded for this candidate" type="warning" showIcon />
  }

  return (
    <Image.PreviewGroup>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
        {snapshots.map((snap) => {
          const snapTime = snap.timestamp_ms
          const nearViolation = events?.some((e) => {
            if (!e.occurred_at) return false
            const evtMs = dayjs(e.occurred_at).valueOf()
            return Math.abs(evtMs - snapTime) < 60000
          })
          return (
            <div key={snap.filename} style={{ textAlign: 'center', width: 120 }}>
              <Image
                src={snap.url}
                width={120}
                height={90}
                style={{
                  objectFit: 'cover',
                  border: nearViolation ? '2px solid #ff4d4f' : '2px solid #d9d9d9',
                  borderRadius: 6,
                }}
                preview={{ src: snap.url }}
              />
              <div style={{ fontSize: 11, color: nearViolation ? '#ff4d4f' : '#999', marginTop: 3 }}>
                {snapTime ? dayjs(snapTime).format('HH:mm:ss') : ''}
                {nearViolation && ' ⚠'}
              </div>
            </div>
          )
        })}
      </div>
    </Image.PreviewGroup>
  )
}

export default function IntegrityReport() {
  const { id: quizId, participantId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [loading, setLoading]             = useState(true)
  const [participant, setParticipant]     = useState(null)  // from exam results
  const [integrityEntry, setIntegrity]    = useState(null)  // from proctoring report
  const [snapshots, setSnapshots]         = useState([])
  const [snapsLoading, setSnapsLoading]   = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError]                 = useState(null)
  const [allResults, setAllResults]       = useState(null)

  useEffect(() => {
    const pid = Number(participantId)
    Promise.all([
      examAPI.getResults(quizId).catch(() => null),
      proctoringAPI.getReport(quizId).catch(() => ({ data: [] })),
    ]).then(([resultsRes, procRes]) => {
      const participants = resultsRes?.data?.participants || []
      const p = participants.find(p2 => p2.participant_id === pid) || null
      setParticipant(p)
      setAllResults(resultsRes?.data)

      const proc = (procRes?.data || []).find(v => v.participant_id === pid) || null
      setIntegrity(proc)

      if (proc) {
        setSnapsLoading(true)
        proctoringAPI.getSnapshots(quizId, pid)
          .then(r => setSnapshots(r.data.snapshots || []))
          .finally(() => setSnapsLoading(false))
      }
    }).catch(() => setError('Failed to load integrity data'))
    .finally(() => setLoading(false))
  }, [quizId, participantId])

  const handleLock = async () => {
    const token = integrityEntry?.events?.[0]?.session_token
    if (!token) return
    setActionLoading(true)
    await proctoringAPI.lockSession(token).catch(() => {})
    const r = await proctoringAPI.getReport(quizId).catch(() => ({ data: [] }))
    const proc = (r.data || []).find(v => v.participant_id === Number(participantId)) || null
    setIntegrity(proc)
    setActionLoading(false)
  }

  const handleUnlock = async () => {
    const token = integrityEntry?.events?.[0]?.session_token
    if (!token) return
    setActionLoading(true)
    await proctoringAPI.unlockSession(token).catch(() => {})
    const r = await proctoringAPI.getReport(quizId).catch(() => ({ data: [] }))
    const proc = (r.data || []).find(v => v.participant_id === Number(participantId)) || null
    setIntegrity(proc)
    setActionLoading(false)
  }

  if (loading) return <div style={{ padding: 32 }}><Spin /></div>
  if (error)   return <Alert message={error} type="error" style={{ margin: 32 }} />

  const intScore    = integrityEntry?.integrity_score ?? null
  const violations  = integrityEntry?.events || []
  const isLocked    = integrityEntry?.is_locked ?? false
  const rawScore    = participant?.score ?? null
  const maxScore    = participant?.max_score ?? allResults?.max_score ?? 100
  const marksRank   = participant?.rank ?? '—'
  const timeSecs    = participant?.time_taken_seconds
  const webcamOk    = integrityEntry?.webcam_granted

  // Compute adjusted score: raw * (integrity / 100)
  const adjustedScore = (rawScore != null && intScore != null)
    ? Math.round(rawScore * (intScore / 100) * 10) / 10
    : rawScore

  // Compute adjusted rank across all participants
  const mergedParticipants = (allResults?.participants || []).map(p => {
    const proc = null // simplified — adjusted rank shown as label only
    return p
  })

  return (
    <div style={{ padding: '24px', maxWidth: 1000, margin: '0 auto' }}>
      <Space style={{ marginBottom: 20 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate(`/quiz/${quizId}/exam-results`)}
        >
          {t('exam.backToResults', 'Back to results')}
        </Button>
        <Text type="secondary">
          {t('exam.integrityReport', 'Integrity Report')}
        </Text>
      </Space>

      {/* ── Candidate header ── */}
      <Card style={{ marginBottom: 20 }}>
        <Row gutter={24} align="middle">
          <Col flex="auto">
            <Space direction="vertical" size={2}>
              <Title level={4} style={{ margin: 0 }}>
                <UserOutlined style={{ marginRight: 8 }} />
                {participant?.display_name || `Participant #${participantId}`}
              </Title>
              {participant?.email && <Text type="secondary">{participant.email}</Text>}
            </Space>
          </Col>
          <Col>
            <Space size="large">
              <Statistic
                title={t('exam.score', 'Score')}
                value={rawScore ?? '—'}
                suffix={maxScore ? `/ ${maxScore}` : ''}
              />
              <Statistic
                title={t('exam.marksRank', 'Marks rank')}
                value={marksRank}
                prefix={<TrophyOutlined />}
              />
              {timeSecs != null && (
                <Statistic
                  title={t('exam.timeTaken', 'Time taken')}
                  value={`${Math.floor(timeSecs / 60)}m ${Math.round(timeSecs % 60)}s`}
                  prefix={<ClockCircleOutlined />}
                />
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      {/* ── Integrity score card ── */}
      <Card
        title={<Space><SafetyOutlined />{t('exam.integrityScore', 'Integrity Score')}</Space>}
        extra={
          integrityEntry ? (
            isLocked ? (
              <Button
                icon={<UnlockOutlined />}
                onClick={handleUnlock}
                loading={actionLoading}
                size="small"
              >
                {t('exam.unlockSession', 'Unlock')}
              </Button>
            ) : (
              <Button
                danger
                icon={<LockOutlined />}
                onClick={handleLock}
                loading={actionLoading}
                size="small"
              >
                {t('exam.lockSession', 'Lock')}
              </Button>
            )
          ) : null
        }
        style={{ marginBottom: 20 }}
      >
        {integrityEntry ? (
          <Row gutter={32} align="middle">
            <Col>
              <Progress
                type="circle"
                percent={intScore ?? 100}
                strokeColor={integrityColor(intScore)}
                size={120}
                format={(p) => (
                  <span style={{ color: integrityColor(intScore), fontWeight: 700 }}>{p}%</span>
                )}
              />
            </Col>
            <Col flex="auto">
              <Space direction="vertical" size={6}>
                <Tag color={intScore >= 70 ? 'success' : intScore >= 40 ? 'warning' : 'error'} style={{ fontSize: 14, padding: '3px 10px' }}>
                  {integrityLabel(intScore)}
                </Tag>
                <Text>
                  <b>{violations.length}</b> {t('exam.violationEvents', 'violation event(s)')} recorded.
                </Text>
                {intScore != null && intScore < 100 && rawScore != null && (
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    {t('exam.adjustedScoreExplain', 'Adjusted score')}: <b>{adjustedScore}</b>
                    {' '}({rawScore} × {intScore}% integrity = {adjustedScore})
                  </Text>
                )}
                {isLocked && (
                  <Tag color="red" icon={<LockOutlined />}>{t('exam.sessionLocked', 'Session locked')}</Tag>
                )}
                {webcamOk === false && (
                  <Alert
                    message={t('exam.webcamDenied', 'Webcam was denied by the candidate')}
                    type="warning"
                    showIcon
                    style={{ marginTop: 4 }}
                  />
                )}
              </Space>
            </Col>
          </Row>
        ) : (
          <Alert
            message={t('exam.noProctoringData', 'No proctoring data recorded for this candidate')}
            type="info"
            showIcon
          />
        )}
      </Card>

      {/* ── Webcam snapshots ── */}
      <Card
        title={
          <Space>
            <CameraOutlined />
            {t('exam.webcamSnapshots', 'Webcam Snapshots')}
            <Text type="secondary" style={{ fontSize: 13 }}>
              ({snapsLoading ? '…' : snapshots.length})
            </Text>
          </Space>
        }
        style={{ marginBottom: 20 }}
      >
        <SnapshotGrid snapshots={snapshots} events={violations} loading={snapsLoading} />
      </Card>

      {/* ── Violation timeline ── */}
      <Card
        title={
          <Space>
            <WarningOutlined style={{ color: '#faad14' }} />
            {t('exam.violationTimeline', 'Violation Timeline')}
          </Space>
        }
      >
        <ViolationTimeline events={violations} />
      </Card>
    </div>
  )
}
