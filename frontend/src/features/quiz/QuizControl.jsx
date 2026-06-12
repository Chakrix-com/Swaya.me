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
  Progress,
  Rate,
  message,
  Alert,
  Input,
  Table,
  Popconfirm,
  Modal,
  Divider,
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
  DesktopOutlined,
  FullscreenOutlined,
  ThunderboltOutlined,
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
  const [qrModalOpen, setQrModalOpen] = useState(false)
  const [lobbyParticipants, setLobbyParticipants] = useState([])

  useEffect(() => {
    if (id) {
      loadQuiz()
      loadLatestSession()
    }
  }, [id])

  useEffect(() => {
    if (session) {
      loadResults()
      const interval = setInterval(loadResults, 3000)
      return () => clearInterval(interval)
    }
  }, [session])

  useEffect(() => {
    if (!session) return
    // Poll participant names during lobby only
    const loadLobbyParticipants = async () => {
      try {
        const r = await sessionAPI.listParticipants(session.id)
        setLobbyParticipants(r.data.participants || [])
      } catch (_) {}
    }
    loadLobbyParticipants()
    const iv = setInterval(loadLobbyParticipants, 3000)
    return () => clearInterval(iv)
  }, [session])

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
          return { ...prev, ...openSession }
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
      if (['word_cloud', 'one_word'].includes(response.data.current_question?.question_type)) {
        loadWordCloudData(response.data.current_question.id)
      }
    } catch (error) {
      console.error(t('quiz.failedToLoadResults'), error)
    }
    if (latestResults?.quiz_type !== 'poll' && quiz?.quiz_type !== 'poll') {
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
      const words = Object.entries(response.data.word_frequencies).map(([word, count]) => ({
        text: word,
        value: count,
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
      navigate(`/quiz/${id}/recap/${session.id}`)
    } catch (error) {
      message.error(t('quiz.failedToEnd'))
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusTranslation = (status) => {
    if (!status) return t('quiz.ready')
    return t(`quiz.${status.toLowerCase()}`)
  }

  const getSessionStatusUi = (status) => {
    const normalized = typeof status === 'string' ? status.toLowerCase() : ''
    switch (normalized) {
      case 'active':
        return { label: t('quiz.active'), valueColor: '#52c41a', tagColor: 'green', tagLabel: t('quiz.live') }
      case 'created':
        return { label: t('quiz.started', { defaultValue: 'Started' }), valueColor: '#1677ff', tagColor: 'blue', tagLabel: t('quiz.started', { defaultValue: 'Started' }) }
      case 'ended':
        return { label: t('quiz.ended'), valueColor: '#fa8c16', tagColor: 'orange', tagLabel: t('quiz.ended') }
      case 'completed':
        return { label: t('quiz.completed'), valueColor: '#722ed1', tagColor: 'purple', tagLabel: t('quiz.completed') }
      default:
        return { label: getStatusTranslation(status), valueColor: '#595959', tagColor: 'default', tagLabel: getStatusTranslation(status) }
    }
  }

  const copyJoinLink = () => {
    const inputElement = document.getElementById('join-url-input')
    if (!inputElement || !inputElement.value) {
      message.error(t('quiz.noUrlToCopy'))
      return
    }
    const joinUrl = inputElement.value
    const textarea = document.createElement('textarea')
    textarea.value = joinUrl
    textarea.style.cssText = 'position:fixed;top:0;left:0;opacity:0'
    document.body.appendChild(textarea)
    try {
      textarea.focus()
      textarea.select()
      textarea.setSelectionRange(0, textarea.value.length)
      const successful = document.execCommand('copy')
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

  // ── Derived state ──────────────────────────────────────────────────────────
  const currentQuestion = results?.current_question
  const currentQuestionAnswerCount = Number(currentQuestion?.total_answers ?? 0)
  const visibleLeaderboard = (leaderboard && currentQuestionAnswerCount > 0)
    ? leaderboard
    : (leaderboard ? { ...leaderboard, entries: [] } : null)
  const isPoll = (results?.quiz_type || quiz?.quiz_type) === 'poll'
  const isWordCloudQuestion = ['word_cloud', 'one_word'].includes(currentQuestion?.question_type)
  const isTextQuestion = ['single_line', 'paragraph'].includes(currentQuestion?.question_type)
  const isOptionQuestion = currentQuestion && !isWordCloudQuestion && !isTextQuestion
  const effectiveSessionStatus = results?.status || session?.status
  const normalizedSessionStatus = typeof effectiveSessionStatus === 'string' ? effectiveSessionStatus.toLowerCase() : ''
  const isSessionActive = normalizedSessionStatus === 'active'
  const isSessionRunning = isSessionActive || normalizedSessionStatus === 'created'
  const isLobby = session && !isSessionActive && normalizedSessionStatus === 'created' && (!results || results.current_question_index === -1)
  const isComplete = session && results && !currentQuestion && results.current_question_index >= 0
  const sessionStatusUi = getSessionStatusUi(effectiveSessionStatus)
  const timedQuestionActive = Boolean(isSessionActive && currentQuestion?.max_time_seconds)
  const displayTimerRemaining = currentQuestion?.max_time_seconds
    ? (timerRemaining ?? Number(currentQuestion.max_time_seconds))
    : null
  const joinUrl = session ? `${window.location.origin}/join/${session.join_code}` : ''
  const isLastQuestion = results && quiz && results.current_question_index >= (quiz.questions?.length - 1)
  const canGoBack = results && results.current_question_index > 0
  const joinCode = session ? String(session.join_code).replace(/,/g, '') : ''
  const presentImmersiveTooltip = t('quiz.presentImmersiveTooltip', { defaultValue: 'Open immersive presenter mode in a new tab.' })
  const totalJoined = results?.total_participants || 0
  const answeredCount = currentQuestion?.total_answers || 0

  useEffect(() => {
    if (!currentQuestion?.max_time_seconds || !currentQuestion?.timer_started_at) {
      setTimerRemaining(null)
      return
    }
    const maxSeconds = Number(currentQuestion.max_time_seconds)
    const rawStartedAt = String(currentQuestion.timer_started_at)
    const startedAtIso = /Z$|[+-]\d{2}:\d{2}$/.test(rawStartedAt) ? rawStartedAt : `${rawStartedAt}Z`
    const startedAt = new Date(startedAtIso).getTime()
    if (!maxSeconds || Number.isNaN(startedAt)) { setTimerRemaining(null); return }
    const updateRemaining = () => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000)
      setTimerRemaining(Math.max(0, maxSeconds - elapsed))
    }
    updateRemaining()
    const interval = setInterval(updateRemaining, 1000)
    return () => clearInterval(interval)
  }, [currentQuestion?.id, currentQuestion?.max_time_seconds, currentQuestion?.timer_started_at])

  if (!quiz) {
    return <div style={{ padding: 24 }}>{t('common.loading')}</div>
  }

  // ── Reusable sub-renders ───────────────────────────────────────────────────

  const nextButton = (
    timedQuestionActive ? (
      <Popconfirm
        title={t('quiz.timerOverrideTitle', { defaultValue: 'Skip this timed question early?' })}
        description={t('quiz.timerOverrideDescription', { defaultValue: 'This question has an active timer. Continue only if you want to override it now.' })}
        onConfirm={handleAdvanceQuestion}
        okText={t('quiz.timerOverrideOk', { defaultValue: 'Yes, continue' })}
        cancelText={t('common.cancel')}
        placement="left"
      >
        <Button type="primary" block size="large" icon={isLastQuestion ? <CheckCircleOutlined /> : <ArrowRightOutlined />} loading={loading}>
          {isLastQuestion ? t('quiz.finish') : t('quiz.nextQuestion')} <kbd className="qc-kbd">{isLastQuestion ? '↵' : '→'}</kbd>
        </Button>
      </Popconfirm>
    ) : (
      <Button
        type="primary"
        block
        size="large"
        icon={isLastQuestion ? <CheckCircleOutlined /> : <ArrowRightOutlined />}
        onClick={handleAdvanceQuestion}
        loading={loading}
      >
        {isLastQuestion ? t('quiz.finish') : t('quiz.nextQuestion')} <kbd className="qc-kbd">{isLastQuestion ? '↵' : '→'}</kbd>
      </Button>
    )
  )

  const stopButton = (
    <Popconfirm
      title={t('quiz.stopQuizTitle')}
      description={
        timedQuestionActive
          ? t('quiz.timerEndOverrideDescription', { defaultValue: 'A timer is running. Ending now overrides it. Results are saved to History.' })
          : t('quiz.stopQuizSaved', { defaultValue: 'Results are saved to History.' })
      }
      onConfirm={handleEndSession}
      okText={t('quiz.stopQuizOk')}
      cancelText={t('common.cancel')}
      okButtonProps={{ danger: true }}
      placement="left"
    >
      <Button danger block icon={<CloseCircleOutlined />} loading={loading}>
        {t('quiz.stopQuiz')}
      </Button>
    </Popconfirm>
  )

  // ── Leaderboard table (rendered in stage pane) ─────────────────────────────
  const leaderboardCard = visibleLeaderboard && !isPoll && (
    <Card
      className="quiz-control-leaderboard-card"
      title={
        <Space wrap className="quiz-control-leaderboard-title">
          <TrophyOutlined style={{ color: '#faad14' }} />
          <span>{t('leaderboard.title')}</span>
          {visibleLeaderboard.total_participants > 0 && (
            <Tag color="blue">{visibleLeaderboard.total_participants} {t('quiz.participants')}</Tag>
          )}
          {visibleLeaderboard.mcq_question_count > 0 && <Tag color="default">{t('leaderboard.mcqOnly')}</Tag>}
        </Space>
      }
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
                  return <Tag color={colors[rank] ? undefined : 'default'} style={colors[rank] ? { backgroundColor: colors[rank], color: '#000', borderColor: colors[rank] } : {}}>{rank}</Tag>
                },
              },
              { title: t('leaderboard.participant'), dataIndex: 'display_name', ellipsis: true },
              {
                title: visibleLeaderboard.mcq_question_count > 1 ? `${t('leaderboard.score')} / ${visibleLeaderboard.mcq_question_count}` : t('leaderboard.score'),
                dataIndex: 'score',
                width: 100,
                render: (score) => <Tag color="green">{score}</Tag>,
              },
              {
                title: t('leaderboard.timeTaken'),
                dataIndex: 'time_taken_seconds',
                width: 90,
                render: (secs) => secs != null ? <Text type="secondary" style={{ fontSize: 12 }}>{secs.toFixed(1)}s</Text> : <Text type="secondary" style={{ fontSize: 12 }}>—</Text>,
              },
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
  )

  // ── Main render ────────────────────────────────────────────────────────────
  return (
    <div className="quiz-cockpit">

      {/* ════════════════ LEFT: STAGE PANE ════════════════ */}
      <div className="quiz-cockpit-stage">

        {/* Title row */}
        <div className="qc-stage-title">
          <Space>
            <Tag color={isPoll ? 'purple' : 'blue'} style={{ margin: 0 }}>
              {isPoll ? t('quiz.poll', { defaultValue: 'Poll' }) : t('quiz.quizTypeLabel', { defaultValue: 'Quiz' })}
            </Tag>
            <Title level={4} style={{ margin: 0 }}>{quiz.title}</Title>
          </Space>
          {quiz.description && <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 2 }}>{quiz.description}</Text>}
        </div>

        {/* Join bar — pinned & visible once session exists */}
        {session && (
          <div className="qc-join-bar">
            <div className="qc-join-code-block">
              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 2 }}>{t('quiz.joinCode')}</Text>
              <div className="qc-join-code">{joinCode}</div>
              <Text type="secondary" style={{ fontSize: 11 }}>swaya.me/join</Text>
            </div>
            <div className="qc-join-url-block">
              <Input id="join-url-input" value={joinUrl} readOnly size="small" style={{ marginBottom: 6 }} />
              <Button icon={<CopyOutlined />} onClick={copyJoinLink} size="small" block>
                {t('quiz.copyJoinLink')}
              </Button>
            </div>
            <div className="qc-join-qr" onClick={() => setQrModalOpen(true)} title={t('quizPresent.expandQr', { defaultValue: 'Click to enlarge QR code' })}>
              <QRCodeCanvas value={joinUrl} size={80} level="H" includeMargin />
              <span className="qc-qr-expand"><FullscreenOutlined /></span>
            </div>
          </div>
        )}

        {/* ── Stage content ── */}
        {!session ? (
          /* No session yet — start panel */
          <Card>
            <Space direction="vertical" align="center" style={{ width: '100%', padding: '24px 0' }}>
              <Title level={3}>{t('quiz.readyToStart')}</Title>
              <Text>{t('quiz.startSessionDesc')}</Text>
              <Button type="primary" size="large" icon={<PlayCircleOutlined />} onClick={handleStartSession} loading={loading}>
                {t('quiz.startSession')}
              </Button>
            </Space>
          </Card>

        ) : isLobby ? (
          /* Session created, lobby — participants joining */
          <Card className="qc-lobby-card">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                <Title level={4} style={{ margin: 0 }}>{t('quiz.readyToStartFirst')}</Title>
                <Tooltip title={presentImmersiveTooltip}>
                  <Button className="quiz-control-present-btn" icon={<DesktopOutlined />} onClick={handleOpenPresent} size="small">
                    {t('quiz.presentView')} <kbd className="qc-kbd">F5</kbd>
                  </Button>
                </Tooltip>
              </Space>
              <Text type="secondary">{t('quiz.clickAdvanceToStart')}</Text>
              {/* Lobby participant list */}
              {lobbyParticipants.length > 0 ? (
                <div className="qc-lobby-names">
                  {lobbyParticipants.map((p, idx) => (
                    <Tag key={idx} color="blue" className="qc-lobby-name-tag">
                      {p.name}
                    </Tag>
                  ))}
                </div>
              ) : (
                <Text type="secondary" style={{ fontSize: 13 }}>
                  {t('quiz.waitingForParticipants', { defaultValue: 'Waiting for participants to join…' })}
                </Text>
              )}
            </Space>
          </Card>

        ) : currentQuestion ? (
          /* Active question */
          <Card className="qc-question-card">
            <Space direction="vertical" style={{ width: '100%' }}>
              {/* Question meta */}
              <Space wrap>
                <Tag color="blue">{t('quiz.questionOf')} {results.current_question_index + 1} {t('quiz.of')} {quiz.questions?.length}</Tag>
                {currentQuestion.question_type === 'word_cloud' && <Tag color="purple">{t('quiz.wordCloud')}</Tag>}
                {currentQuestion.question_type === 'one_word' && <Tag color="volcano">{t('quiz.oneWord')}</Tag>}
                {currentQuestion.question_type === 'single_line' && <Tag color="geekblue">{t('quizPresent.singleLine', { defaultValue: 'Single Line' })}</Tag>}
                {currentQuestion.question_type === 'paragraph' && <Tag color="geekblue">{t('quizPresent.paragraph', { defaultValue: 'Paragraph' })}</Tag>}
                {currentQuestion.question_type === 'scale' && <Tag color="gold">{t('quizPresent.scaleOneToFive', { defaultValue: 'Scale (1-5)' })}</Tag>}
                {currentQuestion.max_time_seconds && <Tag color="orange">{t('quiz.timerTag', { seconds: currentQuestion.max_time_seconds })}</Tag>}
                <Tag color="green">{t('quiz.pointsTag', { points: currentQuestion.points || 1 })}</Tag>
              </Space>

              {currentQuestion.question_image_url && (
                <img src={currentQuestion.question_image_url} alt="" style={{ maxWidth: '100%', maxHeight: 240, borderRadius: 8, display: 'block' }} />
              )}

              <Text strong style={{ fontSize: 16 }}>{currentQuestion.text}</Text>

              <Alert message={`${answeredCount} ${t('quiz.responsesReceived')}`} type="info" showIcon />

              {/* Question body */}
              {isWordCloudQuestion ? (
                wordCloudData.length > 0 ? (
                  <div style={{ width: '100%', height: 280, border: '1px solid #d9d9d9', borderRadius: 8, padding: 16, background: '#fafafa' }}>
                    <ReactWordcloud
                      words={wordCloudData}
                      options={{ rotations: 2, rotationAngles: [0, 90], fontSizes: [20, 60], padding: 5, enableTooltip: true, deterministic: true, fontFamily: 'Arial', colors: ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96'] }}
                    />
                  </div>
                ) : (
                  <Alert message={t('quizPresent.noResponsesYet', { defaultValue: 'No responses yet' })} description={t('quizPresent.wordCloudWillAppear', { defaultValue: 'Word cloud will appear once participants start submitting answers.' })} type="warning" />
                )
              ) : isTextQuestion ? (
                (currentQuestion.text_responses || []).length > 0 ? (
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
                )
              ) : (
                /* MCQ / Scale */
                <Space direction="vertical" style={{ width: '100%' }}>
                  {currentQuestion.question_type === 'scale' ? (() => {
                    const dist = currentQuestion.answer_distribution || []
                    const totalAns = currentQuestion.total_answers || 0
                    let sum = 0
                    dist.forEach((count, idx) => { sum += count * (idx + 1) })
                    const avg = totalAns > 0 ? (sum / totalAns).toFixed(1) : 0
                    return (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px 0', gap: 12 }}>
                        <Text style={{ fontSize: 16 }}>Average: {totalAns} response{totalAns !== 1 ? 's' : ''}</Text>
                        <Space align="baseline">
                          <b style={{ fontSize: 48, color: '#faad14', lineHeight: 1 }}>{avg}</b>
                          <Text type="secondary" style={{ fontSize: 18 }}>/ 5</Text>
                        </Space>
                        <Rate disabled allowHalf value={Number(avg)} style={{ fontSize: 28, color: '#faad14' }} />
                      </div>
                    )
                  })() : (currentQuestion.options || []).map((opt, idx) => {
                    const total = currentQuestion.total_answers || 0
                    const count = currentQuestion.answer_distribution?.[idx] || 0
                    const pct = (count / total * 100) || 0
                    const letter = String.fromCharCode(65 + idx)
                    const isCorrect = currentQuestion.correct_answer === letter
                    return (
                      <div key={idx}>
                        <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 4, alignItems: 'flex-start' }}>
                          <Text strong>{isOptionQuestion && currentQuestion.question_type === 'mcq' ? `${letter}: ${opt}` : opt}</Text>
                          <Text type="secondary">{count} ({pct.toFixed(1)}%)</Text>
                        </Space>
                        <Progress percent={pct} strokeColor={isCorrect ? '#52c41a' : '#1890ff'} size="small" showInfo={false} />
                      </div>
                    )
                  })}
                  {!isPoll && (currentQuestion.question_type === 'mcq' || currentQuestion.question_type === 'scale') && currentQuestion.correct_answer && (
                    <Alert
                      message={`${t('quiz.correctAnswer')}: ${currentQuestion.correct_answer}`}
                      description={currentQuestion.question_type === 'mcq'
                        ? <span dangerouslySetInnerHTML={{ __html: currentQuestion[`option_${currentQuestion.correct_answer.toLowerCase()}`] || '' }} />
                        : ''}
                      type="success"
                      showIcon
                    />
                  )}
                </Space>
              )}
            </Space>
          </Card>

        ) : isComplete ? (
          /* All questions done, session still running */
          <Card>
            <Space direction="vertical" align="center" style={{ width: '100%', padding: '16px 0' }} size="large">
              <Title level={4}>{t('quiz.sessionComplete')}</Title>
              <Text>{t('quiz.allQuestionsAnswered')}</Text>
              <Card size="small" style={{ width: '100%', maxWidth: 560 }}>
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
                  <Button type="primary" onClick={handleSubmitFeedback} loading={feedbackSubmitting} disabled={feedbackSubmitted || !feedbackText.trim()}>
                    {feedbackSubmitted ? t('audience.feedbackSubmitted', { defaultValue: 'Feedback Submitted' }) : t('audience.submitFeedback', { defaultValue: 'Submit Feedback' })}
                  </Button>
                </Space>
              </Card>
            </Space>
          </Card>
        ) : null}

        {/* Leaderboard in stage pane */}
        {leaderboardCard}

      </div>{/* end stage */}

      {/* ════════════════ RIGHT: CONTROL RAIL ════════════════ */}
      <div className="quiz-cockpit-rail">

        {/* Status */}
        <div className="qc-rail-status">
          {isSessionActive && <div className="qc-live-badge">● LIVE</div>}
          <div style={{ color: sessionStatusUi.valueColor, fontWeight: 600 }}>{sessionStatusUi.label}</div>
          {session && <Tag color={sessionStatusUi.tagColor} style={{ marginTop: 4 }}>{sessionStatusUi.tagLabel}</Tag>}
        </div>

        {/* Timer */}
        {displayTimerRemaining !== null && (
          <div className="qc-rail-timer">
            <div className="qc-timer-value" style={{ color: displayTimerRemaining <= 5 ? '#f5222d' : displayTimerRemaining <= 10 ? '#fa8c16' : '#1677ff' }}>
              <ThunderboltOutlined /> {displayTimerRemaining}s
            </div>
            <Progress
              percent={Math.max(0, Math.min(100, (displayTimerRemaining / Number(currentQuestion.max_time_seconds)) * 100))}
              size="small"
              status={displayTimerRemaining <= 5 ? 'exception' : displayTimerRemaining <= 10 ? 'active' : 'normal'}
              showInfo={false}
            />
          </div>
        )}

        {/* Counts */}
        {session && (
          <div className="qc-rail-counts">
            <div className="qc-rail-stat">
              <span className="qc-rail-stat-value">{totalJoined}</span>
              <span className="qc-rail-stat-label"><TeamOutlined /> {t('quiz.participants')}</span>
            </div>
            {currentQuestion && (
              <div className="qc-rail-stat">
                <span className="qc-rail-stat-value" style={{ color: answeredCount >= totalJoined && totalJoined > 0 ? '#52c41a' : undefined }}>{answeredCount}</span>
                <span className="qc-rail-stat-label"><CheckCircleOutlined /> {t('quiz.responses')}</span>
              </div>
            )}
          </div>
        )}

        <Divider style={{ margin: '4px 0' }} />

        {/* Navigation controls */}
        {session && isLobby && (
          <Button type="primary" block size="large" icon={<MobileOutlined />} onClick={handleAdvanceQuestion} loading={loading}>
            {t('quiz.startFirstQuestion')} <kbd className="qc-kbd">Space</kbd>
          </Button>
        )}

        {session && isSessionActive && (
          <>
            <Button block icon={<LeftOutlined />} onClick={handleBackQuestion} loading={loading} disabled={!canGoBack}>
              {t('quiz.previousQuestion')} <kbd className="qc-kbd">←</kbd>
            </Button>
            {nextButton}
            {/* P1-3: answered/joined counter below Next */}
            {currentQuestion && (
              <div className="qc-answered-counter">
                {answeredCount} / {totalJoined} {t('quiz.responsesReceived', { defaultValue: 'answered' })}
              </div>
            )}
          </>
        )}

        {/* Leaderboard toggle */}
        {session && !isPoll && visibleLeaderboard && (
          <Button block icon={results?.leaderboard_visible ? <EyeOutlined /> : <EyeInvisibleOutlined />} onClick={handleToggleLeaderboard}>
            {results?.leaderboard_visible ? t('leaderboard.hideFromParticipants') : t('leaderboard.showToParticipants')}
          </Button>
        )}

        {/* Present F5 */}
        {session && (
          <Tooltip title={presentImmersiveTooltip}>
            <Button block className="quiz-control-present-btn" icon={<DesktopOutlined />} onClick={handleOpenPresent}>
              {t('quiz.presentView')} <kbd className="qc-kbd">F5</kbd>
            </Button>
          </Tooltip>
        )}

        {/* Stop — P1-7: fixed position, reassuring copy */}
        {session && isSessionRunning && (
          <>
            <Divider style={{ margin: '4px 0' }} />
            {stopButton}
          </>
        )}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Back to dashboard */}
        <Button type="link" icon={<LeftOutlined />} onClick={() => navigate('/dashboard')} style={{ padding: 0, textAlign: 'left' }}>
          {t('quiz.backDashboard')}
        </Button>
      </div>{/* end rail */}

      {/* QR enlarge modal */}
      <Modal
        open={qrModalOpen}
        onCancel={() => setQrModalOpen(false)}
        footer={null}
        centered
        title={t('quiz.joinInformation')}
        width={480}
      >
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <QRCodeCanvas value={joinUrl} size={380} level="H" includeMargin />
          <div style={{ marginTop: 12, fontSize: 14, color: '#666', wordBreak: 'break-all' }}>{joinUrl}</div>
        </div>
      </Modal>
    </div>
  )
}
