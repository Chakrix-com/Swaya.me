import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card, Button, Space, Typography, Tag, Statistic, Progress,
  Alert, Table, Divider, Tooltip, message
} from 'antd'
import {
  LeftOutlined, TrophyOutlined, DownloadOutlined, TeamOutlined,
  CheckCircleOutlined, ThunderboltOutlined, BarChartOutlined
} from '@ant-design/icons'
import { sessionAPI } from '../../services/api'

const { Title, Text } = Typography

const MEDAL = { 1: '🥇', 2: '🥈', 3: '🥉' }
const PODIUM_COLOR = { 1: '#FFD700', 2: '#C0C0C0', 3: '#CD7F32' }

export default function SessionRecap() {
  const { id, sessionId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [results, setResults] = useState(null)
  const [leaderboard, setLeaderboard] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!sessionId) return
    const load = async () => {
      try {
        const [rRes, rLb] = await Promise.all([
          sessionAPI.getResults(sessionId),
          sessionAPI.getLeaderboard(sessionId),
        ])
        setResults(rRes.data)
        setLeaderboard(rLb.data)
      } catch (err) {
        message.error(t('quiz.failedToLoadResults'))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [sessionId])

  if (loading) {
    return <div style={{ padding: 32, textAlign: 'center' }}>{t('common.loading')}</div>
  }

  if (!results) {
    return (
      <div style={{ padding: 32 }}>
        <Alert message={t('quiz.failedToLoadResults')} type="error" />
        <Button icon={<LeftOutlined />} style={{ marginTop: 16 }} onClick={() => navigate(`/quiz/${id}/history`)}>
          {t('quiz.viewHistory')}
        </Button>
      </div>
    )
  }

  const isPoll = results.quiz_type === 'poll'
  const questionResults = results.question_results || []
  const totalParticipants = results.total_participants || 0

  // Per-question accuracy
  const questionStats = questionResults.map((q, idx) => {
    const total = q.total_answers || 0
    const distribution = q.answer_distribution || []
    const correctIdx = q.correct_answer_index
    const correctCount = correctIdx != null ? (distribution[correctIdx] || 0) : 0
    const accuracy = total > 0 ? Math.round((correctCount / total) * 100) : 0
    return { idx, text: q.question_text, total, correctCount, accuracy }
  })

  const hardestQuestion = !isPoll && questionStats.length > 0
    ? questionStats.reduce((worst, q) => (q.accuracy < worst.accuracy ? q : worst), questionStats[0])
    : null

  const entries = leaderboard?.entries || []
  const top3 = entries.slice(0, 3)
  const podiumOrder = top3.length >= 2 ? [top3[1], top3[0], top3[2]].filter(Boolean) : top3

  return (
    <div style={{ padding: '24px', maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <Space style={{ marginBottom: 20, width: '100%', justifyContent: 'space-between' }} wrap>
        <Space>
          <Button icon={<LeftOutlined />} onClick={() => navigate('/dashboard')}>
            {t('quiz.backDashboard')}
          </Button>
          <Button onClick={() => navigate(`/quiz/${id}/history`)}>
            {t('quiz.viewHistory')}
          </Button>
        </Space>
        <Tooltip title={t('quiz.exportResults', { defaultValue: 'Download results as Excel' })}>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => window.open(`/api/v1/quizzes/sessions/${sessionId}/export?format=xlsx`, '_blank')}
          >
            {t('quiz.exportResults', { defaultValue: 'Export' })}
          </Button>
        </Tooltip>
      </Space>

      <Title level={3} style={{ marginBottom: 4 }}>{results.quiz_title}</Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 20 }}>
        {t('quiz.sessionRecapSubtitle', { defaultValue: 'Session recap — share, export, or review before your next run.' })}
      </Text>

      {/* Summary stats */}
      <Card style={{ marginBottom: 20 }}>
        <Space size="large" wrap>
          <Statistic title={t('quiz.participants')} value={totalParticipants} prefix={<TeamOutlined />} />
          <Statistic title={t('quiz.totalQuestions', { defaultValue: 'Questions' })} value={results.total_questions} prefix={<BarChartOutlined />} />
          {!isPoll && questionStats.length > 0 && (
            <Statistic
              title={t('quiz.avgAccuracy', { defaultValue: 'Avg Accuracy' })}
              value={Math.round(questionStats.reduce((s, q) => s + q.accuracy, 0) / questionStats.length)}
              suffix="%"
              prefix={<CheckCircleOutlined />}
            />
          )}
          {hardestQuestion && (
            <div>
              <Text type="secondary" style={{ display: 'block', fontSize: 12, marginBottom: 4 }}>
                {t('quiz.hardestQuestion', { defaultValue: 'Hardest Question' })}
              </Text>
              <Tag color="red" style={{ maxWidth: 200, whiteSpace: 'normal', wordBreak: 'break-word' }}>
                Q{hardestQuestion.idx + 1}: {hardestQuestion.text?.slice(0, 60)}{hardestQuestion.text?.length > 60 ? '…' : ''}
                {' '}({hardestQuestion.accuracy}% correct)
              </Tag>
            </div>
          )}
        </Space>
      </Card>

      {/* Podium */}
      {!isPoll && entries.length > 0 && (
        <Card
          title={<Space><TrophyOutlined style={{ color: '#faad14' }} />{t('leaderboard.title')}</Space>}
          style={{ marginBottom: 20 }}
        >
          {podiumOrder.length >= 2 && (
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap: 16, padding: '16px 0 8px' }}>
              {podiumOrder.map(entry => (
                <div key={entry.participant_id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flex: 1, maxWidth: 160 }}>
                  <div style={{ fontSize: 13, textAlign: 'center', fontWeight: entry.rank <= 3 ? 700 : 400, wordBreak: 'break-word' }}>
                    {MEDAL[entry.rank] || ''} {entry.display_name}
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>{entry.score} pts</div>
                  <div style={{
                    width: '100%',
                    height: entry.rank === 1 ? 90 : entry.rank === 2 ? 64 : 48,
                    background: PODIUM_COLOR[entry.rank] || '#d9d9d9',
                    borderRadius: '6px 6px 0 0',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 700, color: 'rgba(0,0,0,0.65)', fontSize: 14,
                  }}>
                    #{entry.rank}
                  </div>
                </div>
              ))}
            </div>
          )}
          {entries.length > 3 && (
            <>
              <Divider style={{ margin: '8px 0' }} />
              <Table
                dataSource={entries.slice(3, 13)}
                rowKey="participant_id"
                pagination={false}
                size="small"
                columns={[
                  { title: t('leaderboard.rank'), dataIndex: 'rank', width: 60, render: r => <Tag>{r}</Tag> },
                  { title: t('leaderboard.participant'), dataIndex: 'display_name', ellipsis: true },
                  { title: t('leaderboard.score'), dataIndex: 'score', width: 80, render: s => <Tag color="green">{s}</Tag> },
                  {
                    title: t('leaderboard.timeTaken'), dataIndex: 'time_taken_seconds', width: 90,
                    render: s => s != null ? <Text type="secondary" style={{ fontSize: 12 }}>{s.toFixed(1)}s</Text> : '—'
                  },
                ]}
              />
              {entries.length > 13 && (
                <div style={{ textAlign: 'center', marginTop: 8, color: '#888', fontSize: 12 }}>
                  +{entries.length - 13} {t('quiz.moreParticipants', { defaultValue: 'more participants' })}
                </div>
              )}
            </>
          )}
        </Card>
      )}

      {/* Per-question accuracy */}
      {questionStats.length > 0 && (
        <Card title={<Space><BarChartOutlined />{t('quiz.perQuestionAccuracy', { defaultValue: 'Per-Question Accuracy' })}</Space>}>
          <Space direction="vertical" style={{ width: '100%' }}>
            {questionStats.map(q => (
              <div key={q.idx}>
                <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 4 }}>
                  <Text style={{ flex: 1, wordBreak: 'break-word' }}>
                    <Text type="secondary">Q{q.idx + 1}</Text> {q.text}
                  </Text>
                  <Text type="secondary" style={{ whiteSpace: 'nowrap', marginLeft: 8 }}>
                    {q.correctCount}/{q.total} ({q.accuracy}%)
                  </Text>
                </Space>
                <Progress
                  percent={q.accuracy}
                  strokeColor={q.accuracy >= 70 ? '#52c41a' : q.accuracy >= 40 ? '#faad14' : '#f5222d'}
                  size="small"
                  showInfo={false}
                />
              </div>
            ))}
          </Space>
        </Card>
      )}
    </div>
  )
}
