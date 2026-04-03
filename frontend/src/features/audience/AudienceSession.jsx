import { useState, useEffect, useRef, useContext } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { useDispatch } from 'react-redux'
import {
  App,
  Card,
  Button,
  Space,
  Typography,
  Tag,
  Alert,
  Result,
  Progress,
  Input,
  Rate,
  Table
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  LoginOutlined,
  SendOutlined,
  TrophyOutlined,
  LogoutOutlined
} from '@ant-design/icons'
import ReactWordcloud from 'react-wordcloud'
import { sessionAPI, questionAPI, feedbackAPI } from '../../services/api'
import { useTranslation } from 'react-i18next'
import { clearSession } from '../../store/sessionSlice'
import PublicBrandHeader from '../../components/PublicBrandHeader'
import RichTextRenderer from '../quiz/components/RichTextRenderer'
import RichTextEditor from '../quiz/components/RichTextEditor'
import { VisitorThemeContext } from '../../App'

const { Title, Text } = Typography
const { TextArea } = Input

export default function AudienceSession() {
  const { message } = App.useApp()
  const location = useLocation()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { t } = useTranslation()
  const { theme } = useContext(VisitorThemeContext)
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
  const [timerRemaining, setTimerRemaining] = useState(null)
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
    let latestResults = null
    try {
      let response
      try {
        response = await sessionAPI.getAudienceResults(sessionId, sessionToken)
      } catch (error) {
        // Backward compatibility for servers that have not yet deployed audience-safe endpoints
        if (error.response?.status === 404) {
          response = await sessionAPI.getResults(sessionId, sessionToken)
        } else {
          throw error
        }
      }
      latestResults = response.data
      const newQuestionId = response.data.current_question?.question_id
      const newStatus = response.data.status

      if (sessionStatus && sessionStatus !== newStatus) {
        if (newStatus === 'ended') {
          message.success(t('audience.quizEndedThanks', { defaultValue: 'Quiz has ended! Thank you for participating!' }))
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
          }
        } else if (newStatus === 'active' && sessionStatus === 'created') {
          message.info(t('audience.quizStarting', { defaultValue: 'Quiz is starting!' }))
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
        message.warning(t('audience.sessionRestarted', { defaultValue: 'Session has been restarted. Please rejoin with the new code.' }))
      }
    }
    if (latestResults?.quiz_type !== 'poll') {
      sessionAPI.getAudienceLeaderboard(sessionId, sessionToken)
        .then(res => setLeaderboard(res.data))
        .catch(async (error) => {
          if (error.response?.status === 404) {
            try {
              const fallback = await sessionAPI.getLeaderboard(sessionId, sessionToken)
              setLeaderboard(fallback.data)
            } catch (_) {}
          }
        })
    } else {
      setLeaderboard(null)
    }
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
    if (isTextQuestion ? !wordCloudAnswer?.trim() : selectedAnswer === null) return

    setLoading(true)
    try {
      if (isTextQuestion) {
        await sessionAPI.submitWordCloudAnswer(sessionToken, {
          question_id: currentQuestion.question_id,
          text_answer: wordCloudAnswer.trim()
        })
        setWordCloudAnswer('')
        if (isWordCloud) {
          setTimeout(() => loadWordCloudData(currentQuestion.question_id), 500)
        } else {
          setSubmitted(true)
        }
      } else if (isScaleQuestion) {
        await sessionAPI.submitAnswer(sessionToken, {
          question_id: currentQuestion.question_id,
          selected_option_index: Number(selectedAnswer)
        })
        setSubmitted(true)
      } else {
        const answerIndex = selectedAnswer.charCodeAt(0) - 65
        await sessionAPI.submitAnswer(sessionToken, {
          question_id: currentQuestion.question_id,
          selected_option_index: answerIndex
        })
        setSubmitted(true)
      }
    } catch (error) {
      const detail = error.response?.data?.detail
      if (detail) {
        message.error(detail)
      } else if (!isWordCloud) {
        setSubmitted(true)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitFeedback = async () => {
    if (!feedbackText || feedbackText.replace(/<[^>]*>/g, '').trim() === '') return
    setFeedbackSubmitting(true)
    try {
      await feedbackAPI.submitParticipant(sessionToken, {
        feedback_text: feedbackText,
        rating: feedbackRating || undefined,
        display_name: displayName,
      })
      setFeedbackSubmitted(true)
      message.success(t('audience.feedbackThanks', { defaultValue: 'Thank you for your feedback' }))
    } catch (error) {
      message.error(error.response?.data?.detail || t('audience.feedbackSubmitFailed', { defaultValue: 'Failed to submit feedback' }))
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  const handleLeaveSession = async () => {
    try {
      if (sessionToken) {
        await sessionAPI.leave(sessionToken)
      }
    } catch (_) {
      // non-blocking
    } finally {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
      dispatch(clearSession())
      message.info(t('audience.leftSession', { defaultValue: 'You left the session' }))
      navigate('/join')
    }
  }

  const isPollSession = results?.quiz_type === 'poll'
  const currentQuestionAnswerCount = Number(results?.current_question?.total_answers ?? 0)
  const visibleLeaderboard = (leaderboard && currentQuestionAnswerCount > 0)
    ? leaderboard
    : (leaderboard ? { ...leaderboard, entries: [] } : null)
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
          {name}{record.is_current_participant ? ` (${t('audience.you', { defaultValue: 'You' })})` : ''}
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
    if (isPollSession || !visibleLeaderboard || results?.leaderboard_visible === false) return null
    return (
      <Card
        size="small"
        title={
          <Space wrap>
            <TrophyOutlined style={{ color: '#faad14' }} />
            <span>{t('leaderboard.title')}</span>
            {visibleLeaderboard.current_participant_rank && (
              <Tag color="blue">{t('leaderboard.yourRank', { rank: visibleLeaderboard.current_participant_rank })}</Tag>
            )}
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        {visibleLeaderboard.entries.length === 0 ? (
          <Text type="secondary">{t('leaderboard.noData')}</Text>
        ) : (
          <>
            <div className="table-responsive">
              <Table
                dataSource={visibleLeaderboard.entries.slice(0, 10)}
                rowKey="participant_id"
                columns={leaderboardColumns}
                pagination={false}
                size="small"
                scroll={{ x: 420 }}
                rowClassName={(record) => record.is_current_participant ? 'leaderboard-you-row' : ''}
              />
            </div>
            {visibleLeaderboard.entries.length > 10 && (
              <div style={{ textAlign: 'center', marginTop: 8, color: 'var(--aud-text-secondary)', fontSize: 12 }}>
                {t('audience.moreParticipants', { count: visibleLeaderboard.entries.length - 10, defaultValue: `+${visibleLeaderboard.entries.length - 10} more participants` })}
              </div>
            )}
          </>
        )}
      </Card>
    )
  }

  const isWordCloud = currentQuestion?.question_type === 'word_cloud'
  const isScaleQuestion = currentQuestion?.question_type === 'scale'
  const isTextQuestion = ['word_cloud', 'single_line', 'paragraph'].includes(currentQuestion?.question_type)
  const isPoll = results?.quiz_type === 'poll'
  const displayTimerRemaining = currentQuestion?.max_time_seconds
    ? (timerRemaining ?? Number(currentQuestion.max_time_seconds))
    : null

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
      setTimerRemaining(Math.max(0, maxSeconds - elapsed))
    }

    updateRemaining()
    const interval = setInterval(updateRemaining, 1000)
    return () => clearInterval(interval)
  }, [currentQuestion?.id, currentQuestion?.max_time_seconds, currentQuestion?.timer_started_at])

  return (
    <div className="audience-session min-vh-100 d-flex flex-column" style={{ position: 'relative', overflowX: 'hidden' }}>
      <PublicBrandHeader />
      <div className="container py-3">
        <div className="row justify-content-center mx-0">
          <div className="col-12 col-sm-10 col-md-8 col-lg-7 px-0 px-sm-3" style={{ position: 'relative', overflowX: 'hidden', minWidth: 0 }}>
            {sessionToken && !sessionInvalidated && sessionStatus !== 'ended' && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
                <Button icon={<LogoutOutlined />} onClick={handleLeaveSession}>
                  {t('audience.leaveSession', { defaultValue: 'Leave Session' })}
                </Button>
              </div>
            )}

            {/* ── No session token ── */}
            {!sessionToken && (
              <Result
                status="error"
                title={t('audience.noSessionFound', { defaultValue: 'No Session Found' })}
                subTitle={t('audience.pleaseJoinFirst', { defaultValue: 'Please join a session first' })}
                extra={
                  <Button type="primary" icon={<LoginOutlined />} onClick={() => navigate('/join')}>
                    {t('audience.goToJoinPage', { defaultValue: 'Go to Join Page' })}
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
                  title={t('audience.sessionRestartedTitle', { defaultValue: 'Session Restarted' })}
                  subTitle={t('audience.sessionRestartedSubtitle', { defaultValue: 'The host has started a new quiz session' })}
                  extra={
                    <Button type="primary" icon={<LoginOutlined />} onClick={() => navigate('/join')} size="large">
                      {t('audience.rejoinQuiz', { defaultValue: 'Rejoin Quiz' })}
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
                  title={t('audience.quizCompleted', { defaultValue: 'Quiz Completed!' })}
                  subTitle={
                    <Space direction="vertical" align="center" style={{ marginTop: 16, width: '100%' }}>
                      {isPoll ? (
                        <Title level={4} style={{ margin: 0 }}>
                          {t('quizPresent.pollCompleted', { defaultValue: 'Poll completed' })}
                        </Title>
                      ) : (
                        <>
                          <Title level={4} style={{ margin: 0 }}>
                            {t('audience.yourScore', { defaultValue: 'Your Score' })}: {results?.participant_correct || 0}/{results?.total_questions || 0}
                          </Title>
                          <Text type="secondary">
                            {t('audience.correctAnswersCount', { count: results?.participant_correct || 0 })}
                          </Text>
                        </>
                      )}
                      <Tag
                        color="blue"
                        style={{ marginTop: 8, maxWidth: '100%', whiteSpace: 'normal', wordBreak: 'break-word' }}
                      >
                        {t('audience.joinedAs', { defaultValue: 'Joined as' })}: {displayName}
                      </Tag>
                      <LeaderboardTable />
                      <Card size="small" style={{ width: '100%', marginTop: 16 }}>
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text strong>{t('audience.shareFeedback', { defaultValue: 'Share Feedback' })}</Text>
                          <Rate value={feedbackRating} onChange={setFeedbackRating} disabled={feedbackSubmitted} />
                          <div style={{ marginBottom: 20 }}>
                            <RichTextEditor
                              value={feedbackText}
                              onChange={setFeedbackText}
                              placeholder={t('audience.feedbackPlaceholder', { defaultValue: 'Tell us what worked well or what can improve' })}
                              isDark={theme === 'dark'}
                              disabled={feedbackSubmitted}
                              showCode={false}
                            />
                          </div>
                          <Button
                            type="primary"
                            onClick={handleSubmitFeedback}
                            loading={feedbackSubmitting}
                            disabled={feedbackSubmitted || !feedbackText || feedbackText.replace(/<[^>]*>/g, '').trim() === ''}
                          >
                            {feedbackSubmitted ? t('audience.feedbackSubmitted', { defaultValue: 'Feedback Submitted' }) : t('audience.submitFeedback', { defaultValue: 'Submit Feedback' })}
                          </Button>
                        </Space>
                      </Card>
                    </Space>
                  }
                  extra={<Text type="secondary">{t('quizPresent.thanksForParticipating', { defaultValue: 'Thanks for participating.' })}</Text>}
                />
              </Card>
            )}

            {/* ── Waiting for host / next question ── */}
            {sessionToken && !sessionInvalidated && !currentQuestion && sessionStatus !== 'ended' && (
              <Card>
                  <Space direction="vertical" align="center" style={{ width: '100%' }}>
                    <LoadingOutlined style={{ fontSize: 48 }} />
                    <Title level={3}>
                      {sessionStatus === 'created' ? t('audience.waiting') : t('audience.waitingForNextQuestion', { defaultValue: 'Waiting for next question...' })}
                    </Title>
                    <Text type="secondary">
                      {sessionStatus === 'created' ? t('audience.quizWillStartSoon', { defaultValue: 'The quiz will start soon' }) : t('audience.hostPreparingNextQuestion', { defaultValue: 'Host is preparing the next question' })}
                    </Text>
                    <Tag color="blue" style={{ maxWidth: '100%', whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      {t('audience.joinedAs', { defaultValue: 'Joined as' })}: {displayName}
                    </Tag>
                  </Space>
                </Card>
              )}

            {/* ── Active question ── */}
            {sessionToken && !sessionInvalidated && currentQuestion && (
              <>
                <Card style={{ marginBottom: 16 }}>
                  <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Tag color="blue">{t('quiz.question')} {results.current_question_index + 1}</Tag>
                    {isWordCloud && <Tag color="purple">{t('quiz.wordCloud')}</Tag>}
                    {currentQuestion.question_type === 'single_line' && <Tag color="geekblue">{t('quizPresent.singleLine', { defaultValue: 'Single Line' })}</Tag>}
                    {currentQuestion.question_type === 'paragraph' && <Tag color="geekblue">{t('quizPresent.paragraph', { defaultValue: 'Paragraph' })}</Tag>}
                    {isScaleQuestion && <Tag color="gold">{t('quizPresent.scaleOneToFive', { defaultValue: 'Scale 1-5' })}</Tag>}
                    {currentQuestion.max_time_seconds ? <Tag color="orange">{t('quiz.timerTag', { seconds: currentQuestion.max_time_seconds })}</Tag> : null}
                    <Text strong style={{ wordBreak: 'break-word' }}>{displayName}</Text>
                  </Space>
                  {currentQuestion.max_time_seconds ? (
                    <Space direction="vertical" style={{ width: '100%', marginTop: 8 }} size={4}>
                        <Text type="secondary">{t('quiz.timeLeft', { seconds: displayTimerRemaining })}</Text>
                        <Progress
                          percent={Math.max(0, Math.min(100, (Number(displayTimerRemaining) / Number(currentQuestion.max_time_seconds)) * 100))}
                          size="small"
                          status={Number(displayTimerRemaining) <= 5 ? 'exception' : Number(displayTimerRemaining) <= 10 ? 'active' : 'normal'}
                          showInfo={false}
                        />
                      </Space>
                    ) : null}
                </Card>

                <Card
                  title={
                    <Space direction="vertical" style={{ width: '100%' }}>
                      {currentQuestion.question_image_url && (
                        <img
                          src={currentQuestion.question_image_url}
                          alt={t('quiz.question')}
                          style={{ maxWidth: '100%', maxHeight: 240, borderRadius: 8, display: 'block' }}
                        />
                      )}
                      <RichTextRenderer
                        content={currentQuestion.text}
                        isDark={theme === 'dark'}
                        className="aud-question-text"
                      />
                    </Space>
                  }
                >
                  {isTextQuestion ? (
                    <>
                      <TextArea
                        rows={currentQuestion.question_type === 'paragraph' ? 5 : 3}
                        placeholder={
                          currentQuestion.question_type === 'word_cloud'
                            ? t('audience.enterWordCloudAnswer', { defaultValue: 'Enter your answer (max 100 characters)' })
                            : currentQuestion.question_type === 'single_line'
                              ? t('audience.enterShortAnswer', { defaultValue: 'Enter a short answer' })
                              : t('audience.enterParagraphAnswer', { defaultValue: 'Enter your paragraph answer' })
                        }
                        maxLength={
                          currentQuestion.question_type === 'word_cloud'
                            ? 100
                            : currentQuestion.question_type === 'single_line'
                              ? 255
                              : 2000
                        }
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
                        {t('quiz.submitAnswer')}
                      </Button>
                      {isWordCloud && wordCloudData.length > 0 ? (
                        <>
                          <Alert
                            message={t('audience.liveWordCloud', { defaultValue: 'Live Word Cloud' })}
                            description={t('audience.responsesSubmittedCount', { count: wordCloudData.reduce((sum, w) => sum + w.value, 0) })}
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
                      ) : isWordCloud ? (
                        <Alert
                          message={t('audience.beFirstToRespond', { defaultValue: 'Be the first to respond!' })}
                          description={t('audience.wordCloudGrow', { defaultValue: 'Submit your answer and watch the word cloud grow.' })}
                          type="info"
                          showIcon
                        />
                      ) : (
                        <Alert
                          message={t('audience.responseSubmitted', { defaultValue: 'Response submitted' })}
                          description={t('audience.waitingHostNext', { defaultValue: 'Waiting for the host to move to the next question.' })}
                          type="success"
                          showIcon
                        />
                      )}
                    </>
                  ) : !submitted ? (
                    <>
                      {isScaleQuestion ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, width: '100%', alignItems: 'center', padding: '24px 0' }}>
                          <Text style={{ fontSize: 18, color: 'var(--aud-input-text)' }}>{t('audience.tapStarToRate', { defaultValue: 'Tap a star to rate:' })}</Text>
                          <Rate
                            className="audience-rate-stars"
                            style={{ fontSize: 48, color: '#faad14' }}
                            value={selectedAnswer ? Number(selectedAnswer) + 1 : 0}
                            onChange={(val) => {
                              // We submit 0-indexed values for our backend (0 = 1 star, 4 = 5 stars)
                              if (val > 0) setSelectedAnswer(String(val - 1))
                            }}
                          />
                          <Text type="secondary">{selectedAnswer ? t('audience.selectedStars', { count: Number(selectedAnswer) + 1 }) : t('audience.noRatingSelected', { defaultValue: 'No rating selected' })}</Text>
                        </div>
                      ) : (
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
                                border: `2px solid ${isSelected ? 'var(--ctrl-radio-selected-border)' : 'var(--ctrl-radio-option-border)'}`,
                                borderRadius: 8,
                                backgroundColor: isSelected ? 'var(--ctrl-radio-selected-bg)' : 'var(--aud-input-bg)',
                                cursor: 'pointer',
                                boxSizing: 'border-box',
                                wordBreak: 'break-word',
                                overflowWrap: 'break-word',
                                color: 'var(--aud-text-primary)',
                              }}
                            >
                              <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                                <span style={{ fontWeight: 700, marginTop: 4 }}>{key}:</span>
                                <RichTextRenderer
                                  content={label || ''}
                                  isDark={theme === 'dark'}
                                  style={{ flex: 1 }}
                                />
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
                      )}
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
                        {t('quiz.submitAnswer')}
                      </Button>
                    </>
                  ) : (
                    <>
                      <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        {isScaleQuestion ? (() => {
                          const dist = currentQuestion.answer_distribution || []
                          const totalAns = currentQuestion.total_answers || 0
                          let sum = 0
                          dist.forEach((count, idx) => { sum += count * (idx + 1) })
                          const avg = totalAns > 0 ? (sum / totalAns).toFixed(1) : 0
                          return (
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 0', gap: 16 }}>
                               <Text style={{ fontSize: 18 }}>{t('quizPresent.averageRating', { defaultValue: 'Average Rating' })}</Text>
                               <Space align="baseline">
                                 <b style={{ fontSize: 48, color: '#faad14', lineHeight: 1 }}>{avg}</b>
                                 <Text type="secondary" style={{ fontSize: 18 }}>/ 5</Text>
                               </Space>
                               <Rate disabled allowHalf value={Number(avg)} style={{ fontSize: 32, color: '#faad14' }} />
                               <Text type="secondary">{t('audience.ratingsCount', { count: totalAns })}</Text>
                            </div>
                          )
                        })() : isPoll ? ['A', 'B', 'C', 'D'].map((key) => {
                          const label = currentQuestion[`option_${key.toLowerCase()}`]
                          const idx = key.charCodeAt(0) - 65
                          const dist = currentQuestion.answer_distribution || [0, 0, 0, 0]
                          const totalAns = currentQuestion.total_answers || 0
                          const count = dist[idx] || 0
                          const pct = totalAns > 0 ? (count / totalAns * 100) : 0
                          const selected = selectedAnswer === key
                          return (
                            <div key={key} style={{
                              border: `2px solid ${selected ? 'var(--ctrl-radio-selected-border)' : 'var(--ctrl-radio-option-border)'}`,
                              borderRadius: 8,
                              padding: '12px 16px',
                              background: selected ? 'var(--ctrl-radio-selected-bg)' : 'var(--aud-input-bg)',
                              color: 'var(--aud-text-primary)',
                            }}>
                              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 8 }}>
                                <span style={{ fontWeight: 700, marginTop: 4 }}>{key}:</span>
                                <RichTextRenderer
                                  content={label || ''}
                                  isDark={theme === 'dark'}
                                  style={{ flex: 1 }}
                                />
                                <span style={{ whiteSpace: 'nowrap', fontSize: 13, color: 'var(--aud-text-secondary)', marginTop: 4 }}>
                                  {count} ({pct.toFixed(1)}%)
                                </span>
                              </div>
                              <Progress
                                percent={parseFloat(pct.toFixed(1))}
                                strokeColor="#1890ff"
                                showInfo={false}
                                size="small"
                              />
                            </div>
                          )
                        }) : ['A', 'B', 'C', 'D'].map((key) => {
                          const label = currentQuestion[`option_${key.toLowerCase()}`]
                          const idx = key.charCodeAt(0) - 65
                          const dist = currentQuestion.answer_distribution || [0, 0, 0, 0]
                          const totalAns = currentQuestion.total_answers || 0
                          const count = dist[idx] || 0
                          const pct = totalAns > 0 ? (count / totalAns * 100) : 0
                          const correct = currentQuestion.correct_answer === key
                          const selected = selectedAnswer === key
                          const borderColor = correct ? 'var(--ctrl-success-border)' : selected ? 'var(--ctrl-error-border)' : 'var(--ctrl-radio-option-border)'
                          const bgColor = correct ? 'var(--ctrl-success-bg)' : selected ? 'var(--ctrl-error-bg)' : 'var(--aud-input-bg)'
                          const badgeBg = correct ? '#52c41a' : selected ? '#ff4d4f' : '#bfbfbf'
                          const badgeIcon = correct ? <CheckCircleOutlined /> : selected ? <CloseCircleOutlined /> : key
                          return (
                            <div key={key} style={{
                              border: `2px solid ${borderColor}`, borderRadius: 8,
                              padding: '12px 16px', background: bgColor,
                              opacity: (!correct && !selected) ? 0.55 : 1,
                              transition: 'all 0.3s ease',
                              color: 'var(--aud-text-primary)',
                            }}>
                              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 8 }}>
                                <span style={{
                                  width: 30, height: 30, borderRadius: '50%',
                                  background: badgeBg, color: '#fff',
                                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                                  fontSize: 14, fontWeight: 700, flexShrink: 0,
                                  marginTop: 4
                                }}>
                                  {badgeIcon}
                                </span>
                                <RichTextRenderer
                                  content={label || ''}
                                  isDark={theme === 'dark'}
                                  style={{ flex: 1, fontWeight: correct ? 600 : 400 }}
                                />
                                <span style={{ whiteSpace: 'nowrap', fontSize: 13, color: 'var(--aud-text-secondary)', marginTop: 4 }}>
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
                        message={t('audience.waitingForNextQuestion', { defaultValue: 'Waiting for next question...' })}
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
