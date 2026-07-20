import { useState } from 'react'
import { Input, InputNumber, Button, Divider, Select, Radio, Space, Grid } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import SafeModal from '../../components/SafeModal'

const { useBreakpoint } = Grid
import {
  ThunderboltOutlined,
  BarChartOutlined,
  FileTextOutlined,
  AppstoreOutlined,
  RocketOutlined,
} from '@ant-design/icons'

const INTENTS = [
  {
    key: 'quiz',
    emoji: '⚡',
    labelKey: 'create.energyLabel',
    labelDefault: 'Energy',
    modeKey: 'create.energyMode',
    modeDefault: 'Live Quiz',
    descKey: 'create.energyDesc',
    descDefault: 'Leaderboard, speed points',
    Icon: ThunderboltOutlined,
    accentVar: 'var(--sw-tile-quiz-fg)',
    bgVar: 'var(--sw-tile-quiz-bg)',
  },
  {
    key: 'poll',
    emoji: '🤝',
    labelKey: 'create.honestyLabel',
    labelDefault: 'Honesty',
    modeKey: 'create.honestyMode',
    modeDefault: 'Live Poll',
    descKey: 'create.honestyDesc',
    descDefault: 'Anonymous, word clouds, pulse',
    Icon: BarChartOutlined,
    accentVar: 'var(--sw-tile-poll-fg)',
    bgVar: 'var(--sw-tile-poll-bg)',
  },
  {
    key: 'exam',
    emoji: '🎯',
    labelKey: 'create.itCountsLabel',
    labelDefault: 'It Counts',
    modeKey: 'create.itCountsMode',
    modeDefault: 'Test',
    descKey: 'create.itCountsDesc',
    descDefault: 'Timed, graded, proctored',
    Icon: FileTextOutlined,
    accentVar: 'var(--sw-tile-exam-fg)',
    bgVar: 'var(--sw-tile-exam-bg)',
  },
  {
    key: 'offline_poll',
    emoji: '📋',
    labelKey: 'create.asyncLabel',
    labelDefault: 'Async',
    modeKey: 'create.asyncMode',
    modeDefault: 'Survey',
    descKey: 'create.asyncDesc',
    descDefault: 'Link-based, no live host needed',
    Icon: AppstoreOutlined,
    accentVar: 'var(--sw-tile-opoll-fg)',
    bgVar: 'var(--sw-tile-opoll-bg)',
  },
]

export default function CreateChooser({ open, onClose }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const screens = useBreakpoint()
  const isMobile = !screens.md
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiContentType, setAiContentType] = useState('general')
  const [aiDifficulty, setAiDifficulty] = useState('medium')
  const [aiQuizType, setAiQuizType] = useState('quiz')

  const pick = (type) => {
    onClose()
    navigate(`/quiz/new?type=${type}`)
  }

  const handleGenerate = () => {
    if (!aiPrompt.trim()) return
    onClose()
    const params = new URLSearchParams({
      type: aiQuizType,
      ai_prompt: aiPrompt.trim(),
      ai_content_type: aiContentType,
      ai_difficulty: aiDifficulty,
    })
    navigate(`/quiz/new?${params.toString()}`)
  }

  return (
    <SafeModal
      open={open}
      onCancel={onClose}
      footer={null}
      width={isMobile ? 'calc(100vw - 24px)' : 860}
      borderRadius={20}
    >
      <div style={{ margin: -20, padding: isMobile ? '20px 16px 16px' : '32px 28px 28px' }}>
      <div style={{ textAlign: 'center', marginBottom: isMobile ? 16 : 28 }}>
        <div style={{ fontSize: isMobile ? 17 : 22, fontWeight: 700, color: 'var(--sw-text1)' }}>
          {t('create.intentTitle', 'What does this moment need?')}
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4, 1fr)',
        gap: isMobile ? 10 : 16,
      }}>
        {INTENTS.map(intent => (
          <div
            key={intent.key}
            style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
          >
            <button
              onClick={() => pick(intent.key)}
              style={{
                flex: 1,
                background: intent.bgVar,
                border: '2px solid transparent',
                borderRadius: 16,
                padding: isMobile ? '16px 10px 14px' : '24px 16px 20px',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'border-color 0.15s, transform 0.15s, box-shadow 0.15s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = intent.accentVar
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.10)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'transparent'
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <div style={{ fontSize: isMobile ? 24 : 32, marginBottom: 6 }}>{intent.emoji}</div>
              <div style={{
                fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
                color: intent.accentVar, textTransform: 'uppercase', marginBottom: 3,
              }}>
                {t(intent.labelKey, intent.labelDefault)}
              </div>
              <div style={{ fontSize: isMobile ? 13 : 16, fontWeight: 700, color: 'var(--sw-text1)', marginBottom: isMobile ? 4 : 8 }}>
                {t(intent.modeKey, intent.modeDefault)}
              </div>
              {!isMobile && (
                <div style={{ fontSize: 13, color: 'var(--sw-text3)', lineHeight: 1.5 }}>
                  {t(intent.descKey, intent.descDefault)}
                </div>
              )}
            </button>

          </div>
        ))}
      </div>

      <Divider style={{ margin: '24px 0 20px' }}>
        <span style={{ fontSize: 12, color: 'var(--sw-text3)' }}>
          {t('create.aiOr', 'or let AI draft it')}
        </span>
      </Divider>

      <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: 10, alignItems: 'flex-start' }}>
        <Input.TextArea
          placeholder={t('create.aiPlaceholder', '"10 questions on photosynthesis for class 9, Hindi"')}
          value={aiPrompt}
          onChange={e => setAiPrompt(e.target.value)}
          autoSize={{ minRows: 2, maxRows: 4 }}
          style={{ flex: 1, borderRadius: 10, fontSize: 14, width: '100%' }}
          onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); handleGenerate() } }}
        />
        <div style={{ display: 'flex', flexDirection: isMobile ? 'row' : 'column', flexWrap: isMobile ? 'wrap' : 'nowrap', gap: 6, minWidth: isMobile ? '100%' : 130 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--sw-text3)', whiteSpace: 'nowrap' }}>
              {t('create.aiTypeLabel', 'Type:')}
            </span>
            <Select
              size="small"
              value={aiQuizType}
              onChange={v => setAiQuizType(v)}
              style={{ flex: 1 }}
              options={[
                { value: 'quiz', label: t('quiz.quizTypeLabel', 'Quiz') },
                { value: 'exam', label: t('exam.typeLabel', 'Exam') },
                { value: 'poll', label: t('quiz.poll', 'Poll') },
                { value: 'offline_poll', label: t('offlinePoll.typeLabel', 'Survey') },
              ]}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--sw-text3)', whiteSpace: 'nowrap' }}>
              {t('ai.contentTypeLabel')}:
            </span>
            <Select
              size="small"
              value={aiContentType}
              onChange={v => setAiContentType(v)}
              style={{ flex: 1 }}
              options={[
                { value: 'general', label: t('ai.contentTypeGeneral') },
                { value: 'code', label: t('ai.contentTypeCode') },
                { value: 'sql', label: t('ai.contentTypeSQL') },
                { value: 'math', label: t('ai.contentTypeMath') },
                { value: 'visual', label: t('ai.contentTypeVisual') },
              ]}
            />
          </div>
          {aiQuizType === 'exam' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--sw-text3)', whiteSpace: 'nowrap' }}>
                {t('ai.difficultyLabel')}:
              </span>
              <Select
                size="small"
                value={aiDifficulty}
                onChange={v => setAiDifficulty(v)}
                style={{ flex: 1 }}
                options={[
                  { value: 'easy', label: t('ai.difficultyEasy') },
                  { value: 'medium', label: t('ai.difficultyMedium') },
                  { value: 'hard', label: t('ai.difficultyHard') },
                ]}
              />
            </div>
          )}
          <Button
            type="primary"
            icon={<RocketOutlined />}
            onClick={handleGenerate}
            disabled={!aiPrompt.trim()}
            style={{ borderRadius: 10, fontWeight: 600 }}
          >
            {t('create.aiGenerate', 'Generate')}
          </Button>
        </div>
      </div>
      </div>
    </SafeModal>
  )
}
