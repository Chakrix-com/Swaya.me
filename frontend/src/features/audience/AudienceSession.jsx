import { useState, useEffect, useRef, useContext, useCallback } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
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
import { trackEvent } from '../../services/metrics'
import useSessionChannel from '../../hooks/useSessionChannel'
import { useTranslation } from 'react-i18next'
import { clearSession } from '../../store/sessionSlice'
import PublicBrandHeader from '../../components/PublicBrandHeader'
import RichTextRenderer from '../quiz/components/RichTextRenderer'
import RichTextEditor from '../quiz/components/RichTextEditor'
import PromoCard from '../../components/PromoCard'
import { VisitorThemeContext } from '../../App'
import { applySkin } from '../../themes/skins'
import useWakeLock from '../../hooks/useWakeLock'

const { Title, Text } = Typography
const { TextArea } = Input

export default function AudienceSession() {
  const { message } = App.useApp()
  const location = useLocation()
  const navigate = useNavigate()
  const { sessionId: sessionIdParam } = useParams()
  const dispatch = useDispatch()
  const { t } = useTranslation()
  const { theme } = useContext(VisitorThemeContext)
  const reduxSession = useSelector((state) => state.session.session)

  // Rehydrate from sessionStorage so a page refresh reconnects automatically
  const storedSession = (() => {
    try { return JSON.parse(sessionStorage.getItem('swaya_participant_session') || 'null') } catch { return null }
  })()

  const locationState = location.state || {}
  // sessionId: URL param is authoritative on refresh; token comes from state/storage
  const sessionId = sessionIdParam || locationState.sessionId || reduxSession?.session_id || storedSession?.sessionId
  const sessionToken = locationState.sessionToken || reduxSession?.session_token || storedSession?.sessionToken
  const displayName = locationState.displayName || reduxSession?.display_name || storedSession?.displayName || 'Guest'

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
  const [rankDelta, setRankDelta] = useState(null)
  const prevRankRef = useRef(null)
  const lastQuestionIdRef = useRef(null)
  const pollingIntervalRef = useRef(null)
  const sseConnectedRef = useRef(false)
  const containerRef = useRef(null)

  // Keep screen awake while the session is live
  useWakeLock(!!sessionToken && sessionStatus !== 'ended')

  // Persist session to sessionStorage so page refresh reconnects automatically
  useEffect(() => {
    if (sessionToken && sessionId) {
      sessionStorage.setItem('swaya_participant_session', JSON.stringify({ sessionToken, sessionId, displayName }))
    }
  }, [sessionToken, sessionId, displayName])

  // Analytics beacon: participant_join (first time) or participant_rejoin (page refresh)
  const beaconFiredRef = useRef(false)
  useEffect(() => {
    if (sessionToken && sessionId && !beaconFiredRef.current) {
      beaconFiredRef.current = true
      const isRejoin = !!storedSession
      trackEvent(isRejoin ? 'participant_rejoin' : 'participant_join', { sessionId: Number(sessionId) })
    }
  }, [sessionToken, sessionId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Restart the polling interval at the given ms rate
  const resetPollInterval = useCallback((ms) => {
    if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current)
    pollingIntervalRef.current = setInterval(loadResults, ms)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // SSE event handler — fires on every server push
  const handleSseEvent = useCallback((event) => {
    if (event.type === 'sse_unavailable') {
      if (sseConnectedRef.current) {
        sseConnectedRef.current = false
        resetPollInterval(2000)  // SSE lost — back to fast polling
      }
      return
    }
    // First successful SSE frame: slow the safety-net poll to 5 s
    if (!sseConnectedRef.current) {
      sseConnectedRef.current = true
      resetPollInterval(5000)
    }
    // Trigger an immediate fetch so the UI reflects the push right away
    loadResults()
  }, [resetPollInterval]) // eslint-disable-line react-hooks/exhaustive-deps

  useSessionChannel(sessionId, sessionToken, handleSseEvent)

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
          trackEvent('participant_session_end', { sessionId: Number(sessionId) })
          sessionStorage.removeItem('swaya_participant_session')
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

      if (['word_cloud', 'one_word'].includes(response.data.current_question?.question_type)) {
        loadWordCloudData(response.data.current_question.question_id)
      }
    } catch (error) {
      if (error.response?.status === 403) {
        setSessionInvalidated(true)
        sessionStorage.removeItem('swaya_participant_session')
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
      if (detail) message.error(detail)
      // Always transition to submitted state for non-word-cloud types —
      // an error usually means "already answered", so the answer was recorded.
      if (!isWordCloud) setSubmitted(true)
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
      sessionStorage.removeItem('swaya_participant_session')
      message.info(t('audience.leftSession', { defaultValue: 'You left the session' }))
      navigate('/join')
    }
  }

  // Track rank delta for "▲/▼ N places" display
  useEffect(() => {
    const currentRank = leaderboard?.current_participant_rank
    if (!currentRank) { prevRankRef.current = null; return }
    if (prevRankRef.current !== null && prevRankRef.current !== currentRank) {
      setRankDelta(prevRankRef.current - currentRank) // positive = moved up
    } else {
      setRankDelta(null)
    }
    prevRankRef.current = currentRank
  }, [leaderboard?.current_participant_rank])

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
    const entries = visibleLeaderboard.entries || []
    const top10 = entries.slice(0, 10)
    const youEntry = entries.find(e => e.is_current_participant)
    const youInTop10 = top10.some(e => e.is_current_participant)
    const top3 = entries.slice(0, 3)
    const podiumOrder = top3.length >= 2 ? [top3[1], top3[0], top3[2]].filter(Boolean) : []
    const podiumColors = { 1: '#FFD700', 2: '#C0C0C0', 3: '#CD7F32' }
    const podiumHeights = { 1: 80, 2: 56, 3: 44 }

    return (
      <Card
        size="small"
        title={
          <Space wrap>
            <TrophyOutlined style={{ color: '#faad14' }} />
            <span>{t('leaderboard.title')}</span>
            {visibleLeaderboard.current_participant_rank && (
              <Tag color="blue">
                {t('leaderboard.yourRank', { rank: visibleLeaderboard.current_participant_rank })}
              </Tag>
            )}
            {rankDelta !== null && rankDelta !== 0 && (
              <Tag color={rankDelta > 0 ? 'green' : 'red'} style={{ fontWeight: 700 }}>
                {rankDelta > 0 ? `▲ ${rankDelta}` : `▼ ${Math.abs(rankDelta)}`} {t('leaderboard.places', { defaultValue: 'places' })}
              </Tag>
            )}
          </Space>
        }
        style={{ marginTop: 16 }}
      >
        {entries.length === 0 ? (
          <Text type="secondary">{t('leaderboard.noData')}</Text>
        ) : (
          <>
            {/* Podium for top 3 */}
            {podiumOrder.length >= 2 && (
              <div className="aud-podium">
                {podiumOrder.map((entry) => (
                  <div key={entry.participant_id} className="aud-podium-slot">
                    <div className="aud-podium-name" style={{ fontWeight: entry.is_current_participant ? 700 : 400, color: entry.is_current_participant ? '#1890ff' : undefined }}>
                      {entry.display_name}{entry.is_current_participant ? ` (${t('audience.you', { defaultValue: 'You' })})` : ''}
                    </div>
                    <div className="aud-podium-score">{entry.score}</div>
                    <div className="aud-podium-block" style={{ height: podiumHeights[entry.rank] || 40, background: podiumColors[entry.rank] || '#d9d9d9' }}>
                      #{entry.rank}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {/* Full table (beyond podium) */}
            {entries.length > 3 && (
              <div className="table-responsive" style={{ marginTop: podiumOrder.length >= 2 ? 12 : 0 }}>
                <Table
                  dataSource={top10}
                  rowKey="participant_id"
                  columns={leaderboardColumns}
                  pagination={false}
                  size="small"
                  scroll={{ x: 420 }}
                  rowClassName={(record) => record.is_current_participant ? 'leaderboard-you-row' : ''}
                />
              </div>
            )}
            {/* Pinned "you" row if outside top 10 */}
            {youEntry && !youInTop10 && (
              <div style={{ marginTop: 8, paddingTop: 8, borderTop: '2px dashed #1890ff' }}>
                <Table
                  dataSource={[youEntry]}
                  rowKey="participant_id"
                  columns={leaderboardColumns}
                  pagination={false}
                  size="small"
                  showHeader={false}
                  rowClassName={() => 'leaderboard-you-row'}
                />
              </div>
            )}
            {entries.length > 10 && (
              <div style={{ textAlign: 'center', marginTop: 8, color: 'var(--aud-text-secondary)', fontSize: 12 }}>
                {t('audience.moreParticipants', { count: entries.length - 10, defaultValue: `+${entries.length - 10} more participants` })}
              </div>
            )}
          </>
        )}
      </Card>
    )
  }

  const isWordCloud = currentQuestion?.question_type === 'word_cloud'
  const isOneWord = currentQuestion?.question_type === 'one_word'
  const isScaleQuestion = currentQuestion?.question_type === 'scale'
  const isTextQuestion = ['word_cloud', 'one_word', 'single_line', 'paragraph'].includes(currentQuestion?.question_type)
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

  useEffect(() => {
    applySkin(results?.skin, containerRef.current)
    return () => applySkin(null, containerRef.current)
  }, [results?.skin])


  return (
    <div ref={containerRef} className="audience-session min-vh-100 d-flex flex-column" style={{ position: 'relative', overflowX: 'hidden' }}>
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
            {sessionToken && !sessionInvalidated && sessionStatus === 'ended' && (
              <Space direction="vertical" style={{ width: '100%' }} size="middle">
                {/* Personal summary card */}
                <Card>
                  <Space direction="vertical" align="center" style={{ width: '100%', padding: '12px 0' }} size="large">
                    <div style={{ fontSize: 52 }}>{isPoll ? '📊' : '🏁'}</div>
                    <Title level={3} style={{ margin: 0 }}>{t('audience.quizCompleted', { defaultValue: 'Quiz Completed!' })}</Title>
                    {results?.quiz_title && <Text type="secondary" style={{ fontSize: 16 }}>{results.quiz_title}</Text>}

                    {!isPoll && (
                      <Space size="large" wrap style={{ justifyContent: 'center' }}>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: 32, fontWeight: 800, color: '#1677ff' }}>
                            {results?.participant_score ?? 0}
                          </div>
                          <Text type="secondary" style={{ fontSize: 12 }}>{t('leaderboard.pts', { defaultValue: 'pts' })}</Text>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: 32, fontWeight: 800, color: '#52c41a' }}>
                            {results?.participant_correct ?? 0}/{results?.total_questions ?? 0}
                          </div>
                          <Text type="secondary" style={{ fontSize: 12 }}>{t('audience.correct', { defaultValue: 'correct' })}</Text>
                        </div>
                        {leaderboard?.current_participant_rank && (
                          <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: 32, fontWeight: 800, color: '#faad14' }}>
                              #{leaderboard.current_participant_rank}
                            </div>
                            <Text type="secondary" style={{ fontSize: 12 }}>{t('audience.yourRank', { defaultValue: 'your rank' })}</Text>
                          </div>
                        )}
                      </Space>
                    )}

                    <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                      {displayName}
                    </Tag>

                    <Text type="secondary">{t('quizPresent.thanksForParticipating', { defaultValue: 'Thanks for participating.' })}</Text>

                    {/* Conversion CTA */}
                    <Button type="primary" size="large" onClick={() => navigate('/join')}>
                      {t('audience.joinAnotherQuiz', { defaultValue: 'Join another quiz' })}
                    </Button>
                  </Space>
                </Card>

                {/* Leaderboard */}
                <LeaderboardTable />

                {/* Feedback */}
                <Card size="small">
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

                <PromoCard />
              </Space>
            )}

            {/* ── Waiting for host / next question ── */}
            {sessionToken && !sessionInvalidated && !currentQuestion && sessionStatus !== 'ended' && sessionStatus !== null && (
              <Card>
                {sessionStatus === 'created' ? (
                  /* Lobby: "You're in!" moment */
                  <Space direction="vertical" align="center" style={{ width: '100%', padding: '8px 0' }} size="middle">
                    <div style={{ fontSize: 52 }}>✅</div>
                    <Title level={3} style={{ margin: 0 }}>
                      {t('audience.youreIn', { defaultValue: "You're in!" })}
                    </Title>
                    {results?.quiz_title && (
                      <Text strong style={{ fontSize: 16, textAlign: 'center' }}>{results.quiz_title}</Text>
                    )}
                    <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                      {displayName}
                    </Tag>
                    {results?.total_participants > 0 && (
                      <Text type="secondary">
                        {t('audience.othersHere', { count: results.total_participants - 1, defaultValue: `${results.total_participants - 1} others here` })}
                      </Text>
                    )}
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      {t('audience.quizWillStartSoon', { defaultValue: 'The quiz will start soon…' })}
                    </Text>
                  </Space>
                ) : (
                  /* Between questions */
                  <Space direction="vertical" align="center" style={{ width: '100%' }}>
                    <LoadingOutlined style={{ fontSize: 48 }} />
                    <Title level={3}>
                      {t('audience.waitingForNextQuestion', { defaultValue: 'Waiting for next question...' })}
                    </Title>
                    <Text type="secondary">
                      {t('audience.hostPreparingNextQuestion', { defaultValue: 'Host is preparing the next question' })}
                    </Text>
                    <Tag color="blue" style={{ maxWidth: '100%', whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      {t('audience.joinedAs', { defaultValue: 'Joined as' })}: {displayName}
                    </Tag>
                  </Space>
                )}
              </Card>
              )}

            {/* ── Active question ── */}
            {sessionToken && !sessionInvalidated && currentQuestion && sessionStatus !== 'ended' && (
              <>
                <Card style={{ marginBottom: 16 }}>
                  <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Tag color="blue">{t('quiz.question')} {results.current_question_index + 1}</Tag>
                    {isWordCloud && <Tag color="purple">{t('quiz.wordCloud')}</Tag>}
                    {isOneWord && <Tag color="volcano">{t('quiz.oneWord')}</Tag>}
                    {currentQuestion.question_type === 'single_line' && <Tag color="geekblue">{t('quizPresent.singleLine', { defaultValue: 'Single Line' })}</Tag>}
                    {currentQuestion.question_type === 'paragraph' && <Tag color="geekblue">{t('quizPresent.paragraph', { defaultValue: 'Paragraph' })}</Tag>}
                    {isScaleQuestion && <Tag color="gold">{t('quizPresent.scaleOneToFive', { defaultValue: 'Scale 1-5' })}</Tag>}
                    {currentQuestion.max_time_seconds ? <Tag color="orange">{t('quiz.timerTag', { seconds: currentQuestion.max_time_seconds })}</Tag> : null}
                    <Text strong style={{ wordBreak: 'break-word' }}>{displayName}</Text>
                  </Space>
                  {currentQuestion.max_time_seconds ? (
                    <Space direction="vertical" style={{ width: '100%', marginTop: 8 }} size={4}>
                        <Text
                          type="secondary"
                          aria-live={Number(displayTimerRemaining) <= 5 ? 'assertive' : 'off'}
                          aria-label={t('quiz.timeLeft', { seconds: displayTimerRemaining })}
                        >{t('quiz.timeLeft', { seconds: displayTimerRemaining })}</Text>
                        <Progress
                          percent={Math.max(0, Math.min(100, (Number(displayTimerRemaining) / Number(currentQuestion.max_time_seconds)) * 100))}
                          size="small"
                          status={Number(displayTimerRemaining) <= 5 ? 'exception' : Number(displayTimerRemaining) <= 10 ? 'active' : 'normal'}
                          showInfo={false}
                          aria-hidden="true"
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
                    !submitted ? (
                      // ── Text answer entry ──
                      <>
                        {isOneWord ? (
                          <Input
                            placeholder={t('audience.enterOneWord', { defaultValue: 'Enter one word' })}
                            maxLength={30}
                            value={wordCloudAnswer}
                            onChange={(e) => setWordCloudAnswer(e.target.value.replace(/\s/g, ''))}
                            style={{ marginBottom: 16, fontSize: 18, textAlign: 'center' }}
                            size="large"
                            showCount
                          />
                        ) : (
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
                        )}
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
                        {/* Word cloud live preview — visible before/after submission for word_cloud type */}
                        {(isWordCloud || isOneWord) && wordCloudData.length > 0 && (
                          <>
                            <Alert
                              message={t('audience.liveWordCloud', { defaultValue: 'Live Word Cloud' })}
                              description={t('audience.responsesSubmittedCount', { count: wordCloudData.reduce((s, w) => s + w.value, 0) })}
                              type="info"
                              showIcon
                              style={{ marginBottom: 16 }}
                            />
                            <div style={{ width: '100%', height: 300, border: '1px solid #d9d9d9', borderRadius: 8, padding: 16, backgroundColor: '#fafafa' }}>
                              <ReactWordcloud
                                words={wordCloudData}
                                options={{ rotations: 2, rotationAngles: [0, 90], fontSizes: [16, 60], padding: 4, enableTooltip: true, deterministic: true, fontFamily: 'Arial', colors: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96'] }}
                              />
                            </div>
                          </>
                        )}
                        {(isWordCloud || isOneWord) && wordCloudData.length === 0 && (
                          <Alert
                            message={t('audience.beFirstToRespond', { defaultValue: 'Be the first to respond!' })}
                            description={t('audience.wordCloudGrow', { defaultValue: 'Submit your answer and watch the word cloud grow.' })}
                            type="info"
                            showIcon
                          />
                        )}
                      </>
                    ) : (
                      // ── Text answer submitted (reveal state) ──
                      <>
                        <Space direction="vertical" align="center" style={{ width: '100%', padding: '16px 0' }} size="middle">
                          <div style={{ fontSize: 36 }}>✅</div>
                          <Title level={4} style={{ margin: 0 }}>{t('audience.responseRecorded', { defaultValue: 'Response recorded' })}</Title>
                          {wordCloudAnswer && (
                            <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px', maxWidth: '100%', wordBreak: 'break-word', whiteSpace: 'normal' }}>
                              {t('audience.yourAnswer', { defaultValue: 'Your answer' })}: {wordCloudAnswer}
                            </Tag>
                          )}
                          {!(isWordCloud || isOneWord) && (
                            <Text type="secondary">{t('audience.waitingHostNext', { defaultValue: 'Waiting for the host to move to the next question.' })}</Text>
                          )}
                        </Space>
                        {(isWordCloud || isOneWord) && wordCloudData.length > 0 && (
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
                                words={wordCloudData.map(w => ({
                                  ...w,
                                  // Highlight the word the participant submitted
                                  color: w.text.toLowerCase() === wordCloudAnswer.toLowerCase() ? '#f5222d' : undefined,
                                }))}
                                options={{
                                  rotations: 2, rotationAngles: [0, 90],
                                  fontSizes: [16, 60], padding: 4,
                                  enableTooltip: true, deterministic: true, fontFamily: 'Arial',
                                  colors: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96']
                                }}
                              />
                            </div>
                          </>
                        )}
                      </>
                    )
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
                        <div
                          role="radiogroup"
                          aria-label={t('audience.chooseAnswer', { defaultValue: 'Choose your answer' })}
                          style={{ display: 'flex', flexDirection: 'column', gap: 12, width: '100%' }}
                        >
                          {['A', 'B', 'C', 'D'].map((key) => {
                          const label = currentQuestion[`option_${key.toLowerCase()}`]
                          const isSelected = selectedAnswer === key
                          return (
                            <div
                              key={key}
                              role="radio"
                              aria-checked={isSelected}
                              aria-label={`${key}: ${label || ''}`}
                              tabIndex={0}
                              onClick={() => setSelectedAnswer(key)}
                              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedAnswer(key) } }}
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
                                outline: isSelected ? '2px solid var(--ctrl-radio-selected-border)' : undefined,
                                outlineOffset: 2,
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
                  ) : submitted && !currentQuestion.correct_answer && !isPoll && !isScaleQuestion ? (
                    /* P0-2: answer submitted but correct answer not yet revealed — show locked-in state */
                    <Space direction="vertical" align="center" style={{ width: '100%', padding: '24px 0' }} size="large">
                      <div style={{ fontSize: 48 }}>⚡</div>
                      <Title level={4} style={{ margin: 0 }}>{t('audience.lockedIn', { defaultValue: 'Locked in!' })}</Title>
                      <Text type="secondary">{t('audience.waitingForReveal', { defaultValue: 'Waiting for the host to reveal the answer…' })}</Text>
                      {selectedAnswer && (
                        <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                          {t('audience.yourAnswer', { defaultValue: 'Your answer' })}: {selectedAnswer}
                        </Tag>
                      )}
                    </Space>
                  ) : (
                    <>
                      <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        {isScaleQuestion ? (() => {
                          const dist = currentQuestion.answer_distribution || []
                          const totalAns = currentQuestion.total_answers || 0
                          let sum = 0
                          dist.forEach((count, idx) => { sum += count * (idx + 1) })
                          const avg = totalAns > 0 ? (sum / totalAns).toFixed(1) : 0
                          const yourRating = selectedAnswer != null ? Number(selectedAnswer) + 1 : null
                          return (
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px 0', gap: 16 }}>
                               {yourRating != null && (
                                 <Space>
                                   <Text type="secondary">{t('audience.yourRating', { defaultValue: 'Your rating:' })}</Text>
                                   <Rate disabled value={yourRating} style={{ fontSize: 22, color: '#faad14' }} />
                                 </Space>
                               )}
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
                      {/* +N pts feedback after reveal */}
                      {selectedAnswer && currentQuestion.correct_answer && !isPoll && (
                        <div className="aud-pts-reveal" aria-live="polite" aria-atomic="true">
                          {selectedAnswer === currentQuestion.correct_answer ? (
                            <div className="aud-pts-correct">
                              +{currentQuestion.points || 1} {t('leaderboard.pts', { defaultValue: 'pts' })}
                            </div>
                          ) : (
                            <div className="aud-pts-none">
                              {t('audience.noPoints', { defaultValue: 'No points this round' })}
                            </div>
                          )}
                        </div>
                      )}
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
