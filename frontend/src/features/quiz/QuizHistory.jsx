import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card,
  Button,
  Dropdown,
  Space,
  Typography,
  Tag,
  Table,
  Progress,
  Collapse,
  Statistic,
  Row,
  Col,
  Empty,
  Spin,
  Alert,
  message,
} from 'antd'
import {
  DownloadOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FilePptOutlined,
  FileExcelOutlined,
  LeftOutlined,
  TrophyOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  MessageOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { sessionAPI, quizAPI } from '../../services/api'

const { Title, Text } = Typography
const { Panel } = Collapse

// Format seconds as "Xs" or "Xm Ys"
function formatTime(secs) {
  if (secs == null) return '—'
  if (secs < 60) return `${secs.toFixed(1)}s`
  const m = Math.floor(secs / 60)
  const s = (secs % 60).toFixed(0).padStart(2, '0')
  return `${m}m ${s}s`
}

// Per-session detail panel (lazy-loaded when accordion opens)
function SessionDetail({ sessionId, quizType }) {
  const { t } = useTranslation()
  const isPoll = quizType === 'poll'
  const [results, setResults] = useState(null)
  const [leaderboard, setLeaderboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const requests = [sessionAPI.getResults(sessionId)]
        if (!isPoll) requests.push(sessionAPI.getLeaderboard(sessionId))
        const [resResp, lbResp] = await Promise.allSettled(requests)
        if (cancelled) return
        if (resResp.status === 'fulfilled') setResults(resResp.value.data)
        else setError(resResp.reason?.response?.data?.detail || t('quiz.failedToLoadResults'))
        if (!isPoll && lbResp?.status === 'fulfilled') setLeaderboard(lbResp.value.data)
      } catch (e) {
        if (!cancelled) setError(t('quiz.failedToLoadResults'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [sessionId])

  if (loading) return <div style={{ padding: 24, textAlign: 'center' }}><Spin indicator={<LoadingOutlined spin />} /></div>
  if (error) return <Alert type="error" message={error} />

  const rankColors = { 1: '#FFD700', 2: '#C0C0C0', 3: '#CD7F32' }

  const lbColumns = [
    {
      title: t('leaderboard.rank'),
      dataIndex: 'rank',
      width: 55,
      render: (rank) => (
        <Tag style={rankColors[rank] ? { backgroundColor: rankColors[rank], color: '#000', borderColor: rankColors[rank] } : {}}>
          {rank}
        </Tag>
      ),
    },
    {
      title: t('leaderboard.participant'),
      dataIndex: 'display_name',
      ellipsis: true,
    },
    {
      title: `${t('leaderboard.score')}${leaderboard ? ` / ${leaderboard.mcq_question_count}` : ''}`,
      dataIndex: 'score',
      width: 90,
      render: (s) => <Tag color="green">{s}</Tag>,
    },
    {
      title: t('leaderboard.timeTaken'),
      dataIndex: 'time_taken_seconds',
      width: 90,
      render: (secs) => <Text type="secondary" style={{ fontSize: 12 }}>{formatTime(secs)}</Text>,
    },
  ]

  return (
    <div style={{ padding: '8px 0' }}>
      {/* Summary stats */}
      {results && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('quiz.participants')}
              value={results.total_participants}
              prefix={<TeamOutlined />}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic
              title={t('quiz.questions')}
              value={results.total_questions}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ fontSize: 20 }}
            />
          </Col>
          {leaderboard && leaderboard.mcq_question_count > 0 && (
            <Col xs={12} sm={6}>
              <Statistic
                title={t('leaderboard.mcqOnly')}
                value={leaderboard.mcq_question_count}
                valueStyle={{ fontSize: 20 }}
              />
            </Col>
          )}
        </Row>
      )}

      {/* Leaderboard */}
      {leaderboard && (
        <Card
          size="small"
          title={
            <Space>
              <TrophyOutlined style={{ color: '#faad14' }} />
              <span>{t('leaderboard.title')}</span>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          {leaderboard.entries.length === 0 ? (
            <Text type="secondary">{t('leaderboard.noData')}</Text>
          ) : (
            <Table
              dataSource={leaderboard.entries}
              rowKey="participant_id"
              columns={lbColumns}
              pagination={false}
              size="small"
            />
          )}
        </Card>
      )}

      {/* Per-question results */}
      {results && results.question_results && results.question_results.length > 0 && (
        <Card
          size="small"
          title={
            <Space>
              <MessageOutlined />
              <span>{t('quiz.questionResults')}</span>
            </Space>
          }
        >
          {results.question_results.map((q, idx) => {
            const total = q.total_answers || 0
            return (
              <div key={q.question_id} style={{ marginBottom: idx < results.question_results.length - 1 ? 20 : 0 }}>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>
                  {idx + 1}. {q.question_text}
                </Text>
                {q.options?.length > 0 ? (
                  q.options.map((opt, i) => {
                    const count = q.answer_distribution?.[i] || 0
                    const pct = total > 0 ? (count / total) * 100 : 0
                    const isCorrect = i === q.correct_answer_index
                    return (
                      <div key={i} style={{ marginBottom: 6 }}>
                        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 2 }}>
                          <Text style={{ color: isCorrect ? '#52c41a' : undefined }}>
                            {String.fromCharCode(65 + i)}. {opt}
                            {isCorrect && <Tag color="success" style={{ marginLeft: 6 }}>{t('quiz.correct')}</Tag>}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {count} ({pct.toFixed(0)}%)
                          </Text>
                        </Space>
                        <Progress
                          percent={pct}
                          strokeColor={isCorrect ? '#52c41a' : '#1890ff'}
                          showInfo={false}
                          size="small"
                        />
                      </div>
                    )
                  })
                ) : (
                  <Text type="secondary">{t('quiz.wordCloudQuestion')} — {total} {t('quiz.responsesReceived')}</Text>
                )}
              </div>
            )
          })}
        </Card>
      )}
    </div>
  )
}

export default function QuizHistory() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [quizTitle, setQuizTitle] = useState('')
  const [quizType, setQuizType] = useState('quiz')
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [exportingSessionId, setExportingSessionId] = useState(null)

  const handleExport = async (sessionId, format) => {
    setExportingSessionId(sessionId)
    try {
      const response = await sessionAPI.exportSession(sessionId, format)
      const blob = new Blob([response.data], { type: response.headers['content-type'] })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const disposition = response.headers['content-disposition'] || ''
      const match = disposition.match(/filename=(.+)/)
      link.download = match ? match[1] : `quiz_results_${sessionId}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      message.success(t('quiz.exportSuccess'))
    } catch {
      message.error(t('quiz.exportFailed'))
    } finally {
      setExportingSessionId(null)
    }
  }

  const exportMenuItems = (sessionId) => [
    { key: 'pdf',  label: t('quiz.exportPdf'),  icon: <FilePdfOutlined />,  onClick: () => handleExport(sessionId, 'pdf') },
    { key: 'docx', label: t('quiz.exportDocx'), icon: <FileWordOutlined />,  onClick: () => handleExport(sessionId, 'docx') },
    { key: 'pptx', label: t('quiz.exportPptx'), icon: <FilePptOutlined />,   onClick: () => handleExport(sessionId, 'pptx') },
    { key: 'xlsx', label: t('quiz.exportXlsx'), icon: <FileExcelOutlined />, onClick: () => handleExport(sessionId, 'xlsx') },
  ]

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [sessionResp, quizResp] = await Promise.all([
          sessionAPI.listSessions(id),
          quizAPI.get(id),
        ])
        setQuizTitle(sessionResp.data.quiz_title)
        setSessions(sessionResp.data.sessions)
        setQuizType(quizResp.data.quiz_type || 'quiz')
      } catch (e) {
        console.error('Failed to load session history:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const statusColor = { created: 'blue', active: 'green', ended: 'default' }
  const statusLabel = {
    created: t('quiz.started', { defaultValue: 'Started' }),
    active: t('quiz.live'),
    ended: t('quiz.ended'),
  }

  return (
    <div style={{ padding: 24 }}>
      <Space style={{ marginBottom: 20 }}>
        <Button icon={<LeftOutlined />} onClick={() => navigate('/dashboard')}>
          {t('quiz.backDashboard')}
        </Button>
      </Space>

      <Space direction="vertical" size={4} style={{ marginBottom: 4 }}>
        <Tag color={quizType === 'poll' ? 'purple' : 'blue'} style={{ width: 'fit-content' }}>
          {quizType === 'poll' ? t('quiz.poll', { defaultValue: 'Poll' }) : t('quiz.quizTypeLabel', { defaultValue: 'Quiz' })}
        </Tag>
        <Title level={3} style={{ marginBottom: 0 }}>{quizTitle}</Title>
      </Space>
      <Text type="secondary" style={{ display: 'block', marginBottom: 20 }}>
        {t('quiz.sessionHistory')}
      </Text>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin indicator={<LoadingOutlined style={{ fontSize: 32 }} spin />} />
        </div>
      ) : sessions.length === 0 ? (
        <Empty description={t('quiz.noSessionsYet')} />
      ) : (
        <Collapse accordion>
          {sessions.map((session) => {
            const date = new Date(session.created_at)
            const dateStr = date.toLocaleString()
            const header = (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                <Space wrap>
                  <Tag color={statusColor[session.status]}>{statusLabel[session.status]}</Tag>
                  <Text strong>{dateStr}</Text>
                  <Space>
                    <TeamOutlined />
                    <Text>{session.participant_count} {t('quiz.participants')}</Text>
                  </Space>
                  <Text type="secondary">·</Text>
                  <Text type="secondary">{session.total_responses} {t('quiz.responses')}</Text>
                </Space>
                <div onClick={(e) => e.stopPropagation()} style={{ marginLeft: 8 }}>
                  <Dropdown
                    menu={{ items: exportMenuItems(session.id) }}
                    trigger={['click']}
                    disabled={session.status !== 'ended'}
                  >
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      loading={exportingSessionId === session.id}
                    >
                      {t('quiz.export')}
                    </Button>
                  </Dropdown>
                </div>
              </div>
            )
            return (
              <Panel key={session.id} header={header}>
                <SessionDetail sessionId={session.id} quizType={quizType} />
              </Panel>
            )
          })}
        </Collapse>
      )}
    </div>
  )
}
