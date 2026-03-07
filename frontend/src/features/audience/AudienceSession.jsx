import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import {
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Alert,
  Result,
  Progress,
  Input,
  message,
  Rate,
  Table
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  LoginOutlined,
  SendOutlined,
  TrophyOutlined
} from '@ant-design/icons'
import ReactWordcloud from 'react-wordcloud'
import { sessionAPI, questionAPI, feedbackAPI } from '../../services/api'
import { useTranslation } from 'react-i18next'

const { Title, Text } = Typography
const { TextArea } = Input

export default function AudienceSession() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const reduxSession = useSelector((state) => state.session.session)

  const locationState = location.state || {}
  const sessionToken = locationState.sessionToken || reduxSession?.session_token
  const sessionId = locationState.sessionId || reduxSession?.session_id
  const displayName = locationState.displayName || reduxSession?.display_name || 'Guest'

  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [wordCloudAnswer, setWordCloudAnswer] = useState('')
  const [wordCloudData, setWordCloudData] = useState([])
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sessionStatus, setSessionStatus] = useState(null)
  const [sessionInvalidated, setSessionInvalidated] = useState(false)
  const [leaderboard, setLeaderboard] = useState(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [feedbackRating, setFeedbackRating] = useState(0)
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)
  const lastQuestionIdRef = useRef(null)
  const pollingIntervalRef = useRef(null)

  useEffect(() => {
    if (sessionToken && sessionId) {
      pollingIntervalRef.current = setInterval(loadResults, 2000)
      loadResults()
      return () => {
        if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current)
      }
    }
  }, [sessionToken, sessionId])

  const loadResults = async () => {
    if (!sessionToken || !sessionId) return
    try {
      const response = await sessionAPI.getResults(sessionId, sessionToken)
      const newQuestionId = response.data.current_question?.question_id
      const newStatus = response.data.status

      if (sessionStatus && sessionStatus !== newStatus) {
        if (newStatus === 'ended') {
          message.success('Quiz has ended! Thank you for participating!')
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
        } else if (newStatus === 'active' && sessionStatus === 'created') {
          message.info('Quiz is starting!')
        }
      }
      setSessionStatus(newStatus)

      if (lastQuestionIdRef.current && newQuestionId && newQuestionId !== lastQuestionIdRef.current) {
        setSubmitted(false)
        setSelectedAnswer(null)
        setWordCloudAnswer('')
        setWordCloudData([])
      }

      lastQuestionIdRef.current = newQuestionId
      setResults(response.data)
      setCurrentQuestion(response.data.current_question)

      if (response.data.current_question?.question_type === 'word_cloud') {
        loadWordCloudData(response.data.current_question.question_id)
      }
    } catch (error) {
      if (error.response?.status === 403) {
        setSessionInvalidated(true)
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        message.warning('Session has been restarted. Please rejoin with the new code.')
      }
    }
    sessionAPI.getLeaderboard(sessionId, sessionToken)
      .then(res => setLeaderboard(res.data))
      .catch(() => {})
  }

  const loadWordCloudData = async (questionId) => {
    if (!sessionId) return
    try {
      const response = await questionAPI.getWordCloudResults(questionId, sessionId)
      const words = Object.entries(response.data.word_frequencies).map(([word, count]) => ({
        text: word, value: count
      }))
      setWordCloudData(words)
    } catch (error) {
      console.error('Failed to load word cloud data:', error)
    }
  }

  const handleSubmitAnswer = async () => {
    const isWordCloud = currentQuestion?.question_type === 'word_cloud'
    if (isWordCloud ? !wordCloudAnswer?.trim() : !selectedAnswer) return

    setLoading(true)
    try {
      if (isWordCloud) {
        await sessionAPI.submitWordCloudAnswer(sessionToken, {
          question_id: currentQuestion.question_id,
          text_answer: wordCloudAnswer.trim()
        })
        setWordCloudAnswer('')
        setTimeout(() => loadWordCloudData(currentQuestion.question_id), 500)
      } else {
        const answerIndex = selectedAnswer.charCodeAt(0) - 65
        await sessionAPI.submitAnswer(sessionToken, {
          question_id: currentQuestion.question_id,
          selected_option_index: answerIndex
        })
        setSubmitted(true)
      }
    } catch (error) {
      if (!isWordCloud) setSubmitted(true)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitFeedback = async () => {
    if (!feedbackText.trim()) return
    setFeedbackSubmitting(true)
    try {
      await feedbackAPI.submitParticipant(sessionToken, {
        feedback_text: feedbackText.trim(),
        rating: feedbackRating || undefined,
        display_name: displayName,
      })
      setFeedbackSubmitted(true)
      message.success('Thank you for your feedback')
    } catch (error) {
      message.error(error.response?.data?.detail || 'Failed to submit feedback')
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  const rankColors = { 1: '#FFD700', 2: '#C0C0C0', 3: '#CD7F32' }

  const leaderboardColumns = [
    {
      title: t('leaderboard.rank'),
      dataIndex: 'rank',
      width: 55,
      render: (rank) => (
        <Tag style={rankColors[rank] ? { backgroundColor: rankColors[rank], color: 'var(--aud-input-text)', borderColor: rankColors[rank] } : {}}>
          {rank}
        </Tag>
      )
    },
    {
      title: t('leaderboard.participant'),
      dataIndex: 'display_name',
      ellipsis: false,
      render: (name, record) => (
        <span style={{ ...(record.is_current_participant ? { fontWeight: 700, color: '#1890ff' } : {}), whiteSpace: 'normal', wordBreak: 'break-word' }}>
          {name}{record.is_current_participant ? ' (You)' : ''}
        </span>
      )
    },
    {
      title: t('leaderboard.score'),
      dataIndex: 'score',
      width: 72,
      render: (score, record) => (
        <Tag color={record.is_current_participant ? 'blue' : 'green'}>{score}</Tag>
      )
    },
    {
      title: t('leaderboard.timeTaken'),
      dataIndex: 'time_taken_seconds',
      width: 78,
      responsive: ['sm'],
      render: (secs) => secs != null
        ? <Text type="secondary" style={{ fontSize: 12 }}>{secs.toFixed(1)}s</Text>
        : <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
    }
  ]

  const LeaderboardTable = () => {
    if (!leaderboard || results?.leaderboard_visible === false) return null
    return (
      <Card
        size="small"
        title={
          <Space wrap>
            <TrophyOutlined style={{ color: '#faad14' }} />
            <span>{t('leaderboard.title')}</span>
            {leaderboard.current_participant_rank && (
              <Tag color="blue">{t('leaderboard.yourRank', { rank: leaderboard.current_participant_rank })}</Tag>
            )}
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        {leaderboard.entries.length === 0 ? (
          <Text type="secondary">{t('leaderboard.noData')}</Text>
        ) : (
          <>
            <div className="table-responsive">
              <Table
                dataSource={leaderboard.entries.slice(0, 10)}
                rowKey="participant_id"
                columns={leaderboardColumns}
                pagination={false}
                size="small"
                scroll={{ x: 420 }}
                rowClassName={(record) => record.is_current_participant ? 'leaderboard-you-row' : ''}
              />
            </div>
            {leaderboard.entries.length > 10 && (
              <div style={{ textAlign: 'center', marginTop: 8, color: 'var(--aud-text-secondary)', fontSize: 12 }}>
                +{leaderboard.entries.length - 10} more participants
              </div>
            )}
          </>
        )}
      </Card>
    )
  }

  const isWordCloud = currentQuestion?.question_type === 'word_cloud'
  const isCorrect = submitted && !isWordCloud && selectedAnswer === currentQuestion?.correct_answer

  return (
    <div className="audience-session min-vh-100 d-flex flex-column" style={{ position: 'relative', overflowX: 'hidden' }}>
      <div className="container overflow-hidden py-3">
        <div className="row justify-content-center">
          <div className="col-12 col-sm-10 col-md-8 col-lg-7" style={{ position: 'relative', overflowX: 'hidden', minWidth: 0 }}>

            {/* ── No session token ── */}
            {!sessionToken && (
              <Result
                status="error"
                title="No Session Found"
                subTitle="Please join a session first"
                extra={
                  <Button type="primary" icon={<LoginOutlined />} onClick={() => navigate('/join')}>
                    Go to Join Page
                  </Button>
                }
              />
            )}

            {/* ── Session invalidated ── */}
            {sessionToken && sessionInvalidated && (
              <Card>
                <Result
                  status="warning"
                  icon={<CloseCircleOutlined style={{ color: '#faad14' }} />}
                  title="Session Restarted"
                  subTitle="The host has started a new quiz session"
                  extra={
                    <Button type="primary" icon={<LoginOutlined />} onClick={() => navigate('/join')} size="large">
                      Rejoin Quiz
                    </Button>
                  }
                />
              </Card>
            )}

            {/* ── Quiz ended ── */}
            {sessionToken && !sessionInvalidated && sessionStatus === 'ended' && !currentQuestion && (
              <Card>
                <Result
                  status="success"
                  icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                  title="Quiz Completed!"
                  subTitle={
                    <Space direction="vertical" align="center" style={{ marginTop: 16, width: '100%' }}>
                      <Title level={4} style={{ margin: 0 }}>
                        Your Score: {results?.participant_correct || 0}/{results?.total_questions || 0}
                      </Title>
                      <Text type="secondary">
                        You got {results?.participant_correct || 0} correct answer{(results?.participant_correct || 0) !== 1 ? 's' : ''}!
                      </Text>
                      <Tag
                        color="blue"
                        style={{ marginTop: 8, maxWidth: '100%', whiteSpace: 'normal', wordBreak: 'break-word' }}
                      >
                        Joined as: {displayName}
                      </Tag>
                      <LeaderboardTable />
                      <Card size="small" style={{ width: '100%', marginTop: 16 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text strong>Share Feedback</Text>
                          <Rate value={feedbackRating} onChange={setFeedbackRating} disabled={feedbackSubmitted} />
                          <TextArea
                            rows={3}
                            maxLength={500}
                            showCount
                            value={feedbackText}
                            onChange={(e) => setFeedbackText(e.target.value)}
                            placeholder="Tell us what worked well or what can improve"
                            disabled={feedbackSubmitted}
                          />
                          <Button
                            type="primary"
                            onClick={handleSubmitFeedback}
                            loading={feedbackSubmitting}
                            disabled={feedbackSubmitted || !feedbackText.trim()}
                          >
                            {feedbackSubmitted ? 'Feedback Submitted' : 'Submit Feedback'}
                          </Button>
                        </Space>
                      </Card>
                    </Space>
                  }
                  extra={<Text type="secondary">Thank you for participating!</Text>}
                />
              </Card>
            )}

            {/* ── Waiting for host / next question ── */}
            {sessionToken && !sessionInvalidated && !currentQuestion && sessionStatus !== 'ended' && (
              <Card>
                  <Space direction="vertical" align="center" style={{ width: '100%' }}>
                    <LoadingOutlined style={{ fontSize: 48 }} />
                    <Title level={3}>
                      {sessionStatus === 'created' ? 'Waiting for quiz to start...' : 'Waiting for next question...'}
                    </Title>
                    <Text type="secondary">
                      {sessionStatus === 'created' ? 'The quiz will start soon' : 'Host is preparing the next question'}
                    </Text>
                    <Tag color="blue" style={{ maxWidth: '100%', whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      Joined as: {displayName}
                    </Tag>
                  </Space>
                </Card>
              )}

            {/* ── Active question ── */}
            {sessionToken && !sessionInvalidated && currentQuestion && (
              <>
                <Card style={{ marginBottom: 16 }}>
                  <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Tag color="blue">Question {results.current_question_index + 1}</Tag>
                    {isWordCloud && <Tag color="purple">Word Cloud</Tag>}
                    <Text strong style={{ wordBreak: 'break-word' }}>{displayName}</Text>
                  </Space>
                </Card>

                <Card
                  title={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {currentQuestion.question_image_url && (
                        <img
                          src={currentQuestion.question_image_url}
                          alt="Question"
                          style={{ maxWidth: '100%', maxHeight: 240, borderRadius: 8, display: 'block' }}
                        />
                      )}
                      <Title
                        level={3}
                        style={{
                          margin: currentQuestion.question_image_url ? '8px 0 0 0' : 0,
                          wordBreak: 'break-word',
                          overflowWrap: 'break-word',
                          whiteSpace: 'normal'
                        }}
                      >
                        {currentQuestion.text}
                      </Title>
                    </Space>
                  }
                >
                  {isWordCloud ? (
                    <>
                      <TextArea
                        rows={3}
                        placeholder="Enter your answer (max 100 characters)"
                        maxLength={100}
                        value={wordCloudAnswer}
                        onChange={(e) => setWordCloudAnswer(e.target.value)}
                        showCount
                        style={{ marginBottom: 16 }}
                      />
                      <Button
                        type="primary"
                        size="large"
                        block
                        icon={<SendOutlined />}
                        disabled={!wordCloudAnswer.trim()}
                        onClick={handleSubmitAnswer}
                        loading={loading}
                        style={{ marginBottom: 24 }}
                      >
                        Submit Answer
                      </Button>
                      {wordCloudData.length > 0 ? (
                        <>
                          <Alert
                            message="Live Word Cloud"
                            description={`${wordCloudData.reduce((sum, w) => sum + w.value, 0)} responses submitted`}
                            type="info"
                            showIcon
                            style={{ marginBottom: 16 }}
                          />
                          <div style={{
                            width: '100%', height: 300,
                            border: '1px solid #d9d9d9', borderRadius: 8,
                            padding: 16, backgroundColor: '#fafafa'
                          }}>
                            <ReactWordcloud
                              words={wordCloudData}
                              options={{
                                rotations: 2, rotationAngles: [0, 90],
                                fontSizes: [16, 60], padding: 4,
                                enableTooltip: true, deterministic: true, fontFamily: 'Arial',
                                colors: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96']
                              }}
                            />
                          </div>
                        </>
                      ) : (
                        <Alert
                          message="Be the first to respond!"
                          description="Submit your answer and watch the word cloud grow."
                          type="info"
                          showIcon
                        />
                      )}
                    </>
                  ) : !submitted ? (
                    <>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}>
                        {['A', 'B', 'C', 'D'].map((key) => {
                          const label = currentQuestion[`option_${key.toLowerCase()}`]
                          const isSelected = selectedAnswer === key
                          return (
                            <div
                              key={key}
                              onClick={() => setSelectedAnswer(key)}
                              style={{
                                display: 'block',
                                width: '100%',
                                padding: '12px 16px',
                                border: `2px solid ${isSelected ? '#1890ff' : '#d9d9d9'}`,
                                borderRadius: 8,
                                backgroundColor: isSelected ? '#e6f7ff' : 'white',
                                cursor: 'pointer',
                                boxSizing: 'border-box',
                                wordBreak: 'break-word',
                                overflowWrap: 'break-word',
                                color: 'var(--aud-input-text)',
                              }}
                            >
                              <div>
                                <span style={{ color: 'var(--aud-input-text)', fontWeight: 700 }}>{key}:</span>{' '}
                                <span style={{ color: 'var(--aud-input-text)' }}>{label}</span>
                              </div>
                              {currentQuestion.option_images?.[key] && (
                                <img
                                  src={currentQuestion.option_images[key]}
                                  alt={`Option ${key}`}
                                  style={{ maxWidth: '100%', maxHeight: 160, borderRadius: 4, marginTop: 8 }}
                                />
                              )}
                            </div>
                          )
                        })}
                      </div>
                      <Button
                        type="primary"
                        size="large"
                        block
                        icon={<SendOutlined />}
                        disabled={!selectedAnswer}
                        onClick={handleSubmitAnswer}
                        loading={loading}
                        style={{ marginTop: 24 }}
                      >
                        Submit Answer
                      </Button>
                    </>
                  ) : (
                    <>
                      <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        {['A', 'B', 'C', 'D'].map((key) => {
                          const label = currentQuestion[`option_${key.toLowerCase()}`]
                          const idx = key.charCodeAt(0) - 65
                          const dist = currentQuestion.answer_distribution || [0, 0, 0, 0]
                          const totalAns = currentQuestion.total_answers || 0
                          const count = dist[idx] || 0
                          const pct = totalAns > 0 ? (count / totalAns * 100) : 0
                          const correct = currentQuestion.correct_answer === key
                          const selected = selectedAnswer === key
                          const borderColor = correct ? '#52c41a' : selected ? '#ff4d4f' : '#d9d9d9'
                          const bgColor = correct ? '#f6ffed' : selected ? '#fff1f0' : '#fafafa'
                          const badgeBg = correct ? '#52c41a' : selected ? '#ff4d4f' : '#bfbfbf'
                          const badgeIcon = correct ? <CheckCircleOutlined /> : selected ? <CloseCircleOutlined /> : key
                          return (
                            <div key={key} style={{
                              border: `2px solid ${borderColor}`, borderRadius: 8,
                              padding: '12px 16px', background: bgColor,
                              opacity: (!correct && !selected) ? 0.55 : 1,
                              transition: 'all 0.3s ease',
                              color: 'var(--aud-input-text)',
                            }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                                <span style={{
                                  width: 30, height: 30, borderRadius: '50%',
                                  background: badgeBg, color: '#fff',
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                  fontSize: 14, fontWeight: 700, flexShrink: 0,
                                }}>
                                  {badgeIcon}
                                </span>
                                <span style={{ flex: 1, wordBreak: 'break-word', fontWeight: correct ? 600 : 400, color: 'var(--aud-input-text)' }}>
                                  {label}
                                </span>
                                <span style={{ whiteSpace: 'nowrap', fontSize: 13, color: 'var(--aud-text-secondary)' }}>
                                  {count} ({pct.toFixed(1)}%)
                                </span>
                              </div>
                              {currentQuestion.option_images?.[key] && (
                                <img
                                  src={currentQuestion.option_images[key]}
                                  alt={`Option ${key}`}
                                  style={{ maxWidth: '100%', maxHeight: 120, borderRadius: 4, marginBottom: 8 }}
                                />
                              )}
                              <Progress
                                percent={parseFloat(pct.toFixed(1))}
                                strokeColor={correct ? '#52c41a' : '#1890ff'}
                                showInfo={false}
                                size="small"
                              />
                            </div>
                          )
                        })}
                      </Space>
                      <Alert
                        message="Waiting for next question..."
                        type="info"
                        showIcon
                        style={{ marginTop: 16 }}
                      />
                      <LeaderboardTable />
                    </>
                  )}
                </Card>
              </>
            )}

          </div>
        </div>
      </div>
    </div>
  )
}
