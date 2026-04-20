/**
 * ExamResults — host-facing results dashboard
 * Route: /quiz/:id/exam-results (authenticated)
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Button, Table, Space, Tag, Statistic,
  Row, Col, Progress, Alert, Spin, Divider, Tooltip
} from 'antd'
import {
  TrophyOutlined, DownloadOutlined, ArrowLeftOutlined,
  CheckCircleOutlined, CloseCircleOutlined, UserOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartTooltip, ResponsiveContainer, Cell } from 'recharts'
import { examAPI } from '../../services/api'
import dayjs from 'dayjs'
import { ViolationReport } from './ViolationReport'

const { Title, Text } = Typography

export default function ExamResults() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [loading, setLoading] = useState(true)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

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

  const handleExportCsv = () => {
    if (!results) return
    const rows = [
      ['Rank', 'Name', 'Score', 'Max Score', '%', 'Correct', 'Time (s)', 'Completed At'],
      ...results.leaderboard.map(e => [
        e.rank,
        e.display_name,
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
      render: (rank) => (
        rank <= 3
          ? <TrophyOutlined style={{ color: rank === 1 ? '#faad14' : rank === 2 ? '#8c8c8c' : '#cd7f32', fontSize: 18 }} />
          : <Text>{rank}</Text>
      )
    },
    {
      title: t('exam.nameCol'),
      dataIndex: 'display_name',
      render: (name) => <Text strong>{name}</Text>
    },
    {
      title: t('exam.scoreCol'),
      dataIndex: 'score',
      render: (score, row) => (
        <Space>
          <Text strong style={{ color: '#1890ff' }}>{score}</Text>
          <Text type="secondary">/ {row.max_score}</Text>
        </Space>
      )
    },
    {
      title: t('exam.percentCol'),
      dataIndex: 'percentage',
      render: (pct) => (
        <Progress
          percent={pct}
          size="small"
          strokeColor={pct >= 70 ? '#52c41a' : pct >= 40 ? '#faad14' : '#ff4d4f'}
          style={{ width: 100 }}
        />
      )
    },
    {
      title: t('exam.correctAnswers'),
      dataIndex: 'correct_count',
      render: (count) => <Tag color="success" icon={<CheckCircleOutlined />}>{count}</Tag>
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
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/quiz/${id}/edit`)}>
          {t('common.back', 'Back')}
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
          <Text type="secondary">{t('exam.noParticipants')}</Text>
        ) : (
          <Table
            dataSource={results.leaderboard}
            columns={leaderboardColumns}
            rowKey="rank"
            pagination={results.leaderboard.length > 20 ? { pageSize: 20 } : false}
            size="small"
          />
        )}
      </Card>

      {/* Per-question analytics */}
      <Card title={t('exam.questionAnalytics')}>
        {results.question_analytics.map((qa, idx) => (
          <div key={qa.question_id} style={{ marginBottom: 32 }}>
            <Title level={5}>Q{idx + 1}: {qa.question_text}</Title>
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
                  data={qa.options.map((opt, i) => ({
                    name: opt.length > 20 ? opt.slice(0, 20) + '…' : opt,
                    count: qa.answer_distribution[i] || 0,
                    isCorrect: i === qa.correct_answer_index,
                  }))}
                  margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} />
                  <RechartTooltip />
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

      <ViolationReport quizId={id} />
    </div>
  )
}
