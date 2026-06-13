import { useState } from 'react'
import { Modal, Input, InputNumber, Button, Divider } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
    altKey: 'offline_poll',
    altLabelKey: 'create.surveyHint',
    altLabelDefault: 'async? → Survey',
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
]

export default function CreateChooser({ open, onClose }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiCount, setAiCount] = useState(5)

  const pick = (type) => {
    onClose()
    navigate(`/quiz/new?type=${type}`)
  }

  const handleGenerate = () => {
    if (!aiPrompt.trim()) return
    onClose()
    navigate(`/quiz/new?type=quiz&ai_prompt=${encodeURIComponent(aiPrompt.trim())}&ai_count=${aiCount}`)
  }

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      centered
      width={700}
      styles={{
        body: { padding: '32px 28px 28px' },
        content: { borderRadius: 20 },
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--sw-text1)' }}>
          {t('create.intentTitle', 'What does this moment need?')}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16 }}>
        {INTENTS.map(intent => (
          <div
            key={intent.key}
            style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}
          >
            <button
              onClick={() => pick(intent.key)}
              style={{
                flex: 1,
                background: intent.bgVar,
                border: '2px solid transparent',
                borderRadius: 16,
                padding: '24px 16px 20px',
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
              <div style={{ fontSize: 32, marginBottom: 8 }}>{intent.emoji}</div>
              <div style={{
                fontSize: 11, fontWeight: 700, letterSpacing: '0.08em',
                color: intent.accentVar, textTransform: 'uppercase', marginBottom: 4,
              }}>
                {t(intent.labelKey, intent.labelDefault)}
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--sw-text1)', marginBottom: 8 }}>
                {t(intent.modeKey, intent.modeDefault)}
              </div>
              <div style={{ fontSize: 13, color: 'var(--sw-text3)', lineHeight: 1.5 }}>
                {t(intent.descKey, intent.descDefault)}
              </div>
            </button>

            {intent.altKey && (
              <button
                onClick={() => pick(intent.altKey)}
                style={{
                  background: 'none',
                  border: '1px dashed var(--sw-border)',
                  borderRadius: 10,
                  padding: '8px 12px',
                  cursor: 'pointer',
                  fontSize: 12,
                  color: 'var(--sw-text3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  transition: 'color 0.15s, border-color 0.15s',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.color = 'var(--sw-tile-opoll-fg)'
                  e.currentTarget.style.borderColor = 'var(--sw-tile-opoll-fg)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.color = 'var(--sw-text3)'
                  e.currentTarget.style.borderColor = 'var(--sw-border)'
                }}
              >
                <AppstoreOutlined style={{ fontSize: 11 }} />
                {t(intent.altLabelKey, intent.altLabelDefault)}
              </button>
            )}
          </div>
        ))}
      </div>

      <Divider style={{ margin: '24px 0 20px' }}>
        <span style={{ fontSize: 12, color: 'var(--sw-text3)' }}>
          {t('create.aiOr', 'or let AI draft it')}
        </span>
      </Divider>

      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
        <Input.TextArea
          placeholder={t('create.aiPlaceholder', '"10 questions on photosynthesis for class 9, Hindi"')}
          value={aiPrompt}
          onChange={e => setAiPrompt(e.target.value)}
          autoSize={{ minRows: 2, maxRows: 4 }}
          style={{ flex: 1, borderRadius: 10, fontSize: 14 }}
          onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); handleGenerate() } }}
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 120 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 12, color: 'var(--sw-text3)', whiteSpace: 'nowrap' }}>
              {t('create.aiCountLabel', 'Questions:')}
            </span>
            <InputNumber
              min={1} max={50} value={aiCount}
              onChange={v => setAiCount(v || 5)}
              style={{ width: 60 }} size="small"
            />
          </div>
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
    </Modal>
  )
}
