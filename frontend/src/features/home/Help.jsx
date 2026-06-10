import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Layout, Typography, Button, Space, Divider, Row, Col, Card,
  Collapse, Tag, Image,
} from 'antd'
import {
  ArrowLeftOutlined,
  UserOutlined,
  TeamOutlined,
  QuestionCircleOutlined,
  FontSizeOutlined,
  BarChartOutlined,
  EditOutlined,
  AlignLeftOutlined,
  DownOutlined,
  UpOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  TrophyOutlined,
  PieChartOutlined,
  CheckOutlined,
  CloseOutlined,
  BulbOutlined,
  StarOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  FilePptOutlined,
} from '@ant-design/icons'
import logo from '../../assets/logo.png'
import LanguageSwitcher from '../../components/LanguageSwitcher'
import './LegalPage.css'

const { Header, Content, Footer } = Layout
const { Title, Paragraph, Text } = Typography

// ── Non-translated constants ──────────────────────────────────────────────────

const HOST_SCREENSHOTS = [
  '/assets/help-screens/home.png',
  '/assets/help-screens/quiz_builder.png',
  '/assets/help-screens/quiz_session_joincode.png',
  '/assets/help-screens/quiz_session_question_active.png',
  '/assets/help-screens/quiz_history_results.png',
]

const AUDIENCE_SCREENSHOTS = [
  '/assets/help-screens/home.png',
  '/assets/help-screens/audience_join_with_code.png',
  '/assets/help-screens/audience_answering_question.png',
  '/assets/help-screens/audience_in_session_waiting.png',
]

const SCREENSHOT_LANGUAGES = ['en', 'hi', 'ta', 'te', 'ka', 'bn', 'gu', 'es', 'de', 'fr', 'ru']
const SCREENSHOT_ASSET_VERSION = '20260313_fix4'

const QUESTION_TYPE_META = [
  { color: 'blue',   icon: <QuestionCircleOutlined /> },
  { color: 'green',  icon: <FontSizeOutlined /> },
  { color: 'purple', icon: <BarChartOutlined /> },
  { color: 'orange', icon: <EditOutlined /> },
  { color: 'cyan',   icon: <AlignLeftOutlined /> },
]

const POLL_EXAMPLE_META = [
  { color: 'blue',   icon: <QuestionCircleOutlined /> },
  { color: 'green',  icon: <FontSizeOutlined /> },
  { color: 'purple', icon: <BarChartOutlined /> },
  { color: 'cyan',   icon: <AlignLeftOutlined /> },
  { color: 'orange', icon: <EditOutlined /> },
]

const QUIZ_EXAMPLE_ICONS = ['🧠', '📚']

const EXPORT_FORMAT_META = [
  { icon: <FilePdfOutlined   style={{ fontSize: 28, color: '#ff4d4f' }} />, tagColor: 'red',    background: 'var(--visitor-panel-bg)', border: 'var(--visitor-panel-border)', accentColor: '#ff4d4f' },
  { icon: <FileWordOutlined  style={{ fontSize: 28, color: '#1890ff' }} />, tagColor: 'blue',   background: 'var(--visitor-panel-bg)', border: 'var(--visitor-panel-border)', accentColor: '#1890ff' },
  { icon: <FilePptOutlined   style={{ fontSize: 28, color: '#fa8c16' }} />, tagColor: 'orange', background: 'var(--visitor-panel-bg)', border: 'var(--visitor-panel-border)', accentColor: '#fa8c16' },
  { icon: <FileExcelOutlined style={{ fontSize: 28, color: '#52c41a' }} />, tagColor: 'green',  background: 'var(--visitor-panel-bg)', border: 'var(--visitor-panel-border)', accentColor: '#52c41a' },
]

// ── Sub-components ────────────────────────────────────────────────────────────

function DrillDown({ screenshot, screenshotFallback, screenshotAlt, tips, accentColor }) {
  const { t } = useTranslation()
  return (
    <div
      style={{
        marginTop: 12,
        borderLeft: `3px solid ${accentColor}`,
        paddingLeft: 16,
        background: 'var(--visitor-panel-bg)',
        borderRadius: '0 8px 8px 0',
        padding: '16px 16px 16px 20px',
      }}
    >
      <Row gutter={[24, 16]} align="top">
        <Col xs={24} md={12}>
          <Text strong style={{ display: 'block', marginBottom: 10, color: accentColor }}>
            <CameraOutlined style={{ marginRight: 6 }} />
            {t('pages.help.whatItLooksLike')}
          </Text>
          <Image
            src={screenshot}
            fallback={screenshotFallback}
            alt={screenshotAlt}
            style={{ width: '100%', borderRadius: 8, border: '1px solid var(--visitor-panel-border)', cursor: 'zoom-in' }}
            preview={{ mask: t('pages.help.clickToZoom') }}
          />
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 6, textAlign: 'center' }}>
            {screenshotAlt}
          </Text>
        </Col>
        <Col xs={24} md={12}>
          <Text strong style={{ display: 'block', marginBottom: 10, color: accentColor }}>
            <CheckCircleOutlined style={{ marginRight: 6 }} />
            {t('pages.help.stepByStep')}
          </Text>
          <ol style={{ paddingLeft: 20, margin: 0 }}>
            {tips.map((tip, i) => (
              <li key={i} style={{ marginBottom: 8 }}>
                <Text>{tip}</Text>
              </li>
            ))}
          </ol>
        </Col>
      </Row>
    </div>
  )
}

function DetailedSteps({ steps, details, accentColor }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState({})
  const toggle = (i) => setExpanded((s) => ({ ...s, [i]: !s[i] }))

  return (
    <div>
      {steps.map((step, i) => (
        <div key={i} style={{ display: 'flex', gap: 16, marginBottom: expanded[i] ? 24 : 16 }}>
          <div style={{ flexShrink: 0 }}>
            <div
              style={{
                background: accentColor,
                color: '#fff',
                borderRadius: '50%',
                width: 32,
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 14,
                fontWeight: 700,
                marginTop: 2,
              }}
            >
              {i + 1}
            </div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <Text strong style={{ fontSize: 15 }}>{step.title}</Text>
              <Button
                type="link"
                size="small"
                icon={expanded[i] ? <UpOutlined /> : <DownOutlined />}
                onClick={() => toggle(i)}
                style={{ padding: 0, fontSize: 12, color: accentColor }}
              >
                {expanded[i] ? t('pages.help.hideDetails') : t('pages.help.showMeHow')}
              </Button>
            </div>
            <Paragraph type="secondary" style={{ marginBottom: 6, marginTop: 4 }}>
              {step.description}
            </Paragraph>
            {expanded[i] && details[i] && (
              <DrillDown
                screenshot={details[i].screenshot}
                screenshotFallback={details[i].screenshotFallback}
                screenshotAlt={details[i].screenshotAlt}
                tips={details[i].tips}
                accentColor={accentColor}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function MCQCard({ text, options, correct, tip, isQuiz }) {
  return (
    <Card
      size="small"
      bordered={false}
      style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', borderRadius: 8, marginBottom: 12 }}
    >
      <Text strong style={{ display: 'block', marginBottom: 10, fontSize: 14 }}>❓ {text}</Text>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: tip ? 12 : 0 }}>
        {options.map((opt, i) => {
          const isCorrect = isQuiz && i === correct
          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 10px',
                borderRadius: 6,
                background: isCorrect ? 'var(--visitor-header-bg)' : 'var(--visitor-panel-bg)',
                border: '1px solid var(--visitor-panel-border)',
              }}
            >
              <Text style={{ color: 'var(--visitor-text-secondary)', fontWeight: 500, minWidth: 20 }}>
                {String.fromCharCode(65 + i)}.
              </Text>
              <Text style={{ flex: 1 }}>{opt}</Text>
              {isCorrect && <CheckOutlined style={{ color: '#52c41a', fontWeight: 700 }} />}
              {isQuiz && !isCorrect && <CloseOutlined style={{ color: '#d9d9d9', fontSize: 11 }} />}
            </div>
          )
        })}
      </div>
      {tip && (
        <div style={{ borderTop: '1px dashed var(--visitor-panel-border)', paddingTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <BulbOutlined style={{ marginRight: 4, color: '#faad14' }} />
            {tip}
          </Text>
        </div>
      )}
    </Card>
  )
}

function CollapsibleGroup({ buttonStyle, buttonContent, children }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  return (
    <div style={{ marginBottom: 16 }}>
      <Button
        block
        style={{ textAlign: 'left', marginBottom: open ? 8 : 0, ...buttonStyle }}
        onClick={() => setOpen(!open)}
      >
        {buttonContent}
        <Text type="secondary" style={{ float: 'right', fontSize: 12 }}>
          {open ? t('pages.help.hideLabel') : t('pages.help.showExamplesLabel')}
        </Text>
      </Button>
      {open && children}
    </div>
  )
}

function OpenQuestionCard({ text, tip }) {
  return (
    <Card
      size="small"
      bordered={false}
      style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', borderRadius: 8, marginBottom: 12 }}
    >
      <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 14 }}>❓ {text}</Text>
      {tip && (
        <div style={{ borderTop: '1px dashed var(--visitor-panel-border)', paddingTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <BulbOutlined style={{ marginRight: 4, color: '#faad14' }} />
            {tip}
          </Text>
        </div>
      )}
    </Card>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Help() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const [expandedQTypes, setExpandedQTypes] = useState({})
  const toggleQType = (key) => setExpandedQTypes((s) => ({ ...s, [key]: !s[key] }))

  const normalizedLanguage = (i18n.resolvedLanguage || i18n.language || 'en').split('-')[0]
  const screenshotLanguage = SCREENSHOT_LANGUAGES.includes(normalizedLanguage) ? normalizedLanguage : 'en'
  const getScreenshotPath = (sourcePath) => {
    const fileName = sourcePath.split('/').pop()
    return `/assets/help-screens/${screenshotLanguage}/light/${fileName}?v=${SCREENSHOT_ASSET_VERSION}`
  }

  // Load translated data arrays
  const hostSteps        = t('pages.help.hostSteps',          { returnObjects: true })
  const hostDetailsRaw   = t('pages.help.hostDetails',         { returnObjects: true })
  const audienceSteps    = t('pages.help.audienceSteps',       { returnObjects: true })
  const audienceDetailsRaw = t('pages.help.audienceDetails',   { returnObjects: true })
  const questionTypesRaw = t('pages.help.questionTypes',       { returnObjects: true })
  const comparison       = t('pages.help.quizVsPollComparison',{ returnObjects: true })
  const quizExamplesRaw  = t('pages.help.quizExamples',        { returnObjects: true })
  const pollExamplesRaw  = t('pages.help.pollExamples',        { returnObjects: true })
  const exportFormatsRaw = t('pages.help.exportFormats',       { returnObjects: true })
  const faqData          = t('pages.help.faqItems',            { returnObjects: true })
  const howToCreateTips  = t('pages.help.howToCreateTips',     { returnObjects: true })
  const exportHistoryTips = t('pages.help.exportHistoryTips',  { returnObjects: true })
  const recentUpdates    = t('pages.help.recentUpdates.items', { returnObjects: true })

  // Merge translated content with non-translated metadata
  const hostDetails = hostDetailsRaw.map((d, i) => ({
    ...d,
    screenshot: getScreenshotPath(HOST_SCREENSHOTS[i]),
    screenshotFallback: HOST_SCREENSHOTS[i],
  }))
  const audienceDetails = audienceDetailsRaw.map((d, i) => ({
    ...d,
    screenshot: getScreenshotPath(AUDIENCE_SCREENSHOTS[i]),
    screenshotFallback: AUDIENCE_SCREENSHOTS[i],
  }))
  const questionTypes = questionTypesRaw.map((qt, i) => ({ ...qt, ...QUESTION_TYPE_META[i] }))
  const quizExamples = quizExamplesRaw.map((ex, i) => ({ ...ex, icon: QUIZ_EXAMPLE_ICONS[i] }))
  const pollExamples = pollExamplesRaw.map((ex, i) => ({ ...ex, ...POLL_EXAMPLE_META[i] }))
  const exportFormats = exportFormatsRaw.map((fmt, i) => ({ ...fmt, ...EXPORT_FORMAT_META[i] }))

  const faqItems = faqData.map((item, idx) => ({
    key: String(idx + 1),
    label: item.question,
    children: <Paragraph style={{ marginBottom: 0 }}>{item.answer}</Paragraph>,
  }))

  return (
    <Layout className="legal-layout">
      <Header className="legal-header">
        <div className="legal-header-content">
          <div
            className="legal-logo"
            onClick={() => navigate('/')}
            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}
          >
            <img src={logo} alt="Swaya.me" style={{ height: 32, objectFit: 'contain', borderRadius: 4 }} />
            <Text strong style={{ fontSize: 18 }}>Swaya.me</Text>
          </div>
          <Space size="middle">
            <LanguageSwitcher />
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>{t('pages.help.backToHome')}</Button>
          </Space>
        </div>
      </Header>

      <Content className="legal-content">
        <div className="legal-body">

          {/* Hero */}
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <img src={logo} alt="Swaya.me" style={{ height: 80, objectFit: 'contain', borderRadius: 12, marginBottom: 16 }} />
            <Title level={1} style={{ marginBottom: 8 }}>{t('pages.help.heroTitle')}</Title>
            <Paragraph style={{ fontSize: 18, maxWidth: 640, margin: '0 auto' }}>
              {t('pages.help.heroSubtitle')}
            </Paragraph>
            <Paragraph type="secondary" style={{ marginTop: 8 }}>
              {t('pages.help.heroNote')}{' '}
              <Text code>{t('pages.help.heroNoteCode')}</Text>
              {' '}{t('pages.help.heroNoteEnd')}
            </Paragraph>
          </div>

          <Divider />

          {/* Recent updates */}
          <Card bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', marginBottom: 32 }}>
            <Title level={3} style={{ marginBottom: 8 }}>{t('pages.help.recentUpdates.title')}</Title>
            <Paragraph type="secondary" style={{ marginBottom: 12 }}>
              {t('pages.help.recentUpdates.subtitle')}
            </Paragraph>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {(recentUpdates || []).map((item, idx) => (
                <li key={idx} style={{ marginBottom: 6 }}>
                  <Text>{item}</Text>
                </li>
              ))}
            </ul>
          </Card>

          {/* Quick Nav */}
          <Row gutter={[24, 24]} style={{ marginBottom: 48 }}>
            <Col xs={12} sm={6}>
              <Card className="help-quick-nav-card" bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', textAlign: 'center', height: '100%' }}>
                <Space className="help-quick-nav-stack" direction="vertical" size={12}>
                  <UserOutlined style={{ fontSize: 36, color: '#1890ff' }} />
                  <Title level={4} style={{ marginBottom: 4 }}>{t('pages.help.navHostTitle')}</Title>
                  <Paragraph type="secondary" style={{ marginBottom: 8 }}>{t('pages.help.navHostDesc')}</Paragraph>
                  <Button onClick={() => document.getElementById('hosts').scrollIntoView({ behavior: 'smooth' })}>
                    {t('pages.help.navHostButton')}
                  </Button>
                </Space>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="help-quick-nav-card" bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', textAlign: 'center', height: '100%' }}>
                <Space className="help-quick-nav-stack" direction="vertical" size={12}>
                  <TeamOutlined style={{ fontSize: 36, color: '#52c41a' }} />
                  <Title level={4} style={{ marginBottom: 4 }}>{t('pages.help.navParticipantTitle')}</Title>
                  <Paragraph type="secondary" style={{ marginBottom: 8 }}>{t('pages.help.navParticipantDesc')}</Paragraph>
                  <Button onClick={() => document.getElementById('audience').scrollIntoView({ behavior: 'smooth' })}>
                    {t('pages.help.navParticipantButton')}
                  </Button>
                </Space>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="help-quick-nav-card" bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', textAlign: 'center', height: '100%' }}>
                <Space className="help-quick-nav-stack" direction="vertical" size={12}>
                  <PieChartOutlined style={{ fontSize: 36, color: '#722ed1' }} />
                  <Title level={4} style={{ marginBottom: 4 }}>{t('pages.help.navQuizVsPollTitle')}</Title>
                  <Paragraph type="secondary" style={{ marginBottom: 8 }}>{t('pages.help.navQuizVsPollDesc')}</Paragraph>
                  <Button onClick={() => document.getElementById('quiz-vs-poll').scrollIntoView({ behavior: 'smooth' })}>
                    {t('pages.help.navQuizVsPollButton')}
                  </Button>
                </Space>
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card className="help-quick-nav-card" bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', textAlign: 'center', height: '100%' }}>
                <Space className="help-quick-nav-stack" direction="vertical" size={12}>
                  <DownloadOutlined style={{ fontSize: 36, color: '#389e0d' }} />
                  <Title level={4} style={{ marginBottom: 4 }}>{t('pages.help.navExportTitle')}</Title>
                  <Paragraph type="secondary" style={{ marginBottom: 8 }}>{t('pages.help.navExportDesc')}</Paragraph>
                  <Button onClick={() => document.getElementById('export').scrollIntoView({ behavior: 'smooth' })}>
                    {t('pages.help.navExportButton')}
                  </Button>
                </Space>
              </Card>
            </Col>
          </Row>

          <Divider />

          {/* For Hosts */}
          <div id="hosts" style={{ scrollMarginTop: 80 }}>
            <Title level={2}>
              <UserOutlined style={{ marginRight: 10, color: '#1890ff' }} />
              {t('pages.help.hostsTitle')}
            </Title>
            <Paragraph>
              {t('pages.help.hostsIntro')}{' '}
              <Text strong style={{ color: '#1890ff' }}>{t('pages.help.hostsIntroStrong')}</Text>
              {' '}{t('pages.help.hostsIntroEnd')}
            </Paragraph>
            <DetailedSteps steps={hostSteps} details={hostDetails} accentColor="#1890ff" />
          </div>

          <Divider />

          {/* For Audience */}
          <div id="audience" style={{ scrollMarginTop: 80 }}>
            <Title level={2}>
              <TeamOutlined style={{ marginRight: 10, color: '#52c41a' }} />
              {t('pages.help.audienceTitle')}
            </Title>
            <Paragraph>
              {t('pages.help.audienceIntro')}{' '}
              <Text strong style={{ color: '#52c41a' }}>{t('pages.help.audienceIntroStrong')}</Text>
              {' '}{t('pages.help.audienceIntroEnd')}
            </Paragraph>
            <DetailedSteps steps={audienceSteps} details={audienceDetails} accentColor="#52c41a" />
          </div>

          <Divider />

          {/* Question Types */}
          <div id="question-types" style={{ scrollMarginTop: 80 }}>
            <Title level={2}>{t('pages.help.questionTypesTitle')}</Title>
            <Paragraph>{t('pages.help.questionTypesIntro')}</Paragraph>
            <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
              {questionTypes.map((qt) => (
                <Col xs={24} sm={12} md={8} key={qt.type}>
                  <Card
                    bordered={false}
                    style={{
                      background: expandedQTypes[qt.type] ? 'var(--visitor-header-bg)' : 'var(--visitor-panel-bg)',
                      height: '100%',
                      cursor: 'pointer',
                      transition: 'background 0.2s',
                    }}
                    onClick={() => toggleQType(qt.type)}
                  >
                    <Space align="start" style={{ marginBottom: 8 }}>
                      <Tag color={qt.color} icon={qt.icon}>{qt.type}</Tag>
                    </Space>
                    <Paragraph type="secondary" style={{ marginBottom: expandedQTypes[qt.type] ? 12 : 0 }}>
                      {qt.summary}
                    </Paragraph>
                    {expandedQTypes[qt.type] && (
                      <Paragraph style={{ marginBottom: 0, fontSize: 13, borderTop: '1px solid var(--visitor-panel-border)', paddingTop: 10 }}>
                        {qt.detail}
                      </Paragraph>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {expandedQTypes[qt.type] ? t('pages.help.lessLabel') : t('pages.help.moreLabel')}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>

          <Divider />

          {/* Quiz vs Poll */}
          <div id="quiz-vs-poll" style={{ scrollMarginTop: 80 }}>
            <Title level={2}>
              <PieChartOutlined style={{ marginRight: 10, color: '#722ed1' }} />
              {t('pages.help.quizVsPollTitle')}
            </Title>
            <Paragraph>
              {t('pages.help.quizVsPollIntro1')}{' '}
              <Text strong>{t('pages.help.quizVsPollQuiz')}</Text>
              {' '}{t('pages.help.quizVsPollAnd')}{' '}
              <Text strong>{t('pages.help.quizVsPollPoll')}</Text>
              {t('pages.help.quizVsPollIntro2')}{' '}
              <Text strong style={{ color: '#1890ff' }}>{t('pages.help.quizVsPollKeyDiff')}</Text>
              {t('pages.help.quizVsPollIntro3')}
            </Paragraph>

            {/* Comparison cards */}
            <Row gutter={[16, 0]} style={{ marginBottom: 32 }}>
              <Col xs={24} md={12}>
                <Card bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', borderTop: '4px solid #1890ff', height: '100%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <TrophyOutlined style={{ fontSize: 28, color: '#1890ff' }} />
                    <Title level={3} style={{ margin: 0, color: '#1890ff' }}>{t('pages.help.quizVsPollQuiz')}</Title>
                    <Tag color="blue">{t('pages.help.quizTagScored')}</Tag>
                  </div>
                  {comparison.map((row) => (
                    <div key={row.aspect} style={{
                      marginBottom: 10,
                      ...(row.highlight ? { background: 'var(--visitor-header-bg)', borderRadius: 6, padding: '8px 10px', marginLeft: -10, marginRight: -10 } : {}),
                    }}>
                      <Text type="secondary" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>
                        {row.highlight
                          ? <Text strong style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--visitor-accent-strong)' }}>⭐ {row.aspect}</Text>
                          : row.aspect}
                      </Text>
                      <div><Text strong={row.highlight}>{row.quiz}</Text></div>
                    </div>
                  ))}
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', borderTop: '4px solid #722ed1', height: '100%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                    <PieChartOutlined style={{ fontSize: 28, color: '#722ed1' }} />
                    <Title level={3} style={{ margin: 0, color: '#722ed1' }}>{t('pages.help.quizVsPollPoll')}</Title>
                    <Tag color="purple">{t('pages.help.pollTagNoScoring')}</Tag>
                  </div>
                  {comparison.map((row) => (
                    <div key={row.aspect} style={{
                      marginBottom: 10,
                      ...(row.highlight ? { background: 'var(--visitor-header-bg)', borderRadius: 6, padding: '8px 10px', marginLeft: -10, marginRight: -10 } : {}),
                    }}>
                      <Text type="secondary" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 }}>
                        {row.highlight
                          ? <Text strong style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--visitor-accent-strong)' }}>⭐ {row.aspect}</Text>
                          : row.aspect}
                      </Text>
                      <div><Text strong={row.highlight}>{row.poll}</Text></div>
                    </div>
                  ))}
                </Card>
              </Col>
            </Row>

            {/* Leaderboard hero */}
            <Card
              bordered={false}
              style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', marginBottom: 32 }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <TrophyOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                <Title level={3} style={{ margin: 0, color: '#1890ff' }}>{t('pages.help.leaderboardTitle')}</Title>
              </div>
              <Paragraph style={{ marginBottom: 16 }}>
                {t('pages.help.leaderboardIntro')}{' '}
                <Text strong>{t('pages.help.leaderboardIntroStrong1')}</Text>
                {' '}{t('pages.help.leaderboardIntroMiddle')}{' '}
                <Text strong>{t('pages.help.leaderboardIntroStrong2')}</Text>
                {t('pages.help.leaderboardIntroEnd')}
              </Paragraph>
              <Row gutter={[24, 16]}>
                <Col xs={24} md={12}>
                  <Text strong style={{ display: 'block', marginBottom: 10, color: '#1890ff' }}>
                    <CameraOutlined style={{ marginRight: 6 }} />{t('pages.help.leaderboardHowItLooks')}
                  </Text>
                  <Image
                    src={getScreenshotPath('/assets/help-screens/quiz_leaderboard_host.png')}
                    fallback="/assets/help-screens/quiz_leaderboard_host.png"
                    alt="Live leaderboard showing participant rankings"
                    style={{ width: '100%', borderRadius: 8, border: '1px solid var(--visitor-panel-border)', cursor: 'zoom-in' }}
                    preview={{ mask: t('pages.help.clickToZoom') }}
                  />
                </Col>
                <Col xs={24} md={12}>
                  <Text strong style={{ display: 'block', marginBottom: 10, color: '#1890ff' }}>
                    <CheckCircleOutlined style={{ marginRight: 6 }} />{t('pages.help.leaderboardHowRankingWorks')}
                  </Text>
                  <ol style={{ paddingLeft: 20, margin: 0 }}>
                    <li style={{ marginBottom: 10 }}>
                      <Text strong>{t('pages.help.leaderboardRank1Strong')}</Text>
                      <Text type="secondary">{t('pages.help.leaderboardRank1Text')}</Text>
                    </li>
                    <li style={{ marginBottom: 10 }}>
                      <Text strong>{t('pages.help.leaderboardRank2Strong')}</Text>
                      <Text type="secondary">{t('pages.help.leaderboardRank2Text')}</Text>
                    </li>
                    <li style={{ marginBottom: 10 }}>
                      <Text strong>{t('pages.help.leaderboardRank3Strong')}</Text>
                      <Text type="secondary">{t('pages.help.leaderboardRank3Text')}</Text>
                    </li>
                    <li style={{ marginBottom: 0 }}>
                      <Text strong>{t('pages.help.leaderboardRank4Strong')}</Text>
                      <Text type="secondary">{t('pages.help.leaderboardRank4Text')}</Text>
                    </li>
                  </ol>
                </Col>
              </Row>
              <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--visitor-header-bg)', borderRadius: 6, border: '1px solid var(--visitor-panel-border)' }}>
                <Text>
                  <Text strong>{t('pages.help.pollNoLeaderboardStrong')}</Text>
                  {t('pages.help.pollNoLeaderboardText')}
                </Text>
              </div>
            </Card>

            {/* How to create */}
            <Title level={3}>{t('pages.help.howToCreateTitle')}</Title>
            <Paragraph>
              {t('pages.help.howToCreateIntro')}{' '}
              <Text code>{t('pages.help.howToCreateNewQuiz')}</Text>
              {' '}{t('pages.help.howToCreateAnd')}{' '}
              <Text code>{t('pages.help.howToCreatePoll')}</Text>
              {t('pages.help.howToCreateEnd')}
            </Paragraph>
            <DrillDown
              screenshot={getScreenshotPath('/assets/help-screens/dashboard_buttons.png')}
              screenshotFallback="/assets/help-screens/dashboard_buttons.png"
              screenshotAlt={t('pages.help.howToCreateDrilldownAlt')}
              tips={howToCreateTips}
              accentColor="#722ed1"
            />

            <Divider dashed style={{ margin: '32px 0' }} />

            {/* Quiz examples */}
            <Title level={3}>
              <TrophyOutlined style={{ marginRight: 8, color: '#1890ff' }} />
              {t('pages.help.exampleQuizTitle')}
            </Title>
            <Paragraph>{t('pages.help.exampleQuizIntro')}</Paragraph>
            {quizExamples.map((group) => (
              <CollapsibleGroup
                key={group.label}
                buttonStyle={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)' }}
                buttonContent={<><span style={{ marginRight: 8 }}>{group.icon}</span><Text strong>{group.label}</Text></>}
              >
                {group.questions.map((q, i) => (
                  <MCQCard key={i} {...q} isQuiz={true} />
                ))}
              </CollapsibleGroup>
            ))}

            <Divider dashed style={{ margin: '32px 0' }} />

            {/* Poll examples */}
            <Title level={3}>
              <PieChartOutlined style={{ marginRight: 8, color: '#722ed1' }} />
              {t('pages.help.examplePollTitle')}
            </Title>
            <Paragraph>{t('pages.help.examplePollIntro')}</Paragraph>
            {pollExamples.map((group) => (
              <CollapsibleGroup
                key={group.type}
                buttonStyle={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)' }}
                buttonContent={<><Tag color={group.color} icon={group.icon}>{group.type}</Tag><Text style={{ marginLeft: 4 }}>{group.label}</Text></>}
              >
                {group.questions.map((q, i) =>
                  q.options
                    ? <MCQCard key={i} text={q.text} options={q.options} tip={q.tip} isQuiz={false} />
                    : <OpenQuestionCard key={i} text={q.text} tip={q.tip} />
                )}
              </CollapsibleGroup>
            ))}

            {/* Quick rule */}
            <Card bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', marginTop: 24 }}>
              <Space align="start">
                <StarOutlined style={{ fontSize: 20, color: '#faad14', marginTop: 2 }} />
                <div>
                  <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 15 }}>{t('pages.help.quickRuleTitle')}</Text>
                  <Space direction="vertical" size={6}>
                    <Text>
                      <TrophyOutlined style={{ color: '#1890ff', marginRight: 6 }} />
                      {t('pages.help.quickRuleQuiz')}{' '}
                      <Text strong>{t('pages.help.quickRuleQuizStrong')}</Text>
                      {' '}{t('pages.help.quickRuleQuizMid')}{' '}
                      <Text strong style={{ color: '#1890ff' }}>{t('pages.help.quickRuleQuizEnd')}</Text>.
                    </Text>
                    <Text>
                      <PieChartOutlined style={{ color: '#722ed1', marginRight: 6 }} />
                      {t('pages.help.quickRulePoll')}{' '}
                      <Text strong>{t('pages.help.quickRulePollStrong')}</Text>
                      {' '}{t('pages.help.quickRulePollMid')}{' '}
                      <Text strong style={{ color: '#722ed1' }}>{t('pages.help.quickRulePollEnd')}</Text>.
                    </Text>
                  </Space>
                </div>
              </Space>
            </Card>
          </div>

          <Divider />

          {/* Export Results */}
          <div id="export" style={{ scrollMarginTop: 80 }}>
            <Title level={2}>
              <DownloadOutlined style={{ marginRight: 10, color: '#389e0d' }} />
              {t('pages.help.exportTitle')}
            </Title>
            <Paragraph>{t('pages.help.exportIntro')}</Paragraph>

            <Title level={3} style={{ marginTop: 24 }}>{t('pages.help.exportAccessTitle')}</Title>
            <Paragraph>
              {t('pages.help.exportAccessIntro')}{' '}
              <Text strong>{t('pages.help.exportAccessHistory')}</Text>
              {t('pages.help.exportAccessMid')}{' '}
              <Text strong>{t('pages.help.exportAccessExport')}</Text>
              {' '}{t('pages.help.exportAccessEnd')}
            </Paragraph>

            <DrillDown
              screenshot={getScreenshotPath('/assets/help-screens/quiz_history_page.png')}
              screenshotFallback="/assets/help-screens/quiz_history_page.png"
              screenshotAlt={t('pages.help.exportHistoryAlt')}
              tips={exportHistoryTips}
              accentColor="#389e0d"
            />

            <div style={{ marginBottom: 32 }}>
              <Text strong style={{ display: 'block', marginBottom: 8, color: '#389e0d' }}>
                <CameraOutlined style={{ marginRight: 6 }} />{t('pages.help.exportDropdownLabel')}
              </Text>
              <Image
                src={getScreenshotPath('/assets/help-screens/quiz_export_dropdown.png')}
                fallback="/assets/help-screens/quiz_export_dropdown.png"
                alt={t('pages.help.exportDropdownAlt')}
                style={{ maxWidth: 600, width: '100%', borderRadius: 8, border: '1px solid var(--visitor-panel-border)' }}
                preview={{ mask: t('pages.help.clickToZoom') }}
              />
            </div>

            <Title level={3}>{t('pages.help.exportFormatComparisonTitle')}</Title>
            <Row gutter={[20, 20]} style={{ marginBottom: 32 }}>
              {exportFormats.map((fmt) => (
                <Col xs={24} sm={12} key={fmt.key}>
                  <Card
                    bordered={false}
                    style={{
                      background: fmt.background,
                      border: `1px solid ${fmt.border}`,
                      borderTop: `4px solid ${fmt.accentColor}`,
                      height: '100%',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                      {fmt.icon}
                      <div>
                        <Title level={4} style={{ margin: 0, color: fmt.accentColor }}>{fmt.label}</Title>
                        <Tag color={fmt.tagColor} style={{ marginTop: 4 }}>.{fmt.key}</Tag>
                      </div>
                    </div>
                    <Paragraph type="secondary" style={{ marginBottom: 12, fontStyle: 'italic' }}>
                      {fmt.useCase}
                    </Paragraph>
                    <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 13 }}>{t('pages.help.exportWhatsIncluded')}</Text>
                    <ul style={{ paddingLeft: 18, margin: 0 }}>
                      {fmt.includes.map((item, i) => (
                        <li key={i} style={{ marginBottom: 6 }}>
                          <Text style={{ fontSize: 13 }}>{item}</Text>
                        </li>
                      ))}
                    </ul>
                  </Card>
                </Col>
              ))}
            </Row>

            <Card bordered={false} style={{ background: 'var(--visitor-panel-bg)', border: '1px solid var(--visitor-panel-border)', marginBottom: 8 }}>
              <Space align="start">
                <BulbOutlined style={{ fontSize: 18, color: '#faad14', marginTop: 2 }} />
                <div>
                  <Text strong style={{ display: 'block', marginBottom: 4 }}>{t('pages.help.exportWhichFormatTitle')}</Text>
                  <Space direction="vertical" size={4}>
                    <Text><Text strong style={{ color: '#ff4d4f' }}>PDF</Text> {t('pages.help.exportWhichPdf')}</Text>
                    <Text><Text strong style={{ color: '#1890ff' }}>Word</Text> {t('pages.help.exportWhichWord')}</Text>
                    <Text><Text strong style={{ color: '#fa8c16' }}>PowerPoint</Text> {t('pages.help.exportWhichPowerPoint')}</Text>
                    <Text><Text strong style={{ color: '#52c41a' }}>Excel</Text> {t('pages.help.exportWhichExcel')}</Text>
                  </Space>
                </div>
              </Space>
            </Card>
          </div>

          <Divider />

          {/* FAQ */}
          <div id="faq" style={{ scrollMarginTop: 80 }}>
            <Title level={2}>
              <QuestionCircleOutlined style={{ marginRight: 10, color: '#722ed1' }} />
              {t('pages.help.faqTitle')}
            </Title>
            <Collapse accordion items={faqItems} style={{ marginBottom: 32 }} />
          </div>

          <Divider />

          {/* Contact */}
          <Title level={2}>{t('pages.help.contactTitle')}</Title>
          <Paragraph>
            {t('pages.help.contactText')}{' '}
            <a href="mailto:info@chakrix.net">info@chakrix.net</a>
          </Paragraph>

        </div>
      </Content>

      <Footer className="legal-footer">
        <Space direction="vertical" size={8} style={{ width: '100%', alignItems: 'center' }}>
          <Text type="secondary">{t('pages.help.footerRights')}</Text>
          <Space split={<Divider type="vertical" />} wrap>
            <a onClick={() => navigate('/about')}>{t('pages.help.footerAbout')}</a>
            <a onClick={() => navigate('/privacy-policy')}>{t('pages.help.footerPrivacy')}</a>
            <a onClick={() => navigate('/terms-of-service')}>{t('pages.help.footerTerms')}</a>
            <a onClick={() => navigate('/help')}>{t('pages.help.footerHelp')}</a>
            <a href="mailto:info@chakrix.net">{t('pages.help.footerContact')}</a>
          </Space>
        </Space>
      </Footer>
    </Layout>
  )
}
