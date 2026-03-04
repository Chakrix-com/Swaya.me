import { useState, useEffect, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Spin, Tag } from 'antd'
import { TeamOutlined, TrophyOutlined, LeftOutlined, RightOutlined, UserOutlined, ThunderboltOutlined, ClockCircleOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons'
import { QRCodeCanvas } from 'qrcode.react'
import ReactWordcloud from 'react-wordcloud'
import { sessionAPI, questionAPI } from '../../services/api'
import './QuizPresent.css'

const OPTION_LETTERS = ['A', 'B', 'C', 'D']
const OPTION_BG = [
  'rgba(64,150,255,0.14)',
  'rgba(82,196,26,0.14)',
  'rgba(250,173,20,0.14)',
  'rgba(245,34,45,0.14)',
]
const OPTION_BORDER = [
  'rgba(64,150,255,0.45)',
  'rgba(82,196,26,0.45)',
  'rgba(250,173,20,0.45)',
  'rgba(245,34,45,0.45)',
]
const OPTION_ACCENT = ['#4096ff', '#52c41a', '#faad14', '#f5222d']
const WORDCLOUD_COLORS = ['#4096ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96', '#13c2c2']

/* ── Waiting ─────────────────────────────────────────── */
function WaitingView({ participantCount }) {
  return (
    <div className="pv-center-fill">
      <span className="pv-waiting-emoji">📡</span>
      <h2 className="pv-waiting-title">Waiting for the quiz to start…</h2>
      <p className="pv-waiting-sub">
        {participantCount > 0
          ? `${participantCount} participant${participantCount !== 1 ? 's' : ''} joined`
          : 'Participants can join using the code'}
      </p>
    </div>
  )
}

/* ── Single MCQ option card ──────────────────────────── */
function OptionCard({ index, letter, text, imageUrl, count, total, revealed, isCorrect }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0

  const bg     = revealed ? (isCorrect ? 'rgba(82,196,26,0.18)' : 'rgba(255,255,255,0.03)') : OPTION_BG[index]
  const border = revealed ? (isCorrect ? 'rgba(82,196,26,0.75)' : 'rgba(255,255,255,0.09)') : OPTION_BORDER[index]
  const accent = revealed ? (isCorrect ? '#52c41a'               : 'rgba(255,255,255,0.22)') : OPTION_ACCENT[index]

  return (
    <div
      className={`pv-option-card${revealed ? (isCorrect ? ' pv-option-correct' : ' pv-option-wrong') : ''}`}
      style={{ background: bg, border: `1px solid ${border}` }}
    >
      <div className="pv-option-row">
        <span className="pv-option-badge" style={{ background: accent }}>
          {revealed ? (isCorrect ? <CheckOutlined /> : <CloseOutlined />) : letter}
        </span>
        <span className="pv-option-text" style={revealed && !isCorrect ? { opacity: 0.4 } : {}}>
          {text}
        </span>
        {total > 0 && (
          <span className="pv-option-pct" style={revealed && !isCorrect ? { opacity: 0.35 } : {}}>
            {pct}%
          </span>
        )}
      </div>
      {imageUrl && <img src={imageUrl} alt={`Option ${letter}`} className="pv-option-img" />}
      <div className="pv-bar-track">
        <div
          className="pv-bar-fill"
          style={{ width: pct > 0 ? `${pct}%` : '0%', background: accent }}
        />
      </div>
    </div>
  )
}

/* ── MCQ Question ────────────────────────────────────── */
function MCQView({ question, questionNumber, totalQuestions, revealed }) {
  const opts = question.options || [
    question.option_a,
    question.option_b,
    question.option_c,
    question.option_d,
  ]
  const dist = question.answer_distribution || [0, 0, 0, 0]
  const total = question.total_answers || 0
  const images = question.option_images || {}
  const correctIndex = question.correct_answer_index ?? -1

  return (
    <div className="pv-question-wrap">
      <div className="pv-question-meta">
        <Tag color="blue" style={{ fontSize: 13, padding: '2px 10px' }}>
          Question {questionNumber} of {totalQuestions}
        </Tag>
        {total > 0 && (
          <Tag color="geekblue" style={{ fontSize: 12 }}>
            {total} response{total !== 1 ? 's' : ''}
          </Tag>
        )}
        {revealed && (
          <Tag color="success" style={{ fontSize: 12 }}>
            <CheckOutlined /> Answer revealed
          </Tag>
        )}
      </div>

      {question.question_image_url && (
        <div className="pv-question-img-wrap">
          <img src={question.question_image_url} alt="Question" className="pv-question-img" />
        </div>
      )}

      <p className="pv-question-text">{question.text || question.question_text}</p>

      <div className="pv-options-grid">
        {opts.map((opt, i) => (
          <OptionCard
            key={i}
            index={i}
            letter={OPTION_LETTERS[i]}
            text={opt}
            imageUrl={images[OPTION_LETTERS[i]]}
            count={dist[i] || 0}
            total={total}
            revealed={revealed}
            isCorrect={i === correctIndex}
          />
        ))}
      </div>
    </div>
  )
}

/* ── Word Cloud Question ─────────────────────────────── */
function WordCloudView({ question, wordCloudData, questionNumber, totalQuestions }) {
  const total = question.total_answers || 0
  return (
    <div className="pv-question-wrap">
      <div className="pv-question-meta">
        <Tag color="purple" style={{ fontSize: 13, padding: '2px 10px' }}>
          Question {questionNumber} of {totalQuestions}
        </Tag>
        <Tag color="purple">Word Cloud</Tag>
        {total > 0 && (
          <Tag color="default" style={{ fontSize: 12 }}>
            {total} submission{total !== 1 ? 's' : ''}
          </Tag>
        )}
      </div>

      {question.question_image_url && (
        <div className="pv-question-img-wrap">
          <img src={question.question_image_url} alt="Question" className="pv-question-img" />
        </div>
      )}

      <p className="pv-question-text">{question.text || question.question_text}</p>

      <div className="pv-wordcloud-container">
        {wordCloudData.length > 0 ? (
          <ReactWordcloud
            words={wordCloudData}
            options={{
              rotations: 1,
              rotationAngles: [0],
              fontSizes: [22, 88],
              padding: 6,
              enableTooltip: false,
              deterministic: true,
              fontFamily: 'Inter, Arial, sans-serif',
              colors: WORDCLOUD_COLORS,
            }}
          />
        ) : (
          <div className="pv-center-fill">
            <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: 16, margin: 0 }}>
              Waiting for responses…
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Ended / Leaderboard ─────────────────────────────── */
const MEDALS = ['🥇', '🥈', '🥉']
const PODIUM_COLORS = ['#ffd700', '#c0c0c0', '#cd7f32']

function EndedView({ leaderboard }) {
  const entries = leaderboard?.entries || []
  // Reorder top 3 as [2nd, 1st, 3rd] for classic podium visual
  const raw3 = entries.slice(0, 3)
  const podium = raw3.length === 3
    ? [raw3[1], raw3[0], raw3[2]]
    : raw3.length === 2
      ? [raw3[1], raw3[0]]
      : raw3
  const rest = entries.slice(3, 10)

  return (
    <div className="pv-ended-wrap">
      <div className="pv-ended-header">
        <TrophyOutlined className="pv-ended-icon" />
        <h2 className="pv-ended-title">Final Leaderboard</h2>
      </div>

      {podium.length > 0 && (
        <div className="pv-podium">
          {podium.map((entry, vi) => {
            // Map visual index back to actual rank index (2nd=0, 1st=1, 3rd=2 when length=3)
            const actualIdx = raw3.length === 3
              ? (vi === 0 ? 1 : vi === 1 ? 0 : 2)
              : vi === 0 && raw3.length === 2 ? 1 : 0
            const color = PODIUM_COLORS[actualIdx]
            const isFirst = actualIdx === 0
            return (
              <div
                key={entry.participant_id}
                className={`pv-podium-card${isFirst ? ' pv-podium-card-first' : ''}`}
                style={{ borderColor: color }}
              >
                <span className="pv-podium-medal">{MEDALS[actualIdx]}</span>
                <span className="pv-podium-name" style={{ color }}>
                  {entry.display_name}
                </span>
                <span className="pv-podium-score" style={{ color }}>
                  {entry.score}
                </span>
                <span className="pv-podium-time">
                  {entry.time_taken_seconds != null ? `${entry.time_taken_seconds.toFixed(1)}s` : '—'}
                </span>
              </div>
            )
          })}
        </div>
      )}

      {rest.length > 0 && (
        <div className="pv-lb-rest">
          {rest.map((entry) => (
            <div key={entry.participant_id} className="pv-lb-row">
              <span className="pv-lb-rank">#{entry.rank}</span>
              <span className="pv-lb-name">{entry.display_name}</span>
              <span className="pv-lb-score">{entry.score}</span>
              <span className="pv-lb-time">
                {entry.time_taken_seconds != null ? `${entry.time_taken_seconds.toFixed(1)}s` : '—'}
              </span>
            </div>
          ))}
        </div>
      )}

      {entries.length === 0 && (
        <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 16 }}>No scores to display</p>
      )}
    </div>
  )
}

/* ── Full Leaderboard Lightbox ───────────────────────── */
const MODAL_MEDALS = ['🥇', '🥈', '🥉']
const RANK_COLORS = ['#ffd700', '#c0c0c0', '#cd7f32']

function LeaderboardModal({ leaderboard, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const entries = leaderboard?.entries || []

  return (
    <div className="pv-lb-backdrop" onClick={onClose}>
      <div className="pv-lb-panel" onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div className="pv-lb-panel-header">
          <div className="pv-lb-panel-title">
            <TrophyOutlined style={{ color: '#ffd700', fontSize: 18 }} />
            <span>Full Leaderboard</span>
            {leaderboard?.mcq_question_count > 1 && (
              <span className="pv-lb-panel-meta">
                {leaderboard.mcq_question_count} MCQ questions
              </span>
            )}
          </div>
          <button className="pv-lb-panel-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        {/* Table */}
        <div className="pv-lb-panel-body">
          {entries.length === 0 ? (
            <p className="pv-lb-empty">No scores yet — keep playing!</p>
          ) : (
            <table className="pv-lb-table">
              <thead>
                <tr>
                  <th className="pv-lbt-rank"><TrophyOutlined className="pv-lbt-icon" /> #</th>
                  <th className="pv-lbt-name"><UserOutlined className="pv-lbt-icon" /> Participant</th>
                  <th className="pv-lbt-score"><ThunderboltOutlined className="pv-lbt-icon" /> Score</th>
                  <th className="pv-lbt-time"><ClockCircleOutlined className="pv-lbt-icon" /> Time</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry, i) => (
                  <tr key={entry.participant_id} className={i < 3 ? 'pv-lbt-top' : ''}>
                    <td className="pv-lbt-rank">
                      {i < 3 ? (
                        <span className="pv-lbt-rank-top">
                          <span style={{ fontSize: 16 }}>{MODAL_MEDALS[i]}</span>
                          <span className="pv-lbt-rank-num">#{entry.rank ?? i + 1}</span>
                        </span>
                      ) : (
                        <span style={{ color: 'rgba(255,255,255,0.45)' }}>#{entry.rank}</span>
                      )}
                    </td>
                    <td className="pv-lbt-name" style={i < 3 ? { color: RANK_COLORS[i], fontWeight: 700 } : {}}>
                      {entry.display_name}
                    </td>
                    <td className="pv-lbt-score">{entry.score}</td>
                    <td className="pv-lbt-time">
                      {entry.time_taken_seconds != null
                        ? `${entry.time_taken_seconds.toFixed(1)}s`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer hint */}
        <div className="pv-lb-panel-footer">
          Press <kbd>Esc</kbd> or click outside to close
        </div>
      </div>
    </div>
  )
}

/* ── Host Control Bar ───────────────────────────────── */
function ControlBar({ currentQIdx, totalQ, loading, onAdvance, onBack, onStop, onToggleHelp, revealed }) {
  const notStarted = currentQIdx === -1
  const isLastQ = !notStarted && currentQIdx >= totalQ - 1
  const prevDisabled = loading || notStarted || currentQIdx <= 0
  const [confirmStop, setConfirmStop] = useState(false)

  let advanceLabel, advanceTitle
  if (loading) {
    advanceLabel = '…'
    advanceTitle = ''
  } else if (notStarted) {
    advanceLabel = '▶ Start'
    advanceTitle = 'Start quiz'
  } else if (revealed) {
    advanceLabel = isLastQ ? <>End <CheckOutlined /></> : <>Continue <RightOutlined /></>
    advanceTitle = isLastQ ? 'End session' : 'Next question'
  } else {
    advanceLabel = isLastQ ? 'Finish ✓' : <RightOutlined />
    advanceTitle = isLastQ ? 'Reveal answer' : 'Reveal answer'
  }

  return (
    <div className="pv-ctrl-bar">
      <button className="pv-ctrl-btn" onClick={onBack} disabled={prevDisabled} title="Previous question">
        <LeftOutlined /> <kbd className="pv-kbd">←</kbd>
      </button>
      <button
        className={`pv-ctrl-btn pv-ctrl-primary${revealed ? ' pv-ctrl-continue' : ''}`}
        onClick={onAdvance}
        disabled={loading}
        title={advanceTitle}
      >
        {advanceLabel}
        {' '}<kbd className="pv-kbd">{notStarted ? 'Space' : '→'}</kbd>
      </button>
      {confirmStop ? (
        <>
          <button className="pv-ctrl-btn pv-ctrl-stop-confirm" onClick={onStop} disabled={loading}>
            Confirm Stop
          </button>
          <button className="pv-ctrl-btn" onClick={() => setConfirmStop(false)}>
            Cancel
          </button>
        </>
      ) : (
        <button className="pv-ctrl-btn pv-ctrl-stop" onClick={() => setConfirmStop(true)}>
          ■ Stop
        </button>
      )}
      <button className="pv-ctrl-btn pv-ctrl-help" onClick={onToggleHelp} title="Keyboard shortcuts">
        ?
      </button>
    </div>
  )
}

/* ── Compact Leaderboard (sidebar) ───────────────────── */
const CLB_MEDALS = ['🥇', '🥈', '🥉']

function CompactLeaderboard({ entries, total, onExpand }) {
  if (!entries || entries.length === 0) return null
  const top5 = entries.slice(0, 5)
  return (
    <div className="pv-clb-wrap">
      <div className="pv-clb-header">
        <TrophyOutlined style={{ fontSize: 11, color: '#faad14' }} />
        <span>Live Standings</span>
        <button className="pv-clb-expand-icon" onClick={onExpand} title="View full leaderboard">
          ⛶
        </button>
      </div>
      {top5.map((entry, i) => (
        <div key={entry.participant_id} className="pv-clb-row">
          <span className="pv-clb-rank">
            {i < 3 ? <span className="pv-clb-medal">{CLB_MEDALS[i]}</span> : null}
            <span className="pv-clb-rank-num">#{entry.rank ?? i + 1}</span>
          </span>
          <span className="pv-clb-name">{entry.display_name}</span>
          <span className="pv-clb-score">
            <ThunderboltOutlined className="pv-clb-icon" /> {entry.score}
          </span>
        </div>
      ))}
      {total > 5 && (
        <button className="pv-clb-view-all" onClick={onExpand}>
          View all {total} participants →
        </button>
      )}
    </div>
  )
}

/* ── Sidebar ─────────────────────────────────────────── */
function Sidebar({ quizTitle, joinCode, joinUrl, participantCount, leaderboard, onExpandLeaderboard }) {
  return (
    <aside className="pv-sidebar">
      <div className="pv-sidebar-title">{quizTitle}</div>

      {joinCode && (
        <>
          <div className="pv-sidebar-divider" />
          <div className="pv-qr-wrap">
            <QRCodeCanvas value={joinUrl} size={164} level="H" includeMargin={false} />
            <span className="pv-qr-label">Scan to join</span>
          </div>
          <div className="pv-join-code-wrap">
            <span className="pv-join-code-label">Join Code</span>
            <span className="pv-join-code">{joinCode}</span>
            <span className="pv-join-host">{window.location.hostname}</span>
          </div>
        </>
      )}

      <div className="pv-sidebar-divider" />

      <div className="pv-participants">
        <TeamOutlined className="pv-participants-icon" />
        <span className="pv-participants-count">{participantCount}</span>
        <span className="pv-participants-label">Participants</span>
      </div>

      {leaderboard?.entries?.some(e => e.score > 0) && (
        <>
          <div className="pv-sidebar-divider" />
          <CompactLeaderboard
            entries={leaderboard.entries}
            total={leaderboard.total_participants}
            onExpand={onExpandLeaderboard}
          />
        </>
      )}
    </aside>
  )
}

/* ── Root ────────────────────────────────────────────── */
export default function QuizPresent() {
  const { sessionId } = useParams()
  const [searchParams] = useSearchParams()
  const joinCode = searchParams.get('code') || ''

  const [results, setResults] = useState(null)
  const [leaderboard, setLeaderboard] = useState(null)
  const [wordCloudData, setWordCloudData] = useState([])
  const [ctrlLoading, setCtrlLoading] = useState(false)
  const [showLbModal, setShowLbModal] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const prevQIdx = useRef(-2)

  // Host controls are shown only when a JWT token is present in this browser
  const isHost = !!localStorage.getItem('token')

  const joinUrl = joinCode ? `${window.location.origin}/join/${joinCode}` : ''

  const refreshResults = async () => {
    try {
      const res = await sessionAPI.getResults(Number(sessionId), null)
      setResults(res.data)
      prevQIdx.current = res.data.current_question_index
    } catch (_) {}
    try {
      const lb = await sessionAPI.getLeaderboard(Number(sessionId), null)
      setLeaderboard(lb.data)
    } catch (_) {}
  }

  const handleAdvance = async () => {
    const notStarted = (results?.current_question_index ?? -1) === -1
    const isWordCloud = results?.current_question?.question_type === 'word_cloud'
    // First press on an MCQ: reveal answer, don't advance yet
    if (!notStarted && !revealed && !isWordCloud) {
      setRevealed(true)
      return
    }
    setCtrlLoading(true)
    try {
      await sessionAPI.advance(Number(sessionId))
      await refreshResults()
      setRevealed(false)
    } catch (_) {}
    setCtrlLoading(false)
  }

  // Reset reveal whenever the question changes (also handles Back navigation)
  useEffect(() => {
    setRevealed(false)
  }, [results?.current_question_index])

  const handleBack = async () => {
    setCtrlLoading(true)
    try {
      await sessionAPI.back(Number(sessionId))
      await refreshResults()
    } catch (_) {}
    setCtrlLoading(false)
  }

  const handleEnd = async () => {
    setCtrlLoading(true)
    try {
      await sessionAPI.end(Number(sessionId))
      await refreshResults()
    } catch (_) {}
    setCtrlLoading(false)
  }

  // Keep a ref to the latest handlers so the keyboard listener never goes stale
  const ctrlRef = useRef({})
  ctrlRef.current = {
    isEnded: results?.status === 'ended',
    loading: ctrlLoading,
    advance: handleAdvance,  // already includes reveal-first logic
    back: handleBack,
    toggleLb: () => setShowLbModal(v => !v),
    toggleHelp: () => setShowHelp(v => !v),
    closeOverlays: () => { setShowLbModal(false); setShowHelp(false) },
  }

  useEffect(() => {
    if (!isHost) return
    const onKey = (e) => {
      const { isEnded, loading, advance, back, toggleLb, toggleHelp, closeOverlays } = ctrlRef.current
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
      if (e.key === 'Escape') { closeOverlays(); return }
      if (isEnded) return
      switch (e.key) {
        case 'ArrowRight': case 'ArrowDown': case ' ': case 'PageDown': case 'Enter':
          e.preventDefault()
          if (!loading) advance()
          break
        case 'ArrowLeft': case 'ArrowUp': case 'Backspace': case 'PageUp':
          e.preventDefault()
          if (!loading) back()
          break
        case 'l': case 'L':
          toggleLb()
          break
        case 'f': case 'F':
          if (!document.fullscreenElement) document.documentElement.requestFullscreen?.()
          else document.exitFullscreen?.()
          break
        case '?':
          toggleHelp()
          break
        default: break
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [isHost])

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await sessionAPI.getResults(Number(sessionId), null)
        const data = res.data
        setResults(data)

        try {
          const lb = await sessionAPI.getLeaderboard(Number(sessionId), null)
          setLeaderboard(lb.data)
        } catch (_) {}

        if (data.current_question?.question_type === 'word_cloud') {
          if (prevQIdx.current !== data.current_question_index) {
            setWordCloudData([])
          }
          try {
            const wc = await questionAPI.getWordCloudResults(
              data.current_question.id,
              Number(sessionId)
            )
            const words = Object.entries(wc.data.word_frequencies).map(([text, value]) => ({
              text,
              value,
            }))
            setWordCloudData(words)
          } catch (_) {}
        }

        prevQIdx.current = data.current_question_index
      } catch (_) {}
    }

    poll()
    const interval = setInterval(poll, 2000)
    return () => clearInterval(interval)
  }, [sessionId])

  const participantCount = results?.total_participants ?? 0
  const qNumber = (results?.current_question_index ?? -1) + 1
  const totalQ = results?.total_questions ?? 0
  const currentQ = results?.current_question
  const isEnded = results?.status === 'ended'
  const isWaiting = !isEnded && (results?.current_question_index === -1 || !currentQ)

  return (
    <div className="pv-root">
      <Sidebar
        quizTitle={results?.quiz_title ?? 'Quiz'}
        joinCode={joinCode}
        joinUrl={joinUrl}
        participantCount={participantCount}
        leaderboard={leaderboard}
        onExpandLeaderboard={() => setShowLbModal(true)}
      />

      <main className="pv-main">
        {!results ? (
          <div className="pv-center-fill">
            <Spin size="large" />
          </div>
        ) : isEnded ? (
          <EndedView leaderboard={leaderboard} />
        ) : isWaiting ? (
          <WaitingView participantCount={participantCount} />
        ) : currentQ?.question_type === 'word_cloud' ? (
          <WordCloudView
            question={currentQ}
            wordCloudData={wordCloudData}
            questionNumber={qNumber}
            totalQuestions={totalQ}
          />
        ) : (
          <MCQView question={currentQ} questionNumber={qNumber} totalQuestions={totalQ} revealed={revealed} />
        )}
      </main>

      {isHost && !isEnded && (
        <ControlBar
          currentQIdx={results?.current_question_index ?? -1}
          totalQ={totalQ}
          loading={ctrlLoading}
          onAdvance={handleAdvance}
          onBack={handleBack}
          onStop={handleEnd}
          onToggleHelp={() => setShowHelp(v => !v)}
          revealed={revealed}
        />
      )}

      {showLbModal && (
        <LeaderboardModal
          leaderboard={leaderboard}
          onClose={() => setShowLbModal(false)}
        />
      )}

      {showHelp && isHost && (
        <div className="pv-help-backdrop" onClick={() => setShowHelp(false)}>
          <div className="pv-help-panel" onClick={e => e.stopPropagation()}>
            <div className="pv-help-title">Keyboard Shortcuts</div>
            <table className="pv-help-table">
              <tbody>
                <tr><td><kbd>→</kbd> <kbd>Space</kbd> <kbd>Enter</kbd></td><td>Next question</td></tr>
                <tr><td><kbd>←</kbd> <kbd>Backspace</kbd></td><td>Previous question</td></tr>
                <tr><td><kbd>PageDown</kbd></td><td>Next question</td></tr>
                <tr><td><kbd>PageUp</kbd></td><td>Previous question</td></tr>
                <tr><td><kbd>L</kbd></td><td>Toggle leaderboard</td></tr>
                <tr><td><kbd>F</kbd></td><td>Toggle fullscreen</td></tr>
                <tr><td><kbd>?</kbd></td><td>Show / hide this panel</td></tr>
                <tr><td><kbd>Esc</kbd></td><td>Close overlays</td></tr>
              </tbody>
            </table>
            <button className="pv-help-close" onClick={() => setShowHelp(false)}>✕ Close</button>
          </div>
        </div>
      )}
    </div>
  )
}
