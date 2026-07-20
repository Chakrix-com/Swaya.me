/**
 * ExamResults — host-facing results dashboard
 * Route: /quiz/:id/exam-results (authenticated)
 */
import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Button, Table, Space, Tag, Statistic,
  Row, Col, Progress, Alert, Spin, Divider, Tooltip, Input, message, List,
  Badge, Timeline, Image
} from 'antd'
const { TextArea } = Input
import {
  TrophyOutlined, DownloadOutlined, ArrowLeftOutlined,
  CheckCircleOutlined, CloseCircleOutlined, UserOutlined,
  ClockCircleOutlined, SyncOutlined, RobotOutlined, FilePdfOutlined,
  LockOutlined, UnlockOutlined, WarningOutlined, CameraOutlined,
  ArrowUpOutlined, ArrowDownOutlined, MailOutlined
} from '@ant-design/icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartTooltip, ResponsiveContainer, Cell } from 'recharts'
import { examAPI, proctoringAPI } from '../../services/api'
import dayjs from 'dayjs'
import { exportExamResultsPDF } from './exportPDF'
import RichTextRenderer from '../quiz/components/RichTextRenderer'
import ReactMarkdown from 'react-markdown'
import SafeModal from '../../components/SafeModal'
import SafeConfirm from '../../components/SafeConfirm'
import './ExamResults.css'

const { Title, Text } = Typography
const stripHtml = (h) => (h || '').replace(/<[^>]*>/g, '').trim()

function integrityColor(score) {
  if (score >= 70) return '#52c41a'
  if (score >= 40) return '#faad14'
  return '#ff4d4f'
}

const DEFAULT_AI_PROMPT = `Your report MUST contain exactly these sections:

## 1. Score Summary
Quantitative overview: average, median (estimate from distribution), pass rate, score spread.

## 2. Question Difficulty Ranking
List questions from hardest to easiest with % correct. Highlight any question where < 40% got it right (needs review) or > 90% got it right (possibly too easy).

## 3. Common Mistake Patterns
For the hardest questions, which wrong answer was most chosen and what misconception does that suggest?

## 4. Qualitative Insights
What topics or skills are participants weakest/strongest in, based on the question content and results?

## 5. Recommendations
Concrete actionable suggestions: which topics need more training, which questions should be revised, any anomalies to investigate.

Be concise. Use bullet points. Do not repeat raw numbers already obvious from the dashboard.`

export default function ExamResults() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [loading, setLoading] = useState(true)
  const [results, setResults] = useState(null)
  const [violationData, setViolationData] = useState([])
  const [proctoringEnabled, setProctoringEnabled] = useState(false)
  const [error, setError] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [analysing, setAnalysing] = useState(false)
  const [analysisError, setAnalysisError] = useState(null)
  const [customPrompt, setCustomPrompt] = useState(DEFAULT_AI_PROMPT)
  const [downloadingPDF, setDownloadingPDF] = useState(false)
  const [sendingEmails, setSendingEmails] = useState(false)
  const [sendEmailsConfirmOpen, setSendEmailsConfirmOpen] = useState(false)
  const [senderName, setSenderName] = useState('')

  // Interview sheet modal
  const [interviewModal, setInterviewModal] = useState({ open: false, participantId: null, name: '', email: '', score: 0, maxScore: 0, quizId: null })
  const [interviewSheet, setInterviewSheet] = useState(null)
  const [interviewLoading, setInterviewLoading] = useState(false)
  const [interviewError, setInterviewError] = useState(null)
  const [interviewGenCount, setInterviewGenCount] = useState(0)
  const [interviewEmail, setInterviewEmail] = useState('')
  const [emailSending, setEmailSending] = useState(false)
  const [emailSent, setEmailSent] = useState(false)
  const [downloadingFormat, setDownloadingFormat] = useState(null)
  const [interviewGenCounts, setInterviewGenCounts] = useState({})

  // Participant exam-detail modal
  const [participantDetail, setParticipantDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)

  // Proctoring detail modal
  const [selectedProctoring, setSelectedProctoring] = useState(null)
  const [proSnapshots, setProSnapshots] = useState([])
  const [proSnapshotsLoading, setProSnapshotsLoading] = useState(false)
  const [proActionLoading, setProActionLoading] = useState(false)

  const handleRowDetailClick = async (record) => {
    if (!record.participant_id || !record.is_completed) return
    setDetailOpen(true)
    setDetailLoading(true)
    setParticipantDetail(null)
    try {
      const res = await examAPI.getParticipantDetail(id, record.participant_id)
      setParticipantDetail(res.data)
    } catch (_) {
      setParticipantDetail(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const openInterviewModal = (record) => {
    setInterviewModal({
      open: true,
      participantId: record.participant_id,
      name: record.display_name,
      email: record.email || '',
      score: record.score,
      maxScore: record.max_score,
      quizId: id,
    })
    setInterviewSheet(null)
    setInterviewError(null)
    setInterviewEmail(record.email || '')
    setEmailSent(false)
    setInterviewGenCount(interviewGenCounts[record.participant_id] || 0)
  }

  const handleGenerateSheet = async () => {
    setInterviewLoading(true)
    setInterviewError(null)
    try {
      const res = await examAPI.generateInterviewSheet(interviewModal.quizId, interviewModal.participantId)
      setInterviewSheet(res.data.sheet)
      setInterviewGenCount(res.data.generation_count)
      setInterviewGenCounts(prev => ({ ...prev, [interviewModal.participantId]: res.data.generation_count }))
    } catch (err) {
      const status = err.response?.status
      if (status === 429) {
        setInterviewError('Regeneration limit reached (5/5). No more generations available for this participant.')
      } else {
        setInterviewError(err.response?.data?.detail || 'Failed to generate interview sheet. Please try again.')
      }
    } finally {
      setInterviewLoading(false)
    }
  }

  const handleDownloadSheet = async (format) => {
    if (!interviewSheet) return
    setDownloadingFormat(format)
    try {
      const res = await examAPI.downloadInterviewSheet(interviewModal.quizId, interviewModal.participantId, {
        sheet: interviewSheet,
        format,
        participant_name: interviewModal.name,
      })
      const blob = new Blob([res.data])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const slug = interviewModal.name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'participant'
      a.download = `${slug}_interview.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // silent — browser will show download error
    } finally {
      setDownloadingFormat(null)
    }
  }

  const handleEmailSheet = async () => {
    if (!interviewSheet || !interviewEmail.trim()) return
    setEmailSending(true)
    setEmailSent(false)
    try {
      await examAPI.emailInterviewSheet(interviewModal.quizId, interviewModal.participantId, {
        sheet: interviewSheet,
        participant_name: interviewModal.name,
        recipient_email: interviewEmail.trim(),
        quiz_title: results?.quiz_title || '',
      })
      setEmailSent(true)
    } catch {
      setEmailSent(false)
    } finally {
      setEmailSending(false)
    }
  }

  const handleViewProctoring = (entry) => {
    setSelectedProctoring(entry)
    setProSnapshots([])
    setProSnapshotsLoading(true)
    proctoringAPI.getSnapshots(id, entry.participant_id)
      .then(res => setProSnapshots(res.data.snapshots || []))
      .catch(() => setProSnapshots([]))
      .finally(() => setProSnapshotsLoading(false))
  }

  const handleLock = async (entry) => {
    setProActionLoading(true)
    try {
      const token = entry._integrityEntry?.events?.[0]?.session_token
      if (token) await proctoringAPI.lockSession(token)
      // Refresh proctoring data
      const res = await proctoringAPI.getReport(id).catch(() => ({ data: [] }))
      setViolationData(res.data || [])
      if (selectedProctoring?.participant_id === entry.participant_id) {
        setSelectedProctoring(prev => ({ ...prev, is_locked: true }))
      }
    } catch (_) {} finally { setProActionLoading(false) }
  }

  const handleUnlock = async (entry) => {
    setProActionLoading(true)
    try {
      const token = entry._integrityEntry?.events?.[0]?.session_token
      if (token) await proctoringAPI.unlockSession(token)
      const res = await proctoringAPI.getReport(id).catch(() => ({ data: [] }))
      setViolationData(res.data || [])
      if (selectedProctoring?.participant_id === entry.participant_id) {
        setSelectedProctoring(prev => ({ ...prev, is_locked: false }))
      }
    } catch (_) {} finally { setProActionLoading(false) }
  }

  useEffect(() => {
    const load = async () => {
      try {
        const [examRes, reportRes, configRes] = await Promise.all([
          examAPI.getResults(id),
          proctoringAPI.getReport(id).catch(() => ({ data: [] })),
          fetch(`/api/v1/proctoring/config/${id}`).then(r => r.json()).catch(() => null),
        ])
        setResults(examRes.data)
        setViolationData(reportRes.data || [])
        setProctoringEnabled(configRes?.enabled ?? false)
      } catch (err) {
        setError(err.response?.data?.detail || t('common.error'))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id, t])

  const handleAnalyse = async () => {
    setAnalysing(true)
    setAnalysisError(null)
    try {
      const res = await examAPI.analyzeResults(id, customPrompt.trim())
      setAnalysis(res.data.analysis)
    } catch (err) {
      setAnalysisError(err.response?.data?.detail || t('exam.analysisError'))
    } finally {
      setAnalysing(false)
    }
  }

  const handleDownloadPDF = async () => {
    if (!results) return
    setDownloadingPDF(true)
    try {
      await exportExamResultsPDF(results, analysis)
    } finally {
      setDownloadingPDF(false)
    }
  }

  const handleSendEmails = () => {
    setSendEmailsConfirmOpen(true)
  }

  const doSendEmails = async () => {
    setSendEmailsConfirmOpen(false)
    setSendingEmails(true)
    try {
      await examAPI.sendParticipantEmails(id, senderName.trim() || null)
      message.success(t('exam.emailsQueuedContent'))
      // Refresh results so the button flips to "Emails Sent ✓"
      const updated = await examAPI.getResults(id)
      setResults(updated.data)
    } catch {
      message.error(t('exam.emailFailedContent'))
    } finally {
      setSendingEmails(false)
    }
  }

  // Merge leaderboard with proctoring data and compute both rankings
  const mergedParticipants = useMemo(() => {
    if (!results?.leaderboard) return []
    const integrityMap = {}
    ;(violationData || []).forEach(v => { integrityMap[v.participant_id] = v })

    const merged = results.leaderboard.map((p, i) => {
      const integrity = integrityMap[p.participant_id] ?? null
      const integrityScore = integrity?.integrity_score ?? null
      const adjustedScore = p.is_completed
        ? (integrityScore != null ? Math.round(p.score * (integrityScore / 100) * 10) / 10 : p.score)
        : null
      return {
        ...p,
        marks_rank: p.rank ?? (i + 1),
        integrity_score: integrityScore,
        violation_count: integrity?.violation_count ?? null,
        is_locked: integrity?.is_locked ?? false,
        webcam_required: integrity?.webcam_required ?? null,
        webcam_granted: integrity?.webcam_granted ?? null,
        adjusted_score: adjustedScore,
        _integrityEntry: integrity,
      }
    })

    // Adjusted rank — only among completed participants
    const completed = merged.filter(p => p.is_completed)
    const byAdjusted = [...completed].sort((a, b) =>
      b.adjusted_score - a.adjusted_score ||
      (a.time_taken_seconds ?? Infinity) - (b.time_taken_seconds ?? Infinity)
    )
    const adjRankMap = {}
    byAdjusted.forEach((p, i) => { adjRankMap[p.participant_id] = i + 1 })

    return merged.map(p => ({
      ...p,
      adjusted_rank: p.is_completed ? (adjRankMap[p.participant_id] ?? null) : null,
    }))
  }, [results, violationData])

  const handleExportCsv = () => {
    if (!results) return
    const hasProcData = proctoringEnabled || violationData.length > 0
    const headers = ['Marks Rank', 'Name', 'Email', 'Score', 'Max Score', '%', 'Time (s)']
    if (hasProcData) headers.push('Integrity Score', 'Adjusted Score', 'Adjusted Rank', 'Violations', 'Locked')
    const rows = [
      headers,
      ...mergedParticipants.map(e => {
        const base = [
          e.marks_rank ?? '',
          e.display_name,
          e.email || '',
          e.score,
          e.max_score,
          e.percentage,
          e.time_taken_seconds != null ? Math.round(e.time_taken_seconds) : '',
        ]
        if (hasProcData) base.push(
          e.integrity_score ?? 'N/A',
          e.adjusted_score ?? '',
          e.adjusted_rank ?? '',
          e.violation_count ?? 0,
          e.is_locked ? 'Yes' : 'No',
        )
        return base
      })
    ]
    const csv = rows.map(r => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `exam-results-${id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert type="error" message={error} />
        <Button style={{ marginTop: 16 }} onClick={() => navigate('/dashboard')}>
          {t('exam.backToDashboard')}
        </Button>
      </div>
    )
  }

  const hasProcData = proctoringEnabled || violationData.length > 0

  const rankCell = (rank, record) => {
    if (!record.is_completed) {
      if (record.is_abandoned) return <Tag color="default">{t('exam.abandoned', 'Abandoned')}</Tag>
      return <Tag icon={<SyncOutlined spin />} color="processing">{t('exam.inProgress')}</Tag>
    }
    return <Text>{rank}</Text>
  }

  const adjRankCell = (adjRank, record) => {
    if (!record.is_completed || adjRank == null) return '—'
    const delta = record.marks_rank - adjRank
    return (
      <Space size={2}>
        <Text>{adjRank}</Text>
        {delta > 0 && (
          <Tooltip title={t('exam.adjRankUp', { delta })}>
            <Text style={{ color: '#52c41a', fontSize: 11 }}><ArrowUpOutlined />{delta}</Text>
          </Tooltip>
        )}
        {delta < 0 && (
          <Tooltip title={t('exam.adjRankDown', { delta: Math.abs(delta) })}>
            <Text style={{ color: '#ff4d4f', fontSize: 11 }}><ArrowDownOutlined />{Math.abs(delta)}</Text>
          </Tooltip>
        )}
      </Space>
    )
  }

  const baseColumns = [
    {
      title: t('exam.rankCol'),
      dataIndex: 'marks_rank',
      width: 70,
      fixed: 'left',
      defaultSortOrder: 'ascend',
      sorter: (a, b) => (a.marks_rank ?? 9999) - (b.marks_rank ?? 9999),
      render: (rank, row) => rankCell(rank, row),
    },
    {
      title: t('exam.nameCol'),
      dataIndex: 'display_name',
      width: 180,
      fixed: 'left',
      render: (name, row) => (
        <div>
          <Text strong style={row.is_completed ? {} : { color: '#8c8c8c' }}>{name}</Text>
          {row.email && (
            <div style={{ fontSize: 11, color: '#888' }}>
              {row.email}
              {results?.participant_emails_sent && row.is_completed && (
                <MailOutlined style={{ marginLeft: 5, color: '#52c41a', fontSize: 10 }} title={t('exam.emailResultSent')} />
              )}
            </div>
          )}
        </div>
      ),
    },
    {
      title: t('exam.scoreCol'),
      dataIndex: 'score',
      width: 110,
      sorter: (a, b) => (b.score ?? -1) - (a.score ?? -1),
      render: (score, row) => row.is_completed ? (
        <Space>
          <Text strong style={{ color: '#1890ff' }}>{score}</Text>
          <Text type="secondary">/ {row.max_score}</Text>
        </Space>
      ) : <Text type="secondary">—</Text>
    },
    {
      title: t('exam.percentCol'),
      dataIndex: 'percentage',
      width: 130,
      render: (pct, row) => row.is_completed ? (
        <Progress
          percent={pct}
          size="small"
          strokeColor={pct >= 70 ? '#52c41a' : pct >= 40 ? '#faad14' : '#ff4d4f'}
          style={{ width: 100 }}
        />
      ) : <Text type="secondary">—</Text>
    },
    {
      title: t('exam.timeTakenCol'),
      dataIndex: 'time_taken_seconds',
      width: 100,
      render: (secs) => {
        if (secs == null) return '—'
        const m = Math.floor(secs / 60)
        const s = Math.round(secs % 60)
        return <Text><ClockCircleOutlined style={{ marginRight: 4 }} />{m}m {s}s</Text>
      }
    },
  ]

  const proctoringColumns = [
    {
      title: t('proctoring.report.integrityScore'),
      dataIndex: 'integrity_score',
      width: 90,
      render: (score) => score != null
        ? <Badge count={score} style={{ backgroundColor: integrityColor(score) }} overflowCount={100} />
        : <Text type="secondary" style={{ fontSize: 12 }}>N/A</Text>,
      sorter: (a, b) => (a.integrity_score ?? 101) - (b.integrity_score ?? 101),
    },
    {
      title: t('exam.adjScoreCol'),
      dataIndex: 'adjusted_score',
      width: 90,
      render: (val, row) => row.is_completed
        ? <Text style={{ color: '#722ed1' }}>{val}</Text>
        : '—',
      sorter: (a, b) => (b.adjusted_score ?? -1) - (a.adjusted_score ?? -1),
    },
    {
      title: t('exam.adjRankCol'),
      dataIndex: 'adjusted_rank',
      width: 90,
      render: (adjRank, row) => adjRankCell(adjRank, row),
      sorter: (a, b) => (a.adjusted_rank ?? 9999) - (b.adjusted_rank ?? 9999),
    },
    {
      title: t('proctoring.report.violations'),
      dataIndex: 'violation_count',
      width: 80,
      render: (count) => count == null ? <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
        : count > 0
          ? <Tag color="orange" icon={<WarningOutlined />}>{count}</Tag>
          : <Tag color="success">0</Tag>,
      sorter: (a, b) => (b.violation_count ?? -1) - (a.violation_count ?? -1),
    },
    {
      title: t('proctoring.report.status'),
      width: 90,
      render: (_, row) => {
        if (!row._integrityEntry) return <Tag color="default">—</Tag>
        if (row.is_locked) return <Tag color="red" icon={<LockOutlined />}>{t('proctoring.report.locked')}</Tag>
        if (row.violation_count > 0) return <Tag color="orange" icon={<WarningOutlined />}>{t('proctoring.report.flagged')}</Tag>
        return <Tag color="green" icon={<CheckCircleOutlined />}>{t('proctoring.report.clean')}</Tag>
      },
    },
  ]

  const actionColumn = {
    title: t('proctoring.report.actions'),
    width: 140,
    render: (_, row) => (
      <Space size={4}>
        {row.is_completed && (
          <Button size="small" onClick={(e) => { e.stopPropagation(); handleRowDetailClick(row) }}>
            {t('exam.btnAnswers')}
          </Button>
        )}
        {row._integrityEntry && (
          <>
            <Button
              size="small"
              icon={<CameraOutlined />}
              onClick={(e) => { e.stopPropagation(); handleViewProctoring(row) }}
            >
              {t('exam.integrityMergedTag')}
            </Button>
            <Button
              size="small"
              type="link"
              onClick={(e) => { e.stopPropagation(); navigate(`/quiz/${id}/exam-results/integrity/${row.participant_id}`) }}
            >
              {t('exam.fullReport', 'Full report')}
            </Button>
          </>
        )}
      </Space>
    ),
  }

  const interviewColumn = {
    title: t('exam.interviewSheet'),
    key: 'interview',
    width: 160,
    render: (_, row) => {
      const genCount = interviewGenCounts[row.participant_id] || 0
      const atLimit = genCount >= 5
      const label = genCount > 0 ? t('exam.interviewSheetWithCount', { count: genCount }) : t('exam.interviewSheet')
      return (
        <Tooltip title={!row.is_completed ? t('exam.interviewSheetTooltipNotComplete') : atLimit ? t('exam.interviewSheetTooltipLimit') : t('exam.interviewSheetTooltipGenerate')}>
          <Button
            size="small"
            icon={<RobotOutlined />}
            disabled={!row.is_completed}
            onClick={(e) => { e.stopPropagation(); openInterviewModal(row) }}
            style={{ fontSize: 12 }}
          >
            {label}
          </Button>
        </Tooltip>
      )
    },
  }

  const tableColumns = hasProcData
    ? [...baseColumns, ...proctoringColumns, actionColumn, interviewColumn]
    : [...baseColumns, {
        ...actionColumn,
        render: (_, row) => row.is_completed
          ? <Button size="small" onClick={(e) => { e.stopPropagation(); handleRowDetailClick(row) }}>{t('exam.btnAnswers')}</Button>
          : null,
      }, interviewColumn]

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/quiz/${id}/edit`)}>
          {t('common.back', 'Back')}
        </Button>
        <Button
          icon={<FilePdfOutlined />}
          onClick={handleDownloadPDF}
          loading={downloadingPDF}
          disabled={!results}
        >
          {analysis ? t('exam.downloadPdfWithAi') : t('exam.downloadPdf')}
        </Button>
        {!results?.participant_emails_sent && (
          <Input
            placeholder={t('exam.senderNamePlaceholder')}
            value={senderName}
            onChange={e => setSenderName(e.target.value)}
            style={{ width: 220 }}
            disabled={sendingEmails}
          />
        )}
        <Button
          icon={<MailOutlined />}
          type={results?.participant_emails_sent ? 'default' : 'primary'}
          onClick={handleSendEmails}
          loading={sendingEmails}
          disabled={!results || results.participant_emails_sent || sendingEmails}
        >
          {results?.participant_emails_sent ? t('exam.emailsSentDone') : t('exam.sendResultsToParticipants')}
        </Button>
      </Space>

      <Title level={2}>
        {t('exam.resultsTitle')}: {results.quiz_title}
      </Title>

      <Space style={{ marginBottom: 8 }}>
        <Tag color={results.is_open ? 'green' : 'red'}>
          {results.is_open ? t('exam.statusOpen') : t('exam.statusClosed')}
        </Tag>
        {results.slug && (
          <Text type="secondary" copyable={{ text: `${window.location.origin}/e/${results.slug}` }}>
            /e/{results.slug}
          </Text>
        )}
      </Space>

      {results.exam_start_at && results.exam_end_at && (
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary">
            {dayjs(results.exam_start_at).format('DD MMM YYYY, HH:mm')}
            {' → '}
            {dayjs(results.exam_end_at).format('DD MMM YYYY, HH:mm')}
          </Text>
        </div>
      )}

      {/* Summary stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('exam.totalStarted')}
              value={results.total_started}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('exam.totalCompleted')}
              value={results.total_completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('exam.totalAbandoned')}
              value={results.total_abandoned}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('exam.averageScore')}
              value={results.average_score}
              suffix={`/ ${results.max_score}`}
              valueStyle={{ color: '#1890ff' }}
              prefix={<TrophyOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Unified leaderboard + integrity table */}
      <Card
        title={
          <Space>
            <TrophyOutlined />
            {t('exam.leaderboard')}
            {hasProcData && (
              <Tag color="purple" style={{ marginLeft: 8 }}>
                {t('exam.integrityMergedTag')}
              </Tag>
            )}
          </Space>
        }
        extra={
          <Button icon={<DownloadOutlined />} onClick={handleExportCsv}>
            {t('exam.exportCsv')}
          </Button>
        }
        style={{ marginBottom: 24 }}
      >
        {hasProcData && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message={
              <span>
                <strong>{t('exam.adjScoreCol')}</strong> {t('exam.adjScoreFormula')} &nbsp;
                <strong>{t('exam.adjRankCol')}</strong> {t('exam.adjRankFormula')} &nbsp;
                {t('exam.adjArrowsNote')}
              </span>
            }
          />
        )}
        {mergedParticipants.length === 0 ? (
          <Text type="secondary">{t('exam.noParticipantsYet', 'No one has started this exam yet.')}</Text>
        ) : (
          <Table
            dataSource={mergedParticipants}
            columns={tableColumns}
            rowKey={(r, i) => r.participant_id ?? `ip-${i}`}
            pagination={mergedParticipants.length > 20 ? { pageSize: 20 } : false}
            size="small"
            scroll={{ x: 'max-content' }}
          />
        )}
      </Card>

      {/* Per-question analytics */}
      <Card title={t('exam.questionAnalytics')}>
        {results.question_analytics.map((qa, idx) => (
          <div key={qa.question_id} style={{ marginBottom: 32 }}>
            <Space align="start" style={{ marginBottom: 8 }}>
              <Text strong style={{ whiteSpace: 'nowrap' }}>Q{idx + 1}.</Text>
              <RichTextRenderer content={qa.question_text} />
            </Space>
            <Row align="middle" gutter={16} style={{ marginBottom: 8 }}>
              <Col>
                <Tag color={qa.percent_correct >= 70 ? 'success' : qa.percent_correct >= 40 ? 'warning' : 'error'}>
                  {qa.percent_correct}% {t('exam.percentCorrect')}
                </Tag>
              </Col>
              <Col>
                <Text type="secondary">{t('exam.responsesCount', { count: qa.total_answers })}</Text>
              </Col>
            </Row>

            {qa.options && qa.answer_distribution && (() => {
              const correctIndices = new Set(qa.correct_answer_indices || (qa.correct_answer_index != null ? [qa.correct_answer_index] : []))
              return (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart
                  data={qa.options.map((opt, i) => {
                    const plain = stripHtml(opt)
                    return {
                      name: plain.length > 24 ? plain.slice(0, 24) + '…' : plain,
                      fullText: plain,
                      count: qa.answer_distribution[i] || 0,
                      isCorrect: correctIndices.has(i),
                    }
                  })}
                  margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} />
                  <RechartTooltip formatter={(value, name, props) => [value, props.payload.fullText]} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {qa.options.map((_, i) => (
                      <Cell
                        key={i}
                        fill={correctIndices.has(i) ? '#52c41a' : '#1890ff'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              )
            })()}
            {idx < results.question_analytics.length - 1 && <Divider />}
          </div>
        ))}
      </Card>

      {/* AI Analysis panel */}
      <Card
        style={{ marginBottom: 24 }}
        title={
          <Space>
            <RobotOutlined />
            <span>{t('exam.aiAnalysisTitle')}</span>
          </Space>
        }
        extra={
          <Space>
            {analysis && (
              <Button
                icon={<FilePdfOutlined />}
                onClick={handleDownloadPDF}
                loading={downloadingPDF}
              >
                {t('exam.downloadPdfBtn')}
              </Button>
            )}
            <Button
              type="primary"
              icon={<RobotOutlined />}
              onClick={handleAnalyse}
              loading={analysing}
              disabled={results.total_completed === 0}
            >
              {analysing ? t('exam.aiAnalysing') : analysis ? t('exam.aiReanalyseButton') : t('exam.aiAnalyseButton')}
            </Button>
          </Space>
        }
      >
        <TextArea
          rows={8}
          value={customPrompt}
          onChange={(e) => setCustomPrompt(e.target.value)}
          disabled={analysing || results.total_completed === 0}
          style={{ marginBottom: 12, fontFamily: 'monospace', fontSize: 13 }}
        />
        {results.total_completed === 0 && !analysing && !analysis && (
          <Text type="secondary">{t('exam.aiAnalysisUnavailable')}</Text>
        )}
        {analysisError && <Alert type="error" message={analysisError} style={{ marginBottom: 12 }} />}
        {analysing && (
          <div style={{ textAlign: 'center', padding: '32px 0' }}>
            <Spin size="large" />
            <div style={{ marginTop: 12 }}>
              <Text type="secondary">{t('exam.aiAnalysingMessage')}</Text>
            </div>
          </div>
        )}
        {analysis && !analysing && (
          <div className="ai-analysis-content">
            <ReactMarkdown>{analysis}</ReactMarkdown>
          </div>
        )}
      </Card>

      {/* Participant exam-detail modal */}
      <SafeModal
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={760}
        title={
          participantDetail
            ? `${participantDetail.display_name}${participantDetail.email ? ` — ${participantDetail.email}` : ''}`
            : t('exam.participantDetailTitle')
        }
      >
        {detailLoading && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        )}
        {!detailLoading && participantDetail && (
          <>
            <Space wrap style={{ marginBottom: 16 }}>
              <Tag color="blue">{participantDetail.score} / {participantDetail.max_score} pts</Tag>
              <Tag color={participantDetail.percentage >= 70 ? 'success' : participantDetail.percentage >= 40 ? 'warning' : 'error'}>
                {participantDetail.percentage}%
              </Tag>
              <Tag color="green" icon={<CheckCircleOutlined />}>{participantDetail.correct_count} correct</Tag>
              <Tag color="red" icon={<CloseCircleOutlined />}>{participantDetail.wrong_count} wrong</Tag>
              {participantDetail.unanswered_count > 0 && (
                <Tag color="default">{participantDetail.unanswered_count} unanswered</Tag>
              )}
              {participantDetail.time_taken_seconds != null && (
                <Tag icon={<ClockCircleOutlined />}>
                  {Math.floor(participantDetail.time_taken_seconds / 60)}m {Math.round(participantDetail.time_taken_seconds % 60)}s
                </Tag>
              )}
            </Space>
            <List
              dataSource={participantDetail.questions}
              renderItem={(q, idx) => {
                const answered = q.participant_answer != null || (Array.isArray(q.participant_answer_indices) && q.participant_answer_indices.length > 0)
                const color = q.is_correct === true ? '#f6ffed' : q.is_correct === false ? '#fff2f0' : '#fafafa'
                const borderColor = q.is_correct === true ? '#b7eb8f' : q.is_correct === false ? '#ffa39e' : '#d9d9d9'
                return (
                  <List.Item style={{ display: 'block', padding: '10px 0' }}>
                    <div style={{ background: color, border: `1px solid ${borderColor}`, borderRadius: 6, padding: '10px 14px' }}>
                      <Space align="start" style={{ width: '100%' }}>
                        {q.is_correct === true
                          ? <CheckCircleOutlined style={{ color: '#52c41a', marginTop: 3 }} />
                          : q.is_correct === false
                          ? <CloseCircleOutlined style={{ color: '#ff4d4f', marginTop: 3 }} />
                          : <span style={{ color: '#bbb', marginTop: 3 }}>–</span>
                        }
                        <div style={{ flex: 1 }}>
                          <Text strong>Q{idx + 1}. </Text>
                          <Text>{stripHtml(q.question_text)}</Text>
                          {q.options && (
                            <div style={{ marginTop: 6 }}>
                              {q.options.map((opt, i) => {
                                const isChosen = Array.isArray(q.participant_answer_indices)
                                  ? q.participant_answer_indices.includes(i)
                                  : i === q.participant_answer
                                const isCorrect = Array.isArray(q.correct_answer_indices)
                                  ? q.correct_answer_indices.includes(i)
                                  : i === q.correct_answer_index
                                return (
                                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                                    <span style={{
                                      fontWeight: isCorrect ? 700 : 400,
                                      color: isCorrect ? '#389e0d' : isChosen ? '#cf1322' : '#595959',
                                    }}>
                                      {String.fromCharCode(65 + i)}. {stripHtml(opt)}
                                    </span>
                                    {isCorrect && <Tag color="success" style={{ margin: 0, fontSize: 11 }}>{t('exam.tagCorrect')}</Tag>}
                                    {isChosen && !isCorrect && <Tag color="error" style={{ margin: 0, fontSize: 11 }}>{t('exam.tagTheirAnswer')}</Tag>}
                                    {isChosen && isCorrect && <Tag color="success" style={{ margin: 0, fontSize: 11 }}>{t('exam.tagTheirAnswer')}</Tag>}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                          {!answered && <Text type="secondary" style={{ fontSize: 12 }}>{t('exam.tagNotAnswered')}</Text>}
                          <div style={{ marginTop: 4 }}>
                            <Text type="secondary" style={{ fontSize: 11 }}>{q.points_earned} / {q.points_possible} pts</Text>
                          </div>
                        </div>
                      </Space>
                    </div>
                  </List.Item>
                )
              }}
            />
          </>
        )}
        {!detailLoading && !participantDetail && (
          <Alert type="error" message={t('exam.couldNotLoadDetail')} />
        )}
      </SafeModal>

      {/* Interview Sheet Modal */}
      <SafeModal
        open={interviewModal.open}
        onCancel={() => setInterviewModal(prev => ({ ...prev, open: false }))}
        footer={null}
        width={920}
        title={
          <Space>
            <RobotOutlined />
            <span>{t('exam.interviewSheetModalTitle', { name: interviewModal.name })}</span>
            {interviewModal.score != null && interviewModal.maxScore != null && (
              <Tag color="blue">{interviewModal.score}/{interviewModal.maxScore}</Tag>
            )}
          </Space>
        }
      >
        {/* Generate / Regenerate controls */}
        <div style={{ marginBottom: 16 }}>
          {!interviewSheet && !interviewLoading && !interviewError && (
            <div style={{ textAlign: 'center', padding: '32px 0' }}>
              <RobotOutlined style={{ fontSize: 40, color: '#4361ee', marginBottom: 12, display: 'block' }} />
              <div style={{ marginBottom: 16, color: '#555' }}>
                {t('exam.interviewSheetIntro')}
              </div>
              <Button type="primary" size="large" icon={<RobotOutlined />} onClick={handleGenerateSheet}>
                {t('exam.interviewSheetGenerateBtn')}
              </Button>
            </div>
          )}

          {interviewLoading && (
            <div style={{ textAlign: 'center', padding: '48px 0' }}>
              <Spin size="large" />
              <div style={{ marginTop: 16, color: '#555' }}>{t('exam.interviewSheetGenerating')}</div>
              <div style={{ marginTop: 8, color: '#888', fontSize: 13 }}>{t('exam.interviewSheetWait')}</div>
            </div>
          )}

          {interviewError && !interviewLoading && (
            <Alert
              type="error"
              message={interviewError}
              style={{ marginBottom: 12 }}
              action={
                interviewGenCount < 5 && (
                  <Button size="small" onClick={handleGenerateSheet}>{t('exam.interviewSheetRetry')}</Button>
                )
              }
            />
          )}

          {interviewSheet && !interviewLoading && (
            <>
              <Space style={{ marginBottom: 12 }} wrap>
                <Button
                  icon={<SyncOutlined />}
                  onClick={handleGenerateSheet}
                  disabled={interviewGenCount >= 5}
                >
                  {interviewGenCount >= 5
                    ? t('exam.interviewSheetRegenLimit')
                    : t('exam.interviewSheetRegenBtn', { count: interviewGenCount })}
                </Button>
              </Space>

              {/* Rendered Markdown preview */}
              <div
                className="ai-analysis-content"
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: 8,
                  padding: '16px 20px',
                  marginBottom: 20,
                  background: '#fafafa',
                  minHeight: 200,
                }}
              >
                <ReactMarkdown>{interviewSheet}</ReactMarkdown>
              </div>

              {/* Deliver section */}
              <Divider orientation="left" style={{ margin: '12px 0' }}>{t('exam.interviewSheetDeliver')}</Divider>

              {/* Email row */}
              <div style={{ marginBottom: 12 }}>
                <Space.Compact style={{ width: '100%' }}>
                  <Input
                    prefix={<MailOutlined />}
                    placeholder={t('exam.interviewSheetRecipientEmail')}
                    value={interviewEmail}
                    onChange={e => { setInterviewEmail(e.target.value); setEmailSent(false) }}
                    style={{ flex: 1 }}
                  />
                  <Button
                    type="primary"
                    icon={<MailOutlined />}
                    onClick={handleEmailSheet}
                    loading={emailSending}
                    disabled={!interviewEmail.trim() || emailSending}
                  >
                    {t('exam.interviewSheetSend')}
                  </Button>
                </Space.Compact>
                {emailSent && (
                  <div style={{ marginTop: 6, color: '#52c41a', fontSize: 13 }}>
                    <CheckCircleOutlined style={{ marginRight: 4 }} />{t('exam.interviewSheetEmailQueued')}
                  </div>
                )}
              </div>

              {/* Download row */}
              <Space>
                <span style={{ color: '#555', fontSize: 13 }}>{t('exam.interviewSheetDownload')}</span>
                <Button
                  size="small"
                  icon={<FilePdfOutlined />}
                  loading={downloadingFormat === 'pdf'}
                  disabled={downloadingFormat != null}
                  onClick={() => handleDownloadSheet('pdf')}
                >
                  PDF
                </Button>
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  loading={downloadingFormat === 'docx'}
                  disabled={downloadingFormat != null}
                  onClick={() => handleDownloadSheet('docx')}
                >
                  Word
                </Button>
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  loading={downloadingFormat === 'md'}
                  disabled={downloadingFormat != null}
                  onClick={() => handleDownloadSheet('md')}
                >
                  Markdown
                </Button>
              </Space>
            </>
          )}
        </div>
      </SafeModal>

      {/* Proctoring detail modal */}
      <SafeModal
        title={
          <Space>
            <CameraOutlined />
            {selectedProctoring?.display_name || `#${selectedProctoring?.participant_id}`}
            {selectedProctoring?.email ? ` — ${selectedProctoring.email}` : ''}
          </Space>
        }
        open={!!selectedProctoring}
        onCancel={() => { setSelectedProctoring(null); setProSnapshots([]) }}
        footer={
          selectedProctoring && (
            <Space>
              {selectedProctoring.is_locked ? (
                <Button
                  icon={<UnlockOutlined />}
                  onClick={() => handleUnlock(selectedProctoring)}
                  loading={proActionLoading}
                >
                  {t('exam.unlockSession')}
                </Button>
              ) : (
                <Button
                  danger
                  icon={<LockOutlined />}
                  onClick={() => handleLock(selectedProctoring)}
                  loading={proActionLoading}
                >
                  {t('exam.lockSession')}
                </Button>
              )}
            </Space>
          )
        }
        width={700}
      >
        {selectedProctoring && (
          <>
            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>
                <CameraOutlined /> {t('proctoring.report.webcamSnapshots')} ({proSnapshotsLoading ? '…' : proSnapshots.length})
              </Text>
              {proSnapshotsLoading ? (
                <Spin size="small" />
              ) : proSnapshots.length === 0 ? (
                <Alert message={t('proctoring.report.noSnapshots')} type="warning" showIcon style={{ marginBottom: 8 }} />
              ) : (
                <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 8 }}>
                  <Image.PreviewGroup>
                    {proSnapshots.map((snap) => {
                      const snapTime = snap.timestamp_ms
                      const nearViolation = selectedProctoring._integrityEntry?.events?.some((e) => {
                        if (!e.occurred_at) return false
                        const evtMs = dayjs(e.occurred_at).valueOf()
                        return Math.abs(evtMs - snapTime) < 60000
                      })
                      return (
                        <div key={snap.filename} style={{ flexShrink: 0, textAlign: 'center' }}>
                          <Image
                            src={snap.url}
                            width={100}
                            height={75}
                            style={{
                              objectFit: 'cover',
                              border: nearViolation ? '2px solid #ff4d4f' : '2px solid #d9d9d9',
                              borderRadius: 4,
                            }}
                            preview={{ src: snap.url }}
                          />
                          <div style={{ fontSize: 10, color: nearViolation ? '#ff4d4f' : '#999', marginTop: 2 }}>
                            {snap.timestamp_ms ? dayjs(snap.timestamp_ms).format('HH:mm:ss') : ''}
                            {nearViolation && ' ⚠'}
                          </div>
                        </div>
                      )
                    })}
                  </Image.PreviewGroup>
                </div>
              )}
            </div>

            {(!selectedProctoring._integrityEntry?.events || selectedProctoring._integrityEntry.events.length === 0) ? (
              selectedProctoring.integrity_score != null && selectedProctoring.integrity_score < 100 ? (
                <Alert
                  message={t('exam.biometricEventsTitle')}
                  description={t('exam.biometricEventsDesc', { score: selectedProctoring.integrity_score })}
                  type="warning"
                  showIcon
                />
              ) : (
                <Alert message={t('exam.noViolationEvents')} type="success" showIcon />
              )
            ) : (
              <Timeline
                items={selectedProctoring._integrityEntry.events.map((e) => ({
                  color: e.event_type.includes('LOCK') ? 'red' : e.event_type.includes('HONEYPOT') ? 'red' : 'orange',
                  children: (
                    <div>
                      <Text strong>{e.event_type}</Text>
                      {e.rule_id && <Text type="secondary"> ({e.rule_id})</Text>}
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {e.occurred_at ? dayjs(e.occurred_at).format('HH:mm:ss') : ''}
                      </Text>
                      {e.metadata && Object.keys(e.metadata).length > 0 && (
                        <pre style={{ fontSize: 11, marginTop: 4, color: '#666' }}>
                          {JSON.stringify(e.metadata, null, 2)}
                        </pre>
                      )}
                    </div>
                  ),
                }))}
              />
            )}
          </>
        )}
      </SafeModal>

      <SafeConfirm
        open={sendEmailsConfirmOpen}
        title={t('exam.sendResultsTitle')}
        description={t('exam.sendResultsContent', { count: results?.total_completed ?? 0, name: senderName.trim() || 'Swaya.me' })}
        okText={t('exam.sendResultsOk')}
        cancelText={t('common.cancel')}
        danger={false}
        onConfirm={doSendEmails}
        onCancel={() => setSendEmailsConfirmOpen(false)}
      />
    </div>
  )
}
