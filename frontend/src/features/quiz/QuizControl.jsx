import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Card,
  Button,
  Space,
  Tooltip,
  Typography,
  Tag,
  Statistic,
  Row,
  Col,
  Progress,
  Rate,
  message,
  Alert,
  Input,
  Table,
  Popconfirm
} from 'antd'
import {
  PlayCircleOutlined,
  ArrowRightOutlined,
  MobileOutlined,
  CloseCircleOutlined,
  LeftOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  TrophyOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  DesktopOutlined
} from '@ant-design/icons'
import { QRCodeCanvas } from 'qrcode.react'
import ReactWordcloud from 'react-wordcloud'
import { sessionAPI, quizAPI, questionAPI, feedbackAPI } from '../../services/api'
import './QuizControl.css'

const { Title, Text } = Typography
const { TextArea } = Input

export default function QuizControl() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [quiz, setQuiz] = useState(null)
  const [session, setSession] = useState(null)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [wordCloudData, setWordCloudData] = useState([])
  const [leaderboard, setLeaderboard] = useState(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [feedbackRating, setFeedbackRating] = useState(0)
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)
  const [timerRemaining, setTimerRemaining] = useState(null)

  useEffect(() => {
    if (id) {
      loadQuiz()
      loadLatestSession()
    }
  }, [id])

  useEffect(() => {
    if (session) {
      loadResults() // Immediate first load
      const interval = setInterval(loadResults, 3000) // Refresh every 3 seconds
      return () => clearInterval(interval)
    }
  }, [session])

  // Keyboard shortcuts mirror the present screen — ref initialised here, populated below
  const kbRef = useRef({})
  useEffect(() => {
    const onKey = (e) => {
      const { session, results, loading, handleAdvanceQuestion, handleBackQuestion, handleOpenPresent } = kbRef.current
      const normalizedSessionStatus = typeof session?.status === 'string' ? session.status.toLowerCase() : ''
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
      if (e.key === 'F5' && session) {
        e.preventDefault()
        handleOpenPresent()
        return
      }
      if (normalizedSessionStatus !== 'active') return
      if (loading) return
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ' || e.key === 'PageDown' || e.key === 'Enter') {
        // Don't intercept Enter/Space when a Popconfirm button is focused
        if (e.target.closest?.('.ant-popover')) return
        e.preventDefault()
        handleAdvanceQuestion()
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp' || e.key === 'Backspace' || e.key === 'PageUp') {
        if (results?.current_question_index > 0) {
          e.preventDefault()
          handleBackQuestion()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  const loadQuiz = async () => {
    try {
      const response = await quizAPI.get(id)
      setQuiz(response.data)
    } catch (error) {
      message.error(t('quiz.failedToLoadQuiz'))
      console.error(error)
    }
  }

  const loadLatestSession = async () => {
    try {
      const response = await sessionAPI.listSessions(id)
      const sessions = response?.data?.sessions || []
      const openSession = sessions.find((item) => {
        const status = typeof item?.status === 'string' ? item.status.toLowerCase() : ''
        return status === 'active' || status === 'created'
      })
      if (openSession) {
        setSession((prev) => {
          if (prev?.id === openSession.id) return prev
          return {
            ...prev,
            ...openSession,
          }
        })
      }
    } catch (error) {
      console.error('Failed to load sessions:', error)
    }
  }

  const loadResults = async () => {
    if (!session) return
    let latestResults = null
    try {
      const response = await sessionAPI.getResults(session.id)
      latestResults = response.data
      setResults(response.data)

      // If current question is word cloud, fetch word cloud data
      if (response.data.current_question?.question_type === 'word_cloud') {
        loadWordCloudData(response.data.current_question.id)
      }
    } catch (error) {
      console.error(t('quiz.failedToLoadResults'), error)
    }
    if (latestResults?.quiz_type !== 'poll' && quiz?.quiz_type !== 'poll') {
      // Leaderboard is non-critical — fetch independently so it never blocks results
      sessionAPI.getLeaderboard(session.id)
        .then(res => setLeaderboard(res.data))
        .catch(() => {})
    } else {
      setLeaderboard(null)
    }
  }

  const loadWordCloudData = async (questionId) => {
    if (!session) return
    try {
      const response = await questionAPI.getWordCloudResults(questionId, session.id)
      // Transform dict {word: count} to array [{text, value}] for react-wordcloud
      const words = Object.entries(response.data.word_frequencies).map(([word, count]) => ({
        text: word,
        value: count
      }))
      setWordCloudData(words)
    } catch (error) {
      console.error('Failed to load word cloud data:', error)
    }
  }

  const handleStartSession = async () => {
    setLoading(true)
    try {
      const response = await sessionAPI.start(id)
      setSession(response.data)
      message.success(t('quiz.sessionStarted'))
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.failedToStart'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleAdvanceQuestion = async () => {
    setLoading(true)
    try {
      await sessionAPI.advance(session.id)
      message.success(t('quiz.movedToNextQuestion'))
      await loadResults()
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.failedToAdvance'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleBackQuestion = async () => {
    setLoading(true)
    try {
      await sessionAPI.back(session.id)
      message.success(t('quiz.movedToPreviousQuestion'))
      await loadResults()
    } catch (error) {
      message.error(error.response?.data?.detail || t('quiz.failedToGoBack'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleOpenPresent = () => {
    if (!session) return
    window.open(
      `/present/${session.id}?code=${session.join_code}`,
      '_blank',
      'noopener,noreferrer'
    )
  }

  // Populate the keyboard-shortcut ref here, AFTER all const functions are defined
  kbRef.current = { session, results, loading, handleAdvanceQuestion, handleBackQuestion, handleOpenPresent }

  const handleToggleLeaderboard = async () => {
    try {
      await sessionAPI.toggleLeaderboard(session.id)
      await loadResults()
    } catch (error) {
      message.error(t('leaderboard.toggleFailed'))
      console.error(error)
    }
  }

  const handleEndSession = async () => {
    setLoading(true)
    try {
      await sessionAPI.end(session.id)
      message.success(t('quiz.sessionEnded'))
      navigate('/dashboard')
    } catch (error) {
      message.error(t('quiz.failedToEnd'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusTranslation = (status) => {
    if (!status) return t('quiz.ready')
    const statusKey = status.toLowerCase()
    return t(`quiz.${statusKey}`)
  }

  const getSessionStatusUi = (status) => {
    const normalized = typeof status === 'string' ? status.toLowerCase() : ''
    switch (normalized) {
      case 'active':
        return {
          label: t('quiz.active'),
          valueColor: '#52c41a',
          tagColor: 'green',
          tagLabel: t('quiz.live'),
        }
      case 'created':
        return {
          label: t('quiz.started', { defaultValue: 'Started' }),
          valueColor: '#1677ff',
          tagColor: 'blue',
          tagLabel: t('quiz.started', { defaultValue: 'Started' }),
        }
      case 'ended':
        return {
          label: t('quiz.ended'),
          valueColor: '#fa8c16',
          tagColor: 'orange',
          tagLabel: t('quiz.ended'),
        }
      case 'completed':
        return {
          label: t('quiz.completed'),
          valueColor: '#722ed1',
          tagColor: 'purple',
          tagLabel: t('quiz.completed'),
        }
      default:
        return {
          label: getStatusTranslation(status),
          valueColor: '#595959',
          tagColor: 'default',
          tagLabel: getStatusTranslation(status),
        }
    }
  }

  const copyJoinLink = () => {
    const inputElement = document.getElementById('join-url-input')
    if (!inputElement || !inputElement.value) {
      message.error(t('quiz.noUrlToCopy'))
      return
    }

    const joinUrl = inputElement.value
    
    // Safari workaround: Create temporary textarea (not readonly)
    const textarea = document.createElement('textarea')
    textarea.value = joinUrl
    textarea.style.position = 'fixed'
    textarea.style.top = '0'
    textarea.style.left = '0'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    
    try {
      // Focus and select the textarea
      textarea.focus()
      textarea.select()
      textarea.setSelectionRange(0, textarea.value.length)
      
      // Execute copy command
      const successful = document.execCommand('copy')
      
      // Clean up
      document.body.removeChild(textarea)
      
      if (successful) {
        message.success(t('quiz.linkCopied'))
      } else {
        message.error(t('quiz.copyManually'))
      }
    } catch (err) {
      console.error('Copy failed:', err)
      document.body.removeChild(textarea)
      message.error(t('quiz.copyManually'))
    }
  }

  const handleSubmitFeedback = async () => {
    if (!feedbackText.trim()) return
    setFeedbackSubmitting(true)
    try {
      await feedbackAPI.submitUser({
        quiz_id: Number(id),
        session_id: session?.id,
        rating: feedbackRating || undefined,
        feedback_text: feedbackText.trim(),
      })
      setFeedbackSubmitted(true)
      message.success(t('audience.feedbackSubmitted', { defaultValue: 'Feedback submitted' }))
    } catch (error) {
      message.error(error.response?.data?.detail || t('audience.feedbackSubmitFailed', { defaultValue: 'Failed to submit feedback' }))
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  const currentQuestion = results?.current_question
  const currentQuestionAnswerCount = Number(currentQuestion?.total_answers ?? 0)
  const visibleLeaderboard = (leaderboard && currentQuestionAnswerCount > 0)
    ? leaderboard
    : (leaderboard ? { ...leaderboard, entries: [] } : null)
  const isPoll = (results?.quiz_type || quiz?.quiz_type) === 'poll'
  const isWordCloudQuestion = currentQuestion?.question_type === 'word_cloud'
  const isTextQuestion = ['single_line', 'paragraph'].includes(currentQuestion?.question_type)
  const isOptionQuestion = currentQuestion && !isWordCloudQuestion && !isTextQuestion
  const effectiveSessionStatus = results?.status || session?.status
  const normalizedSessionStatus = typeof effectiveSessionStatus === 'string' ? effectiveSessionStatus.toLowerCase() : ''
  const isSessionActive = normalizedSessionStatus === 'active'
  const sessionStatusUi = getSessionStatusUi(effectiveSessionStatus)
  const presentLabel = t('quiz.presentView')
  const timedQuestionActive = Boolean(isSessionActive && currentQuestion?.max_time_seconds)
  const displayTimerRemaining = currentQuestion?.max_time_seconds
    ? (timerRemaining ?? Number(currentQuestion.max_time_seconds))
    : null
  const presentImmersiveTooltip = t(
    'quiz.presentImmersiveTooltip',
    { defaultValue: 'Open immersive presenter mode in a new tab for audience-facing display.' }
  )

  useEffect(() => {
    if (!currentQuestion?.max_time_seconds || !currentQuestion?.timer_started_at) {
      setTimerRemaining(null)
      return
    }

    const maxSeconds = Number(currentQuestion.max_time_seconds)
    const rawStartedAt = String(currentQuestion.timer_started_at)
    const startedAtIso = /Z$|[+-]\d{2}:\d{2}$/.test(rawStartedAt) ? rawStartedAt : `${rawStartedAt}Z`
    const startedAt = new Date(startedAtIso).getTime()
    if (!maxSeconds || Number.isNaN(startedAt)) {
      setTimerRemaining(null)
      return
    }

    const updateRemaining = () => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000)
      const next = Math.max(0, maxSeconds - elapsed)
      setTimerRemaining(next)
    }

    updateRemaining()
    const interval = setInterval(updateRemaining, 1000)
    return () => clearInterval(interval)
  }, [currentQuestion?.id, currentQuestion?.max_time_seconds, currentQuestion?.timer_started_at])

  if (!quiz) {
    return <div style={{ padding: 24 }}>{t('common.loading')}</div>
  }

  return (
    <div className="quiz-control-page" style={{ padding: 24 }}>
      <Space wrap className="quiz-control-topbar">
        <Button
          icon={<LeftOutlined />}
          onClick={() => navigate('/dashboard')}
        >
          {t('quiz.backDashboard')}
        </Button>
        {session && (
          <Tooltip title={presentImmersiveTooltip}>
            <Button
              type="primary"
              className="quiz-control-present-btn"
              icon={<DesktopOutlined />}
              onClick={handleOpenPresent}
            >
              {presentLabel} <kbd className="qc-kbd">F5</kbd>
            </Button>
          </Tooltip>
        )}
        {session && isSessionActive && (
          <Popconfirm
            title={t('quiz.stopQuizTitle')}
            description={t('quiz.stopQuizConfirm')}
            onConfirm={handleEndSession}
            okText={t('quiz.stopQuizOk')}
            cancelText={t('common.cancel')}
            okButtonProps={{ danger: true }}
          >
            <Tooltip title={t('tooltip.stopQuiz')}>
              <Button
                danger
                icon={<CloseCircleOutlined />}
                loading={loading}
              >
                {t('quiz.stopQuiz')}
              </Button>
            </Tooltip>
          </Popconfirm>
        )}
      </Space>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={24} md={24} lg={14} xl={14}>
          <Card>
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Tag color={isPoll ? 'purple' : 'blue'} style={{ width: 'fit-content' }}>
                {isPoll ? t('quiz.poll', { defaultValue: 'Poll' }) : t('quiz.quizTypeLabel', { defaultValue: 'Quiz' })}
              </Tag>
              <Title level={2} style={{ marginBottom: 0 }}>{quiz.title}</Title>
            </Space>
            {quiz.description && <Text type="secondary">{quiz.description}</Text>}
          </Card>
        </Col>
        <Col xs={12} sm={12} md={12} lg={4} xl={4}>
          <Card style={{ height: '100%' }}>
            <div style={{ textAlign: 'center' }}>
              <Statistic
                title={t('quiz.participants')}
                value={results?.total_participants || 0}
                prefix={<TeamOutlined />}
                valueStyle={{ fontSize: 28 }}
              />
            </div>
          </Card>
        </Col>
        <Col xs={12} sm={12} md={12} lg={6} xl={6}>
          <Card style={{ height: '100%', minHeight: 100 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 14, color: '#00000073', marginBottom: 8 }}>{t('quiz.status')}</div>
              <div style={{ fontSize: 24, fontWeight: 600, color: sessionStatusUi.valueColor }}>
                {sessionStatusUi.label}
              </div>
              {session && (
                <Tag color={sessionStatusUi.tagColor} style={{ marginTop: 8 }}>
                  {sessionStatusUi.tagLabel}
                </Tag>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {!session ? (
        <Card>
          <Space direction="vertical" align="center" style={{ width: '100%' }}>
            <Title level={3}>{t('quiz.readyToStart')}</Title>
            <Text>{t('quiz.startSessionDesc')}</Text>
            <Button
              type="primary"
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={handleStartSession}
              loading={loading}
            >
              {t('quiz.startSession')}
            </Button>
          </Space>
        </Card>
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col xs={24} lg={24}>
              <Card title={t('quiz.joinInformation')}>
                <Row gutter={16}>
                  <Col xs={24} md={8} style={{ textAlign: 'center' }}>
                    <QRCodeCanvas
                      value={`${window.location.origin}/join/${session.join_code}`}
                      size={160}
                      level="H"
                      includeMargin={true}
                    />
                  </Col>
                  <Col xs={24} md={8}>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      <div>
                        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                          {t('quiz.joinUrl')}
                        </Text>
                        <Input
                          id="join-url-input"
                          value={`${window.location.origin}/join/${session.join_code}`}
                          readOnly
                          size="large"
                          style={{ marginBottom: 8 }}
                        />
                        <Button
                          type="primary"
                          icon={<CopyOutlined />}
                          onClick={copyJoinLink}
                          block
                        >
                          {t('quiz.copyJoinLink')}
                        </Button>
                      </div>
                    </Space>
                  </Col>
                  <Col xs={24} md={8}>
                    <div style={{ textAlign: 'center' }}>
                      <Statistic
                        title={t('quiz.joinCode')}
                        value={session.join_code}
                        formatter={(value) => String(value).replace(/,/g, '')}
                        valueStyle={{ color: '#3f8600', fontSize: 32, fontWeight: 'bold' }}
                      />
                      <Text type="secondary" style={{ fontSize: 12 }}>{t('quiz.enterCodeAt')}</Text>
                      <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>{t('tooltip.sessionCode')}</div>
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>

          {visibleLeaderboard && !isPoll && (
            <Card
              className="quiz-control-leaderboard-card"
              title={
                <Space wrap className="quiz-control-leaderboard-title">
                  <TrophyOutlined style={{ color: '#faad14' }} />
                  <span>{t('leaderboard.title')}</span>
                  {visibleLeaderboard.total_participants > 0 && (
                    <Tag color="blue">{visibleLeaderboard.total_participants} {t('quiz.participants')}</Tag>
                  )}
                  {visibleLeaderboard.mcq_question_count > 0 && (
                    <Tag color="default">{t('leaderboard.mcqOnly')}</Tag>
                  )}
                </Space>
              }
              extra={
                <Button
                  className="quiz-control-leaderboard-extra-btn"
                  size="small"
                  icon={results?.leaderboard_visible ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                  onClick={handleToggleLeaderboard}
                >
                  {results?.leaderboard_visible ? t('leaderboard.hideFromParticipants') : t('leaderboard.showToParticipants')}
                </Button>
              }
              style={{ marginBottom: 24 }}
            >
              {visibleLeaderboard.entries.length === 0 ? (
                <Text type="secondary">{t('leaderboard.noData')}</Text>
              ) : (
                <>
                  <Table
                    dataSource={visibleLeaderboard.entries.slice(0, 10)}
                    rowKey="participant_id"
                    pagination={false}
                    size="small"
                    columns={[
                      {
                        title: t('leaderboard.rank'),
                        dataIndex: 'rank',
                        width: 60,
                        render: (rank) => {
                          const colors = { 1: '#FFD700', 2: '#C0C0C0', 3: '#CD7F32' }
                          return (
                            <Tag color={colors[rank] ? undefined : 'default'} style={colors[rank] ? { backgroundColor: colors[rank], color: '#000', borderColor: colors[rank] } : {}}>
                              {rank}
                            </Tag>
                          )
                        }
                      },
                      {
                        title: t('leaderboard.participant'),
                        dataIndex: 'display_name',
                        ellipsis: true,
                      },
                      {
                        title: visibleLeaderboard.mcq_question_count > 1 ? `${t('leaderboard.score')} / ${visibleLeaderboard.mcq_question_count}` : t('leaderboard.score'),
                        dataIndex: 'score',
                        width: 100,
                        render: (score) => <Tag color="green">{score}</Tag>
                      },
                      {
                        title: t('leaderboard.timeTaken'),
                        dataIndex: 'time_taken_seconds',
                        width: 90,
                        render: (secs) => secs != null
                          ? <Text type="secondary" style={{ fontSize: 12 }}>{secs.toFixed(1)}s</Text>
                          : <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
                      }
                    ]}
                  />
                  {visibleLeaderboard.entries.length > 10 && (
                    <div style={{ textAlign: 'center', marginTop: 8, color: '#888', fontSize: 12 }}>
                      +{visibleLeaderboard.entries.length - 10} more participants
                    </div>
                  )}
                </>
              )}
            </Card>
          )}

          {currentQuestion ? (
            <Card
              title={
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space>
                    <Tag color="blue">{t('quiz.questionOf')} {results.current_question_index + 1} {t('quiz.of')} {quiz.questions?.length}</Tag>
                    {isWordCloudQuestion && <Tag color="purple">{t('quiz.wordCloud')}</Tag>}
                    {currentQuestion.question_type === 'single_line' && <Tag color="geekblue">{t('quizPresent.singleLine', { defaultValue: 'Single Line' })}</Tag>}
                    {currentQuestion.question_type === 'paragraph' && <Tag color="geekblue">{t('quizPresent.paragraph', { defaultValue: 'Paragraph' })}</Tag>}
                    {currentQuestion.question_type === 'scale' && <Tag color="gold">{t('quizPresent.scaleOneToFive', { defaultValue: 'Scale (1-5)' })}</Tag>}
                    {currentQuestion.max_time_seconds ? <Tag color="orange">{t('quiz.timerTag', { seconds: currentQuestion.max_time_seconds })}</Tag> : null}
                    <Tag color="green">{t('quiz.pointsTag', { points: currentQuestion.points || 1 })}</Tag>
                  </Space>
                  {currentQuestion.max_time_seconds ? (
                    <Space direction="vertical" style={{ width: '100%' }} size={4}>
                      <Text type="secondary">{t('quiz.timeLeft', { seconds: displayTimerRemaining })}</Text>
                      <Progress
                        percent={Math.max(0, Math.min(100, (Number(displayTimerRemaining) / Number(currentQuestion.max_time_seconds)) * 100))}
                        size="small"
                        status={Number(displayTimerRemaining) <= 5 ? 'exception' : Number(displayTimerRemaining) <= 10 ? 'active' : 'normal'}
                        showInfo={false}
                      />
                    </Space>
                  ) : null}
                  {currentQuestion.question_image_url && (
                    <img 
                      src={currentQuestion.question_image_url} 
                      alt={t('quiz.question')} 
                      style={{ 
                        maxWidth: '100%', 
                        maxHeight: '300px', 
                        borderRadius: '8px',
                        marginTop: '8px',
                        display: 'block'
                      }} 
                    />
                  )}
                  <Text strong style={{ display: 'block', marginTop: currentQuestion.question_image_url ? '8px' : '0' }}>
                    {currentQuestion.text}
                  </Text>
                </Space>
              }
              style={{ marginBottom: 24 }}
            >
              <Alert
                message={`${currentQuestion.total_answers || 0} ${t('quiz.responsesReceived')}`}
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              {isWordCloudQuestion ? (
                // Word Cloud Question View
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                  <Alert
                    message={t('quiz.wordCloudQuestion')}
                    description={`${currentQuestion.total_answers || 0} ${t('quiz.responsesReceived')}`}
                    type="info"
                    showIcon
                  />
                  
                  {wordCloudData.length > 0 ? (
                    <div style={{ 
                      width: '100%', 
                      height: '400px', 
                      border: '1px solid #d9d9d9',
                      borderRadius: '8px',
                      padding: '16px',
                      backgroundColor: '#fafafa'
                    }}>
                      <ReactWordcloud
                        words={wordCloudData}
                        options={{
                          rotations: 2,
                          rotationAngles: [0, 90],
                          fontSizes: [20, 80],
                          padding: 5,
                          enableTooltip: true,
                          deterministic: true,
                          fontFamily: 'Arial',
                          colors: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96']
                        }}
                      />
                    </div>
                  ) : (
                    <Alert
                      message={t('quizPresent.noResponsesYet', { defaultValue: 'No responses yet' })}
                      description={t('quizPresent.wordCloudWillAppear', { defaultValue: 'Word cloud will appear once participants start submitting answers.' })}
                      type="warning"
                    />
                  )}
                </Space>
              ) : isTextQuestion ? (
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                  <Alert
                    message={t('quizPresent.textResponseQuestion', { defaultValue: 'Text Response Question' })}
                    description={`${currentQuestion.total_answers || 0} ${t('quiz.responsesReceived')}`}
                    type="info"
                    showIcon
                  />
                  {(currentQuestion.text_responses || []).length > 0 ? (
                    <Card size="small" title={t('quizPresent.latestResponses', { defaultValue: 'Latest responses' })}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        {currentQuestion.text_responses.map((entry, idx) => (
                          <div key={idx} style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 8 }}>
                            <Text strong>{entry.participant_name}</Text>
                            <div><Text>{entry.text}</Text></div>
                          </div>
                        ))}
                      </Space>
                    </Card>
                  ) : (
                    <Text type="secondary">{t('quizPresent.noTextResponsesYet', { defaultValue: 'No text responses yet.' })}</Text>
                  )}
                </Space>
              ) : (
                // Option-based Question View (MCQ/Scale)
                <Space direction="vertical" style={{ width: '100%' }} size="large">
                  {currentQuestion.question_type === 'scale' ? (() => {
                    const dist = currentQuestion.answer_distribution || []
                    const totalAns = currentQuestion.total_answers || 0
                    let sum = 0
                    dist.forEach((count, idx) => { sum += count * (idx + 1) })
                    const avg = totalAns > 0 ? (sum / totalAns).toFixed(1) : 0
                    return (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 0', gap: 16 }}>
                         <Text style={{ fontSize: 18 }}>Average Rating of {totalAns} Response{totalAns !== 1 ? 's' : ''}</Text>
                         <Space align="baseline">
                           <b style={{ fontSize: 48, color: '#faad14', lineHeight: 1 }}>{avg}</b>
                           <Text type="secondary" style={{ fontSize: 18 }}>/ 5</Text>
                         </Space>
                         <Rate disabled allowHalf value={Number(avg)} style={{ fontSize: 32, color: '#faad14' }} />
                      </div>
                    )
                  })() : (currentQuestion.options || []).map((opt, idx) => {
                    const total = currentQuestion.total_answers || 0
                    const count = currentQuestion.answer_distribution?.[idx] || 0
                    const pct = ((count / total * 100) || 0)
                    const letter = String.fromCharCode(65 + idx)
                    const isCorrect = currentQuestion.correct_answer === letter
                    return (
                      <div key={idx}>
                        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 8, alignItems: 'flex-start' }}>
                          <Space direction="vertical">
                            <Text strong>{isOptionQuestion && currentQuestion.question_type === 'mcq' ? `${letter}: ${opt}` : opt}</Text>
                          </Space>
                          <Text>{count} {t('quiz.responses')} ({pct.toFixed(1)}%)</Text>
                        </Space>
                        <Progress percent={pct} strokeColor={isCorrect ? '#52c41a' : '#1890ff'} />
                      </div>
                    )
                  })}

              {!isPoll && (currentQuestion.question_type === 'mcq' || currentQuestion.question_type === 'scale') && currentQuestion.correct_answer && (
                <Alert
                  message={`${t('quiz.correctAnswer')}: ${currentQuestion.correct_answer}`}
                      description={
                        currentQuestion.question_type === 'mcq'
                          ? <span dangerouslySetInnerHTML={{ __html: currentQuestion[`option_${currentQuestion.correct_answer.toLowerCase()}`] || '' }} />
                          : ''
                      }
                      type="success"
                      showIcon
                    />
                  )}
                </Space>
              )}

              <div style={{ marginTop: 24, display: 'flex', justifyContent: 'center', gap: 16, flexWrap: 'wrap' }}>
                <Button
                  type="default"
                  size="large"
                  icon={<LeftOutlined />}
                  onClick={handleBackQuestion}
                  loading={loading}
                  disabled={results.current_question_index === 0}
                >
                  {t('quiz.previousQuestion')} <kbd className="qc-kbd">←</kbd>
                </Button>
                {timedQuestionActive ? (
                  <Popconfirm
                    title={t('quiz.timerOverrideTitle', { defaultValue: 'Skip this timed question early?' })}
                    description={t('quiz.timerOverrideDescription', { defaultValue: 'This question has an active timer. Continue only if you want to override it now.' })}
                    onConfirm={handleAdvanceQuestion}
                    okText={t('quiz.timerOverrideOk', { defaultValue: 'Yes, continue' })}
                    cancelText={t('common.cancel')}
                  >
                    <Button
                      type="primary"
                      size="large"
                      icon={results.current_question_index < (quiz.questions?.length - 1) ? <ArrowRightOutlined /> : <CheckCircleOutlined />}
                      loading={loading}
                    >
                      {results.current_question_index < (quiz.questions?.length - 1) ? t('quiz.nextQuestion') : t('quiz.finish')}
                      {' '}<kbd className="qc-kbd">{results.current_question_index < (quiz.questions?.length - 1) ? '→' : '↵'}</kbd>
                    </Button>
                  </Popconfirm>
                ) : (
                  <Button
                    type="primary"
                    size="large"
                    icon={results.current_question_index < (quiz.questions?.length - 1) ? <ArrowRightOutlined /> : <CheckCircleOutlined />}
                    onClick={handleAdvanceQuestion}
                    loading={loading}
                  >
                    {results.current_question_index < (quiz.questions?.length - 1) ? t('quiz.nextQuestion') : t('quiz.finish')}
                    {' '}<kbd className="qc-kbd">{results.current_question_index < (quiz.questions?.length - 1) ? '→' : '↵'}</kbd>
                  </Button>
                )}
                <Popconfirm
                  title={t('quiz.stopQuizTitle')}
                  description={timedQuestionActive
                    ? t('quiz.timerEndOverrideDescription', { defaultValue: 'A timer is currently running for this question. Ending now will override the timer and end the session.' })
                    : t('quiz.stopQuizConfirm')
                  }
                  onConfirm={handleEndSession}
                  okText={t('quiz.stopQuizOk')}
                  cancelText={t('common.cancel')}
                  okButtonProps={{ danger: true }}
                >
                  <Button
                    danger
                    size="large"
                    icon={<CloseCircleOutlined />}
                    loading={loading}
                  >
                    {t('quiz.stopQuiz')}
                  </Button>
                </Popconfirm>
              </div>
            </Card>
          ) : !results || results.current_question_index === -1 ? (
            <Card>
              <Space direction="vertical" align="center" style={{ width: '100%' }}>
                <Title level={4}>{t('quiz.readyToStartFirst')}</Title>
                <Text>{t('quiz.clickAdvanceToStart')}</Text>
                <Space wrap style={{ justifyContent: 'center' }}>
                  <Button
                    type="primary"
                    size="large"
                    icon={<MobileOutlined />}
                    onClick={handleAdvanceQuestion}
                    loading={loading}
                  >
                    {t('quiz.startFirstQuestion')} <kbd className="qc-kbd">Space</kbd>
                  </Button>
                  <Tooltip title={presentImmersiveTooltip}>
                    <Button
                      type="primary"
                      className="quiz-control-present-btn"
                      size="large"
                      icon={<DesktopOutlined />}
                      onClick={handleOpenPresent}
                    >
                      {presentLabel} <kbd className="qc-kbd">F5</kbd>
                    </Button>
                  </Tooltip>
                </Space>
              </Space>
            </Card>
          ) : (
            <Card>
              <Space direction="vertical" align="center" style={{ width: '100%' }} size="large">
                <Title level={4}>{t('quiz.sessionComplete')}</Title>
                <Text>{t('quiz.allQuestionsAnswered')}</Text>
                <Card size="small" style={{ width: '100%', maxWidth: 620 }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>{t('audience.shareFeedback', { defaultValue: 'Share Feedback' })}</Text>
                    <Rate value={feedbackRating} onChange={setFeedbackRating} disabled={feedbackSubmitted} />
                    <TextArea
                      rows={4}
                      value={feedbackText}
                      onChange={(e) => setFeedbackText(e.target.value)}
                      maxLength={500}
                      showCount
                      disabled={feedbackSubmitted}
                      placeholder={t('quizPresent.shareHostExperience', { defaultValue: 'Share your experience running this quiz' })}
                    />
                    <Button
                      type="primary"
                      onClick={handleSubmitFeedback}
                      loading={feedbackSubmitting}
                      disabled={feedbackSubmitted || !feedbackText.trim()}
                    >
                      {feedbackSubmitted ? t('audience.feedbackSubmitted', { defaultValue: 'Feedback Submitted' }) : t('audience.submitFeedback', { defaultValue: 'Submit Feedback' })}
                    </Button>
                  </Space>
                </Card>
                <Button
                  type="primary"
                  icon={<LeftOutlined />}
                  onClick={() => navigate('/dashboard')}
                >
                  {t('quiz.backDashboard')}
                </Button>
              </Space>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
