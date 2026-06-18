import { useState, useEffect, useRef, useContext, useCallback } from 'react'
import EmojiReactionBar from './EmojiReactionBar'
import VideoEmbed from '../quiz/components/VideoEmbed'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useSelector } from 'react-redux'
import { useDispatch } from 'react-redux'
import {
  App,
  Input,
  Rate,
} from 'antd'
import ReactWordcloud from 'react-wordcloud'
import { sessionAPI, questionAPI } from '../../services/api'
import { trackEvent } from '../../services/metrics'
import useSessionChannel from '../../hooks/useSessionChannel'
import { useTranslation } from 'react-i18next'
import { clearSession } from '../../store/sessionSlice'
import PublicBrandHeader from '../../components/PublicBrandHeader'
import RichTextRenderer from '../quiz/components/RichTextRenderer'
import { VisitorThemeContext } from '../../App'
import { applySkin } from '../../themes/skins'
import useWakeLock from '../../hooks/useWakeLock'
import './AudienceSession.css'

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
  const [endedEarly, setEndedEarly] = useState(false)
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
          // Detect if host ended mid-session (not all questions were presented)
          const totalQ = response.data.total_questions ?? 0
          const lastIdx = response.data.current_question_index ?? -1
          const wasEarly = sessionStatus === 'active' && totalQ > 0 && lastIdx < totalQ - 1
          if (wasEarly) {
            setEndedEarly(true)
            message.warning(t('audience.quizEndedByHost', { defaultValue: 'The host has ended the quiz.' }), 5)
          } else {
            message.success(t('audience.quizEndedThanks', { defaultValue: 'Quiz has ended! Thank you for participating!' }))
          }
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

  // Tap-to-submit for MCQ / poll (no separate Submit button)
  const handleSelectAndSubmit = async (key) => {
    if (submitted || loading) return
    setSelectedAnswer(key)
    navigator.vibrate?.(50)
    setLoading(true)
    try {
      await sessionAPI.submitAnswer(sessionToken, {
        question_id: currentQuestion.question_id,
        selected_option_index: key.charCodeAt(0) - 65,
      })
      setSubmitted(true)
    } catch (err) {
      const detail = err.response?.data?.detail
      if (detail) message.error(detail)
      setSubmitted(true)
    } finally {
      setLoading(false)
    }
  }

  // Tap-to-submit for star rating
  const handleStarAndSubmit = async (val) => {
    if (submitted || loading || val === 0) return
    setSelectedAnswer(String(val - 1))
    setLoading(true)
    try {
      await sessionAPI.submitAnswer(sessionToken, {
        question_id: currentQuestion.question_id,
        selected_option_index: val - 1,
      })
      setSubmitted(true)
    } catch (err) {
      const detail = err.response?.data?.detail
      if (detail) message.error(detail)
      setSubmitted(true)
    } finally {
      setLoading(false)
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
  const quizType = results?.quiz_type
  const isGameShow = quizType === 'quiz' || quizType === 'poll'
  const currentQuestionAnswerCount = Number(results?.current_question?.total_answers ?? 0)
  // Show full leaderboard: when session is ended, between questions (no active question),
  // or when the current question already has answers. Clear entries only while a fresh
  // question is active and nobody has answered yet (avoid spoiling standings mid-question).
  const visibleLeaderboard = (leaderboard && (sessionStatus === 'ended' || !currentQuestion || currentQuestionAnswerCount > 0))
    ? leaderboard
    : (leaderboard ? { ...leaderboard, entries: [] } : null)
  const LeaderboardTable = ({ withBars = false }) => {
    if (isPollSession || !visibleLeaderboard || results?.leaderboard_visible === false) return null
    const entries = visibleLeaderboard.entries || []
    const top10 = entries.slice(0, 10)
    const youEntry = entries.find(e => e.is_current_participant)
    const youInTop10 = top10.some(e => e.is_current_participant)
    const maxScore = entries[0]?.score || 1
    const medals = ['🥇', '🥈', '🥉']

    if (entries.length === 0) {
      return <p className="aud2-subtext aud2-subtext--centered">{t('leaderboard.noData')}</p>
    }

    const renderRow = (entry) => {
      const isYou = entry.is_current_participant
      const medal = entry.rank <= 3 ? medals[entry.rank - 1] : null
      const barPct = withBars ? Math.min(100, (entry.score / maxScore) * 100) : null
      return (
        <div key={entry.participant_id} className={`aud2-lb-row${isYou ? ' aud2-lb-row--you' : ''}`}>
          <span className="aud2-lb-rank">{medal || `${entry.rank}.`}</span>
          <span className="aud2-lb-name">
            {entry.display_name}{isYou ? ` (${t('audience.you', { defaultValue: 'You' })})` : ''}
          </span>
          <span className="aud2-lb-score">{entry.score}</span>
          {withBars && (
            <div className="aud2-lb-bar-track">
              <div className="aud2-lb-bar-fill" style={{ width: `${barPct}%` }} />
            </div>
          )}
        </div>
      )
    }

    return (
      <div className="aud2-lb-wrap">
        <p className="aud2-lb-title">
          🏆 {t('leaderboard.title')}
          {visibleLeaderboard.current_participant_rank
            ? ` — ${t('leaderboard.yourRank', { rank: visibleLeaderboard.current_participant_rank })}`
            : null}
          {rankDelta !== null && rankDelta !== 0 && (
            <span className={`aud2-rank-delta aud2-rank-delta--${rankDelta > 0 ? 'up' : 'down'}`}>
              {' '}{rankDelta > 0 ? `↑${rankDelta}` : `↓${Math.abs(rankDelta)}`}
            </span>
          )}
        </p>
        <div className="aud2-lb-list">
          {top10.map(renderRow)}
          {youEntry && !youInTop10 && (
            <>
              <div className="aud2-lb-divider" />
              {renderRow(youEntry)}
            </>
          )}
        </div>
        {entries.length > 10 && (
          <p className="aud2-subtext aud2-subtext--centered" style={{ fontSize: 11, marginTop: 4 }}>
            {t('audience.moreParticipants', { count: entries.length - 10, defaultValue: `+${entries.length - 10} more participants` })}
          </p>
        )}
      </div>
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
    <div ref={containerRef} className={`aud2-page audience-session${isGameShow ? ' aud2-page--gameshow' : ''}${quizType ? ` aud2-page--${quizType}` : ''}`}>
      <PublicBrandHeader />
      {sessionStatus === 'ended' && (
        <a href="https://www.swaya.me" target="_blank" rel="noopener noreferrer" className="aud2-promo-bar">
          <span className="aud2-promo-bar__star">✦</span>
          <span>{t('promo.tagline')}</span>
          <span className="aud2-promo-bar__arrow">→</span>
        </a>
      )}
      <div className="aud2-body">
            {/* S0 — no session token */}
            {!sessionToken && (
              <div className="aud2-screen aud2-screen--center">
                <div className="aud2-center-panel">
                  <span className="aud2-hero-icon">🔒</span>
                  <h2 className="aud2-heading">{t('audience.noSessionFound', { defaultValue: 'No Session Found' })}</h2>
                  <p className="aud2-subtext">{t('audience.pleaseJoinFirst', { defaultValue: 'Please join a session first' })}</p>
                  <button className="aud2-cta-btn" onClick={() => navigate('/join')}>
                    {t('audience.goToJoinPage', { defaultValue: 'Go to Join Page' })}
                  </button>
                </div>
              </div>
            )}

            {/* S7 — session invalidated */}
            {sessionToken && sessionInvalidated && (
              <div className="aud2-screen aud2-screen--center">
                <div className="aud2-center-panel">
                  <span className="aud2-hero-icon">⚠️</span>
                  <h2 className="aud2-heading">{t('audience.sessionRestartedTitle', { defaultValue: 'Session Restarted' })}</h2>
                  <p className="aud2-subtext">{t('audience.sessionRestartedSubtitle', { defaultValue: 'The host has started a new quiz session' })}</p>
                  <button className="aud2-cta-btn" onClick={() => navigate('/join')}>
                    {t('audience.rejoinQuiz', { defaultValue: 'Rejoin Quiz' })}
                  </button>
                </div>
              </div>
            )}

            {/* S6 — quiz ended */}
            {sessionToken && !sessionInvalidated && sessionStatus === 'ended' && (
              <div className="aud2-screen aud2-screen--scroll">
                <div className="aud2-ended-panel">
                  <div className="aud2-ended-hero">
                    <span className="aud2-hero-icon">{isPoll ? '📊' : endedEarly ? '⏹️' : '🏁'}</span>
                    <h2 className="aud2-heading">
                      {endedEarly
                        ? t('audience.quizEndedByHostTitle', { defaultValue: 'Quiz ended by host' })
                        : t('audience.quizCompleted', { defaultValue: 'Quiz Completed!' })}
                    </h2>
                    {results?.quiz_title && <p className="aud2-quiz-title">{results.quiz_title}</p>}
                    {endedEarly && (
                      <p className="aud2-subtext aud2-subtext--warn">
                        {t('audience.quizEndedEarlyNote', { defaultValue: 'The host ended this session early. Your score reflects questions answered so far.' })}
                      </p>
                    )}
                  </div>

                  {!isPoll && (
                    <div className="aud2-stats-row">
                      <div className="aud2-stat">
                        <div className="aud2-stat-num">{results?.participant_score ?? 0}</div>
                        <div className="aud2-stat-label">{t('leaderboard.pts', { defaultValue: 'pts' })}</div>
                      </div>
                      <div className="aud2-stat">
                        <div className="aud2-stat-num">{results?.participant_correct ?? 0}/{results?.total_questions ?? 0}</div>
                        <div className="aud2-stat-label">{t('audience.correct', { defaultValue: 'correct' })}</div>
                      </div>
                      {leaderboard?.current_participant_rank && (
                        <div className="aud2-stat">
                          <div className="aud2-stat-num">#{leaderboard.current_participant_rank}</div>
                          <div className="aud2-stat-label">{t('audience.yourRank', { defaultValue: 'your rank' })}</div>
                        </div>
                      )}
                    </div>
                  )}

                  <span className="aud2-name-tag">{displayName}</span>

                  {results?.reaction_style && (
                    <EmojiReactionBar reactionStyle={results.reaction_style} sessionToken={sessionToken} />
                  )}

                  <LeaderboardTable withBars />

                  <button className="aud2-cta-btn" onClick={() => navigate('/join')}>
                    {t('audience.joinAnotherQuiz', { defaultValue: 'Join another quiz' })}
                  </button>
                </div>
              </div>
            )}

            {/* S1 — lobby */}
            {sessionToken && !sessionInvalidated && !currentQuestion && sessionStatus === 'created' && (
              <div className="aud2-screen aud2-screen--center">
                <button className="aud2-leave-float" onClick={handleLeaveSession}>
                  {t('audience.leaveSession', { defaultValue: 'Leave Session' })}
                </button>
                <div className="aud2-center-panel">
                  {isGameShow && (
                    <span className="aud2-gs-hero-emoji">{quizType === 'quiz' ? '🎯' : '📊'}</span>
                  )}
                  <div className="aud2-pulse-dots"><span /><span /><span /></div>
                  {results?.quiz_title && <h2 className="aud2-quiz-title">{results.quiz_title}</h2>}
                  <p className="aud2-greeting">Hi, {displayName} 👋</p>
                  {results?.total_participants > 0 && (
                    <p className="aud2-participant-count">
                      {t('audience.othersHere', { count: results.total_participants - 1, defaultValue: `${results.total_participants - 1} others here` })}
                    </p>
                  )}
                  <p className="aud2-subtext">
                    {isGameShow
                      ? t('audience.getReady', { defaultValue: 'Get ready!' })
                      : t('audience.quizWillStartSoon', { defaultValue: 'The quiz will start soon…' })}
                  </p>
                </div>
              </div>
            )}

            {/* S2 — between questions */}
            {sessionToken && !sessionInvalidated && !currentQuestion && sessionStatus !== 'ended' && sessionStatus !== null && sessionStatus !== 'created' && (
              <div className="aud2-screen">
                <div className="aud2-between-header">
                  <span className="aud2-q-counter">
                    {results?.total_questions ? `${(results.current_question_index || 0) + 1} / ${results.total_questions}` : ''}
                  </span>
                  {leaderboard?.current_participant_rank && (
                    <span className="aud2-rank-badge">
                      #{leaderboard.current_participant_rank}
                      {rankDelta > 0 && <span className="aud2-rank-delta aud2-rank-delta--up"> ↑{rankDelta}</span>}
                      {rankDelta < 0 && <span className="aud2-rank-delta aud2-rank-delta--down"> ↓{Math.abs(rankDelta)}</span>}
                    </span>
                  )}
                </div>
                <div className="aud2-between-loading">
                  <div className="aud2-pulse-dots"><span /><span /><span /></div>
                  <p className="aud2-subtext">{t('audience.hostPreparingNextQuestion', { defaultValue: 'Host is preparing the next question' })}</p>
                </div>
                <LeaderboardTable />
              </div>
            )}

            {/* S3 / S4 / S5 — active question */}
            {sessionToken && !sessionInvalidated && currentQuestion && sessionStatus !== 'ended' && (
              <div className="aud2-screen">

                {/* Timer strip */}
                {displayTimerRemaining !== null && (
                  <div className="aud2-timer-track" role="progressbar" aria-label={t('quiz.timeLeft', { seconds: displayTimerRemaining })} aria-valuenow={displayTimerRemaining} aria-valuemax={currentQuestion.max_time_seconds}>
                    <div
                      className={`aud2-timer-bar${displayTimerRemaining <= 10 ? ' aud2-timer-bar--danger' : ''}`}
                      style={{ width: `${Math.max(0, Math.min(100, (displayTimerRemaining / Number(currentQuestion.max_time_seconds)) * 100))}%` }}
                    />
                  </div>
                )}

                {/* Question area */}
                <div className="aud2-question-area">
                  <VideoEmbed url={currentQuestion.question_video_url} height={180} />
                  {currentQuestion.question_image_url && (
                    <img src={currentQuestion.question_image_url} alt="" className="aud2-question-img" />
                  )}
                  <RichTextRenderer content={currentQuestion.text} isDark={theme === 'dark'} className="aud2-question-text" />
                  {displayTimerRemaining !== null && (
                    <p className="aud2-timer-label" aria-live={displayTimerRemaining <= 5 ? 'assertive' : 'off'}>
                      {t('quiz.timeLeft', { seconds: displayTimerRemaining })}
                    </p>
                  )}
                </div>

                {/* Answer area */}
                <div className="aud2-answer-area">

                  {/* ── Text types: unanswered ── */}
                  {isTextQuestion && !submitted && (
                    <div className="aud2-text-answer-wrap">
                      {isOneWord ? (
                        <Input
                          placeholder={t('audience.enterOneWord', { defaultValue: 'Enter one word' })}
                          maxLength={30}
                          value={wordCloudAnswer}
                          onChange={(e) => setWordCloudAnswer(e.target.value.replace(/\s/g, ''))}
                          className="aud2-oneline-input"
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
                          maxLength={currentQuestion.question_type === 'word_cloud' ? 100 : currentQuestion.question_type === 'single_line' ? 255 : 2000}
                          value={wordCloudAnswer}
                          onChange={(e) => setWordCloudAnswer(e.target.value)}
                          showCount
                        />
                      )}
                      <button className="aud2-submit-btn" disabled={!wordCloudAnswer.trim() || loading} onClick={handleSubmitAnswer}>
                        {loading ? '…' : t('quiz.submitAnswer')}
                      </button>
                      {(isWordCloud || isOneWord) && wordCloudData.length > 0 && (
                        <div className="aud2-wordcloud-wrap">
                          <p className="aud2-subtext">{t('audience.liveWordCloud', { defaultValue: 'Live Word Cloud' })} · {wordCloudData.reduce((s, w) => s + w.value, 0)} {t('audience.responses', { defaultValue: 'responses' })}</p>
                          <div style={{ width: '100%', height: 240, borderRadius: 8, overflow: 'hidden', background: 'var(--aud-surface)' }}>
                            <ReactWordcloud words={wordCloudData} options={{ rotations: 2, rotationAngles: [0, 90], fontSizes: [14, 52], padding: 4, enableTooltip: true, deterministic: true, fontFamily: 'Arial', colors: ['#6366f1', '#22c55e', '#faad14', '#f5222d', '#7c3aed', '#ec4899'] }} />
                          </div>
                        </div>
                      )}
                      {(isWordCloud || isOneWord) && wordCloudData.length === 0 && (
                        <p className="aud2-subtext">{t('audience.beFirstToRespond', { defaultValue: 'Be the first to respond!' })}</p>
                      )}
                    </div>
                  )}

                  {/* ── Text types: submitted ── */}
                  {isTextQuestion && submitted && (
                    <div className="aud2-confirmed-panel">
                      <span className="aud2-hero-icon" style={{ fontSize: 36 }}>✅</span>
                      <h3 className="aud2-confirmed-heading">{t('audience.responseRecorded', { defaultValue: 'Response recorded' })}</h3>
                      {wordCloudAnswer && (
                        <div className="aud2-your-answer-tag">{t('audience.yourAnswer', { defaultValue: 'Your answer' })}: {wordCloudAnswer}</div>
                      )}
                      {!(isWordCloud || isOneWord) && (
                        <p className="aud2-subtext">{t('audience.waitingHostNext', { defaultValue: 'Waiting for the host to move to the next question.' })}</p>
                      )}
                      {(isWordCloud || isOneWord) && wordCloudData.length > 0 && (
                        <div className="aud2-wordcloud-wrap" style={{ width: '100%' }}>
                          <p className="aud2-subtext">{wordCloudData.reduce((s, w) => s + w.value, 0)} {t('audience.responses', { defaultValue: 'responses' })}</p>
                          <div style={{ width: '100%', height: 240, borderRadius: 8, overflow: 'hidden', background: 'var(--aud-surface)' }}>
                            <ReactWordcloud
                              words={wordCloudData.map(w => ({ ...w, color: w.text.toLowerCase() === wordCloudAnswer.toLowerCase() ? '#ef4444' : undefined }))}
                              options={{ rotations: 2, rotationAngles: [0, 90], fontSizes: [14, 52], padding: 4, enableTooltip: true, deterministic: true, fontFamily: 'Arial', colors: ['#6366f1', '#22c55e', '#faad14', '#f5222d', '#7c3aed', '#ec4899'] }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* ── Scale: unanswered ── */}
                  {isScaleQuestion && !submitted && (
                    <div className="aud2-scale-wrap">
                      <p className="aud2-subtext">{t('audience.tapStarToRate', { defaultValue: 'Tap a star to rate:' })}</p>
                      <Rate style={{ fontSize: 52, color: '#faad14' }} value={selectedAnswer ? Number(selectedAnswer) + 1 : 0} onChange={handleStarAndSubmit} />
                      {selectedAnswer && <p className="aud2-subtext">{t('audience.selectedStars', { count: Number(selectedAnswer) + 1 })}</p>}
                    </div>
                  )}

                  {/* ── Scale: submitted (avg) ── */}
                  {isScaleQuestion && submitted && (() => {
                    const dist = currentQuestion.answer_distribution || []
                    const totalAns = currentQuestion.total_answers || 0
                    let sum = 0; dist.forEach((c, i) => { sum += c * (i + 1) })
                    const avg = totalAns > 0 ? (sum / totalAns).toFixed(1) : 0
                    const yourRating = selectedAnswer != null ? Number(selectedAnswer) + 1 : null
                    return (
                      <div className="aud2-scale-result">
                        {yourRating != null && (
                          <div className="aud2-your-rating">
                            <span className="aud2-subtext">{t('audience.yourRating', { defaultValue: 'Your rating:' })}</span>
                            <Rate disabled value={yourRating} style={{ fontSize: 22, color: '#faad14' }} />
                          </div>
                        )}
                        <p className="aud2-subtext">{t('quizPresent.averageRating', { defaultValue: 'Average Rating' })}</p>
                        <div className="aud2-avg-rating">
                          <span className="aud2-avg-num">{avg}</span>
                          <span className="aud2-avg-denom">/ 5</span>
                        </div>
                        <Rate disabled allowHalf value={Number(avg)} style={{ fontSize: 36, color: '#faad14' }} />
                        <p className="aud2-subtext">{t('audience.ratingsCount', { count: totalAns })}</p>
                        <p className="aud2-subtext">{t('audience.waitingForNextQuestion', { defaultValue: 'Waiting for next question...' })}</p>
                      </div>
                    )
                  })()}

                  {/* ── MCQ / Poll: unanswered ── */}
                  {!isTextQuestion && !isScaleQuestion && !submitted && (
                    <div className="aud2-options-list" role="radiogroup" aria-label={t('audience.chooseAnswer', { defaultValue: 'Choose your answer' })}>
                      {['A', 'B', 'C', 'D'].map((key) => {
                        const label = currentQuestion[`option_${key.toLowerCase()}`]
                        if (!label) return null
                        const isSelected = selectedAnswer === key
                        return (
                          <button
                            key={key}
                            role="radio"
                            aria-checked={isSelected}
                            className={`aud2-option${isSelected ? ' aud2-option--selected' : ''}${isGameShow ? ` aud2-gs aud2-gs--${key.toLowerCase()}` : ''}`}
                            onClick={() => handleSelectAndSubmit(key)}
                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleSelectAndSubmit(key) } }}
                            disabled={loading}
                          >
                            <span className="aud2-option-key">{key}</span>
                            <span className="aud2-option-body">
                              <RichTextRenderer content={label} isDark={theme === 'dark'} className="aud2-option-text" />
                              {currentQuestion.option_images?.[key] && (
                                <img src={currentQuestion.option_images[key]} alt={`Option ${key}`} className="aud2-option-img" />
                              )}
                            </span>
                          </button>
                        )
                      })}
                    </div>
                  )}

                  {/* ── S4: Locked in (quiz, no reveal yet) ── */}
                  {!isTextQuestion && !isScaleQuestion && submitted && !currentQuestion.correct_answer && !isPoll && (
                    <div className="aud2-locked-panel">
                      <span className="aud2-locked-icon">⚡</span>
                      <h3 className="aud2-locked-heading">{t('audience.lockedIn', { defaultValue: 'Locked in!' })}</h3>
                      {selectedAnswer && currentQuestion[`option_${selectedAnswer.toLowerCase()}`] && (
                        <div className="aud2-locked-choice">
                          <span className="aud2-option-key">{selectedAnswer}</span>
                          <RichTextRenderer content={currentQuestion[`option_${selectedAnswer.toLowerCase()}`]} isDark={theme === 'dark'} className="aud2-option-text" />
                        </div>
                      )}
                      {results?.total_answers != null && results?.total_participants > 1 && (
                        <div className="aud2-response-rate">
                          <span className="aud2-response-count">{results.total_answers} / {results.total_participants} {t('audience.answered', { defaultValue: 'answered' })}</span>
                          <div className="aud2-response-track">
                            <div className="aud2-response-fill" style={{ width: `${Math.min(100, (results.total_answers / results.total_participants) * 100)}%` }} />
                          </div>
                        </div>
                      )}
                      <p className="aud2-subtext">{t('audience.waitingForReveal', { defaultValue: 'Waiting for the host to reveal the answer…' })}</p>
                    </div>
                  )}

                  {/* ── Poll: result (immediately after submit) ── */}
                  {isPoll && submitted && (
                    <div className="aud2-options-list">
                      {['A', 'B', 'C', 'D'].map((key) => {
                        const label = currentQuestion[`option_${key.toLowerCase()}`]
                        if (!label) return null
                        const idx = key.charCodeAt(0) - 65
                        const dist = currentQuestion.answer_distribution || [0, 0, 0, 0]
                        const totalAns = currentQuestion.total_answers || 0
                        const count = dist[idx] || 0
                        const pct = totalAns > 0 ? (count / totalAns * 100) : 0
                        const isSelected = selectedAnswer === key
                        return (
                          <div key={key} className={`aud2-option aud2-option--result${isSelected ? ' aud2-option--selected' : ''}`}>
                            <span className="aud2-option-key">{key}</span>
                            <span className="aud2-option-body">
                              <RichTextRenderer content={label} isDark={theme === 'dark'} className="aud2-option-text" />
                            </span>
                            <span className="aud2-pct">{count} ({pct.toFixed(1)}%)</span>
                            <div className="aud2-dist-bar-track">
                              <div className="aud2-dist-bar-fill" style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                        )
                      })}
                      <p className="aud2-subtext aud2-subtext--centered">{t('audience.waitingForNextQuestion', { defaultValue: 'Waiting for next question...' })}</p>
                    </div>
                  )}

                  {/* ── S5: MCQ reveal ── */}
                  {!isPoll && !isScaleQuestion && !isTextQuestion && submitted && currentQuestion.correct_answer && (
                    <>
                      <div className={`aud2-status-banner aud2-status-banner--${selectedAnswer === currentQuestion.correct_answer ? 'correct' : 'wrong'}`}>
                        {selectedAnswer === currentQuestion.correct_answer
                          ? `✓ ${t('audience.correct', { defaultValue: 'Correct!' })}`
                          : `✗ ${t('audience.wrong', { defaultValue: 'Wrong' })}`}
                      </div>
                      <div className="aud2-options-list aud2-options-list--revealed">
                        {['A', 'B', 'C', 'D'].map((key) => {
                          const label = currentQuestion[`option_${key.toLowerCase()}`]
                          if (!label) return null
                          const isCorrect = currentQuestion.correct_answer === key
                          const isSelected = selectedAnswer === key
                          const idx = key.charCodeAt(0) - 65
                          const dist = currentQuestion.answer_distribution || [0, 0, 0, 0]
                          const total = currentQuestion.total_answers || 0
                          const pct = total > 0 ? (dist[idx] / total * 100) : 0
                          return (
                            <div
                              key={key}
                              className={`aud2-option aud2-option--result ${isCorrect ? 'aud2-option--correct' : isSelected ? 'aud2-option--wrong' : 'aud2-option--faded'}`}
                            >
                              <span className={`aud2-option-key aud2-option-key--${isCorrect ? 'correct' : isSelected ? 'wrong' : 'neutral'}`}>{key}</span>
                              <span className="aud2-option-body">
                                <RichTextRenderer content={label} isDark={theme === 'dark'} className="aud2-option-text" style={{ fontWeight: isCorrect ? 600 : 400 }} />
                                {currentQuestion.option_images?.[key] && (
                                  <img src={currentQuestion.option_images[key]} alt={`Option ${key}`} className="aud2-option-img" />
                                )}
                              </span>
                              <span className="aud2-pct">{pct.toFixed(0)}%</span>
                              <div className="aud2-dist-bar-track">
                                <div className={`aud2-dist-bar-fill${isCorrect ? ' aud2-dist-bar-fill--correct' : ''}`} style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          )
                        })}
                      </div>
                      <div className="aud2-pts-reveal" aria-live="polite" aria-atomic="true">
                        {selectedAnswer === currentQuestion.correct_answer ? (
                          <div className="aud2-pts-correct">+{currentQuestion.points || 1} {t('leaderboard.pts', { defaultValue: 'pts' })}</div>
                        ) : (
                          <div className="aud2-pts-none">{t('audience.noPoints', { defaultValue: 'No points this round' })}</div>
                        )}
                      </div>
                      <LeaderboardTable />
                      <p className="aud2-subtext aud2-subtext--centered" style={{ marginTop: 4 }}>{t('audience.waitingForNextQuestion', { defaultValue: 'Waiting for next question...' })}</p>
                    </>
                  )}

                </div>{/* end aud2-answer-area */}

                <div className="aud2-footer">
                  <button className="aud2-leave-btn" onClick={handleLeaveSession}>
                    {t('audience.leaveSession', { defaultValue: 'Leave Session' })}
                  </button>
                </div>
              </div>
            )}

      </div>
    </div>
  )
}
