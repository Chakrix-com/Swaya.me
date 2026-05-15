import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, Typography, Space, Tag, Spin, Alert, Statistic, Row, Col,
  Divider, Button, message, Progress
} from 'antd'
import { ArrowLeftOutlined, UserOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useTranslation } from 'react-i18next'
import { offlinePollAPI, quizAPI } from '../../services/api'

const { Title, Text, Paragraph } = Typography

const CHART_COLORS = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2']

export default function OfflinePollResults() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [loading, setLoading] = useState(true)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!id) return
    quizAPI.get(id)
      .then(res => {
        const quiz = res.data
        if (!quiz.poll_slug) {
          setError('This quiz is not an offline poll or has not been published yet.')
          setLoading(false)
          return null
        }
        return offlinePollAPI.getResults(quiz.poll_slug)
      })
      .then(res => {
        if (res) setResults(res.data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.response?.data?.detail || 'Failed to load results')
        setLoading(false)
      })
  }, [id])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (error) return <Alert type="error" message={error} style={{ margin: 24 }} />
  if (!results) return null

  const completionRate = results.total_participants > 0
    ? Math.round((results.completed_participants / results.total_participants) * 100)
    : 0

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>
          {t('common.back', 'Back')}
        </Button>
      </Space>

      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space align="center" wrap>
            <Title level={3} style={{ margin: 0 }}>{results.quiz_title}</Title>
            {results.is_open
              ? <Tag color="green">{t('offlinePoll.pollOpen', 'Poll open')}</Tag>
              : <Tag color="default">{t('offlinePoll.pollClosed', 'Poll closed')}</Tag>}
          </Space>

          {results.offline_start_at && (
            <Text type="secondary">
              {new Date(results.offline_start_at).toLocaleString()} — {results.offline_end_at ? new Date(results.offline_end_at).toLocaleString() : '∞'}
            </Text>
          )}

          {results.poll_slug && (
            <Space>
              <Text type="secondary" copyable={{ text: `${window.location.origin}/poll/${results.poll_slug}` }}>
                {`/poll/${results.poll_slug}`}
              </Text>
            </Space>
          )}

          <Divider />

          <Row gutter={24}>
            <Col xs={12} sm={8}>
              <Statistic
                title={t('offlinePoll.totalParticipants', 'Total participants')}
                value={results.total_participants}
                prefix={<UserOutlined />}
              />
            </Col>
            <Col xs={12} sm={8}>
              <Statistic
                title={t('offlinePoll.completed', 'Completed')}
                value={results.completed_participants}
                prefix={<CheckCircleOutlined />}
              />
            </Col>
            <Col xs={24} sm={8}>
              <div>
                <Text type="secondary">{t('offlinePoll.completionRate')}</Text>
                <Progress percent={completionRate} size="small" />
              </div>
            </Col>
          </Row>
        </Space>
      </Card>

      {/* Per-question results */}
      {results.question_results.map((qr, idx) => (
        <Card key={qr.question_id} style={{ marginTop: 16 }}>
          <Title level={5}>
            Q{idx + 1}: {qr.question_text}
          </Title>
          <Text type="secondary">{qr.total_answers} {t('common.responses', 'responses')}</Text>

          {qr.question_type === 'mcq' && qr.options && qr.answer_distribution && (
            <div style={{ marginTop: 16 }}>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={qr.options.map((opt, i) => ({
                    label: opt.length > 20 ? opt.slice(0, 20) + '…' : opt,
                    count: qr.answer_distribution[i] || 0,
                  }))}
                  margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
                >
                  <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {qr.options.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {/* Option labels */}
              <Row gutter={8} style={{ marginTop: 8 }}>
                {qr.options.map((opt, i) => (
                  <Col key={i} xs={12} sm={6}>
                    <Space size={4}>
                      <div style={{ width: 12, height: 12, borderRadius: 2, background: CHART_COLORS[i % CHART_COLORS.length] }} />
                      <Text style={{ fontSize: 12 }}>{opt}: <strong>{qr.answer_distribution[i] || 0}</strong></Text>
                    </Space>
                  </Col>
                ))}
              </Row>
            </div>
          )}

          {qr.word_frequencies && Object.keys(qr.word_frequencies).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Space wrap>
                {Object.entries(qr.word_frequencies).slice(0, 30).map(([word, count]) => (
                  <Tag
                    key={word}
                    color="blue"
                    style={{ fontSize: Math.max(12, Math.min(20, 12 + count * 2)) }}
                  >
                    {word} ({count})
                  </Tag>
                ))}
              </Space>
            </div>
          )}

          {qr.question_type !== 'mcq' && (!qr.word_frequencies || Object.keys(qr.word_frequencies).length === 0) && (
            <Paragraph type="secondary" style={{ marginTop: 8 }}>No responses yet.</Paragraph>
          )}
        </Card>
      ))}
    </div>
  )
}
