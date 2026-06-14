import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import logo from '../../assets/logo.png'
import LanguageSwitcher from '../../components/LanguageSwitcher'
import BetaBadge from '../../components/BetaBadge'
import OpenSourceBadge from '../../components/OpenSourceBadge'
import ThemePicker from '../../components/ThemePicker'
import './Home.css'

const MODES = ['try', 'quiz', 'poll', 'test']

// ── buzzer demo ──────────────────────────────────────────────────────────────
const BUZZ_HINT_KEYS = [
  'home.buzzer.hint1',
  'home.buzzer.hint2',
  'home.buzzer.hint3',
  'home.buzzer.hint4',
  'home.buzzer.hint5',
]
function BuzzerDemo() {
  const { t } = useTranslation()
  const [count, setCount] = useState(12407)
  const [best, setBest] = useState(0.31)
  const [hintKey, setHintKey] = useState(BUZZ_HINT_KEYS[0])
  const [speech, setSpeech] = useState('')
  const [speechVisible, setSpeechVisible] = useState(false)
  const [pressed, setPressed] = useState(false)
  const [confetti, setConfetti] = useState([])
  const pressesRef = useRef(0)
  const speechTimer = useRef(null)

  const handleBuzz = () => {
    pressesRef.current += 1
    const presses = pressesRef.current
    const newCount = count + 1
    setCount(newCount)
    const sec = parseFloat((0.28 + Math.random() * 0.9).toFixed(2))
    let msg = t('home.buzzer.speechBuzz', { time: sec })
    if (sec < best) { setBest(sec); msg = t('home.buzzer.speechRecord', { time: sec }) }
    setSpeech(msg)
    setSpeechVisible(true)
    setHintKey(BUZZ_HINT_KEYS[Math.min(presses, BUZZ_HINT_KEYS.length - 1)])
    clearTimeout(speechTimer.current)
    speechTimer.current = setTimeout(() => setSpeechVisible(false), 1400)
    setPressed(true)
    setTimeout(() => setPressed(false), 90)
    const pieces = Array.from({ length: 14 }, (_, i) => ({
      id: Date.now() + i,
      angle: Math.random() * Math.PI * 2,
      dist: 80 + Math.random() * 100,
      rot: Math.random() * 540 - 270,
      color: ['var(--pub-quiz)', 'var(--pub-poll)', 'var(--pub-test)', 'var(--pub-opoll)', '#FFD43A'][i % 5],
      circle: Math.random() < 0.4,
    }))
    setConfetti(pieces)
    setTimeout(() => setConfetti([]), 1200)
  }

  return (
    <div className="pub-demo pub-buzzer-demo" role="tabpanel">
      <div className="pub-buzzer-zone">
        <div className={`pub-speech${speechVisible ? ' pub-speech--show' : ''}`}>{speech}</div>
        <div className="pub-buzzer-base">
          <button
            className={`pub-buzzer${pressed ? ' pub-buzzer--pressed' : ''}`}
            aria-label={t('home.buzzer.ariaLabel')}
            onClick={handleBuzz}
          >
            {t('home.buzzer.pressMe')}
          </button>
          <div className="pub-buzz-stats">
            <div>
              <span className="pub-buzz-big pub-buzz-big--red">{count.toLocaleString('en-IN')}</span>
              {t('home.buzzer.buzzesToday')}
            </div>
            <div>
              <span className="pub-buzz-big pub-buzz-big--blue">{best}s</span>
              {t('home.buzzer.fastestBuzz')}
            </div>
          </div>
          <div className="pub-buzz-hint">{t(hintKey)}</div>
        </div>
        {confetti.map(p => (
          <div
            key={p.id}
            className="pub-confetti"
            style={{
              background: p.color,
              borderRadius: p.circle ? '50%' : undefined,
              '--dx': `${Math.cos(p.angle) * p.dist}px`,
              '--dy': `${Math.sin(p.angle) * p.dist - 60}px`,
              '--rot': `${p.rot}deg`,
            }}
          />
        ))}
      </div>
    </div>
  )
}

// ── animated quiz bars ──────────────────────────────────────────────────────
function QuizDemo() {
  const { t } = useTranslation()
  const [votes, setVotes] = useState([0, 0, 0, 0])
  const [total, setTotal] = useState(0)
  const [secs, setSecs] = useState(14)
  const [count, setCount] = useState(112)
  const W = [0.55, 0.2, 0.15, 0.1]

  useEffect(() => {
    const id = setInterval(() => {
      setVotes(prev => {
        const next = [...prev]
        let t2 = total
        const burst = 2 + Math.floor(Math.random() * 6)
        for (let b = 0; b < burst; b++) {
          const r = Math.random(); let acc = 0
          for (let i = 0; i < 4; i++) { acc += W[i]; if (r <= acc) { next[i]++; t2++; break } }
        }
        setTotal(t2)
        return next
      })
      setSecs(s => { if (s <= 0) { setVotes([0,0,0,0]); setTotal(0); return 14 } return s - 1 })
      if (Math.random() < 0.3) setCount(c => c + 1)
    }, 900)
    return () => clearInterval(id)
  }, [])

  const opts = [
    t('home.v2.demoQuizOpt1', 'Jupiter'),
    t('home.v2.demoQuizOpt2', 'Mercury'),
    t('home.v2.demoQuizOpt3', 'Mars'),
    t('home.v2.demoQuizOpt4', 'Venus'),
  ]
  const colors = ['var(--pub-quiz)', 'var(--pub-opoll)', 'var(--pub-poll)', 'var(--pub-test)']

  return (
    <div className="pub-demo pub-demo--active" id="quizDemo" role="tabpanel">
      <div className="pub-demo-top">
        <span className="pub-pill pub-pill--quiz">{t('home.v2.demoQuizPill', 'LIVE QUIZ')}</span>
        <span>{t('home.v2.demoQuizMeta', 'Question 3 of 10')}</span>
      </div>
      <h3 className="pub-demo-q">{t('home.v2.demoQuizQuestion', 'Which planet has the shortest day?')}</h3>
      {opts.map((label, i) => {
        const pct = total ? Math.max(4, (votes[i] / total) * 100) : 4
        return (
          <div className="pub-opt" key={i}>
            <div className="pub-opt-row">
              <span>{label}</span>
              <span className="pub-opt-n">{votes[i]}</span>
            </div>
            <div className="pub-bar">
              <div className="pub-bar-fill" style={{ width: `${pct.toFixed(1)}%`, background: colors[i] }} />
            </div>
          </div>
        )
      })}
      <div className="pub-demo-foot">
        <span><b>{count}</b> {t('home.v2.demoQuizAnswering', 'answering')}</span>
        <span>⏱ <b>00:{String(secs).padStart(2, '0')}</b></span>
      </div>
    </div>
  )
}

// ── word cloud poll demo ─────────────────────────────────────────────────────
const CLOUD_WORDS = [
  { text: 'challenging', cls: 's1' }, { text: 'fun', cls: 's3' }, { text: 'fast', cls: 's2' },
  { text: 'confusing', cls: 's4' }, { text: 'rewarding', cls: 's2' }, { text: 'intense', cls: 's3' },
  { text: 'growth', cls: 's1' }, { text: 'long', cls: 's4' }, { text: 'team', cls: 's3' },
  { text: 'caffeine', cls: 's4' }, { text: 'proud', cls: 's2' },
]
function PollDemo() {
  const { t } = useTranslation()
  const [words, setWords] = useState(CLOUD_WORDS)
  useEffect(() => {
    const id = setInterval(() => {
      setWords(w => { const n = [...w]; n.push(n.shift()); return n })
    }, 2400)
    return () => clearInterval(id)
  }, [])
  return (
    <div className="pub-demo" id="pollDemo" role="tabpanel">
      <div className="pub-demo-top">
        <span className="pub-pill pub-pill--poll">{t('home.v2.demoPollPill', 'LIVE POLL')}</span>
        <span>{t('home.v2.demoPollMeta', 'Word cloud')}</span>
      </div>
      <h3 className="pub-demo-q">{t('home.v2.demoPollQuestion', 'One word for how this term went?')}</h3>
      <div className="pub-cloud">
        {words.map((w, i) => <span key={w.text} className={`pub-cloud-word pub-cloud-word--${w.cls}`}>{w.text}</span>)}
      </div>
      <div className="pub-demo-foot">
        <span><b>87</b> {t('home.v2.demoPollResponses', 'responses')}</span>
        <span>{t('home.v2.demoPollLive', 'updating live')}</span>
      </div>
    </div>
  )
}

// ── test report demo ─────────────────────────────────────────────────────────
function TestDemo() {
  const { t } = useTranslation()
  const rows = [
    { q: 'Q1 · Data structures', pct: 88, flag: false },
    { q: 'Q2 · SQL joins',       pct: 76, flag: false },
    { q: 'Q3 · Recursion',       pct: 41, flag: true  },
    { q: 'Q4 · Big-O',           pct: 69, flag: false },
  ]
  return (
    <div className="pub-demo" id="testDemo" role="tabpanel">
      <div className="pub-demo-top">
        <span className="pub-pill pub-pill--test">{t('home.v2.demoTestPill', 'TEST REPORT')}</span>
        <span>{t('home.v2.demoTestMeta', 'Auto-scored · 42 candidates')}</span>
      </div>
      <h3 className="pub-demo-q">{t('home.v2.demoTestTitle', 'Unit 4 — Screening results')}</h3>
      <div className="pub-report">
        {rows.map(r => (
          <div key={r.q} className={`pub-report-row${r.flag ? ' pub-report-row--flag' : ''}`}>
            <span className="pub-report-q">{r.q}</span>
            <span className="pub-report-meter"><i style={{ width: `${r.pct}%` }} /></span>
            <span className="pub-report-pct">{r.pct}%</span>
          </div>
        ))}
      </div>
      <div className="pub-demo-foot">
        <span>{t('home.v2.demoTestAvg', 'avg score')} <b>71%</b></span>
        <span>{t('home.v2.demoTestExport', 'export: PDF · Excel')}</span>
      </div>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────
export default function Home() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [mode, setMode] = useState('try')
  const [userTouched, setUserTouched] = useState(false)
  const [joinCode, setJoinCode] = useState('')

  useEffect(() => {
    if (userTouched) return
    const id = setInterval(() => {
      setMode(m => m === 'try' ? 'quiz' : m === 'quiz' ? 'poll' : m === 'poll' ? 'test' : 'try')
    }, 6000)
    return () => clearInterval(id)
  }, [userTouched])

  const selectMode = (m) => { setUserTouched(true); setMode(m) }

  const handleJoin = () => {
    if (joinCode.trim()) navigate(`/join/${joinCode.trim()}`)
  }

  return (
    <div className="pub-page">
      <div className="pub-wash" aria-hidden="true" />

      <div className="pub-wrap">
        {/* ── nav ── */}
        <nav className="pub-nav">
          <a className="pub-logo" href="/" onClick={e => { e.preventDefault(); navigate('/') }}>
            <img src={logo} alt="Swaya.me" className="pub-logo-img" />
            Swaya.me
            <BetaBadge />
          </a>
          <div className="pub-nav-actions">
            <OpenSourceBadge />
            <ThemePicker />
            <LanguageSwitcher />
            <button className="pub-btn pub-btn--ghost pub-btn--sm" onClick={() => navigate('/login')}>
              {t('home.login', 'Log in')}
            </button>
            <button className="pub-btn pub-btn--sm" onClick={() => navigate('/register')}>
              {t('home.v2.startFree', 'Start free')}
            </button>
          </div>
        </nav>

        {/* ── hero ── */}
        <header className="pub-hero">
          <div className="pub-hero-left">
            <span className="pub-kicker">
              <span className="pub-kicker-dot" aria-hidden="true" />
              {t('home.v2.kicker', 'Live · quizzes · polls · tests')}
            </span>
            <h1 className="pub-h1">
              {t('home.v2.heroTitle1', 'One room.')}<br />
              <em>{t('home.v2.heroTitle2', 'Every voice.')}</em>
            </h1>
            <p className="pub-lede">{t('home.v2.lede', 'Swaya turns any audience into participants. Run a quiz when you want energy, a poll when you want honesty, a test when it counts — everyone joins from their phone with one code.')}</p>
            <div className="pub-hero-ctas">
              <button className="pub-btn" onClick={() => navigate('/register')}>
                {t('home.v2.ctaPrimary', 'Create your first session — free')}
              </button>
              <button className="pub-btn pub-btn--ghost" onClick={() => navigate('/login')}>
                {t('home.v2.ctaSecondary', 'See it live')}
              </button>
            </div>
            <div className="pub-join-chip">
              <span className="pub-join-code">RX4-92K</span>
              <span className="pub-join-label">
                {t('home.v2.joinLabel', 'Got a code from a host? Type it here — no app, no account.')}
              </span>
            </div>
          </div>

          <div className="pub-stage">
            <div className="pub-beam" aria-hidden="true" />
            <div className="pub-mode-tabs" role="tablist" aria-label="Session modes">
              {MODES.map(m => (
                <button
                  key={m}
                  className={`pub-mode-tab pub-mode-tab--${m}${mode === m ? ' pub-mode-tab--active' : ''}`}
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => selectMode(m)}
                >
                  {m === 'try' ? (t('home.v2.tab_try', 'Try it ⚡')) : t(`home.v2.tab_${m}`, m.charAt(0).toUpperCase() + m.slice(1))}
                </button>
              ))}
            </div>
            <div className="pub-demo-wrap">
              {mode === 'try'  && <BuzzerDemo />}
              {mode === 'quiz' && <QuizDemo />}
              {mode === 'poll' && <PollDemo />}
              {mode === 'test' && <TestDemo />}
            </div>
          </div>
        </header>

        {/* ── modes section ── */}
        <section id="modes" className="pub-section">
          <div className="pub-sec-head">
            <div className="pub-sec-eyebrow">{t('home.v2.modesEyebrow', 'Three instruments')}</div>
            <h2 className="pub-h2">{t('home.v2.modesTitle1', 'Same room, same code —')} <em>{t('home.v2.modesTitle2', 'different jobs')}</em></h2>
            <p>{t('home.v2.modesSub', 'One platform, three modes. Pick the one the moment needs.')}</p>
          </div>
          <div className="pub-modes">
            {[
              { key: 'quiz', title: t('home.v2.quizCardTitle', 'When you want energy'), desc: t('home.v2.quizCardDesc', 'Timed questions, points for speed and accuracy, a leaderboard that reshuffles live.'), forText: t('home.v2.quizCardFor', 'teachers, trainers, event hosts') },
              { key: 'poll', title: t('home.v2.pollCardTitle', 'When you want honesty'), desc: t('home.v2.pollCardDesc', 'Opinion polls, word clouds, pulse checks — anonymous by default, visualised as they arrive.'), forText: t('home.v2.pollCardFor', 'team leads, town halls, webinars') },
              { key: 'test', title: t('home.v2.testCardTitle', 'When it counts'), desc: t('home.v2.testCardDesc', 'Timed assessments with auto-grading, webcam snapshots, per-question analytics and exportable reports.'), forText: t('home.v2.testCardFor', 'institutes, hiring rounds, certification') },
            ].map(({ key, title, desc, forText }) => (
              <div key={key} className={`pub-mode-card pub-mode-card--${key}`}>
                <span className="pub-mode-tag">{t(`home.v2.tab_${key}`, key)}</span>
                <h3>{title}</h3>
                <p>{desc}</p>
                <p className="pub-mode-for">{t('home.v2.forLabel', 'For')} <b>{forText}</b></p>
              </div>
            ))}
          </div>
        </section>

        {/* ── how it works ── */}
        <section id="how" className="pub-section">
          <div className="pub-sec-head">
            <div className="pub-sec-eyebrow">{t('home.v2.howEyebrow', 'How it works')}</div>
            <h2 className="pub-h2">{t('home.v2.howTitle1', 'Five minutes from idea to')} <em>{t('home.v2.howTitle2', 'everyone in')}</em></h2>
          </div>
          <div className="pub-steps">
            {[
              { title: t('home.v2.step1Title', 'Build'), desc: t('home.v2.step1Desc', 'Write questions in the editor, import a spreadsheet, or let AI draft them.') },
              { title: t('home.v2.step2Title', 'Share'), desc: <>{t('home.v2.step2DescA', 'Every session gets a short code like')} <span className="pub-mono">RX4-92K</span>. {t('home.v2.step2DescB', 'On the projector, in the chat, on the wall.')}</> },
              { title: t('home.v2.step3Title', 'Run'), desc: t('home.v2.step3Desc', 'Answers stream in live. Quizzes get a leaderboard, polls get a picture of the room, tests get a full report.') },
            ].map(({ title, desc }) => (
              <div key={title} className="pub-step">
                <h3>{title}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── trust ── */}
        <section id="trust" className="pub-section">
          <div className="pub-trust">
            <div>
              <div className="pub-sec-eyebrow">{t('home.v2.trustEyebrow', 'When it counts')}</div>
              <h2 className="pub-h2">{t('home.v2.trustTitle1', 'Built to be')} <em>{t('home.v2.trustTitle2', 'trusted')}</em>{t('home.v2.trustTitle3', ', not just enjoyed')}</h2>
              <ul className="pub-trust-list">
                {[
                  { b: t('home.v2.trust1b', 'Auto-scoring with per-question analytics'), t: t('home.v2.trust1', 'see exactly where a class or candidate pool struggled.') },
                  { b: t('home.v2.trust2b', 'Webcam snapshots during tests'), t: t('home.v2.trust2', 'light-touch proctoring for screenings and exams.') },
                  { b: t('home.v2.trust3b', 'Exportable evidence'), t: t('home.v2.trust3', 'PDF, Excel, Word and PowerPoint reports the moment a session ends.') },
                  { b: t('home.v2.trust4b', 'Eleven languages'), t: t('home.v2.trust4', 'English, हिन्दी, தமிழ், తెలుగు, ಕನ್ನಡ, বাংলা, ગુજરાતી, Español, Français, Deutsch, Русский.') },
                ].map(item => (
                  <li key={item.b}><b>{item.b}</b> — {item.t}</li>
                ))}
              </ul>
            </div>
            <blockquote className="pub-quote">
              <p>"{t('home.v2.quote', 'The quiz got them excited. The report is why we kept the subscription.')}"</p>
              <cite>{t('home.v2.quoteCite', '— What we build for: both halves of that sentence')}</cite>
            </blockquote>
          </div>
        </section>

        {/* ── CTA ── */}
        <section className="pub-section">
          <div className="pub-cta">
            <h2 className="pub-h2">{t('home.v2.ctaTitle', 'The next session could be yours')}</h2>
            <p>{t('home.v2.ctaSub', 'Create a quiz, a poll, or a test now. Share the code. Watch the room light up — or settle down and focus. Free to start.')}</p>
            <button className="pub-btn pub-btn--cta" onClick={() => navigate('/register')}>
              {t('home.v2.ctaButton', "Create a session — it's free")}
            </button>
          </div>
        </section>

        {/* ── footer ── */}
        <footer className="pub-footer">
          <span>© 2026 Swaya.me</span>
          <div className="pub-footer-links">
            <button className="pub-footer-link" onClick={() => navigate('/about')}>{t('pages.legal.aboutLink', 'About')}</button>
            <button className="pub-footer-link" onClick={() => navigate('/privacy-policy')}>{t('pages.legal.privacyLink', 'Privacy')}</button>
            <button className="pub-footer-link" onClick={() => navigate('/terms-of-service')}>{t('pages.legal.termsLink', 'Terms')}</button>
            <a className="pub-footer-link" href="mailto:info@chakrix.net">{t('pages.legal.contactLink', 'Contact')}</a>
          </div>
        </footer>
      </div>
    </div>
  )
}
