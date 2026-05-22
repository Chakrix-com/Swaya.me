/**
 * ExamResults — host-facing results dashboard
 * Route: /quiz/:id/exam-results (authenticated)
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Button, Table, Space, Tag, Statistic,
  Row, Col, Progress, Alert, Spin, Divider, Tooltip, Input, Modal, List
} from 'antd'
const { TextArea } = Input
import {
  TrophyOutlined, DownloadOutlined, ArrowLeftOutlined,
  CheckCircleOutlined, CloseCircleOutlined, UserOutlined,
  ClockCircleOutlined, SyncOutlined, RobotOutlined, FilePdfOutlined
} from '@ant-design/icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartTooltip, ResponsiveContainer, Cell } from 'recharts'
import { examAPI } from '../../services/api'
import dayjs from 'dayjs'
import { ViolationReport } from './ViolationReport'
import { exportExamResultsPDF } from './exportPDF'
import RichTextRenderer from '../quiz/components/RichTextRenderer'
import ReactMarkdown from 'react-markdown'
import './ExamResults.css'

const { Title, Text } = Typography
const stripHtml = (h) => (h || '').replace(/<[^>]*>/g, '').trim()

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
  const [error, setError] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [analysing, setAnalysing] = useState(false)
  const [analysisError, setAnalysisError] = useState(null)
  const [customPrompt, setCustomPrompt] = useState(DEFAULT_AI_PROMPT)
  const [downloadingPDF, setDownloadingPDF] = useState(false)
  const [participantDetail, setParticipantDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)

  const handleRowClick = async (record) => {
    if (!record.participant_id) return
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

  useEffect(() => {
    const load = async () => {
      try {
        const res = await examAPI.getResults(id)
        setResults(res.data)
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
      setAnalysisError(err.response?.data?.detail || 'AI analysis failed. Please try again.')
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

  const handleExportCsv = () => {
    if (!results) return
    const rows = [
      ['Rank', 'Name', 'Email', 'Score', 'Max Score', '%', 'Correct', 'Time (s)', 'Completed At'],
      ...results.leaderboard.map(e => [
        e.rank,
        e.display_name,
        e.email || '',
        e.score,
        e.max_score,
        e.percentage,
        e.correct_count,
        e.time_taken_seconds != null ? Math.round(e.time_taken_seconds) : '',
        e.completed_at ? dayjs(e.completed_at).format('YYYY-MM-DD HH:mm:ss') : '',
      ])
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

  const leaderboardColumns = [
    {
      title: t('exam.rankCol'),
      dataIndex: 'rank',
      width: 60,
      render: (rank, row) => {
        if (!row.is_completed) return <Tag icon={<SyncOutlined spin />} color="processing">{t('exam.inProgress')}</Tag>
        if (rank <= 3) return <TrophyOutlined style={{ color: rank === 1 ? '#faad14' : rank === 2 ? '#8c8c8c' : '#cd7f32', fontSize: 18 }} />
        return <Text>{rank}</Text>
      }
    },
    {
      title: t('exam.nameCol'),
      dataIndex: 'display_name',
      render: (name, row) => <Text strong style={row.is_completed ? {} : { color: '#8c8c8c' }}>{name}</Text>
    },
    {
      title: t('exam.emailCol'),
      dataIndex: 'email',
      render: (email) => email ? <Text type="secondary" style={{ fontSize: 12 }}>{email}</Text> : <Text type="secondary">—</Text>
    },
    {
      title: t('exam.scoreCol'),
      dataIndex: 'score',
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
      title: t('exam.correctAnswers'),
      dataIndex: 'correct_count',
      render: (count, row) => row.is_completed
        ? <Tag color="success" icon={<CheckCircleOutlined />}>{count}</Tag>
        : <Text type="secondary">—</Text>
    },
    {
      title: t('exam.timeTakenCol'),
      dataIndex: 'time_taken_seconds',
      render: (secs) => {
        if (secs == null) return '—'
        const m = Math.floor(secs / 60)
        const s = Math.round(secs % 60)
        return <Text><ClockCircleOutlined style={{ marginRight: 4 }} />{m}m {s}s</Text>
      }
    },
    {
      title: t('exam.completedAtCol'),
      dataIndex: 'completed_at',
      render: (dt) => dt ? dayjs(dt).format('HH:mm, DD MMM') : '—'
    },
  ]

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
          {analysis ? 'Download PDF Report (with AI)' : 'Download PDF Report'}
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

      {/* Leaderboard */}
      <Card
        title={
          <Space>
            <TrophyOutlined />
            {t('exam.leaderboard')}
          </Space>
        }
        extra={
          <Button icon={<DownloadOutlined />} onClick={handleExportCsv}>
            {t('exam.exportCsv')}
          </Button>
        }
        style={{ marginBottom: 24 }}
      >
        {results.leaderboard.length === 0 ? (
          <Text type="secondary">{t('exam.noParticipantsYet', 'No one has started this exam yet.')}</Text>
        ) : (
          <Table
            dataSource={results.leaderboard}
            columns={leaderboardColumns}
            rowKey={(r, i) => r.participant_id ?? `ip-${i}`}
            pagination={results.leaderboard.length > 20 ? { pageSize: 20 } : false}
            size="small"
            onRow={(record) => ({
              onClick: () => handleRowClick(record),
              style: record.is_completed ? { cursor: 'pointer' } : {},
            })}
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
                <Text type="secondary">{qa.total_answers} responses</Text>
              </Col>
            </Row>

            {qa.options && qa.answer_distribution && (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart
                  data={qa.options.map((opt, i) => {
                    const plain = stripHtml(opt)
                    return {
                      name: plain.length > 24 ? plain.slice(0, 24) + '…' : plain,
                      fullText: plain,
                      count: qa.answer_distribution[i] || 0,
                      isCorrect: i === qa.correct_answer_index,
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
                        fill={i === qa.correct_answer_index ? '#52c41a' : '#1890ff'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
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
                Download PDF
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

      <ViolationReport quizId={id} />

      <Modal
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={760}
        title={
          participantDetail
            ? `${participantDetail.display_name}${participantDetail.email ? ` — ${participantDetail.email}` : ''}`
            : 'Participant Detail'
        }
        destroyOnClose
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
                const answered = q.participant_answer != null
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
                                const isChosen = i === q.participant_answer
                                const isCorrect = i === q.correct_answer_index
                                return (
                                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                                    <span style={{
                                      fontWeight: isCorrect ? 700 : 400,
                                      color: isCorrect ? '#389e0d' : isChosen ? '#cf1322' : '#595959',
                                    }}>
                                      {String.fromCharCode(65 + i)}. {stripHtml(opt)}
                                    </span>
                                    {isCorrect && <Tag color="success" style={{ margin: 0, fontSize: 11 }}>Correct</Tag>}
                                    {isChosen && !isCorrect && <Tag color="error" style={{ margin: 0, fontSize: 11 }}>Their answer</Tag>}
                                    {isChosen && isCorrect && <Tag color="success" style={{ margin: 0, fontSize: 11 }}>Their answer</Tag>}
                                  </div>
                                )
                              })}
                            </div>
                          )}
                          {!answered && <Text type="secondary" style={{ fontSize: 12 }}>Not answered</Text>}
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
          <Alert type="error" message="Could not load participant detail." />
        )}
      </Modal>
    </div>
  )
}
