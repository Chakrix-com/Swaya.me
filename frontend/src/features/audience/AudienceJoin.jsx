import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { App } from 'antd'
import { sessionAPI } from '../../services/api'
import { useDispatch } from 'react-redux'
import { setSession } from '../../store/sessionSlice'
import PublicBrandHeader from '../../components/PublicBrandHeader'
import './AudienceJoin.css'

const ADJECTIVES = ['Swift', 'Clever', 'Brave', 'Calm', 'Bold', 'Keen', 'Quick', 'Wise', 'Bright', 'Sharp', 'Cool', 'Epic', 'Jazzy', 'Nifty', 'Plucky', 'Snappy', 'Zesty']
const NOUNS = ['Falcon', 'Panda', 'Comet', 'Quasar', 'Ember', 'Titan', 'Rocket', 'Nebula', 'Pixel', 'Nova', 'Lynx', 'Phoenix', 'Vortex', 'Prism', 'Cipher', 'Axiom']

function randomName() {
  const adj = ADJECTIVES[Math.floor(Math.random() * ADJECTIVES.length)]
  const noun = NOUNS[Math.floor(Math.random() * NOUNS.length)]
  return `${adj} ${noun}`
}

const MODE_LABEL = {
  quiz: 'Live Quiz',
  poll: 'Live Poll',
  offline_poll: 'Survey',
  exam: 'Test',
}
const MODE_EMOJI = {
  quiz: '\u{1F3AF}',
  poll: '\u{1F4CA}',
  offline_poll: '\u{1F4CB}',
  exam: '\u{1F4DD}',
}

function AudienceJoin() {
  const { t } = useTranslation()
  const { message } = App.useApp()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { joinCode: paramCode } = useParams()

  const [step, setStep] = useState('code')
  const [activityInfo, setActivityInfo] = useState(null)
  const [resolvedCode, setResolvedCode] = useState('')
  const [looking, setLooking] = useState(false)
  const [joining, setJoining] = useState(false)
  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const [displayName, setDisplayName] = useState('')

  const digitRefs = useRef([])
  const prevCodeRef = useRef('')
  const nameInputRef = useRef(null)

  useEffect(() => {
    if (paramCode) {
      const clean = paramCode.replace(/\D/g, '').slice(0, 6)
      const newDigits = ['', '', '', '', '', '']
      clean.split('').forEach((d, i) => { newDigits[i] = d })
      setDigits(newDigits)
      if (clean.length === 6) {
        handleLookup(clean)
      }
    }
  }, [paramCode]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleLookup = async (code) => {
    const clean = (code || digits.join('')).replace(/\D/g, '').slice(0, 6)
    if (clean.length < 6) return
    if (clean === prevCodeRef.current && step === 'name') return
    prevCodeRef.current = clean
    setLooking(true)
    try {
      const res = await sessionAPI.lookup(clean)
      setActivityInfo(res.data)
      setResolvedCode(clean)
      setDisplayName(randomName())
      setStep('name')
      setTimeout(() => nameInputRef.current?.focus(), 100)
    } catch {
      message.error(t('audience.invalidCode', { defaultValue: 'No active session found for that code.' }))
    } finally {
      setLooking(false)
    }
  }

  const handleJoin = async () => {
    setJoining(true)
    try {
      const response = await sessionAPI.join({
        join_code: resolvedCode,
        display_name: displayName?.trim() || undefined,
      })
      dispatch(setSession(response.data))
      navigate(`/session/${response.data.session_id}`, {
        state: {
          sessionToken: response.data.session_token,
          sessionId: response.data.session_id,
          displayName: displayName || t('audience.anonymous', { defaultValue: 'Anonymous' }),
        }
      })
    } catch (error) {
      message.error(error.response?.data?.detail || t('common.error'))
    } finally {
      setJoining(false)
    }
  }

  const handleDigitChange = (index, value) => {
    const digit = value.replace(/\D/g, '').slice(-1)
    const newDigits = [...digits]
    newDigits[index] = digit
    setDigits(newDigits)

    if (digit && index < 5) {
      digitRefs.current[index + 1]?.focus()
    }

    const code = newDigits.join('')
    if (code.length === 6 && newDigits.every(d => d !== '')) {
      handleLookup(code)
    }
  }

  const handleDigitKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      digitRefs.current[index - 1]?.focus()
    }
    if (e.key === 'Enter') {
      const code = digits.join('')
      if (code.length === 6) handleLookup(code)
    }
  }

  const handleDigitPaste = (e) => {
    e.preventDefault()
    const pasted = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6)
    const newDigits = ['', '', '', '', '', '']
    pasted.split('').forEach((d, i) => { newDigits[i] = d })
    setDigits(newDigits)

    if (pasted.length >= 6) {
      handleLookup(pasted)
    } else {
      digitRefs.current[Math.min(pasted.length, 5)]?.focus()
    }
  }

  const handleNameKeyDown = (e) => {
    if (e.key === 'Enter') handleJoin()
  }

  const resetToCode = () => {
    setStep('code')
    setActivityInfo(null)
    prevCodeRef.current = ''
    setDigits(['', '', '', '', '', ''])
    setTimeout(() => digitRefs.current[0]?.focus(), 100)
  }

  const quizType = activityInfo?.quiz_type

  return (
    <div className={`aj-page${quizType ? ` aj-page--${quizType}` : ''}`}>
      <PublicBrandHeader />
      <div className="aj-body">

        {step === 'code' && (
          <div className="aj-card" key="code">
            <h1 className="aj-heading">{t('audience.joinQuiz')}</h1>
            <p className="aj-subtext">
              {t('audience.enterSixDigitCode', { defaultValue: 'Enter the 6-digit code shown on screen' })}
            </p>

            <div className="aj-digits" onPaste={handleDigitPaste}>
              {digits.map((d, i) => (
                <input
                  key={i}
                  ref={el => { digitRefs.current[i] = el }}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={2}
                  value={d}
                  className={`aj-digit${d ? ' aj-digit--filled' : ''}`}
                  onChange={(e) => handleDigitChange(i, e.target.value)}
                  onKeyDown={(e) => handleDigitKeyDown(i, e)}
                  autoFocus={i === 0}
                  aria-label={`Digit ${i + 1}`}
                />
              ))}
            </div>

            <button
              className="aj-btn aj-btn--primary"
              onClick={() => handleLookup()}
              disabled={digits.join('').length < 6 || looking}
            >
              {looking ? <span className="aj-spinner" /> : t('audience.continue', { defaultValue: 'Continue' })}
            </button>
          </div>
        )}

        {step === 'name' && (
          <div className="aj-card aj-card--name" key="name">
            <div className="aj-preview">
              <span className="aj-mode-badge">
                {MODE_EMOJI[quizType]} {t(`audience.mode.${quizType}`, { defaultValue: MODE_LABEL[quizType] || quizType })}
              </span>
              <h2 className="aj-quiz-title">{activityInfo?.quiz_title}</h2>
              {activityInfo?.participant_count > 0 && (
                <p className="aj-participant-count">
                  {t('audience.othersHere', { count: activityInfo.participant_count, defaultValue: `${activityInfo.participant_count} others here` })}
                </p>
              )}
            </div>

            <div className="aj-name-section">
              <label className="aj-label">{t('audience.displayName')}</label>
              <div className="aj-name-row">
                <input
                  ref={nameInputRef}
                  type="text"
                  className="aj-input"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  onKeyDown={handleNameKeyDown}
                  placeholder={t('audience.displayNameOptional', { defaultValue: 'Your name (anonymous if blank)' })}
                  maxLength={40}
                />
                <button
                  className="aj-btn aj-btn--reroll"
                  onClick={() => setDisplayName(randomName())}
                  title={t('audience.rerollName', { defaultValue: 'Suggest a random name' })}
                  type="button"
                >
                  🎲
                </button>
              </div>
            </div>

            <button
              className="aj-btn aj-btn--primary aj-btn--join"
              onClick={handleJoin}
              disabled={joining}
            >
              {joining ? <span className="aj-spinner" /> : t('audience.join')}
            </button>

            <button className="aj-btn aj-btn--link" onClick={resetToCode}>
              {t('audience.changeCode', { defaultValue: '← Change code' })}
            </button>
          </div>
        )}

      </div>
    </div>
  )
}

export default AudienceJoin
