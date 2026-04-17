import { useState, useEffect, useRef } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Spin, Tag, Rate, Progress, Modal } from 'antd'
import { TeamOutlined, TrophyOutlined, LeftOutlined, RightOutlined, UserOutlined, ThunderboltOutlined, ClockCircleOutlined, CheckOutlined, CloseOutlined, FullscreenOutlined } from '@ant-design/icons'
import { QRCodeCanvas } from 'qrcode.react'
import ReactWordcloud from 'react-wordcloud'
import { sessionAPI, questionAPI } from '../../services/api'
import BetaBadge from '../../components/BetaBadge'
import RichTextRenderer from './components/RichTextRenderer'
import './QuizPresent.css'

const OPTION_LETTERS = ['A', 'B', 'C', 'D', 'E']
const OPTION_BG = [
  'rgba(64,150,255,0.14)',
  'rgba(82,196,26,0.14)',
  'rgba(250,173,20,0.14)',
  'rgba(245,34,45,0.14)',
  'rgba(114,46,209,0.14)',
]
const OPTION_BORDER = [
  'rgba(64,150,255,0.45)',
  'rgba(82,196,26,0.45)',
  'rgba(250,173,20,0.45)',
  'rgba(245,34,45,0.45)',
  'rgba(114,46,209,0.45)',
]
const OPTION_ACCENT = ['#4096ff', '#52c41a', '#faad14', '#f5222d', '#722ed1']
const WORDCLOUD_COLORS = ['#4096ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#eb2f96', '#13c2c2']
const WHITEBOARD_COLORS = ['#ff4d4f', '#faad14', '#52c41a', '#40a9ff', '#b37feb', '#ffffff']
const WHITEBOARD_PUSH_INTERVAL_MS = 320
const WHITEBOARD_FALLBACK_POLL_MS = 2000

/* ── Waiting ─────────────────────────────────────────── */
function WaitingView({ participantCount, t }) {
  return (
    <div className="pv-center-fill">
      <span className="pv-waiting-emoji">📡</span>
      <h2 className="pv-waiting-title">{t('audience.waiting')}</h2>
      <p className="pv-waiting-sub">
        {participantCount > 0
          ? t('quizPresent.participantsJoined', { count: participantCount })
          : t('quizPresent.participantsCanJoinUsingCode', { defaultValue: 'Participants can join using the code' })}
      </p>
    </div>
  )
}

/* ── Single MCQ option card ──────────────────────────── */
function OptionCard({ index, letter, text, imageUrl, count, total, revealed, isCorrect, showStats, t }) {
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
        <span className="pv-option-text" style={revealed && !isCorrect ? { opacity: 0.4 } : {}} dangerouslySetInnerHTML={{ __html: text || '' }} />
        {showStats && total > 0 && (
          <span className="pv-option-pct" style={revealed && !isCorrect ? { opacity: 0.35 } : {}}>
            {pct}%
          </span>
        )}
      </div>
      {imageUrl && <img src={imageUrl} alt={t('quiz.option', { defaultValue: 'Option' }) + ` ${letter}`} className="pv-option-img" />}
      <div className="pv-bar-track">
        <div
          className="pv-bar-fill"
          style={{ width: showStats && pct > 0 ? `${pct}%` : '0%', background: accent }}
        />
      </div>
    </div>
  )
}

/* ── MCQ Question ────────────────────────────────────── */
function MCQView({ question, questionNumber, totalQuestions, revealed, isPoll, t }) {
  const fallbackOptions = [
    question.option_a,
    question.option_b,
    question.option_c,
    question.option_d,
  ]
  const opts = (question.options && question.options.length > 0 ? question.options : fallbackOptions).filter(Boolean)
  const dist = question.answer_distribution || new Array(opts.length).fill(0)
  const total = question.total_answers || 0
  const images = question.option_images || {}
  const correctIndex = question.correct_answer_index ?? -1
  const showStats = true
  const revealCorrectness = !isPoll && correctIndex >= 0
  const effectiveRevealed = revealed && revealCorrectness

  return (
    <div className="pv-question-wrap">
      <div className="pv-question-meta">
        <Tag color="blue" style={{ fontSize: 13, padding: '2px 10px' }}>
          {t('quiz.question')} {questionNumber} {t('quiz.of')} {totalQuestions}
        </Tag>
        {total > 0 && (
          <Tag color="geekblue" style={{ fontSize: 12 }}>
            {t('quizPresent.responsesCount', { count: total })}
          </Tag>
        )}
        {effectiveRevealed && (
          <Tag color="success" style={{ fontSize: 12 }}>
            <CheckOutlined /> {t('quizPresent.answerRevealed', { defaultValue: 'Answer revealed' })}
          </Tag>
        )}
        {isPoll && revealed && (
          <Tag color="geekblue" style={{ fontSize: 12 }}>
            {t('quizPresent.statisticsShown', { defaultValue: 'Statistics shown' })}
          </Tag>
        )}
      </div>

      {question.question_image_url && (
        <div className="pv-question-img-wrap">
          <img src={question.question_image_url} alt={t('quiz.question')} className="pv-question-img" />
        </div>
      )}

      <RichTextRenderer content={question.text || question.question_text} isDark={true} className="pv-question-text" />

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
            revealed={effectiveRevealed}
            isCorrect={i === correctIndex}
            showStats={showStats}
            t={t}
          />
        ))}
      </div>
    </div>
  )
}

/* ── Scale Question ──────────────────────────────────── */
function ScaleView({ question, questionNumber, totalQuestions, revealed, t }) {
  const total = question.total_answers || 0
  const dist = question.answer_distribution || []
  let sum = 0
  dist.forEach((count, idx) => { sum += count * (idx + 1) })
  const avg = total > 0 ? (sum / total).toFixed(1) : 0

  return (
    <div className="pv-question-wrap">
      <div className="pv-question-meta">
        <Tag color="blue" style={{ fontSize: 13, padding: '2px 10px' }}>
          {t('quiz.question')} {questionNumber} {t('quiz.of')} {totalQuestions}
        </Tag>
        {total > 0 && (
          <Tag color="geekblue" style={{ fontSize: 12 }}>
            {t('quizPresent.responsesCount', { count: total })}
          </Tag>
        )}
        {revealed && (
          <Tag color="geekblue" style={{ fontSize: 12 }}>
            {t('quizPresent.statisticsShown', { defaultValue: 'Statistics shown' })}
          </Tag>
        )}
      </div>

      {question.question_image_url && (
        <div className="pv-question-img-wrap">
          <img src={question.question_image_url} alt={t('quiz.question')} className="pv-question-img" />
        </div>
      )}

      <RichTextRenderer content={question.text || question.question_text} isDark={true} className="pv-question-text" />

      {revealed ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '48px 0', gap: 24 }}>
          <div style={{ fontSize: 24, color: 'rgba(255,255,255,0.85)' }}>{t('quizPresent.averageRating', { defaultValue: 'Average Rating' })}</div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
            <span style={{ fontSize: 84, fontWeight: 700, color: '#faad14', lineHeight: 1 }}>{avg}</span>
            <span style={{ fontSize: 32, color: 'rgba(255,255,255,0.45)' }}>/ 5</span>
          </div>
          <Rate disabled allowHalf value={Number(avg)} style={{ fontSize: 56, color: '#faad14' }} />
        </div>
      ) : (
        <div className="pv-center-fill" style={{ minHeight: 300 }}>
          <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: 20 }}>
            {t('quizPresent.waitingToRevealAverageRating', { defaultValue: 'Waiting to reveal average rating...' })}
          </p>
        </div>
      )}
    </div>
  )
}

function TextResponseView({ question, questionNumber, totalQuestions, t }) {
  const total = question.total_answers || 0
  const questionTypeLabel = question.question_type === 'single_line' ? t('quizPresent.singleLine', { defaultValue: 'Single Line' }) : t('quizPresent.paragraph', { defaultValue: 'Paragraph' })
  const responses = question.text_responses || []

  return (
    <div className="pv-question-wrap" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="pv-question-meta" style={{ flexShrink: 0 }}>
        <Tag color="geekblue" style={{ fontSize: 13, padding: '2px 10px' }}>
          {t('quiz.question')} {questionNumber} {t('quiz.of')} {totalQuestions}
        </Tag>
        <Tag color="geekblue">{questionTypeLabel}</Tag>
        <Tag color="default">{t('quizPresent.responsesCount', { count: total })}</Tag>
      </div>
      
      {question.question_image_url && (
        <div className="pv-question-img-wrap" style={{ flexShrink: 0 }}>
          <img src={question.question_image_url} alt={t('quiz.question')} className="pv-question-img" />
        </div>
      )}
      
      <RichTextRenderer content={question.text || question.question_text} isDark={true} className="pv-question-text" style={{ flexShrink: 0 }} />
      
      <div className="pv-text-responses-container" style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '0 12px 24px', 
        marginTop: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {responses.length > 0 ? (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '16px',
            alignItems: 'start'
          }}>
            {responses.map((res, i) => (
              <div key={i} style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: '12px',
                padding: '16px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
              }}>
                <div style={{
                  fontSize: 12,
                  color: 'rgba(255,255,255,0.45)',
                  marginBottom: 8,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  {res.participant_name}
                </div>
                <div style={{
                  color: 'rgba(255,255,255,0.95)',
                  fontSize: 16,
                  lineHeight: 1.5,
                  wordBreak: 'break-word',
                  whiteSpace: 'pre-wrap'
                }}>
                  {res.text}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="pv-center-fill" style={{ minHeight: '200px' }}>
            <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: 16, margin: 0 }}>
              {t('quizPresent.waitingForResponses', { defaultValue: 'Waiting for responses…' })}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Word Cloud Question ─────────────────────────────── */
function WordCloudView({ question, wordCloudData, questionNumber, totalQuestions, t }) {
  const total = question.total_answers || 0
  return (
    <div className="pv-question-wrap">
      <div className="pv-question-meta">
        <Tag color="purple" style={{ fontSize: 13, padding: '2px 10px' }}>
          {t('quiz.question')} {questionNumber} {t('quiz.of')} {totalQuestions}
        </Tag>
        <Tag color="purple">{t('quiz.wordCloud')}</Tag>
        {total > 0 && (
          <Tag color="default" style={{ fontSize: 12 }}>
            {t('quizPresent.submissionsCount', { count: total })}
          </Tag>
        )}
      </div>

      {question.question_image_url && (
        <div className="pv-question-img-wrap">
          <img src={question.question_image_url} alt={t('quiz.question')} className="pv-question-img" />
        </div>
      )}

      <RichTextRenderer content={question.text || question.question_text} isDark={true} className="pv-question-text" />

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
              {t('quizPresent.waitingForResponses', { defaultValue: 'Waiting for responses…' })}
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

function EndedView({ leaderboard, t, onClose }) {
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
        <h2 className="pv-ended-title">{t('quizPresent.finalLeaderboard', { defaultValue: 'Final Leaderboard' })}</h2>
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
            const isSecond = actualIdx === 1
            return (
              <div
                key={entry.participant_id}
                className={`pv-podium-card${isFirst ? ' pv-podium-card-first' : isSecond ? ' pv-podium-card-second' : ''}`}
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
        <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 16 }}>{t('quizPresent.noScoresToDisplay', { defaultValue: 'No scores to display' })}</p>
      )}

      <div style={{ textAlign: 'center', marginTop: 32 }}>
        <p style={{ color: 'rgba(255,255,255,0.55)', marginBottom: 12, fontSize: 15 }}>
          {t('quizPresent.thanksForParticipating', { defaultValue: 'Thanks for participating.' })}
        </p>
        <button className="pv-close-window-btn" onClick={onClose}>
          {t('quizPresent.closeWindow', { defaultValue: 'Close this window' })}
        </button>
      </div>
    </div>
  )
}

/* ── Full Leaderboard Lightbox ───────────────────────── */
const MODAL_MEDALS = ['🥇', '🥈', '🥉']
const RANK_COLORS = ['#ffd700', '#c0c0c0', '#cd7f32']

function LeaderboardModal({ leaderboard, onClose, t }) {
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
            <span>{t('quizPresent.fullLeaderboard', { defaultValue: 'Full Leaderboard' })}</span>
            {leaderboard?.mcq_question_count > 1 && (
              <span className="pv-lb-panel-meta">
                {t('quizPresent.mcqQuestionsCount', { count: leaderboard.mcq_question_count })}
              </span>
            )}
          </div>
          <button className="pv-lb-panel-close" onClick={onClose} aria-label={t('common.cancel')}>✕</button>
        </div>

        {/* Table */}
        <div className="pv-lb-panel-body">
          {entries.length === 0 ? (
            <p className="pv-lb-empty">{t('quizPresent.noScoresYetKeepPlaying', { defaultValue: 'No scores yet - keep playing!' })}</p>
          ) : (
            <table className="pv-lb-table">
              <thead>
                <tr>
                  <th className="pv-lbt-rank"><TrophyOutlined className="pv-lbt-icon" /> #</th>
                  <th className="pv-lbt-name"><UserOutlined className="pv-lbt-icon" /> {t('leaderboard.participant')}</th>
                  <th className="pv-lbt-score"><ThunderboltOutlined className="pv-lbt-icon" /> {t('leaderboard.score')}</th>
                  <th className="pv-lbt-time"><ClockCircleOutlined className="pv-lbt-icon" /> {t('leaderboard.timeTaken')}</th>
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
          {t('quizPresent.pressEscToClose', { defaultValue: 'Press Esc or click outside to close' })}
        </div>
      </div>
    </div>
  )
}

/* ── Host Control Bar ───────────────────────────────── */
function ControlBar({
  currentQIdx,
  totalQ,
  loading,
  onAdvance,
  onBack,
  onStop,
  onToggleHelp,
  onToggleWhiteboard,
  onToggleWhiteboardEraser,
  onClearWhiteboard,
  whiteboardEnabled,
  whiteboardEraser,
  whiteboardColor,
  whiteboardSize,
  onWhiteboardSizeChange,
  onWhiteboardColorChange,
  revealed,
  isPoll,
  t,
}) {
  const notStarted = currentQIdx === -1
  const isLastQ = !notStarted && currentQIdx >= totalQ - 1
  const prevDisabled = loading || notStarted || currentQIdx <= 0
  const [confirmStop, setConfirmStop] = useState(false)

  let advanceLabel, advanceTitle
  if (loading) {
    advanceLabel = '…'
    advanceTitle = ''
  } else if (notStarted) {
    advanceLabel = `▶ ${t('quiz.startQuiz')}`
    advanceTitle = t('quiz.startQuiz')
  } else if (revealed) {
    advanceLabel = isLastQ ? <>{t('quizPresent.end')} <CheckOutlined /></> : <>{t('quizPresent.continue')} <RightOutlined /></>
    advanceTitle = isLastQ ? t('quiz.endSession') : t('quiz.nextQuestion')
  } else {
    advanceLabel = isLastQ ? `${t('quiz.finish')} ✓` : (isPoll ? t('quizPresent.showStats', { defaultValue: 'Show stats' }) : <RightOutlined />)
    advanceTitle = isPoll ? t('quizPresent.showStats', { defaultValue: 'Show stats' }) : t('quizPresent.revealAnswer', { defaultValue: 'Reveal answer' })
  }

  return (
    <div className="pv-ctrl-bar">
      {confirmStop ? (
        <>
          <button className="pv-ctrl-btn pv-ctrl-stop-confirm pv-ctrl-confirm-wide" onClick={onStop} disabled={loading}>
            {t('quizPresent.confirmStop', { defaultValue: 'Confirm Stop' })}
          </button>
          <button className="pv-ctrl-btn pv-ctrl-cancel" onClick={() => setConfirmStop(false)}>
            {t('common.cancel')}
          </button>
        </>
      ) : (
        <>
          <button className="pv-ctrl-btn pv-ctrl-nav-back" onClick={onBack} disabled={prevDisabled} title={t('quiz.previousQuestion')}>
            <LeftOutlined />
          </button>
          <button
            className={`pv-ctrl-btn pv-ctrl-primary${revealed ? ' pv-ctrl-continue' : ''}`}
            onClick={onAdvance}
            disabled={loading}
            title={advanceTitle}
          >
            {advanceLabel}
            {' '}<kbd className="pv-kbd">→ / Space</kbd>
          </button>
          <button className="pv-ctrl-btn pv-ctrl-stop" onClick={() => setConfirmStop(true)}>
            ■ {t('quizPresent.stop', { defaultValue: 'Stop' })}
          </button>
          <button className="pv-ctrl-btn pv-ctrl-help" onClick={onToggleHelp} title={t('quizPresent.keyboardShortcuts', { defaultValue: 'Keyboard shortcuts' })}>
            ?
          </button>
          <button
            className={`pv-ctrl-btn pv-ctrl-whiteboard-toggle${whiteboardEnabled ? ' pv-ctrl-whiteboard-toggle-active' : ''}`}
            onClick={onToggleWhiteboard}
            title={t('quizPresent.toggleWhiteboard', { defaultValue: 'Toggle whiteboard' })}
          >
            ✎ {t('quizPresent.whiteboard', { defaultValue: 'Whiteboard' })}
          </button>
          {whiteboardEnabled && (
            <div className="pv-whiteboard-controls">
              <button
                className={`pv-ctrl-btn pv-ctrl-whiteboard-tool${whiteboardEraser ? ' pv-ctrl-whiteboard-tool-active' : ''}`}
                onClick={onToggleWhiteboardEraser}
                title={t('quizPresent.eraser', { defaultValue: 'Eraser' })}
              >
                {t('quizPresent.eraser', { defaultValue: 'Eraser' })}
              </button>
              <button
                className="pv-ctrl-btn pv-ctrl-whiteboard-clear"
                onClick={onClearWhiteboard}
                title={t('quizPresent.clearWhiteboard', { defaultValue: 'Clear whiteboard' })}
              >
                {t('quizPresent.clear', { defaultValue: 'Clear' })}
              </button>
              <input
                className="pv-whiteboard-size"
                type="range"
                min={2}
                max={20}
                value={whiteboardSize}
                onChange={e => onWhiteboardSizeChange(Number(e.target.value))}
                title={t('quizPresent.brushSize', { defaultValue: 'Brush size' })}
              />
              <div className="pv-whiteboard-palette" aria-label={t('quizPresent.brushColor', { defaultValue: 'Brush color' })}>
                {WHITEBOARD_COLORS.map(color => (
                  <button
                    key={color}
                    className={`pv-whiteboard-color${whiteboardColor === color ? ' pv-whiteboard-color-active' : ''}`}
                    style={{ background: color }}
                    onClick={() => onWhiteboardColorChange(color)}
                    title={color}
                    aria-label={t('quizPresent.selectColor', { defaultValue: 'Select color' })}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

/* ── Compact Leaderboard (sidebar) ───────────────────── */
const CLB_MEDALS = ['🥇', '🥈', '🥉']

function CompactLeaderboard({ entries, total, onExpand, t }) {
  if (!entries || entries.length === 0) return null
  const top5 = entries.slice(0, 5)
  return (
    <div className="pv-clb-wrap">
      <div className="pv-clb-header">
        <TrophyOutlined style={{ fontSize: 11, color: '#faad14' }} />
        <span>{t('quizPresent.liveStandings', { defaultValue: 'Live Standings' })}</span>
        <button className="pv-clb-expand-icon" onClick={onExpand} title={t('quizPresent.viewFullLeaderboard', { defaultValue: 'View full leaderboard' })}>
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
          {t('quizPresent.viewAllParticipants', { count: total })}
        </button>
      )}
    </div>
  )
}

/* ── Sidebar ─────────────────────────────────────────── */
function Sidebar({ quizTitle, joinCode, joinUrl, participantCount, leaderboard, onExpandLeaderboard, isPoll, t }) {
  const [qrModalOpen, setQrModalOpen] = useState(false)

  return (
    <aside className="pv-sidebar">
      <div className="pv-sidebar-title">
        <span>{quizTitle}</span>
        <BetaBadge />
      </div>

      {joinCode && (
        <>
          <div className="pv-sidebar-divider" />
          <div className="pv-qr-wrap">
            <div
              style={{ position: 'relative', display: 'inline-block', cursor: 'pointer' }}
              onClick={() => setQrModalOpen(true)}
              title={t('quizPresent.expandQr', { defaultValue: 'Click to enlarge QR code' })}
            >
              <QRCodeCanvas value={joinUrl} size={164} level="H" includeMargin={false} />
              <span style={{
                position: 'absolute', bottom: 4, right: 4,
                background: 'rgba(0,0,0,0.45)', borderRadius: 4,
                color: '#fff', fontSize: 12, padding: '2px 4px', lineHeight: 1,
                pointerEvents: 'none',
              }}>
                <FullscreenOutlined />
              </span>
            </div>
            <span className="pv-qr-label">{t('quizPresent.scanToJoin', { defaultValue: 'Scan to join' })}</span>
          </div>
          <Modal
            open={qrModalOpen}
            onCancel={() => setQrModalOpen(false)}
            footer={null}
            centered
            title={t('quizPresent.scanToJoin', { defaultValue: 'Scan to join' })}
            width={480}
          >
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <QRCodeCanvas value={joinUrl} size={380} level="H" includeMargin={true} />
              <div style={{ marginTop: 12, fontSize: 14, color: '#666', wordBreak: 'break-all' }}>{joinUrl}</div>
            </div>
          </Modal>
          <div className="pv-join-code-wrap">
            <span className="pv-join-code-label">{t('quiz.joinCode')}</span>
            <span className="pv-join-code">{joinCode}</span>
            <span className="pv-join-host">{window.location.hostname}</span>
          </div>
        </>
      )}

      <div className="pv-sidebar-divider" />

      <div className="pv-participants">
        <TeamOutlined className="pv-participants-icon" />
        <span className="pv-participants-count">{participantCount}</span>
        <span className="pv-participants-label">{t('quiz.participants')}</span>
      </div>

      {!isPoll && leaderboard?.entries?.some(e => e.score > 0) && (
        <>
          <div className="pv-sidebar-divider" />
          <CompactLeaderboard
            entries={leaderboard.entries}
            total={leaderboard.total_participants}
            onExpand={onExpandLeaderboard}
            t={t}
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
  const { t } = useTranslation()
  const joinCode = searchParams.get('code') || ''

  const [results, setResults] = useState(null)
  const [leaderboard, setLeaderboard] = useState(null)
  const [wordCloudData, setWordCloudData] = useState([])
  const [ctrlLoading, setCtrlLoading] = useState(false)
  const [showLbModal, setShowLbModal] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const [timerRemaining, setTimerRemaining] = useState(null)
  const [whiteboardEnabled, setWhiteboardEnabled] = useState(false)
  const [whiteboardEraser, setWhiteboardEraser] = useState(false)
  const [whiteboardColor, setWhiteboardColor] = useState(WHITEBOARD_COLORS[0])
  const [whiteboardSize, setWhiteboardSize] = useState(5)
  const [whiteboardImageData, setWhiteboardImageData] = useState(null)
  const prevQIdx = useRef(-2)
  const whiteboardCanvasRef = useRef(null)
  const whiteboardIsDrawingRef = useRef(false)
  const whiteboardLastUpdatedAtRef = useRef(0)
  const whiteboardPushInFlightRef = useRef(false)
  const whiteboardPushQueuedRef = useRef(false)
  const whiteboardLastPushAtRef = useRef(0)

  // Host controls are shown only when a JWT token is present in this browser
  const isHost = !!localStorage.getItem('token')
  const isPoll = results?.quiz_type === 'poll'

  const joinUrl = joinCode ? `${window.location.origin}/join/${joinCode}` : ''

  const refreshResults = async () => {
    try {
      const res = await sessionAPI.getResults(Number(sessionId))
      setResults(res.data)
      prevQIdx.current = res.data.current_question_index
    } catch (_) {}
    if (!isPoll) {
      try {
        const lb = await sessionAPI.getLeaderboard(Number(sessionId))
        setLeaderboard(lb.data)
      } catch (_) {}
    } else {
      setLeaderboard(null)
    }
  }

  const handleAdvance = async () => {
    const notStarted = (results?.current_question_index ?? -1) === -1
    const isOptionQuestion = ['mcq', 'scale'].includes(results?.current_question?.question_type)
    const hasCorrectAnswer =
      results?.current_question?.correct_answer_index !== null
      && results?.current_question?.correct_answer_index !== undefined
    const isRevealQuestion = isOptionQuestion && (isPoll || hasCorrectAnswer)
    // First press on option questions: reveal answer (quiz) or show stats (poll), don't advance yet
    if (!notStarted && !revealed && isRevealQuestion) {
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

  const resizeWhiteboardCanvas = () => {
    const canvas = whiteboardCanvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const nextWidth = Math.max(1, Math.floor(rect.width))
    const nextHeight = Math.max(1, Math.floor(rect.height))
    if (canvas.width === nextWidth && canvas.height === nextHeight) return

    const snapshot = (canvas.width > 0 && canvas.height > 0) ? canvas.toDataURL('image/png') : null
    canvas.width = nextWidth
    canvas.height = nextHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'

    if (snapshot) {
      const img = new Image()
      img.onload = () => ctx.drawImage(img, 0, 0, nextWidth, nextHeight)
      img.src = snapshot
    }
  }

  const clearWhiteboard = () => {
    const canvas = whiteboardCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
  }

  const captureWhiteboardImage = () => {
    const canvas = whiteboardCanvasRef.current
    if (!canvas || canvas.width <= 0 || canvas.height <= 0) return null
    return canvas.toDataURL('image/png')
  }

  const drawWhiteboardImage = (imageData) => {
    const canvas = whiteboardCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    if (!imageData) return
    const img = new Image()
    img.onload = () => ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    img.src = imageData
  }

  const syncWhiteboardState = async (enabled, imageData, questionIndexOverride) => {
    if (!isHost) return
    const questionIndex = questionIndexOverride ?? (results?.current_question_index ?? -1)
    try {
      const res = await sessionAPI.updateWhiteboardState(Number(sessionId), {
        question_index: questionIndex,
        enabled,
        image_data: imageData,
      })
      const updatedAt = Date.parse(String(res?.data?.updated_at || ''))
      if (!Number.isNaN(updatedAt)) {
        whiteboardLastUpdatedAtRef.current = Math.max(whiteboardLastUpdatedAtRef.current, updatedAt)
      }
    } catch (_) {}
  }

  const pushWhiteboardStateThrottled = (force = false) => {
    if (!isHost || !whiteboardEnabled) return
    const now = Date.now()
    if (!force && now - whiteboardLastPushAtRef.current < WHITEBOARD_PUSH_INTERVAL_MS) return

    if (whiteboardPushInFlightRef.current) {
      whiteboardPushQueuedRef.current = true
      return
    }

    whiteboardPushInFlightRef.current = true
    whiteboardLastPushAtRef.current = now
    const imageData = captureWhiteboardImage()
    setWhiteboardImageData(imageData)

    syncWhiteboardState(whiteboardEnabled, imageData)
      .finally(() => {
        whiteboardPushInFlightRef.current = false
        if (whiteboardPushQueuedRef.current) {
          whiteboardPushQueuedRef.current = false
          pushWhiteboardStateThrottled(true)
        }
      })
  }

  const fetchWhiteboardState = async () => {
    if (!isHost && !joinCode) return
    try {
      const res = isHost
        ? await sessionAPI.getWhiteboardState(Number(sessionId))
        : await sessionAPI.getPublicWhiteboardState(Number(sessionId), joinCode)
      const state = res.data
      const updatedAt = Date.parse(String(state.updated_at || ''))
      const effectiveUpdatedAt = Number.isNaN(updatedAt) ? 0 : updatedAt
      if (effectiveUpdatedAt && effectiveUpdatedAt < whiteboardLastUpdatedAtRef.current) return
      if (effectiveUpdatedAt) whiteboardLastUpdatedAtRef.current = effectiveUpdatedAt
      setWhiteboardEnabled(Boolean(state.enabled))
      setWhiteboardImageData(state.image_data || null)
    } catch (_) {}
  }

  const handleToggleWhiteboard = () => {
    const nextEnabled = !whiteboardEnabled
    const imageData = captureWhiteboardImage() || whiteboardImageData
    setWhiteboardEnabled(nextEnabled)
    setWhiteboardImageData(imageData || null)
    syncWhiteboardState(nextEnabled, imageData || null)
  }

  const handleClearWhiteboard = () => {
    clearWhiteboard()
    setWhiteboardImageData(null)
    syncWhiteboardState(whiteboardEnabled, null)
  }

  const getPointerPoint = (event) => {
    const canvas = whiteboardCanvasRef.current
    if (!canvas) return null
    const rect = canvas.getBoundingClientRect()
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    }
  }

  const startWhiteboardDraw = (event) => {
    const canvas = whiteboardCanvasRef.current
    if (!canvas || !whiteboardEnabled) return
    const ctx = canvas.getContext('2d')
    const point = getPointerPoint(event)
    if (!ctx || !point) return

    event.preventDefault()
    canvas.setPointerCapture?.(event.pointerId)
    whiteboardIsDrawingRef.current = true
    ctx.globalCompositeOperation = whiteboardEraser ? 'destination-out' : 'source-over'
    ctx.lineWidth = whiteboardEraser ? whiteboardSize * 2 : whiteboardSize
    ctx.strokeStyle = whiteboardColor
    ctx.beginPath()
    ctx.moveTo(point.x, point.y)
  }

  const continueWhiteboardDraw = (event) => {
    if (!whiteboardIsDrawingRef.current || !whiteboardEnabled) return
    const canvas = whiteboardCanvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const point = getPointerPoint(event)
    if (!ctx || !point) return

    event.preventDefault()
    ctx.lineTo(point.x, point.y)
    ctx.stroke()
    pushWhiteboardStateThrottled()
  }

  const stopWhiteboardDraw = (event) => {
    if (!whiteboardIsDrawingRef.current) return
    whiteboardIsDrawingRef.current = false
    whiteboardCanvasRef.current?.releasePointerCapture?.(event.pointerId)
    const imageData = captureWhiteboardImage()
    setWhiteboardImageData(imageData)
    pushWhiteboardStateThrottled(true)
  }

  useEffect(() => {
    if (!whiteboardEnabled) return undefined
    resizeWhiteboardCanvas()
    window.addEventListener('resize', resizeWhiteboardCanvas)
    return () => window.removeEventListener('resize', resizeWhiteboardCanvas)
  }, [whiteboardEnabled])

  useEffect(() => {
    if (!whiteboardEnabled) return
    resizeWhiteboardCanvas()
    drawWhiteboardImage(whiteboardImageData)
  }, [whiteboardEnabled, whiteboardImageData])

  useEffect(() => {
    fetchWhiteboardState()
    if (joinCode) {
      const streamUrl = sessionAPI.getPublicWhiteboardEventsUrl(Number(sessionId), joinCode)
      const eventSource = new EventSource(streamUrl)
      const onWhiteboardEvent = (event) => {
        try {
          const state = JSON.parse(event.data || '{}')
          const updatedAt = Date.parse(String(state.updated_at || ''))
          const effectiveUpdatedAt = Number.isNaN(updatedAt) ? 0 : updatedAt
          if (effectiveUpdatedAt && effectiveUpdatedAt < whiteboardLastUpdatedAtRef.current) return
          if (effectiveUpdatedAt) whiteboardLastUpdatedAtRef.current = effectiveUpdatedAt
          if (!whiteboardIsDrawingRef.current) {
            setWhiteboardEnabled(Boolean(state.enabled))
            setWhiteboardImageData(state.image_data || null)
          }
        } catch (_) {}
      }
      eventSource.addEventListener('whiteboard', onWhiteboardEvent)
      eventSource.onerror = () => {}
      return () => {
        eventSource.removeEventListener('whiteboard', onWhiteboardEvent)
        eventSource.close()
      }
    }
    const interval = setInterval(fetchWhiteboardState, WHITEBOARD_FALLBACK_POLL_MS)
    return () => clearInterval(interval)
  }, [sessionId, isHost, joinCode])

  // Keep a ref to the latest handlers so the keyboard listener never goes stale
  const ctrlRef = useRef({})
  ctrlRef.current = {
    isEnded: results?.status === 'ended',
    loading: ctrlLoading,
    advance: handleAdvance,  // already includes reveal-first logic
    back: handleBack,
    toggleLb: () => setShowLbModal(v => !v),
    toggleHelp: () => setShowHelp(v => !v),
    toggleWhiteboard: handleToggleWhiteboard,
    clearWhiteboard: handleClearWhiteboard,
    whiteboardEnabled,
    closeOverlays: () => { setShowLbModal(false); setShowHelp(false) },
  }

  useEffect(() => {
    if (!isHost) return
    const onKey = (e) => {
      const { isEnded, loading, advance, back, toggleLb, toggleHelp, toggleWhiteboard, clearWhiteboard, whiteboardEnabled: wbEnabled, closeOverlays } = ctrlRef.current
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
        case 'w': case 'W':
          toggleWhiteboard()
          break
        case 'c': case 'C':
          if (wbEnabled) clearWhiteboard()
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
        const res = await sessionAPI.getResults(Number(sessionId))
        const data = res.data
        setResults(data)

        if (!data.quiz_type || data.quiz_type !== 'poll') {
          try {
            const lb = await sessionAPI.getLeaderboard(Number(sessionId))
            setLeaderboard(lb.data)
          } catch (_) {}
        } else {
          setLeaderboard(null)
        }

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
  const hasCurrentAnswers = Number(currentQ?.total_answers ?? 0) > 0
  const liveLeaderboard = (!isEnded && leaderboard && !hasCurrentAnswers)
    ? { ...leaderboard, entries: [] }
    : leaderboard
  const isWaiting = !isEnded && (results?.current_question_index === -1 || !currentQ)
  const displayTimerRemaining = currentQ?.max_time_seconds
    ? (timerRemaining ?? Number(currentQ.max_time_seconds))
    : null

  useEffect(() => {
    if (!currentQ?.max_time_seconds || !currentQ?.timer_started_at) {
      setTimerRemaining(null)
      return
    }

    const maxSeconds = Number(currentQ.max_time_seconds)
    const rawStartedAt = String(currentQ.timer_started_at)
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
  }, [currentQ?.id, currentQ?.max_time_seconds, currentQ?.timer_started_at])

  return (
    <div className="pv-root">
      <Sidebar
        quizTitle={results?.quiz_title ?? t('quiz.createQuiz')}
        joinCode={joinCode}
        joinUrl={joinUrl}
        participantCount={participantCount}
        leaderboard={liveLeaderboard}
        onExpandLeaderboard={() => setShowLbModal(true)}
        isPoll={isPoll}
        t={t}
      />

      <main className="pv-main">
        <div className="pv-main-content">
          {!results ? (
          <div className="pv-center-fill">
            <Spin size="large" />
          </div>
        ) : isEnded ? (
          isPoll ? (
            <div className="pv-center-fill">
              <h2 className="pv-waiting-title">{t('quizPresent.pollCompleted', { defaultValue: 'Poll completed' })}</h2>
              <p className="pv-waiting-sub">{t('quizPresent.thanksForParticipating', { defaultValue: 'Thanks for participating.' })}</p>
              <button className="pv-close-window-btn" onClick={() => window.close()}>
                {t('quizPresent.closeWindow', { defaultValue: 'Close this window' })}
              </button>
            </div>
          ) : (
            <EndedView leaderboard={leaderboard} t={t} onClose={() => window.close()} />
          )
        ) : isWaiting ? (
          <WaitingView participantCount={participantCount} t={t} />
        ) : currentQ?.question_type === 'word_cloud' ? (
          <>
            {currentQ?.max_time_seconds ? (
              <div style={{ marginBottom: 12 }}>
                <Tag color="orange">{t('quiz.timerTag', { seconds: currentQ.max_time_seconds })}</Tag>
                <span style={{ marginLeft: 8, color: 'rgba(255,255,255,0.85)' }}>
                  {t('quiz.timeLeft', { seconds: displayTimerRemaining })}
                </span>
                <Progress
                  percent={Math.max(0, Math.min(100, (Number(displayTimerRemaining) / Number(currentQ.max_time_seconds)) * 100))}
                  size="small"
                  showInfo={false}
                  status={Number(displayTimerRemaining) <= 5 ? 'exception' : Number(displayTimerRemaining) <= 10 ? 'active' : 'normal'}
                  style={{ marginTop: 6 }}
                />
              </div>
            ) : null}
            <WordCloudView
              question={currentQ}
              wordCloudData={wordCloudData}
              questionNumber={qNumber}
              totalQuestions={totalQ}
              t={t}
            />
          </>
        ) : currentQ?.question_type === 'single_line' || currentQ?.question_type === 'paragraph' ? (
          <>
            {currentQ?.max_time_seconds ? (
              <div style={{ marginBottom: 12 }}>
                <Tag color="orange">{t('quiz.timerTag', { seconds: currentQ.max_time_seconds })}</Tag>
                <span style={{ marginLeft: 8, color: 'rgba(255,255,255,0.85)' }}>
                  {t('quiz.timeLeft', { seconds: displayTimerRemaining })}
                </span>
                <Progress
                  percent={Math.max(0, Math.min(100, (Number(displayTimerRemaining) / Number(currentQ.max_time_seconds)) * 100))}
                  size="small"
                  showInfo={false}
                  status={Number(displayTimerRemaining) <= 5 ? 'exception' : Number(displayTimerRemaining) <= 10 ? 'active' : 'normal'}
                  style={{ marginTop: 6 }}
                />
              </div>
            ) : null}
            <TextResponseView question={currentQ} questionNumber={qNumber} totalQuestions={totalQ} t={t} />
          </>
        ) : currentQ?.question_type === 'scale' ? (
          <>
            {currentQ?.max_time_seconds ? (
              <div style={{ marginBottom: 12 }}>
                <Tag color="orange">{t('quiz.timerTag', { seconds: currentQ.max_time_seconds })}</Tag>
                <span style={{ marginLeft: 8, color: 'rgba(255,255,255,0.85)' }}>
                  {t('quiz.timeLeft', { seconds: displayTimerRemaining })}
                </span>
                <Progress
                  percent={Math.max(0, Math.min(100, (Number(displayTimerRemaining) / Number(currentQ.max_time_seconds)) * 100))}
                  size="small"
                  showInfo={false}
                  status={Number(displayTimerRemaining) <= 5 ? 'exception' : Number(displayTimerRemaining) <= 10 ? 'active' : 'normal'}
                  style={{ marginTop: 6 }}
                />
              </div>
            ) : null}
            <ScaleView question={currentQ} questionNumber={qNumber} totalQuestions={totalQ} revealed={revealed} t={t} />
          </>
        ) : (
          <>
            {currentQ?.max_time_seconds ? (
              <div style={{ marginBottom: 12 }}>
                <Tag color="orange">{t('quiz.timerTag', { seconds: currentQ.max_time_seconds })}</Tag>
                <span style={{ marginLeft: 8, color: 'rgba(255,255,255,0.85)' }}>
                  {t('quiz.timeLeft', { seconds: displayTimerRemaining })}
                </span>
                <Progress
                  percent={Math.max(0, Math.min(100, (Number(displayTimerRemaining) / Number(currentQ.max_time_seconds)) * 100))}
                  size="small"
                  showInfo={false}
                  status={Number(displayTimerRemaining) <= 5 ? 'exception' : Number(displayTimerRemaining) <= 10 ? 'active' : 'normal'}
                  style={{ marginTop: 6 }}
                />
              </div>
            ) : null}
            <MCQView question={currentQ} questionNumber={qNumber} totalQuestions={totalQ} revealed={revealed} isPoll={isPoll} t={t} />
          </>
          )}
        </div>
        {whiteboardEnabled && (
          <canvas
            ref={whiteboardCanvasRef}
            className="pv-whiteboard-canvas"
            onPointerDown={isHost ? startWhiteboardDraw : undefined}
            onPointerMove={isHost ? continueWhiteboardDraw : undefined}
            onPointerUp={isHost ? stopWhiteboardDraw : undefined}
            onPointerLeave={isHost ? stopWhiteboardDraw : undefined}
            style={isHost ? undefined : { pointerEvents: 'none' }}
          />
        )}
      </main>

      {isHost && !isEnded && (
        <div className="pv-ctrl-footer">
          <ControlBar
            currentQIdx={results?.current_question_index ?? -1}
            totalQ={totalQ}
            loading={ctrlLoading}
            onAdvance={handleAdvance}
            onBack={handleBack}
            onStop={handleEnd}
            onToggleHelp={() => setShowHelp(v => !v)}
            onToggleWhiteboard={handleToggleWhiteboard}
            onToggleWhiteboardEraser={() => setWhiteboardEraser(v => !v)}
            onClearWhiteboard={handleClearWhiteboard}
            whiteboardEnabled={whiteboardEnabled}
            whiteboardEraser={whiteboardEraser}
            whiteboardColor={whiteboardColor}
            whiteboardSize={whiteboardSize}
            onWhiteboardSizeChange={setWhiteboardSize}
            onWhiteboardColorChange={(color) => { setWhiteboardColor(color); setWhiteboardEraser(false) }}
            revealed={revealed}
            isPoll={isPoll}
            t={t}
          />
        </div>
      )}

      {showLbModal && !isPoll && (
        <LeaderboardModal
          leaderboard={liveLeaderboard}
          onClose={() => setShowLbModal(false)}
          t={t}
        />
      )}

      {showHelp && isHost && (
        <div className="pv-help-backdrop" onClick={() => setShowHelp(false)}>
          <div className="pv-help-panel" onClick={e => e.stopPropagation()}>
            <div className="pv-help-title">{t('quizPresent.keyboardShortcuts', { defaultValue: 'Keyboard Shortcuts' })}</div>
            <table className="pv-help-table">
              <tbody>
                <tr><td><kbd>→</kbd> or <kbd>Space</kbd> or <kbd>Enter</kbd> or <kbd>PageDown</kbd></td><td>{t('quizPresent.nextQuestionShortcut', { defaultValue: 'Next question (press any one key)' })}</td></tr>
                <tr><td><kbd>←</kbd> or <kbd>Backspace</kbd> or <kbd>PageUp</kbd></td><td>{t('quizPresent.previousQuestionShortcut', { defaultValue: 'Previous question (press any one key)' })}</td></tr>
                {!isPoll && <tr><td><kbd>L</kbd></td><td>{t('quizPresent.toggleLeaderboard', { defaultValue: 'Toggle leaderboard' })}</td></tr>}
                <tr><td><kbd>W</kbd></td><td>{t('quizPresent.toggleWhiteboard', { defaultValue: 'Toggle whiteboard' })}</td></tr>
                <tr><td><kbd>C</kbd></td><td>{t('quizPresent.clearWhiteboard', { defaultValue: 'Clear whiteboard' })}</td></tr>
                <tr><td><kbd>F</kbd></td><td>{t('quizPresent.toggleFullscreen', { defaultValue: 'Toggle fullscreen' })}</td></tr>
                <tr><td><kbd>?</kbd></td><td>{t('quizPresent.showHidePanel', { defaultValue: 'Show / hide this panel' })}</td></tr>
                <tr><td><kbd>Esc</kbd></td><td>{t('quizPresent.closeOverlays', { defaultValue: 'Close overlays' })}</td></tr>
              </tbody>
            </table>
            <button className="pv-help-close" onClick={() => setShowHelp(false)}>✕ {t('quizPresent.close', { defaultValue: 'Close' })}</button>
          </div>
        </div>
      )}
    </div>
  )
}
